"""
Phase 2b: Load lab_results from DuckDB v_labs -> MySQL.
Run order:  01a_rebuild_duckdb.py  ->  01b_recreate_lab_results.py  ->  this file
"""
import os, time
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import duckdb
import polars as pl

load_dotenv()
DB_URL = (
    f"mysql+pymysql://{os.getenv('MYSQL_USER')}:{os.getenv('MYSQL_PASSWORD')}"
    f"@{os.getenv('MYSQL_HOST')}:{os.getenv('MYSQL_PORT')}/{os.getenv('MYSQL_DATABASE')}"
    f"?charset=utf8mb4"
)
engine = create_engine(DB_URL, pool_recycle=3600)

DUCK = r"E:/NidaanKosha-100k/data/nidaan.duckdb"
CHUNK = 250_000

def log(m): print(f"[{time.strftime('%H:%M:%S')}] {m}", flush=True)

# 1) Verify DuckDB v_labs is healthy
log("Verifying DuckDB v_labs ...")
con = duckdb.connect(DUCK, read_only=True)
n_total = con.execute("SELECT COUNT(*) FROM v_labs").fetchone()[0]
log(f"  v_labs rows: {n_total:,}")

# 2) Discover MySQL lab_results columns
log("Discovering MySQL lab_results schema ...")
with engine.connect() as c:
    cols = c.execute(text("""
        SELECT COLUMN_NAME FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'lab_results'
        ORDER BY ORDINAL_POSITION
    """)).fetchall()
my_cols = [c[0] for c in cols]
log(f"  MySQL columns: {my_cols}")

# 3) Map source expressions for each MySQL column
SOURCES = {
    "id":             None,                          # auto-increment
    "document_id":    "document_id",
    "age":            "age",
    "gender":         "gender",
    "loinc":          "COALESCE(loinc, 'UNKNOWN')",
    "loinc_category": "COALESCE(loinc_category, 'UNKNOWN')",
    "test_name_raw":  "COALESCE(test_name_raw, 'UNKNOWN')",
    "value_raw":      "value_raw",
    "value_num":      "TRY_CAST(value_raw AS DOUBLE)",
    "is_numeric":     "CASE WHEN TRY_CAST(value_raw AS DOUBLE) IS NULL THEN 0 ELSE 1 END",
    "unit":           "unit",
    "specimen":       "specimen",
    "display_range":  "display_range",
}
src_exprs = []
for c in my_cols:
    src = SOURCES.get(c)
    if src is None:
        continue
    if src == c:
        src_exprs.append(src)            # simple column -> no alias needed
    else:
        src_exprs.append(f"{src} AS {c}")   # DuckDB accepts unquoted AS alias for valid identifiers
select_sql = f"SELECT {', '.join(src_exprs)} FROM v_labs"
log(f"  Select: {select_sql[:120]}...")

# 4) Chunked insert
log(f"Inserting {n_total:,} rows in chunks of {CHUNK:,} ...")
t0 = time.time()
inserted = 0
for offset in range(0, n_total, CHUNK):
    df = con.execute(f"{select_sql} LIMIT {CHUNK} OFFSET {offset}").fetchdf()
    df.to_sql("lab_results", engine, if_exists="append", index=False, chunksize=5_000)
    inserted += len(df)
    elapsed = time.time() - t0
    rate = inserted / elapsed if elapsed else 0
    eta = (n_total - inserted) / rate if rate else 0
    log(f"  {inserted:>9,}/{n_total:,}  {rate:>7,.0f} rows/s  ETA {eta:>5.0f}s")
con.close()

# 5) Verify
log("Verifying counts ...")
with engine.connect() as c:
    n = c.execute(text("SELECT COUNT(*) FROM lab_results")).scalar()
    n_doc = c.execute(text("SELECT COUNT(DISTINCT document_id) FROM lab_results")).scalar()
    n_null_loinc = c.execute(text("SELECT COUNT(*) FROM lab_results WHERE loinc='UNKNOWN'")).scalar()
    n_numeric = c.execute(text("SELECT COUNT(*) FROM lab_results WHERE is_numeric=1")).scalar()
log(f"  rows:                {n:,}")
log(f"  distinct patients:   {n_doc:,}")
log(f"  unknown loinc:       {n_null_loinc:,}")
log(f"  numeric values:      {n_numeric:,} ({n_numeric*100.0/n:.1f}%)")
log(f"  total time:          {time.time()-t0:.1f}s")
log("DONE.")
