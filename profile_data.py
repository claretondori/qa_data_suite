from run_checks import new_db, load_csv
con = load_csv(new_db())
q = lambda s: con.execute(s).fetchall()
print(q("SELECT COUNT(*) FROM job_postings"))
print(q("SELECT MIN(posted_date), MAX(posted_date), MIN(expiry_date), MAX(expiry_date) FROM job_postings"))
print(q("SELECT pay_period, COUNT(*), MIN(salary_max), MAX(salary_max) FROM job_postings GROUP BY pay_period"))
print(q("SELECT SUM(job_title IS NULL), SUM(company_name IS NULL), SUM(location IS NULL), "
        "SUM(salary_max IS NULL), SUM(closed_date IS NULL) FROM job_postings"))
