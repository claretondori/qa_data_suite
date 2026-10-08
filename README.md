# QA project: API tests + data-quality checks


**What this is**
- **Part 1: API tests.** A pytest suite against the public [JSONPlaceholder](https://jsonplaceholder.typicode.com) API covering successful requests, invalid input, edge cases and documented known gaps (23 tests).
- **Part 2: Data-quality checks.** 12 named SQL queries run on real LinkedIn job-postings data. They find duplicates, missing values, impossible dates and salary problems, and the queries themselves are tested (22 tests).
- `docs/findings.md`: what I found and how I would fix or prevent it.
- `docs/bug_report.md`: a sample bug report written for an engineer.

**Test status:** `45 collected = 43 passed + 2 xfailed` (the xfails are deliberate, see below).

## Data source
Kaggle dataset *LinkedIn Job Postings (2023-2024)* by arshkon (123,849 postings).
License: CC BY-SA 4.0.

The repo ships a **5 000-row random sample** (seed 42) in `data/job_postings_sample.csv`, because the full file is large. `prepare_data.py` only renames columns, converts timestamps to dates and samples rows. It does **not** correct any values, because finding the errors is the point.

I used `original_listed_time` as the posting date. In the sample, posted dates run from 2024-01-26 to 2024-04-20, so this data is mostly a snapshot of early 2024, not the whole of 2023-2024.

## Run it
```bash
python -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\activate
python -m pip install -r requirements.txt
python -m pytest -v                  # all tests (API tests need internet)
python run_checks.py                 # readable report of what each SQL check finds (sample)
python run_checks.py --counts        # just the counts
```

### Rebuild the sample or run on the full data
1. Download `postings.csv` from Kaggle into `raw/` (this folder is git-ignored).
2. `python prepare_data.py raw/postings.csv` writes the 5 000-row sample and a full cleaned file (`data/job_postings_full.csv`, also git-ignored).
3. Run the checks on all 123 849 rows:
```bash
QA_DATASET=job_postings_full.csv python run_checks.py --counts
```
Do not set `QA_DATASET` when running pytest; the golden snapshot is pinned to the sample.

## Project layout
```
sql/checks.sql                 12 named SQL checks (one query per check)
run_checks.py                  loads the CSV into SQLite and runs the checks
prepare_data.py                reshapes the raw Kaggle file into a clean sample
tests/test_api.py              23 API tests (21 pass, 2 expected failures)
tests/test_checks_unit.py      17 unit tests: one per check, on tiny hand-made tables
tests/test_real_data.py        5 tests on the real sample, including a golden snapshot
docs/findings.md               findings and fixes
docs/bug_report.md             sample bug report
.github/workflows/ci.yml       runs the tests on every push
```

## How the tests are designed
- **The SQL checks are tested, not just run.** Each check has a unit test with a few good rows plus one bad row, and must flag exactly that row. Tests also cover boundaries (min = max is allowed; exactly 10x is not wider than 10x; a still-open posting is not closed before posted).
- **Golden snapshot.** `test_real_data.py` pins what each check finds on the sample, so a changed query or changed data makes a test fail.
- **API tests check the contract,** not just that a response arrived: status code, content type, fields, types, and referential integrity (every post author exists).
- **Known gaps are documented, not hidden.** Two tests are marked `xfail`: JSONPlaceholder accepts an empty body and wrong field types and still returns 201, where a production API should return 400/422. JSONPlaceholder is a fake API that does not save writes, so one test records that behaviour on purpose.
- **I checked that the tests can fail.** Changing `>` to `>=` in the min/max salary check makes a unit test fail, as it should.

## Results 
| Check | Sample (5 000) | Full data (123,849) |
|---|---|---|
| Pay period contradicts salary size | 12 | 391 |
| Missing company name / required field | 64 | 1,719 |
| Probable duplicate postings | 12 | 4,645 |
| Implausibly wide salary range (max > 10x min) | 8 | 80 |
| Salary outliers within pay period | 8 | 256 |
| Company name spelling variants (spellings listed) | 0 | 30 |
| Dates impossible, min > max, non-positive salary, applies > views | 0 | 0 |

Key takeaway: **sampling hides duplicates.** A duplicate is only visible when both copies land in the sample, so the sample showed 12 while the full data has 4,645. Details are in `docs/findings.md`.

## Limits
- Duplicates are matched on an exact normalised key (company, title, location, date). Near-duplicates would need fuzzy matching, and rows with a missing company are skipped.
- Salary checks only cover postings that list a salary (24% of the sample).
- I judged the unit mix-ups from job titles and did not open the original postings.

## Not done
Repeating the checks in pandas; browser tests.
