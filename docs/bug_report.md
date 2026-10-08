

# BUG-001: pay_period contradicts the salary size in 391 postings

**Severity:** High (wrong numbers reach customers)   **Priority:** Fix before release
**Component:** salary / pay_period ingestion
**Found by:** `salary_magnitude_vs_pay_period` in `sql/checks.sql`
**Environment:** Kaggle *LinkedIn Job Postings (2023-2024)*; 5,000-row sample (seed 42) and the full 123,849-row file

## Summary
The `pay_period` field disagrees with the size of the salary. YEARLY postings with pay in the tens, and an HOURLY posting with pay in the tens of thousands, show that units are mislabeled or mis-scaled. Any average, comparison or hourly-to-annual conversion that trusts `pay_period` is wrong for these rows.

## Steps to reproduce
1. Run `python prepare_data.py raw/postings.csv`.
2. Run `python run_checks.py` and read `salary_magnitude_vs_pay_period`
   (add `QA_DATASET=job_postings_full.csv` in front to run on the full file).
   Or run the query directly:
   `SELECT posting_id, job_title, pay_period, salary_min, salary_max FROM job_postings WHERE (pay_period='YEARLY' AND salary_max<1000) OR (pay_period='HOURLY' AND salary_max>1000);`

## Expected result
YEARLY salaries are in the thousands or more; HOURLY rates are small (tens, or low hundreds for specialists). The query returns 0 rows.

## Actual result
- **Sample:** 12 rows (1.0% of the 1,211 postings that list a salary).
- **Full file:** 391 rows (0.32% of all postings).

Examples from the sample:

| posting_id | job_title | pay_period | salary_min | salary_max | Likely true meaning |
|-----------|-----------|-----------|-----------|-----------|--------------------|
| 3884435029 | Data Entry Specialist (Aquent) | YEARLY | 20 | 24 | $20-24 per hour |
| 3894232932 | Administrative Assistant ... "80-95K" | YEARLY | 80 | 95 | $80-95 thousand per year (the title says so) |
| 3904982858 | Psychiatric RN (Kaiser Permanente) | YEARLY | 54.16 | 67.07 | $54-67 per hour |
| 3906091917 | Senior Director Social Enterprise | YEARLY | 100 | 135 | $100-135 thousand per year |
| 3904709119 | EMT Part-Time (RedBalloon) | HOURLY | 29,120 | 33,280 | $14-16 per hour, already multiplied by 2,080 hours |

Pattern in the sample: 6 look like hourly wages marked YEARLY, 4 look like thousands, 1 is an annual figure marked HOURLY, and 1 is ambiguous. The *likely true meaning* column is my reading of the job titles, not confirmed against the source postings.

## Impact
- In the sample, the average HOURLY `salary_max` is about $119. Without the single EMT row it is about $65.
- A pipeline that annualises HOURLY pay (x 2,080) would turn the EMT row into 69,222,400 per year.
- YEARLY values like 24 pull yearly averages down and distort salary comparisons between companies or regions.

## Suspected cause (hypothesis, not confirmed)
The pay period appears to come from what the employer entered or from a default, and sometimes disagrees with the numbers entered. The 80-95K title suggests K shorthand is not expanded when the salary is parsed.

## Suggested fix
1. Add a release-blocking check that pay_period matches the salary magnitude (the query above).
2. Expand K notation and standardise units at ingestion.
3. Quarantine contradictory rows for review instead of publishing them.

## Verification
After the fix, the query returns 0 rows on the sample and the full file, and the check runs in CI. Spot-check the posting_ids in the table above.
