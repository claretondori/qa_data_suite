
# Data quality findings: LinkedIn job postings

**Data:** Kaggle *LinkedIn Job Postings (2023-2024)*, 123 849 postings. I ran every check on a 5 000-row random sample (seed 42, committed) and on the full file.
Posted dates in the sample run from 2024-01-26 to 2024-04-20. Only 1 211 of the 5 000 sample rows (24.2%) list a salary, so the salary checks cover about a quarter of the data.
Queries are in `sql/checks.sql`; reproduce with `python run_checks.py`.

## Summary

| # | Issue | Sample (5,000) | Full (123,849) | Example posting_id | Why it matters | Fix / prevention |
|---|-------|---------------|----------------|--------------------|----------------|------------------|
| 1 | **Pay period contradicts the salary size** | 12 (1.0% of rows with salary) | 391 (0.32%) | 3904709119 (HOURLY 33 280), 3894232932 (YEARLY 80-95) | Averages and hourly-to-annual conversions go wrong; one row moves the sample's hourly average from about $65 to $119 | Validate that pay_period matches the magnitude; normalise units at ingestion; quarantine contradictions |
| 2 | **Missing company name** | 64 (1.3%) | 1,719 (1.4%) | 2737009242 | The posting cannot be attributed to a company, so it drops out of *hiring by company* numbers | Reject or quarantine on ingest; track the null rate every release |
| 3 | **Probable duplicate postings** (same company, title, location, date) | 12 surplus rows | 4,645 (3.7%) | 3885108043 | Inflates posting counts for that employer | Dedupe on a normalised key; reconcile conflicting fields before dropping a copy |
| 4 | **Implausibly wide salary range** (max over 10x min) | 8 | 80 | 3887840140 (13,824 to 831,891), 3905224208 (5,000 to 600,000) | Distorts averages and ranges | Flag for review; null or cap suspicious maxima |
| 5 | **Salary outliers within pay period** | 8 | 256 | 3887840140 | Extreme values drag averages | Review manually; see the false-alarm notes below |
| 6 | **Company name spelling variants** (case/spacing) | 0 | 30 spellings | "Avance Consulting" vs "avance consulting" | One company is split across groups | Normalise case and whitespace; match on a company id |

## Details

### 1. Pay period contradicts the salary size (highest priority)
The check flags YEARLY pay under 1,000 and HOURLY pay over 1 000. On the sample, the 12 rows split into three kinds (my reading of the job titles):
- **Hourly wages labeled YEARLY (6 rows):** Data Entry Specialist 20-24, TikTok intern 22-24, Kaiser Psychiatric RN 54.16-67.07, and similar.
- **Salary in thousands labeled YEARLY (4 rows, plus 1 ambiguous):** one posting's own title says 80-95K while the data says 80-95. Others: 50-85, 120-160, 100-135.
- **Annual salary labeled HOURLY (1 row):** an EMT posting at 29,120-33,280. Those are exactly 14 x 2 080 and 16 x 2 080, so $14-16/hr already multiplied by a full year's hours.

The mistake goes in both directions, which points to unreliable pay-period labels. See `docs/bug_report.md`.

### 2. Missing company name
All 64 missing-field rows in the sample are `company_name`; title and location were never missing. The full file has 1719 such rows.

### 3. Probable duplicates, and what sampling hid
The sample shows 12 surplus rows (10 pairs and one triple). The full file shows **4 645**.

This gap is itself a finding. A duplicate is only visible when both copies are in the sample. With a 4.0% sample (5 000 of 123 849), the chance of keeping both rows of a pair is about 0.16%, so I would expect roughly 8 visible duplicates, and I saw 12. So the sample hides almost all duplicates, and **duplicate rates must be measured on the full data**. Row-level problems (missing values, bad salaries) were estimated fairly well by the sample (for example 0.24% vs 0.32% for finding 1).

Evidence that the sample duplicates are probable true duplicates: the posting ids in each pair are very close (for example 3885105395 and 3885108043, same day, same employer, same title), which suggests the same job submitted twice. Caveats:
- Two pairs disagree on salary (National General: 100 000 vs missing; Open Systems Technologies: 140 000 vs 170 000), so even true duplicates may carry conflicting data, and a dedupe rule has to choose which record wins.
- Employers such as hospitals and staffing firms sometimes publish several genuine openings for the same role at one site on one day, so some duplicates may be real. I did not classify the 4 645 full-data duplicates.

### 4 and 5. Salary ranges and outliers
The wide-range check is the more precise of the two. It catches the RN posting at 13 824 to 831 891 and the Work From Home Client Relations Representative at 5 000 to 600 000, both implausible. The IQR outlier check is cruder (see below).

## Things that looked like bugs but weren't
- **Hourly physician rates of $150-200** were flagged as outliers by the IQR rule. That is normal pay for physicians. The rule is crude on skewed pay data.
- **A Travel RN at $2 247 per week** was flagged because the WEEKLY group has only 5 rows, so its quartiles meant nothing. I changed the check to ignore pay periods with fewer than 30 rows, and added a unit test for it.
- **A Software Engineer at 230k-550k (D. E. Shaw Research)** is high but plausible.
- **Missing salary on about 76% of the sample** is how the source works (most postings do not publish pay), not a defect.
- **The date window.** I first used `listed_time` as the posting date, but `original_listed_time` is closer to when it was posted (it reaches back to Dec 2023 in the full file), so I switched.
- **Checks that found nothing, on both sample and full data:** expiry before posted, closed before posted, implausible posted date, min greater than max, non-positive salary, applies greater than views. These risks were checked and are clean.

## How I verified my own queries
Every check has a unit test on a small hand-made table (`tests/test_checks_unit.py`), including boundary cases. Real data also exposed a flaw in my first outlier rule (tiny pay-period groups), which I fixed and tested. I confirmed the tests can fail by changing a comparison operator and watching the matching test break.

## Limits
- Duplicates use an exact normalised key. Near-duplicates ( Sr. vs Senior) need fuzzy matching, and rows with a missing company are skipped.
- 260 sample rows have a pay_period but no salary_max. I did not investigate them because the median-salary column was not loaded.
- I classified unit mix-ups from job titles and did not confirm them against the original postings.
- The data covers early 2024 only; it says nothing about quality in 2023.
