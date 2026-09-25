#!/usr/bin/env python3
"""
make.py â€” Build script for the wellbeing trajectory project.

Usage:
  python make.py all              # rebuild everything (UK + England, all levels)
  python make.py clean            # delete all outputs
  python make.py status           # show what outputs exist
  python make.py supergroup       # just supergroup level (UK + England)
  python make.py group            # just group level
  python make.py tables           # trajectory tables only, all levels
  python make.py maps             # maps only, all levels
  python make.py maps-england     # England-only maps
  python make.py nations          # national comparison
  python make.py curated          # export curated datasets
  python make.py robustness       # run all robustness checks
"""

import argparse
import os
import shutil
import subprocess
import sys

OUTPUT_DIR = "output"
LEVELS = ['supergroup', 'group', 'subgroup']


def run(cmd):
    """Run a command and print it."""
    print(f"\n>>> {cmd}")
    result = subprocess.run(cmd, shell=True)
    if result.returncode != 0:
        print(f"  FAILED (exit code {result.returncode})")
    return result.returncode == 0


def clean():
    """Delete all output directories."""
    if os.path.exists(OUTPUT_DIR):
        shutil.rmtree(OUTPUT_DIR)
        print(f"Cleaned: {OUTPUT_DIR}/")
    else:
        print("Nothing to clean.")


def status():
    """Show what output files exist."""
    if not os.path.exists(OUTPUT_DIR):
        print("No outputs yet.")
        return

    for root, dirs, files in os.walk(OUTPUT_DIR):
        level = root.replace(OUTPUT_DIR, '').lstrip(os.sep)
        if files:
            print(f"\n{level or 'output'}/ ({len(files)} files)")
            for f in sorted(files):
                size = os.path.getsize(os.path.join(root, f)) / 1024
                print(f"  {f:45s} {size:8.1f} KB")


def build_tables(levels=None, england_only=False):
    """Run main.py for specified levels."""
    if levels is None:
        levels = LEVELS
    for level in levels:
        cmd = f"python main.py --level {level}"
        if england_only:
            cmd += " --england-only"
        run(cmd)


def build_maps(levels=None, england_only=False):
    """Run maps.py for specified levels."""
    if levels is None:
        levels = LEVELS
    for level in levels:
        cmd = f"python maps.py --level {level}"
        if england_only:
            cmd += " --england-only"
        run(cmd)


def build_all():
    """Build everything."""
    # Full UK
    build_tables()
    build_maps()

    # England only
    build_tables(levels=['supergroup', 'group'], england_only=True)
    build_maps(levels=['supergroup'], england_only=True)


def build_level(level):
    """Build everything for one level."""
    run(f"python main.py --level {level}")
    run(f"python maps.py --level {level}")
    run(f"python main.py --level {level} --england-only")
    run(f"python maps.py --level {level} --england-only")


def build_curated():
    """Export curated datasets for distribution."""
    run("python export_curated.py")


def build_nations():
    """Run national comparison analysis."""
    import os
    os.makedirs(os.path.join(OUTPUT_DIR, 'nations'), exist_ok=True)
    
    # Run and capture output
    import subprocess
    result = subprocess.run(
        "python compare_nations.py",
        shell=True,
        capture_output=True,
        text=True
    )
    
    # Save to file
    report_path = os.path.join(OUTPUT_DIR, 'nations', 'report.txt')
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(result.stdout)
        if result.stderr:
            f.write("\n\nERRORS:\n")
            f.write(result.stderr)
    
    print(f"Saved: {report_path}")
    return result.returncode == 0


