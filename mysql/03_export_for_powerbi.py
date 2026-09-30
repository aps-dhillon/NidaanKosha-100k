"""
Export disease_cohorts + demographics summary as Power BI-ready CSV/Parquet.
"""
from pathlib import Path
import duckdb

DUCK = Path("E:/NidaanKosha-100k/data/nidaan.duckdb")
OUT = Path("E:/NidaanKosha-100k/data/processed")
OUT.mkdir(parents=True, exist_ok=True)

con = duckdb.connect(str(DUCK), read_only=True)

# One row per patient, with all 10 disease flags
print("Exporting per-patient disease cohort table...")
con.execute(f"""
    COPY (
        SELECT * FROM disease_cohorts
    ) TO '{OUT}/disease_cohorts.parquet' (FORMAT PARQUET, COMPRESSION ZSTD)
""")

# One row per (age_group, gender, condition) for the heatmap
print("Exporting demographic × condition crosstab...")
con.execute(f"""
    COPY (
        SELECT age_group, gender, condition, n_patients, pct
        FROM disease_prevalence_by_demographics
    ) TO '{OUT}/prevalence_crosstab.parquet' (FORMAT PARQUET, COMPRESSION ZSTD)
""")

# Co-occurrence matrix (long form: condition_a, condition_b, n_both, lift)
print("Exporting co-occurrence matrix...")
con.execute(f"""
    COPY (
        SELECT * FROM disease_cooccurrence
    ) TO '{OUT}/disease_cooccurrence.parquet' (FORMAT PARQUET, COMPRESSION ZSTD)
""")

print("All exports done.")
print(f"  -> {OUT}/disease_cohorts.parquet")
print(f"  -> {OUT}/prevalence_crosstab.parquet")
print(f"  -> {OUT}/disease_cooccurrence.parquet")
