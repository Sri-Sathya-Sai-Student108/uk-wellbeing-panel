# QOF Data Setup

Scripts for downloading and processing QOF practice-level data into
LA-level prevalence files that plug into the main analysis.

Run these from this directory (`qof_setup/`).

## Workflow

```bash
# 1. Open download pages in browser (or just one year to test)
python download_qof.py --year 2022 --lookup

# 2. Download the files from the browser tabs:
#    - QOF cardiovascular practice-level file → ../data/qof_practice/qof_cardio_2022.csv
#    - epraccur.csv → ../data/epraccur.csv
#    - NSPL → ../data/nspl.csv

# 3. Check files are in place
python process_qof_practice.py --check

# 4. Process one year (test)
python process_qof_practice.py --year 2022

# 5. If that works, download remaining years and process all
python download_qof.py
python process_qof_practice.py

# 6. Run the panel model (from parent directory)
cd ..
python qof_panel.py
```

## Files

- `download_qof.py` — Opens NHS Digital pages in browser, tracks what's downloaded
- `process_qof_practice.py` — Builds practice→LA lookup, aggregates prevalence
- `downloads.txt` — Plain-text reference of all URLs
- `QOF_DOWNLOAD_GUIDE.md` — Detailed guide with file format notes

## Output

`process_qof_practice.py` produces `../data/qof_hypertension_la.csv` (or diabetes).
The main `qof_panel.py` script auto-detects this file.
