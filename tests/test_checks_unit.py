"""Unit tests for every SQL check, using  hand-made tables where the right answer is known.
Each test: a few GOOD rows + exactly ONE bad row -> the check must return that row and nothing else."""
from run_checks import new_db, insert_rows, run_one

def good(posting_id, **overrides):
    row = dict(posting_id=posting_id, job_title="QA Engineer", company_name=f"Company {posting_id}",
               location="Nairobi, Kenya", posted_date="2024-03-01", expiry_date="2024-04-01", closed_date=None,
               salary_min=50000, salary_max=70000, pay_period="YEARLY", views=100, applies=10)
    row.update(overrides)
    return row

def flagged(check, bad_rows, n_good=5):
    con = new_db()
    insert_rows(con, [good(i) for i in range(1, n_good + 1)] + bad_rows)
    return {r[0] for r in run_one(con, check)}

def test_duplicate_flags_only_the_surplus_copy():
    original = good(100, company_name="Acme", job_title="Analyst")
    copy = good(101, company_name=" ACME ", job_title="analyst")     # same posting, different case/spaces/id
    assert flagged("duplicate_postings", [original, copy]) == {101}

def test_same_title_on_a_different_day_is_not_a_duplicate():
    a = good(100, company_name="Acme", job_title="Analyst", posted_date="2024-03-01")
    b = good(101, company_name="Acme", job_title="Analyst", posted_date="2024-03-02")
    assert flagged("duplicate_postings", [a, b]) == set()

def test_missing_required_fields_catches_null_and_blank():
    bad = [good(100, job_title=None), good(101, company_name="   "), good(102, location="")]
    assert flagged("missing_required_fields", bad) == {100, 101, 102}

def test_expiry_before_posted():
    assert flagged("expiry_before_posted", [good(100, expiry_date="2024-02-01")]) == {100}

def test_expiry_on_same_day_as_posted_is_allowed():
    assert flagged("expiry_before_posted", [good(100, expiry_date="2024-03-01")]) == set()

def test_closed_before_posted_ignores_still_open_postings():
    bad = good(100, closed_date="2024-01-01")
    still_open = good(101, closed_date=None)
    assert flagged("closed_before_posted", [bad, still_open]) == {100}

def test_implausible_posted_date_both_directions():
    bad = [good(100, posted_date="1970-01-01"), good(101, posted_date="2031-01-01")]
    assert flagged("implausible_posted_date", bad) == {100, 101}

def test_salary_min_greater_than_max():
    assert flagged("salary_min_gt_max", [good(100, salary_min=90000, salary_max=40000)]) == {100}

def test_salary_equal_min_and_max_is_allowed():
    assert flagged("salary_min_gt_max", [good(100, salary_min=50000, salary_max=50000)]) == set()

def test_nonpositive_salary():
    bad = [good(100, salary_min=0), good(101, salary_min=-5), good(102, salary_max=0)]
    assert flagged("nonpositive_salary", bad) == {100, 101, 102}

def test_missing_salary_is_not_flagged_as_nonpositive():
    assert flagged("nonpositive_salary", [good(100, salary_min=None, salary_max=None)]) == set()

def test_salary_magnitude_vs_pay_period():
    bad = [good(100, pay_period="YEARLY", salary_max=45), good(101, pay_period="HOURLY", salary_max=95000)]
    ok = good(102, pay_period="HOURLY", salary_min=20, salary_max=30)
    assert flagged("salary_magnitude_vs_pay_period", bad + [ok]) == {100, 101}

def test_salary_outlier_is_judged_within_its_own_pay_period():
    yearly = [good(200 + i, salary_max=60000 + i * 1000) for i in range(40)]
    hourly = [good(300 + i, pay_period="HOURLY", salary_min=15, salary_max=20 + i) for i in range(40)]
    outlier = good(999, salary_max=9999999)
    con = new_db(); insert_rows(con, yearly + hourly + [outlier])
    assert {r[0] for r in run_one(con, "salary_outliers_within_pay_period")} == {999}   # hourly 20-59 NOT flagged

def test_applies_exceed_views():
    assert flagged("applies_exceed_views", [good(100, views=5, applies=9)]) == {100}

def test_company_spelling_variants_are_listed():
    con = new_db()
    insert_rows(con, [good(1, company_name="Acme"), good(2, company_name="Acme"), good(3, company_name="ACME ")])
    rows = run_one(con, "company_name_spelling_variants")
    assert {(r[1], r[2]) for r in rows} == {("Acme", 2), ("ACME ", 1)}


def test_outlier_check_ignores_tiny_pay_period_groups():
    weekly = [good(400 + i, pay_period="WEEKLY", salary_min=1000, salary_max=1000 + i * 100) for i in range(4)]
    big_weekly = good(499, pay_period="WEEKLY", salary_min=1000, salary_max=2247)
    con = new_db(); insert_rows(con, weekly + [big_weekly])
    assert run_one(con, "salary_outliers_within_pay_period") == []      # only 5 rows: not enough to judge

def test_implausibly_wide_salary_range():
    bad = good(100, salary_min=5000, salary_max=600000)
    ok_wide = good(101, salary_min=60000, salary_max=120000)             # 2x is a normal wide range
    exactly_10x = good(102, salary_min=10000, salary_max=100000)         # boundary: not MORE than 10x
    assert flagged("implausibly_wide_salary_range", [bad, ok_wide, exactly_10x]) == {100}


