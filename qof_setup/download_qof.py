#!/usr/bin/env python3
"""
download_qof.py — Helper to download QOF practice-level data.

Opens each QOF publication page in your browser and tells you what to
download. Files should be saved into data/qof_practice/.

Also opens the pages for the GP practice registry (epraccur) and the
ONS postcode lookup (NSPL).

Usage:
  python download_qof.py              # open all pages
  python download_qof.py --year 2022  # open just one year
  python download_qof.py --lookup     # open just the lookup file pages
  python download_qof.py --check      # check which files you already have
"""

import argparse
import os
import sys
import webbrowser
import time

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
QOF_DIR = os.path.join(DATA_DIR, "qof_practice")

# QOF publication pages — cardiovascular group contains hypertension
QOF_PAGES = {
    2012: {
        'url': 'https://digital.nhs.uk/data-and-information/publications/statistical/quality-and-outcomes-framework-achievement-prevalence-and-exceptions-data/quality-and-outcomes-framework-qof-2012-13',
        'file': 'qof_cardio_2012',
        'label': '2012-13',
    },
    2013: {
        'url': 'https://digital.nhs.uk/data-and-information/publications/statistical/quality-and-outcomes-framework-achievement-prevalence-and-exceptions-data/quality-and-outcomes-framework-qof-2013-14',
        'file': 'qof_cardio_2013',
        'label': '2013-14',
    },
    2014: {
        'url': 'https://digital.nhs.uk/data-and-information/publications/statistical/quality-and-outcomes-framework-achievement-prevalence-and-exceptions-data/quality-and-outcomes-framework-qof-2014-15',
        'file': 'qof_cardio_2014',
        'label': '2014-15',
    },
    2015: {
        'url': 'https://digital.nhs.uk/data-and-information/publications/statistical/quality-and-outcomes-framework-achievement-prevalence-and-exceptions-data/quality-and-outcomes-framework-qof-2015-16',
        'file': 'qof_cardio_2015',
        'label': '2015-16',
    },
    2016: {
        'url': 'https://digital.nhs.uk/data-and-information/publications/statistical/quality-and-outcomes-framework-achievement-prevalence-and-exceptions-data/quality-and-outcomes-framework-qof-2016-17',
        'file': 'qof_cardio_2016',
        'label': '2016-17',
    },
    2017: {
        'url': 'https://digital.nhs.uk/data-and-information/publications/statistical/quality-and-outcomes-framework-achievement-prevalence-and-exceptions-data/quality-and-outcomes-framework-qof-2017-18',
        'file': 'qof_cardio_2017',
        'label': '2017-18',
    },
    2018: {
        'url': 'https://digital.nhs.uk/data-and-information/publications/statistical/quality-and-outcomes-framework-achievement-prevalence-and-exceptions-data/quality-and-outcomes-framework-qof-2018-19',
        'file': 'qof_cardio_2018',
        'label': '2018-19',
    },
    2019: {
        'url': 'https://digital.nhs.uk/data-and-information/publications/statistical/quality-and-outcomes-framework-achievement-prevalence-and-exceptions-data/2019-20',
        'file': 'qof_cardio_2019',
        'label': '2019-20',
    },
    2020: {
        'url': 'https://digital.nhs.uk/data-and-information/publications/statistical/quality-and-outcomes-framework-achievement-prevalence-and-exceptions-data/2020-21',
        'file': 'qof_cardio_2020',
        'label': '2020-21',
    },
    2021: {
        'url': 'https://digital.nhs.uk/data-and-information/publications/statistical/quality-and-outcomes-framework-achievement-prevalence-and-exceptions-data/2021-22',
        'file': 'qof_cardio_2021',
        'label': '2021-22',
    },
    2022: {
        'url': 'https://digital.nhs.uk/data-and-information/publications/statistical/quality-and-outcomes-framework-achievement-prevalence-and-exceptions-data/2022-23',
        'file': 'qof_cardio_2022',
        'label': '2022-23',
    },
}

LOOKUP_PAGES = {
    'epraccur': {
        'url': 'https://digital.nhs.uk/services/organisation-data-service/data-search-and-export/csv-downloads/gp-and-gp-practice-related-data',
        'file': 'epraccur.csv',
        'instruction': 'Download the "epraccur" predefined report (auto-downloads as CSV).\n'
                       '    If the auto-download link doesn\'t work, go to DSE directly:\n'
                       '    https://www.odsdatasearchandexport.nhs.uk/\n'
                       '    and search for the "epraccur" predefined report.',
    },
    'nspl': {
        'url': 'https://geoportal.statistics.gov.uk/datasets/ons::national-statistics-postcode-lookup-august-2025-for-the-uk/about',
        'file': 'nspl.csv',
        'instruction': 'Download the NSPL zip, extract the main CSV from the Data folder.\n'
                       '    You only need columns: pcds (postcode) and laua (LA code).\n'
                       '    If this link is outdated, search "NSPL" on geoportal.statistics.gov.uk\n'
                       '    or download from https://www.data.gov.uk/dataset/7ec10db7-c8f4-4a40-8d82-8921935b4865/national-statistics-postcode-lookup-uk',
    },
}


