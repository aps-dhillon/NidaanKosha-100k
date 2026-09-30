"""
Phase 5+6: Feature engineering for ML.
- Pivots v_labs to 1 row per patient with all key lab values
- Adds derived features: ratios, abnormality flags
- Saves to DuckDB (patient_features) + Parquet + CSV
"""
import duckdb
import pandas as pd
import numpy as np
from pathlib import Path

DUCK = r"E:/NidaanKosha-100k/data/nidaan.duckdb"
OUT  = Path(r"E:/NidaanKosha-100k/data/processed")
OUT.mkdir(parents=True, exist_ok=True)

# Map: (loinc_code, column_name, label) — expanded beyond the 10 used in disease_cohorts
LAB_FEATURES = [
    ("4548-4",  "hba1c",                  "HbA1c"),
    ("2345-7",  "glucose",                "Glucose"),
    ("718-7",   "hemoglobin",             "Hemoglobin"),
    ("20570-8", "hematocrit",             "Hematocrit"),
    ("26453-1", "rbc",                    "RBC"),
    ("26464-8", "wbc",                    "WBC"),
    ("26515-7", "platelet",               "Platelet"),
    ("30428-7", "mcv",                    "MCV"),
    ("28539-5", "mch",                    "MCH"),
    ("28540-3", "mchc",                   "MCHC"),
    ("30385-9", "rdw",                    "RDW"),
    ("2093-3",  "total_cholesterol",      "Total Cholesterol"),
    ("2571-8",  "triglycerides",          "Triglycerides"),
    ("2085-9",  "hdl",                    "HDL"),
    ("2089-1",  "ldl",                    "LDL"),
    ("43396-1", "non_hdl_cholesterol",    "Non-HDL"),
    ("1742-6",  "alt_sgpt",               "ALT (SGPT)"),
    ("1920-8",  "ast_sgot",               "AST (SGOT)"),
    ("1975-2",  "bilirubin_total",        "Bilirubin Total"),
    ("1751-7",  "albumin",                "Albumin"),
    ("2885-2",  "total_protein",          "Total Protein"),
    ("6768-6",  "alkaline_phosphatase",   "ALP"),
    ("2160-0",  "creatinine",             "Creatinine"),
    ("3094-0",  "bun",                    "BUN"),
    ("3084-1",  "uric_acid",              "Uric Acid"),
    ("69405-9", "egfr",                   "eGFR"),
    ("3016-3",  "tsh",                    "TSH"),
    ("2276-4",  "ferritin",               "Ferritin"),
    ("2498-4",  "iron",                   "Iron"),
    ("2500-7",  "tibc",                   "TIBC"),
    ("1963-8",  "bicarbonate",            "Bicarbonate"),
    ("2075-0",  "chloride",               "Chloride"),
    ("2951-2",  "sodium",                 "Sodium"),
    ("2823-3",  "potassium",              "Potassium"),
    ("17861-6", "calcium",                "Calcium"),
    ("2132-9",  "vitamin_b12",            "Vitamin B12"),
    ("62292-8", "vitamin_d",              "Vitamin D"),
]

