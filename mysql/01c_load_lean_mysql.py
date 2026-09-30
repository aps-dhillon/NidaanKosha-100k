"""
Phase 2c (lean): Load the 3 small BI-ready tables to MySQL.
- patients:        100K rows (document_id, age, gender, age_group)
- disease_cohorts: 100K rows (patient + 10 has_* flags + key lab values)
- prevalence:      ~50 rows (age_group x gender x condition x pct)
The 6.8M-row lab_results is intentionally NOT loaded — Power BI
queries the curated aggregates, not raw lab values.
"""
import os, time
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import duckdb

load_dotenv()
DB_URL = (
    f"mysql+pymysql://{os.getenv('MYSQL_USER')}:{os.getenv('MYSQL_PASSWORD')}"
    f"@{os.getenv('MYSQL_HOST')}:{os.getenv('MYSQL_PORT')}/{os.getenv('MYSQL_DATABASE')}"
    f"?charset=utf8mb4"
)
engine = create_engine(DB_URL, pool_recycle=3600)
DUCK = r"E:/NidaanKosha-100k/data/nidaan.duckdb"
def log(m): print(f"[{time.strftime('%H:%M:%S')}] {m}", flush=True)

# ------------------------------------------------------------------
# 1) Ensure disease_cohorts exists in DuckDB; recompute prevalence view
# ------------------------------------------------------------------
log("Building DuckDB artifacts (disease_cohorts, prevalence) ...")
con = duckdb.connect(DUCK)   # read-write: need to CREATE OR REPLACE tables/views

# Recreate prevalence_by_demographics from disease_cohorts
con.execute("""
    CREATE OR REPLACE TEMP VIEW prev_unpivot AS
    SELECT document_id AS patient_id, age_group, gender,
           'anemia'           AS condition, has_anemia            AS flag FROM disease_cohorts
    UNION ALL
    SELECT document_id, age_group, gender, 'diabetes',          has_diabetes           FROM disease_cohorts
    UNION ALL
    SELECT document_id, age_group, gender, 'prediabetes',       has_prediabetes        FROM disease_cohorts
    UNION ALL
    SELECT document_id, age_group, gender, 'high_cholesterol',  has_high_cholesterol   FROM disease_cohorts
    UNION ALL
    SELECT document_id, age_group, gender, 'high_triglycerides',has_high_triglycerides FROM disease_cohorts
    UNION ALL
    SELECT document_id, age_group, gender, 'low_hdl',           has_low_hdl            FROM disease_cohorts
    UNION ALL
    SELECT document_id, age_group, gender, 'high_ldl',          has_high_ldl           FROM disease_cohorts
    UNION ALL
    SELECT document_id, age_group, gender, 'thyroid_disorder',  has_thyroid_disorder   FROM disease_cohorts
    UNION ALL
    SELECT document_id, age_group, gender, 'liver_issue',       has_liver_issue        FROM disease_cohorts
    UNION ALL
    SELECT document_id, age_group, gender, 'ckd',               has_ckd                FROM disease_cohorts
""")
con.execute("""
    CREATE OR REPLACE TABLE prevalence_by_demographics AS
    SELECT age_group, gender, condition,
           COUNT(*)::INT                              AS n_patients,
           SUM(flag)::INT                             AS n_positive,
           ROUND(100.0 * SUM(flag) / COUNT(*), 2)     AS pct
    FROM prev_unpivot
    GROUP BY age_group, gender, condition
    ORDER BY condition, age_group, gender
""")
log("  disease_cohorts and prevalence_by_demographics ready in DuckDB")

# ------------------------------------------------------------------
# 2) Read all 3 tables into pandas
# ------------------------------------------------------------------
log("Reading tables from DuckDB ...")
patients = con.execute("""
    SELECT DISTINCT document_id, age, gender,
        CASE
            WHEN age < 30 THEN '18-29'
            WHEN age < 45 THEN '30-44'
            WHEN age < 60 THEN '45-59'
            WHEN age < 75 THEN '60-74'
            ELSE '75+'
        END AS age_group
    FROM v_labs
""").fetchdf()
cohorts = con.execute("SELECT * FROM disease_cohorts").fetchdf()
prev    = con.execute("SELECT * FROM prevalence_by_demographics").fetchdf()
con.close()
log(f"  patients: {len(patients):,}")
log(f"  cohorts:  {len(cohorts):,}")
log(f"  prev:     {len(prev):,}")

