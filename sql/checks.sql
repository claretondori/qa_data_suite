-- name: duplicate_postings
-- Same company + title + location + posted_date under different posting_ids. Returns the SURPLUS copies.
SELECT posting_id, company_name, job_title, location, posted_date FROM (
  SELECT *, ROW_NUMBER() OVER (
    PARTITION BY LOWER(TRIM(company_name)), LOWER(TRIM(job_title)), LOWER(TRIM(location)), posted_date
    ORDER BY posting_id) AS copy_no
  FROM job_postings
  WHERE company_name IS NOT NULL AND job_title IS NOT NULL AND location IS NOT NULL
) WHERE copy_no > 1;

-- name: missing_required_fields
SELECT posting_id,
       CASE WHEN job_title IS NULL OR TRIM(job_title) = '' THEN 'job_title'
            WHEN company_name IS NULL OR TRIM(company_name) = '' THEN 'company_name'
            ELSE 'location' END AS missing_field
FROM job_postings
WHERE job_title IS NULL OR TRIM(job_title) = ''
   OR company_name IS NULL OR TRIM(company_name) = ''
   OR location IS NULL OR TRIM(location) = '';

-- name: expiry_before_posted
SELECT posting_id, posted_date, expiry_date FROM job_postings WHERE expiry_date < posted_date;

-- name: closed_before_posted
SELECT posting_id, posted_date, closed_date FROM job_postings WHERE closed_date < posted_date;

-- name: implausible_posted_date
-- Outside the window the dataset is supposed to cover (set :earliest / :latest in run_checks.py after profiling).
SELECT posting_id, posted_date FROM job_postings WHERE posted_date < :earliest OR posted_date > :latest;

-- name: salary_min_gt_max
SELECT posting_id, salary_min, salary_max FROM job_postings WHERE salary_min > salary_max;

-- name: nonpositive_salary
SELECT posting_id, salary_min, salary_max FROM job_postings WHERE salary_min <= 0 OR salary_max <= 0;

-- name: salary_magnitude_vs_pay_period
-- A "YEARLY" salary under 1,000 or an "HOURLY" one over 1,000 is almost certainly the wrong unit.
SELECT posting_id, pay_period, salary_max FROM job_postings
WHERE (pay_period = 'YEARLY' AND salary_max < 1000) OR (pay_period = 'HOURLY' AND salary_max > 1000);

-- name: salary_outliers_within_pay_period
-- Extreme outliers: salary_max above Q3 + 3*IQR, computed separately for each pay period with at least 30 rows.
WITH ranked AS (
  SELECT pay_period, salary_max, NTILE(4) OVER (PARTITION BY pay_period ORDER BY salary_max) AS quartile
  FROM job_postings WHERE salary_max > 0 AND pay_period IS NOT NULL),
bounds AS (
  SELECT pay_period,
         MAX(CASE WHEN quartile = 1 THEN salary_max END) AS q1,
         MAX(CASE WHEN quartile = 3 THEN salary_max END) AS q3
  FROM ranked GROUP BY pay_period
  HAVING COUNT(*) >= 30)   -- quartiles are meaningless on tiny groups
SELECT p.posting_id, p.pay_period, p.salary_max FROM job_postings p
JOIN bounds b ON p.pay_period = b.pay_period
WHERE p.salary_max > b.q3 + 3 * (b.q3 - b.q1);

-- name: implausibly_wide_salary_range
-- A maximum more than 10x the minimum is almost never a real range (e.g. 5,000 - 600,000).
SELECT posting_id, pay_period, salary_min, salary_max FROM job_postings
WHERE salary_min > 0 AND salary_max > 10 * salary_min;

-- name: applies_exceed_views
-- You cannot apply to a posting nobody viewed.
SELECT posting_id, views, applies FROM job_postings WHERE applies > views;

-- name: company_name_spelling_variants
-- Same company written several ways (case / stray spaces). Lists every spelling with its row count.
WITH v AS (
  SELECT LOWER(TRIM(company_name)) AS company_key, company_name, COUNT(*) AS n
  FROM job_postings WHERE company_name IS NOT NULL AND TRIM(company_name) <> '' GROUP BY 1, 2)
SELECT company_key, company_name, n FROM v
WHERE company_key IN (SELECT company_key FROM v GROUP BY company_key HAVING COUNT(*) > 1)
ORDER BY company_key, n DESC;