def build_features() -> pd.DataFrame:
    con = duckdb.connect(DUCK, read_only=True)
    print(f"Building wide features: {len(LAB_FEATURES)} lab values")

    # 1) PIVOT: one row per patient with all numeric lab values
    pivot_cases = ",\n        ".join(
        f"MAX(CASE WHEN loinc='{loinc}' THEN TRY_CAST(value_raw AS DOUBLE) END) AS {col}"
        for loinc, col, _ in LAB_FEATURES
    )
    df = con.execute(f"""
        SELECT document_id, age, gender,
            CASE
                WHEN age < 30 THEN '18-29'
                WHEN age < 45 THEN '30-44'
                WHEN age < 60 THEN '45-59'
                WHEN age < 75 THEN '60-74'
                ELSE '75+'
            END AS age_group,
            {pivot_cases}
        FROM v_labs
        WHERE TRY_CAST(value_raw AS DOUBLE) IS NOT NULL
        GROUP BY document_id, age, gender
    """).fetchdf()
    print(f"  base shape: {df.shape}")

    # 2) DERIVED features
    df["tc_hdl_ratio"]    = df["total_cholesterol"] / df["hdl"]
    df["ldl_hdl_ratio"]   = df["ldl"]              / df["hdl"]
    df["bun_creat_ratio"] = df["bun"]              / df["creatinine"]
    df["ast_alt_ratio"]   = df["ast_sgot"]         / df["alt_sgpt"]
    df["trig_hdl_ratio"]  = df["triglycerides"]    / df["hdl"]     # atherogenic index
    df["non_hdl_calc"]    = df["total_cholesterol"] - df["hdl"]

    # 3) Encode gender
    df["is_male"] = (df["gender"].str.lower() == "male").astype(int)

    # 4) Missingness signal: how many key tests are missing per patient
    key_tests = ["hba1c", "hemoglobin", "total_cholesterol", "triglycerides",
                 "hdl", "ldl", "creatinine", "tsh", "alt_sgpt"]
    df["n_key_tests_done"]   = df[key_tests].notna().sum(axis=1)
    df["n_key_tests_missing"] = len(key_tests) - df["n_key_tests_done"]

    # 5) Lab COUNTS (panel richness)
    df["n_total_tests"] = con.execute("""
        SELECT document_id, COUNT(*)::INT AS n
        FROM v_labs GROUP BY document_id
    """).fetchdf().set_index("document_id")["n"]
    df["n_total_tests"] = df["n_total_tests"].fillna(0).astype(int)
    con.close()

    print(f"  final shape: {df.shape}")
    print(f"  cols: {list(df.columns)}")
    return df


def attach_labels(df: pd.DataFrame) -> pd.DataFrame:
    """Add the 10 disease flags from disease_cohorts."""
    con = duckdb.connect(DUCK, read_only=True)
    labels = con.execute("""
        SELECT document_id,
               has_anemia, has_diabetes, has_prediabetes,
               has_high_cholesterol, has_high_triglycerides,
               has_low_hdl, has_high_ldl, has_thyroid_disorder,
               has_liver_issue, has_ckd
        FROM disease_cohorts
    """).fetchdf()
    con.close()
    df = df.merge(labels, on="document_id", how="left")
    print(f"  shape after labels: {df.shape}")
    return df


def save(df: pd.DataFrame):
    # DuckDB (best for downstream SQL)
    con = duckdb.connect(DUCK)
    con.execute("DROP TABLE IF EXISTS patient_features")
    con.execute("CREATE TABLE patient_features AS SELECT * FROM df")
    print("  -> DuckDB table patient_features")
    con.close()
    # Parquet + CSV for Power BI / external tools
    df.to_parquet(OUT / "patient_features.parquet", index=False, compression="zstd")
    df.to_csv(OUT / "patient_features.csv", index=False)
    print(f"  -> {OUT}/patient_features.parquet")
    print(f"  -> {OUT}/patient_features.csv")
    # Lab coverage report
    coverage = pd.DataFrame({
        "feature": [c for _, c, _ in LAB_FEATURES],
        "label":   [l for _, _, l in LAB_FEATURES],
        "n_present":  df[[c for _, c, _ in LAB_FEATURES]].notna().sum().values,
        "pct_present": (df[[c for _, c, _ in LAB_FEATURES]].notna().sum().values * 100.0 / len(df)).round(1),
    }).sort_values("pct_present", ascending=False)
    coverage.to_csv(OUT / "lab_coverage.csv", index=False)
    print(f"  -> {OUT}/lab_coverage.csv  (lab test coverage report)")
    print("\n  Top 10 most-available tests:")
    print(coverage.head(10).to_string(index=False))
    print("\n  Bottom 10 (rarely tested):")
    print(coverage.tail(10).to_string(index=False))


if __name__ == "__main__":
    print("=" * 60)
    print("Phase 5+6: Feature engineering")
    print("=" * 60)
    df = build_features()
    df = attach_labels(df)
    save(df)
    print("\nDONE.")