# ------------------------------------------------------------------
# 3) Ensure MySQL tables exist with right schema
# ------------------------------------------------------------------
DDL_PATIENTS = """
CREATE TABLE IF NOT EXISTS patients (
    document_id  VARCHAR(32)  NOT NULL,
    age          TINYINT UNSIGNED NOT NULL,
    gender       VARCHAR(10)  NOT NULL,
    age_group    VARCHAR(10)  NOT NULL,
    PRIMARY KEY (document_id),
    INDEX idx_gender (gender),
    INDEX idx_age_group (age_group)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
"""
DDL_COHORTS = """
CREATE TABLE IF NOT EXISTS disease_cohorts (
    document_id          VARCHAR(32)  NOT NULL,
    age                  TINYINT UNSIGNED,
    gender               VARCHAR(10),
    age_group            VARCHAR(10),
    hba1c                DECIMAL(15,5),
    hemoglobin           DECIMAL(15,5),
    total_cholesterol    DECIMAL(15,5),
    triglycerides        DECIMAL(15,5),
    hdl                  DECIMAL(15,5),
    ldl                  DECIMAL(15,5),
    tsh                  DECIMAL(15,5),
    alt_sgpt             DECIMAL(15,5),
    ast_sgot             DECIMAL(15,5),
    creatinine           DECIMAL(15,5),
    egfr                 DECIMAL(15,5),
    has_anemia           TINYINT(1) NOT NULL DEFAULT 0,
    has_diabetes         TINYINT(1) NOT NULL DEFAULT 0,
    has_prediabetes      TINYINT(1) NOT NULL DEFAULT 0,
    has_high_cholesterol TINYINT(1) NOT NULL DEFAULT 0,
    has_high_triglycerides TINYINT(1) NOT NULL DEFAULT 0,
    has_low_hdl          TINYINT(1) NOT NULL DEFAULT 0,
    has_high_ldl         TINYINT(1) NOT NULL DEFAULT 0,
    has_thyroid_disorder TINYINT(1) NOT NULL DEFAULT 0,
    has_liver_issue      TINYINT(1) NOT NULL DEFAULT 0,
    has_ckd              TINYINT(1) NOT NULL DEFAULT 0,
    PRIMARY KEY (document_id),
    INDEX idx_age_group (age_group),
    INDEX idx_gender (gender)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
"""
DDL_PREV = """
CREATE TABLE IF NOT EXISTS prevalence_by_demographics (
    age_group    VARCHAR(10)  NOT NULL,
    gender       VARCHAR(10)  NOT NULL,
    `condition`  VARCHAR(30)  NOT NULL,
    n_patients   INT          NOT NULL,
    n_positive   INT          NOT NULL,
    pct          DECIMAL(5,2) NOT NULL,
    PRIMARY KEY (age_group, gender, `condition`),
    INDEX idx_condition (`condition`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
"""
with engine.begin() as c:
    c.execute(text(DDL_PATIENTS))
    c.execute(text(DDL_COHORTS))
    c.execute(text(DDL_PREV))
log("MySQL tables ensured")

# ------------------------------------------------------------------
# 4) Truncate + reload (idempotent)
# ------------------------------------------------------------------
def reload(df, table):
    log(f"  truncating {table} ...")
    with engine.begin() as c:
        c.execute(text(f"SET FOREIGN_KEY_CHECKS=0"))
        c.execute(text(f"TRUNCATE TABLE {table}"))
        c.execute(text(f"SET FOREIGN_KEY_CHECKS=1"))
    log(f"  inserting {len(df):,} rows into {table} ...")
    df.to_sql(table, engine, if_exists="append", index=False, chunksize=5_000)
    with engine.connect() as c:
        n = c.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
    log(f"  {table}: {n:,} rows verified")

reload(patients, "patients")
reload(cohorts,  "disease_cohorts")
reload(prev,     "prevalence_by_demographics")

log("DONE. MySQL warehouse ready for Power BI.")
log("  -> mysql nidaan_kosha.patients        (~100K rows)")
log("  -> mysql nidaan_kosha.disease_cohorts (~100K rows, 10 has_* flags)")
log("  -> mysql nidaan_kosha.prevalence_by_demographics (~50 rows)")
