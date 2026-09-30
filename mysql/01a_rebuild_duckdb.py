"""
Phase 2a (rebuild): persist loinc_dict + v_labs in DuckDB so they survive restarts.
This fixes the broken v_labs view from earlier sessions where loinc_dict was a temp table.
"""
import duckdb
import polars as pl

DUCK = r"E:/NidaanKosha-100k/data/nidaan.duckdb"
con = duckdb.connect(DUCK)  # read-write

# ---- 1. Drop broken artifacts ----
con.execute("DROP VIEW IF EXISTS v_labs")
con.execute("DROP TABLE IF EXISTS loinc_dict")
print("Dropped old v_labs view and loinc_dict table (if any)")

# ---- 2. Build persistent loinc_dict from the same clinical mapping ----
LOINC_CATEGORY = {
    # CBC
    "718-7": ("Hemoglobin", "blood", "cbc"),
    "20570-8": ("Hematocrit", "blood", "cbc"),
    "26453-1": ("RBC Count", "blood", "cbc"),
    "26464-8": ("WBC Count", "blood", "cbc"),
    "26515-7": ("Platelet Count", "blood", "cbc"),
    "30428-7": ("MCV", "blood", "cbc"),
    "26478-8": ("Lymphocyte %", "blood", "cbc"),
    "26474-7": ("Lymphocyte Absolute", "blood", "cbc"),
    "26499-4": ("Neutrophil Absolute", "blood", "cbc"),
    "26450-7": ("Eosinophil %", "blood", "cbc"),
    "26449-9": ("Eosinophil Absolute", "blood", "cbc"),
    "26485-3": ("Monocytes %", "blood", "cbc"),
    "26484-6": ("Monocytes Absolute", "blood", "cbc"),
    "30180-4": ("Basophils %", "blood", "cbc"),
    "26444-0": ("Basophils Absolute", "blood", "cbc"),
    "28539-5": ("MCH", "blood", "cbc"),
    "28540-3": ("MCHC", "blood", "cbc"),
    "30385-9": ("RDW CV", "blood", "cbc"),
    "30384-2": ("RDW SD", "blood", "cbc"),
    "28542-9": ("MPV", "blood", "cbc"),
    "48386-7": ("P-LCR", "blood", "cbc"),
    "51637-7": ("Plateletcrit", "blood", "cbc"),
    "30341-2": ("ESR", "blood", "cbc"),
    "53797-7": ("Neutrophils %", "blood", "cbc"),
    "19048-8": ("NRBC %", "blood", "cbc"),
    "51584-1": ("Immature Granulocytes", "blood", "cbc"),
    # Lipid
    "2093-3": ("Total Cholesterol", "serum", "lipid"),
    "2571-8": ("Triglycerides", "serum", "lipid"),
    "2085-9": ("HDL Cholesterol", "serum", "lipid"),
    "2089-1": ("LDL Cholesterol", "serum", "lipid"),
    "13457-7": ("Cholesterol Panels", "serum", "lipid"),
    "43396-1": ("Non-HDL Cholesterol", "serum", "lipid"),
    "9830-1": ("TC/HDL Ratio", "serum", "lipid"),
    "11054-4": ("LDL/HDL Ratio", "serum", "lipid"),
    "2091-7": ("VLDL Cholesterol", "serum", "lipid"),
    # Diabetes
    "4548-4": ("HbA1c", "blood", "diabetes"),
    "27353-2": ("eAG (Avg Glucose)", "blood", "diabetes"),
    "2345-7": ("Glucose", "serum", "diabetes"),
    "2344-0": ("Glucose Challenge", "serum", "diabetes"),
    # Liver
    "1742-6": ("ALT (SGPT)", "serum", "liver"),
    "1920-8": ("AST (SGOT)", "serum", "liver"),
    "1975-2": ("Bilirubin Total", "serum", "liver"),
    "1968-7": ("Bilirubin Direct", "serum", "liver"),
    "1971-1": ("Bilirubin Indirect", "serum", "liver"),
    "1751-7": ("Albumin", "serum", "liver"),
    "2885-2": ("Total Protein", "serum", "liver"),
    "6768-6": ("Alkaline Phosphatase", "serum", "liver"),
    "2324-2": ("GGT", "serum", "liver"),
    "1759-0": ("A/G Ratio", "serum", "liver"),
    "2336-6": ("Globulin", "serum", "liver"),
    # Kidney
    "2160-0": ("Creatinine", "serum", "kidney"),
    "3094-0": ("BUN", "serum", "kidney"),
    "3084-1": ("Uric Acid", "serum", "kidney"),
    "69405-9": ("eGFR", "serum", "kidney"),
    "3097-3": ("BUN/Creatinine Ratio", "serum", "kidney"),
    "17861-6": ("Calcium", "serum", "kidney"),
    # Thyroid
    "3016-3": ("TSH", "serum", "thyroid"),
    "3026-2": ("Total T4", "serum", "thyroid"),
    "3053-6": ("Total T3", "serum", "thyroid"),
    # Electrolytes
    "1963-8": ("Bicarbonate", "serum", "electrolytes"),
    "2075-0": ("Chloride", "serum", "electrolytes"),
    "2951-2": ("Sodium", "serum", "electrolytes"),
    "2823-3": ("Potassium", "serum", "electrolytes"),
    # Iron
    "2498-4": ("Iron", "serum", "iron"),
    "2500-7": ("TIBC", "serum", "iron"),
    "2502-3": ("Transferrin Saturation", "serum", "iron"),
    "2276-4": ("Ferritin", "serum", "iron"),
    # Vitamins
    "2132-9": ("Vitamin B12", "serum", "vitamins"),
    "62292-8": ("Vitamin D 25-OH", "serum", "vitamins"),
    "1754-1": ("Vitamin B12 (alt)", "serum", "vitamins"),
}

loinc_pdf = pl.DataFrame({
    "loinc": list(LOINC_CATEGORY.keys()),
    "canonical_test_name": [v[0] for v in LOINC_CATEGORY.values()],
    "specimen_default": [v[1] for v in LOINC_CATEGORY.values()],
    "category": [v[2] for v in LOINC_CATEGORY.values()],
}).to_pandas()

con.execute("CREATE TABLE loinc_dict AS SELECT * FROM loinc_pdf")
print(f"Persistent loinc_dict created: {con.execute('SELECT COUNT(*) FROM loinc_dict').fetchone()[0]} rows")

# ---- 3. Recreate v_labs VIEW (joins parquet + loinc_dict, persists across sessions) ----
con.execute("""
    CREATE OR REPLACE VIEW v_labs AS
    SELECT
        l.document_id,
        l.age,
        l.gender,
        l.test_name                                  AS test_name_raw,
        l.value                                      AS value_raw,
        l.unit,
        l.specimen,
        l.display_ranges                             AS display_range,
        l.loinc,
        d.canonical_test_name,
        d.category                                   AS loinc_category
    FROM read_parquet('E:/NidaanKosha-100k/data/raw/*.parquet') l
    LEFT JOIN loinc_dict d ON l.loinc = d.loinc
""")
n = con.execute("SELECT COUNT(*) FROM v_labs").fetchone()[0]
print(f"v_labs view created: {n:,} rows")

con.close()
print("Done. Re-open DuckDB in a new session to verify v_labs persists.")