def check_files():
    """Report which files are already downloaded."""
    print("=" * 60)
    print("FILE CHECK")
    print("=" * 60)

    # QOF practice files
    print(f"\nQOF practice files (in {QOF_DIR}/):")
    os.makedirs(QOF_DIR, exist_ok=True)

    found = 0
    for year, info in sorted(QOF_PAGES.items()):
        # Check for csv or xlsx
        csv_path = os.path.join(QOF_DIR, info['file'] + '.csv')
        xlsx_path = os.path.join(QOF_DIR, info['file'] + '.xlsx')
        if os.path.exists(csv_path):
            size = os.path.getsize(csv_path) / 1024 / 1024
            print(f"  [OK]  {info['label']:10s}  {csv_path} ({size:.1f} MB)")
            found += 1
        elif os.path.exists(xlsx_path):
            size = os.path.getsize(xlsx_path) / 1024 / 1024
            print(f"  [OK]  {info['label']:10s}  {xlsx_path} ({size:.1f} MB)")
            found += 1
        else:
            print(f"  [  ]  {info['label']:10s}  MISSING — save as "
                  f"{info['file']}.csv or .xlsx")

    print(f"\n  {found}/{len(QOF_PAGES)} QOF files found")

    # Lookup files
    print(f"\nLookup files (in {DATA_DIR}/):")
    for name, info in LOOKUP_PAGES.items():
        path = os.path.join(DATA_DIR, info['file'])
        if os.path.exists(path):
            size = os.path.getsize(path) / 1024 / 1024
            print(f"  [OK]  {info['file']} ({size:.1f} MB)")
        else:
            print(f"  [  ]  {info['file']} — MISSING")


def open_qof_pages(year=None):
    """Open QOF publication pages in the browser."""
    os.makedirs(QOF_DIR, exist_ok=True)

    if year:
        pages = {year: QOF_PAGES[year]} if year in QOF_PAGES else {}
        if not pages:
            print(f"No QOF page for year {year}. Valid: {sorted(QOF_PAGES.keys())}")
            return
    else:
        pages = QOF_PAGES

    print("=" * 60)
    print("OPENING QOF PUBLICATION PAGES")
    print("=" * 60)
    print(f"\nFor each page, download the file labelled:")
    print(f'  "Prevalence... CARDIOVASCULAR group... GP practice level"')
    print(f"\nSave files into: {QOF_DIR}/\n")

    for yr, info in sorted(pages.items()):
        # Skip if already downloaded
        csv_path = os.path.join(QOF_DIR, info['file'] + '.csv')
        xlsx_path = os.path.join(QOF_DIR, info['file'] + '.xlsx')
        if os.path.exists(csv_path) or os.path.exists(xlsx_path):
            print(f"  {info['label']}: already downloaded, skipping")
            continue

        print(f"  {info['label']}: opening... save as {info['file']}.csv (or .xlsx)")
        webbrowser.open(info['url'])
        time.sleep(1.5)  # Don't overwhelm the browser


def open_lookup_pages():
    """Open lookup file download pages."""
    print("\n" + "=" * 60)
    print("LOOKUP FILES")
    print("=" * 60)

    for name, info in LOOKUP_PAGES.items():
        path = os.path.join(DATA_DIR, info['file'])
        if os.path.exists(path):
            print(f"\n  {name}: already downloaded")
            continue

        print(f"\n  {name}:")
        print(f"    {info['instruction']}")
        print(f"    Save as: {DATA_DIR}/{info['file']}")
        webbrowser.open(info['url'])
        time.sleep(1.5)


def main():
    parser = argparse.ArgumentParser(
        description='Download QOF practice-level data')
    parser.add_argument('--year', type=int,
                        help='Open just one year (e.g. --year 2022)')
    parser.add_argument('--lookup', action='store_true',
                        help='Open just the lookup file pages')
    parser.add_argument('--check', action='store_true',
                        help='Check which files you already have')
    parser.add_argument('--all', action='store_true',
                        help='Open all pages (QOF + lookups)')
    args = parser.parse_args()

    if args.check:
        check_files()
        return

    if args.lookup:
        open_lookup_pages()
        return

    if args.year:
        open_qof_pages(year=args.year)
        return

    # Default: open everything
    open_qof_pages()
    open_lookup_pages()

    print("\n" + "=" * 60)
    print("DONE — check your browser tabs")
    print(f"Save QOF files into: {QOF_DIR}/")
    print(f"Save lookup files into: {DATA_DIR}/")
    print(f"\nRun 'python download_qof.py --check' to verify")
    print("=" * 60)


if __name__ == '__main__':
    main()
