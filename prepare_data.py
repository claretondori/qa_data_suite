"""Turn the raw Kaggle postings.csv into a small, clean-schema sample we can commit to GitHub.

Usage:  python prepare_data.py path/to/postings.csv
IMPORTANT: this script only RESHAPES the data (rename columns, convert timestamps, take a random sample).
It must NOT fix errors - finding the errors is the whole point of Part 2.
"""
import sys
from pathlib import Path
import pandas as pd

SAMPLE_SIZE = 5000
RENAME = {"job_id": "posting_id", "title": "job_title", "location": "location", "company_name": "company_name",
          "original_listed_time": "posted_date", "expiry": "expiry_date", "closed_time": "closed_date",
          "min_salary": "salary_min", "max_salary": "salary_max", "pay_period": "pay_period",
          "views": "views", "applies": "applies"}
DATE_COLUMNS = ["posted_date", "expiry_date", "closed_date"]

def to_date(series):
    """Epoch timestamps -> 'YYYY-MM-DD'. Guesses seconds vs milliseconds from the size of the numbers."""
    nums = pd.to_numeric(series, errors="coerce")
    unit = "ms" if nums.dropna().median() > 1e11 else "s"
    print(f"  {series.name}: treating values as epoch {unit}")
    return pd.to_datetime(nums, unit=unit, errors="coerce").dt.strftime("%Y-%m-%d")

def main(raw_path):
    raw = pd.read_csv(raw_path, usecols=lambda c: c in RENAME, low_memory=False)
    missing = set(RENAME) - set(raw.columns)
    if missing:
        sys.exit(f"Columns not found in the file: {sorted(missing)}. Run `head -1 {raw_path}` and update RENAME.")
    print(f"Raw file: {len(raw):,} rows")
    df = raw.rename(columns=RENAME)[list(RENAME.values())]
    for col in DATE_COLUMNS:
        df[col] = to_date(df[col])
    full_out = Path(__file__).parent / "data" / "job_postings_full.csv"
    full_out.parent.mkdir(exist_ok=True)
    df.to_csv(full_out, index=False)                 # ALL rows; not committed (see .gitignore)
    print(f"Wrote full cleaned file: {len(df):,} rows to {full_out}")
    df = df.sample(n=min(SAMPLE_SIZE, len(df)), random_state=42).sort_values("posting_id")
    print("posted_date range:", df["posted_date"].min(), "->", df["posted_date"].max(), "  <- does this look right?")

if __name__ == "__main__":
    main(sys.argv[1]) if len(sys.argv) == 2 else sys.exit(__doc__)
