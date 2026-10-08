"""Tests on the real sample. Counts are a snapshot : they pin what the checks found on
the committed sample, so any change to a query or to the data shows up as a failing test."""
import pytest
from run_checks import new_db, load_csv, run_all

# After your first run, execute `python run_checks.py --counts` and paste the dict here:
GOLDEN_COUNTS = {'duplicate_postings': 12, 'missing_required_fields': 64, 'expiry_before_posted': 0, 'closed_before_posted': 0, 'implausible_posted_date': 0, 'salary_min_gt_max': 0, 'nonpositive_salary': 0, 'salary_magnitude_vs_pay_period': 12, 'salary_outliers_within_pay_period': 8, 'implausibly_wide_salary_range': 8, 'applies_exceed_views': 0, 'company_name_spelling_variants': 0}

@pytest.fixture(scope="module")
def con():
    return load_csv(new_db())

@pytest.fixture(scope="module")
def results(con):
    return run_all(con)

def test_sample_has_at_least_500_rows(con):
    assert con.execute("SELECT COUNT(*) FROM job_postings").fetchone()[0] >= 500

def test_posting_ids_are_unique(con):
    total, distinct = con.execute("SELECT COUNT(*), COUNT(DISTINCT posting_id) FROM job_postings").fetchone()
    assert total == distinct

def test_every_check_returns_at_most_the_number_of_rows(con, results):
    total = con.execute("SELECT COUNT(*) FROM job_postings").fetchone()[0]
    assert all(len(rows) <= total for rows in results.values())

def test_at_least_three_distinct_kinds_of_issue_are_found(results):
    issue_checks = [n for n, rows in results.items() if rows and n != "company_name_spelling_variants"]
    assert len(issue_checks) >= 3

def test_counts_match_the_golden_snapshot(results):
    assert GOLDEN_COUNTS, "Paste the output of `python run_checks.py --counts` into GOLDEN_COUNTS"
    assert {k: len(v) for k, v in results.items()} == GOLDEN_COUNTS
