"""
Add the 4th MySQL table: disease_cooccurrence (for Power BI's Co-occurrence page).
Source: data/processed/disease_cooccurrence.csv (from src/cooccurrence.py)
"""
import os, time
import pandas as pd
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()
url = "mysql+pymysql://" + os.getenv("MYSQL_USER") + ":" + os.getenv("MYSQL_PASSWORD")
url += "@" + os.getenv("MYSQL_HOST") + ":" + os.getenv("MYSQL_PORT")
url += "/" + os.getenv("MYSQL_DATABASE") + "?charset=utf8mb4"
engine = create_engine(url)

CSV = r"E:/NidaanKosha-100k/data/processed/disease_cooccurrence.csv"
df  = pd.read_csv(CSV)
print(f"Loaded {len(df)} co-occurrence rows")

DDL = """
CREATE TABLE IF NOT EXISTS disease_cooccurrence (
    condition_a          VARCHAR(30) NOT NULL,
    condition_b          VARCHAR(30) NOT NULL,
    n_both               INT NOT NULL,
    pct_of_a             DECIMAL(5,2),
    pct_of_b             DECIMAL(5,2),
    conf_a_given_b       DECIMAL(6,4),
    conf_b_given_a       DECIMAL(6,4),
    lift                 DECIMAL(6,2),
    PRIMARY KEY (condition_a, condition_b),
    INDEX idx_lift (lift)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
"""
with engine.begin() as c:
    c.execute(text(DDL))
    c.execute(text("SET FOREIGN_KEY_CHECKS=0"))
    c.execute(text("TRUNCATE TABLE disease_cooccurrence"))
    c.execute(text("SET FOREIGN_KEY_CHECKS=1"))
df.to_sql("disease_cooccurrence", engine, if_exists="append", index=False, chunksize=200)
with engine.connect() as c:
    n = c.execute(text("SELECT COUNT(*) FROM disease_cooccurrence")).scalar()
print(f"MySQL disease_cooccurrence: {n:,} rows")
print("Done. MySQL now has 4 tables for Power BI.")
