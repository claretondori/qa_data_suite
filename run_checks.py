"""Load the CSV into SQLite and run every named query in sql/checks.sql.
Usage:  python run_checks.py            (readable report)
        python run_checks.py --counts   (just the counts, as a dict you can paste into a test)
"""
import csv,os, re, sqlite3, sys
from pathlib import Path

ROOT = Path(__file__).parent
CSV_PATH = ROOT / "data" / os.environ.get("QA_DATASET", "job_postings_sample.csv")
SQL_PATH = ROOT / "sql/checks.sql"
COLUMNS = ["posting_id", "job_title", "company_name", "location", "posted_date", "expiry_date",
           "closed_date", "salary_min", "salary_max", "pay_period", "views", "applies"]
# Fill these in AFTER profiling the data (see README). The window the dataset claims to cover:
PARAMS = {"earliest": "2023-01-01", "latest": "2024-04-30"}

def new_db():
    con = sqlite3.connect(":memory:")
    con.execute("""CREATE TABLE job_postings (posting_id INTEGER, job_title TEXT, company_name TEXT, location TEXT,
                   posted_date TEXT, expiry_date TEXT, closed_date TEXT, salary_min REAL, salary_max REAL,
                   pay_period TEXT, views REAL, applies REAL)""")
    return con

def insert_rows(con, rows):
    """rows = list of dicts. Missing keys become NULL."""
    con.executemany(f"INSERT INTO job_postings VALUES ({','.join('?' * len(COLUMNS))})",
                    [[r.get(c) for c in COLUMNS] for r in rows])

def load_csv(con, csv_path=CSV_PATH):
    with open(csv_path, newline="", encoding="utf-8") as f:
        insert_rows(con, [{k: (v if v != "" else None) for k, v in r.items()} for r in csv.DictReader(f)])
    return con

def load_checks(sql_path=SQL_PATH):
    parts = re.split(r"^-- name:\s*(\w+)\s*$", sql_path.read_text(), flags=re.M)
    return {parts[i]: parts[i + 1].strip() for i in range(1, len(parts), 2)}

def run_one(con, name):
    return con.execute(load_checks()[name], PARAMS).fetchall()

def run_all(con):
    return {name: con.execute(sql, PARAMS).fetchall() for name, sql in load_checks().items()}

if __name__ == "__main__":
    results = run_all(load_csv(new_db()))
    if "--counts" in sys.argv:
        print({k: len(v) for k, v in results.items()})
    else:
        for name, rows in results.items():
            print(f"\n== {name}: {len(rows)} row(s)")
            for r in rows[:5]: print("  ", r)
            if len(rows) > 5: print(f"   ... and {len(rows) - 5} more")