def build_robustness():
    """Run all robustness checks and create summary report."""
    import os
    import pandas as pd
    import shutil
    
    rob_dir = os.path.join(OUTPUT_DIR, 'robustness')
    
    # Clean robustness directory first
    if os.path.exists(rob_dir):
        shutil.rmtree(rob_dir)
    os.makedirs(rob_dir, exist_ok=True)
    
    print("\n" + "=" * 70)
    print("RUNNING ROBUSTNESS CHECKS")
    print("=" * 70)
    
    # Define specifications
    specs = [
        {'name': 'main', 'flags': '', 'desc': 'WLS+HAC (main)', 'dir': 'main'},
        {'name': 'wls', 'flags': '--no-hac', 'desc': 'WLS (no HAC)', 'dir': 'wls'},
        {'name': 'ols_hac', 'flags': '--no-weighting', 'desc': 'OLS+HAC', 'dir': 'ols_hac'},
        {'name': 'ols', 'flags': '--no-weighting --no-hac', 'desc': 'OLS (no cluster)', 'dir': 'ols'},
        {'name': 'precovid', 'flags': '--pre-covid', 'desc': 'WLS+HAC pre-COVID', 'dir': 'precovid'},
    ]
    
    levels = ['supergroup']  # Just supergroup for robustness (faster)
    
    # Run all combinations
    results = []
    
    for spec in specs:
        for level in levels:
            spec_dir = os.path.join(rob_dir, spec['dir'], level, 'tables')
            os.makedirs(spec_dir, exist_ok=True)
            
            print(f"\n>>> {level} - {spec['desc']}")
            
            # Run with custom output directory
            cmd = f"python main.py --level {level} {spec['flags']}"
            success = run(cmd)
            
            if success:
                # Copy report to robustness directory
                src = os.path.join(OUTPUT_DIR, level, 'tables', 'report.txt')
                dst = os.path.join(spec_dir, 'report.txt')
                if os.path.exists(src):
                    shutil.copy(src, dst)
                    results.append({
                        'level': level,
                        'spec': spec['desc'],
                        'path': dst
                    })
    
    # Create master summary
    summary_path = os.path.join(rob_dir, 'report.txt')
    with open(summary_path, 'w', encoding='utf-8') as f:
        f.write("=" * 70 + "\n")
        f.write("ROBUSTNESS CHECKS SUMMARY\n")
        f.write("=" * 70 + "\n\n")
        f.write("Specifications tested (supergroup level):\n")
        f.write("1. WLS+HAC (main) - Weighted with autocorrelation-robust SEs\n")
        f.write("2. WLS (no HAC) - Weighted without HAC adjustment\n")
        f.write("3. OLS+HAC - Unweighted with autocorrelation-robust SEs\n")
        f.write("4. OLS (no clustering) - Plain unweighted OLS\n")
        f.write("5. WLS+HAC pre-COVID - Main spec on 2011-2019 data only\n\n")
        
        f.write("-" * 70 + "\n")
        f.write("RESULTS LOCATIONS\n")
        f.write("-" * 70 + "\n\n")
        
        for r in results:
            f.write(f"{r['spec']:30s} | {r['path']}\n")
        
        f.write("\n" + "-" * 70 + "\n")
        f.write("COMPARISON NOTES\n")
        f.write("-" * 70 + "\n\n")
        f.write("Compare reports to assess:\n")
        f.write("1. Do trajectory classifications change with/without COVID?\n")
        f.write("2. Are patterns robust to weighting and clustering?\n")
        f.write("3. Is convergence real or COVID recovery artifact?\n")
        f.write("4. Which supergroups most sensitive to specification?\n\n")
        f.write("For the paper Appendix:\n")
        f.write("- Extract % improving for key supergroups\n")
        f.write("- Show pre-COVID validates main findings\n")
        f.write("- Note qualitative similarity across specs\n")
    
    print(f"\n{'=' * 70}")
    print(f"ROBUSTNESS CHECKS COMPLETE")
    print(f"{'=' * 70}")
    print(f"\nSummary saved to: {summary_path}")
    print(f"\nIndividual reports in output/robustness/*/supergroup/tables/report.txt")


def build_retail():
    """Build England and Scotland retail panels from Geolytix snapshots."""
    run("python retail_panel.py --country both")


def build_panel_data():
    """Download shared panel data: claimant count and population."""
    run("python panel_data.py")


def build_skillsforcare():
    """Parse Skills for Care ASCWDS trended data."""
    run("python skills_for_care.py")


def build_england_panel():
    """Assemble base England panel. Requires curated wellbeing panel."""
    # Ensure wellbeing curated panel exists
    wb_path = os.path.join('data', 'curated', 'wellbeing_harmonised_panel.csv')
    if not os.path.exists(wb_path):
        print("Wellbeing harmonised panel missing — building curated data first...")
        build_curated()
    run("python assemble_england.py")


def build_england_sfc():
    """Add Skills for Care and retail to England panel at upper-tier geography."""
    run("python assemble_england_sfc.py")


def build_cohort_report():
    """Generate Table 1 and cohort charts from England SfC panel."""
    run("python cohort_report.py")


def build_bartik_check():
    """Run Bartik IV sanity check against paper benchmarks."""
    run("python bartik_check.py")


def build_paye():
    """Download HMRC PAYE overseas worker share by region."""
    run("python paye_overseas.py")


def main():
    parser = argparse.ArgumentParser(description='Build wellbeing outputs')
    parser.add_argument('target', nargs='?', default='status',
                        choices=['all', 'clean', 'status',
                                 'tables', 'tables-england',
                                 'plots', 'maps', 'maps-england',
                                 'nations', 'curated', 'robustness',
                                 'retail',
                                 'panel-data', 'claimants', 'population',
                                 'skillsforcare', 'paye',
                                 'england-panel', 'england-sfc',
                                 'cohort-report', 'bartik-check',
                                 'supergroup', 'group', 'subgroup'],
                        help='Build target')
    args = parser.parse_args()

    target = args.target

    if target == 'clean':
        clean()
    elif target == 'status':
        status()
    elif target == 'all':
        build_all()
    elif target == 'tables':
        build_tables()
    elif target == 'tables-england':
        build_tables(england_only=True)
    elif target == 'plots':
        build_tables()
    elif target == 'maps':
        build_maps()
    elif target == 'maps-england':
        build_maps(england_only=True)
    elif target == 'curated':
        build_curated()
    elif target == 'nations':
        build_nations()
    elif target == 'robustness':
        build_robustness()
    elif target == 'retail':
        build_retail()
    elif target == 'panel-data':
        build_panel_data()
    elif target == 'claimants':
        run("python panel_data.py --claimants-only")
    elif target == 'population':
        run("python panel_data.py --population-only")
    elif target == 'skillsforcare':
        build_skillsforcare()
    elif target == 'paye':
        build_paye()
    elif target == 'england-panel':
        build_england_panel()
    elif target == 'england-sfc':
        build_england_sfc()
    elif target == 'cohort-report':
        build_cohort_report()
    elif target == 'bartik-check':
        build_bartik_check()
    elif target in LEVELS:
        build_level(target)

    print(f"\n{'=' * 50}")
    print("Done. Run 'python make.py status' to see outputs.")
    print(f"{'=' * 50}")


if __name__ == '__main__':
    main()
