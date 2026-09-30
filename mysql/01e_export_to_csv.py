"""
Export the 4 MySQL BI tables to CSV for Power BI import.
This bypasses the MySQL .NET connector issue entirely.
"""
import os
import pandas as pd
import sqlalchemy
from dotenv import load_dotenv

load_dotenv(r'E:\NidaanKosha-100k\.env')
url = "mysql+pymysql://" + os.getenv('MYSQL_USER') + ":" + os.getenv('MYSQL_PASSWORD')
url += "@" + os.getenv('MYSQL_HOST') + ":" + os.getenv('MYSQL_PORT')
url += "/" + os.getenv('MYSQL_DATABASE') + "?charset=utf8mb4"
engine = sqlalchemy.create_engine(url)

OUT = r"E:\NidaanKosha-100k\data\processed"
TABLES = [
    "patients",
    "disease_cohorts",
    "prevalence_by_demographics",
    "disease_cooccurrence",
]

print(f"Exporting to {OUT}\n")
for t in TABLES:
    df = pd.read_sql_table(t, engine)
    out = f"{OUT}/{t}.csv"
    df.to_csv(out, index=False, encoding="utf-8-sig")  # utf-8-sig for Excel/BI compatibility
    print(f"  {t:35s} -> {out}   ({len(df):,} rows, {os.path.getsize(out):,} bytes)")
print("\nDONE. Ready for Power BI CSV import.")
