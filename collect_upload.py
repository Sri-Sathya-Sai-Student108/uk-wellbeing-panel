#!/usr/bin/env python3
"""
collect_upload.py — Gathers files for GitHub upload into ./to_upload/

Run from the repo root (e.g. D:\\ARDDTP\\Repo). Missing files are reported,
not treated as fatal — check the "MISSING" list printed at the end before
uploading anything.

NOTE: paths below marked [UNCONFIRMED] are still guesses -- the only
folder layout actually confirmed this session is that diagnostics/
contains at least: bartik_check.py, check_scotland_bartik.py,
check_scotland_iv.py, check_scotland_overseas.py, Bartik_IV_England.do,
Bartik_IV_Scotland.do, plus ~30 other check_*/debug_*/find_*/
understand_*/compare_*.py scripts. Whether make.py, retail_panel.py,
assemble_england.py etc. live at the repo root or also inside
diagnostics/ has NOT been confirmed -- a full `dir` of the repo root
would settle this in one go rather than fixing paths file-by-file.
"""

import os
import shutil

DEST = "to_upload"

FILES = [
    # --- Core pipeline -- [UNCONFIRMED] assumed repo root, not verified ---
    "make.py",
    "config.py",
    "retail_panel.py",
    "panel_data.py",
    "skills_for_care.py",
    "paye_overseas.py",
    "assemble_england.py",
    "assemble_england_sfc.py",
    "cohort_report.py",
    "scotland_panel.py",

    # --- Confirmed: diagnostics/ ---
    "diagnostics/bartik_check.py",
    "diagnostics/check_scotland_bartik.py",
    "diagnostics/check_scotland_iv.py",
    "diagnostics/check_scotland_overseas.py",
    "diagnostics/Bartik_IV_England.do",
    "diagnostics/Bartik_IV_Scotland.do",

    # --- Docs / README ---
    "README.SCOT",
    "README.md",
    "BARTIK_RECONCILIATION_SUMMARY.md",
    "Codebase_Reconciliation_and_Documentation_Update.md",

    # --- SSSC raw source files, required by scotland_panel.py ---
    # scotland_panel.py fails SILENTLY (prints a warning, not an error) if
    # these are missing for a given year -- confirm they exist at
    # data/sssc/ before upload.
    "data/sssc/staff_vacancies_in_care_services_data_tables_2023.xlsx",
    "data/sssc/staff_vacancies_in_care_services_data_tables_2024.xlsx",
]


def main():
    if os.path.exists(DEST):
        print(f"Removing existing {DEST}/ ...")
        shutil.rmtree(DEST)
    os.makedirs(DEST)

    copied = []
    missing = []

    for rel_path in FILES:
        src = os.path.normpath(rel_path)
        if os.path.exists(src):
            dst = os.path.join(DEST, os.path.basename(src))
            shutil.copy2(src, dst)
            copied.append(src)
            print(f"  copied:  {src}")
        else:
            missing.append(src)
            print(f"  MISSING: {src}")

    print("\n" + "=" * 60)
    print(f"Done. {len(copied)} files copied into {DEST}/")
    if missing:
        print(f"\n{len(missing)} MISSING (not found, not copied):")
        for m in missing:
            print(f"  - {m}")
        print("\nIf several 'core pipeline' files above show as MISSING,")
        print("that likely means they're inside diagnostics/ too, not at")
        print("the repo root -- a `dir` of the repo root would confirm.")
    print("=" * 60)


if __name__ == "__main__":
    main()
