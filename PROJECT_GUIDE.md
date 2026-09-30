# India Health Atlas — Complete Build Guide
## Step-by-step runbook from zero to Power BI dashboard

This document captures every command, decision, and lesson learned while building the **NidaanKosha-100k Indian Population Health Atlas** capstone. Use it as a reference, a portfolio piece, or a starting point for your own data engineering project.

---

## TABLE OF CONTENTS

1. Project Overview
2. Architecture (3-layer lakehouse)
3. Phase 0 — Environment Setup
4. Phase 1 — Project Scaffolding
5. Phase 2 — Data Architecture (DuckDB + MySQL)
6. Phase 3 — SQL EDA in DuckDB
7. Phase 5+6 — Feature Engineering
8. Phase 7 — Prevalence Atlas + Co-occurrence
9. Phase 8 — XGBoost Modeling
10. Phase 9 — SHAP Explainability
11. Phase 10 — Power BI Dashboard (in progress)
12. Phase 11 — Portfolio Polish (pending)
13. Key Concepts & Lessons Learned
14. What Was Generated (file inventory)

---

## 1. PROJECT OVERVIEW

**Goal:** Build a population health atlas + explainable disease-risk models for India on the **NidaanKosha-100k** dataset (100K patients, 6.8M lab readings, LOINC-coded).

**Deliverables:**
- 3-layer data pipeline (Parquet → DuckDB → MySQL/CSV)
- EDA: prevalence by age × gender, disease co-occurrence
- 10 XGBoost models (one per condition) with realistic AUCs
- SHAP explanations (global + per-patient)
- 4-page Power BI dashboard
- Portfolio-grade README + GitHub repo

**Tech stack:** Python 3.11, DuckDB, MySQL 8.0, Polars, Pandas, XGBoost, SHAP, Seaborn, Power BI Desktop.

---

## 2. ARCHITECTURE (3-LAYER LAKEHOUSE)

```
┌────────────────────────────────────────────────────┐
│  LAYER 1: BRONZE  (parquet files, read-only)      │
│  data/raw/*.parquet (Eka Care, CC BY-SA 4.0)       │
└────────────────────────────────────────────────────┘
                       ↓
┌────────────────────────────────────────────────────┐
│  LAYER 2: SILVER  (DuckDB analytical engine)       │
│  data/nidaan.duckdb                                │
│  → v_labs view, disease_cohorts, patient_features  │
│  → all EDA, modeling, SHAP happens here           │
└────────────────────────────────────────────────────┘
                       ↓
┌────────────────────────────────────────────────────┐
│  LAYER 3: GOLD  (BI-ready, small, denormalized)    │
│  MySQL (4 tables)  +  CSV exports                  │
│  → patients, disease_cohorts, prevalence, coocc   │
│  → Power BI connects here                         │
└────────────────────────────────────────────────────┘
```

**Why this pattern?**
- Parquet is immutable source; never modified.
- DuckDB reads parquet directly (no ETL), gives SQL ergonomics on 6.8M rows.
- MySQL/CSV holds only what Power BI actually needs (~200K rows, <20 MB).
- This is the **medallion / lakehouse** pattern used at Databricks, Snowflake, and modern data teams.

---

## 3. PHASE 0 — ENVIRONMENT SETUP

**Why this is needed:** Windows often has `python` pointing to a Microsoft Store stub. Anaconda Prompt (run as Administrator) is the cleanest way to manage isolated environments.

### Step 3.1: Install Anaconda (if not already)
Download from https://www.anaconda.com/download/ (skip registration, just download). Install to `C:\Users\<you>\anaconda3\`.

### Step 3.2: Launch Anaconda Prompt as Administrator
- Press Windows key, type "Anaconda Prompt", right-click → "Run as administrator"
- This is required because conda needs admin to create envs on Windows.

### Step 3.3: Create the conda env
```bash
conda create -n nidaan python=3.11 -y
conda activate nidaan
```

### Step 3.4: Install packages
```bash
pip install pandas polars pyarrow numpy scipy matplotlib seaborn plotly \
            scikit-learn xgboost lightgbm imbalanced-learn shap optuna \
            sqlalchemy pymysql mysql-connector-python python-dotenv \
            jupyterlab ipykernel duckdb
```

### Step 3.5: Register the Jupyter kernel
```bash
python -m ipykernel install --user --name nidaan --display-name "Python (nidaan)"
```

**Verify:**
```bash
python -c "import duckdb, xgboost, shap, sqlalchemy; print('all good')"
```

---

## 4. PHASE 1 — PROJECT SCAFFOLDING

### Step 4.1: Create project root
```bash
mkdir E:\NidaanKosha-100k
cd /d E:\NidaanKosha-100k
```

### Step 4.2: Create folder structure
```bash
mkdir data\raw data\processed mysql notebooks src app reports\figures models
```

### Step 4.3: Create `.env` (MySQL credentials, gitignored)
Use a password of your own choosing — do not commit real credentials.
```
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=nidaan_user
MYSQL_PASSWORD=<your-password-here>
MYSQL_DATABASE=nidaan_kosha
```

### Step 4.4: Create `.gitignore`
Ignore data/, models, .env, .ipynb_checkpoints, etc. (see file in repo).

### Step 4.5: Create `requirements.txt`
List all pip packages for reproducibility (see file in repo).

### Step 4.6: Create `README.md` (portfolio-facing)
Use the README template in repo; update with results at the end.

### Step 4.7: Add `.gitkeep` to empty dirs
For `app/`, `models/`, `src/`, `data/processed/` so they're tracked by git even when empty.

---

## 5. PHASE 2 — DATA ARCHITECTURE (DuckDB + MySQL)

### Step 5.1: Download the dataset
- Source: https://huggingface.co/datasets/ekacare/NidaanKosha-100k-V1.0
- Download both parquet files to `E:\NidaanKosha-100k\data\raw\`
- Verify SHA256 hashes (provided on HF page)

### Step 5.2: Inspect with Polars
```python
import polars as pl
df = pl.read_parquet(r"E:\NidaanKosha-100k\data\raw\*.parquet")
print(df.shape)           # (6_844_304, 9)
print(df.dtypes)          # columns: document_id, age, gender, test_name, value, unit, specimen, display_ranges, loinc
print(df.n_unique())      # 100,000 patients, 581 LOINC codes
```

### Step 5.3: MySQL setup
- Install MySQL 8.0 via the MySQL Installer (https://dev.mysql.com/downloads/installer/)
- During install, set a root password (any — just remember it)
- Open MySQL Workbench or `mysql -u root -p` and run (replace the placeholder password with your own):
```sql
CREATE DATABASE nidaan_kosha CHARACTER SET utf8mb4;
CREATE USER 'nidaan_user'@'localhost' IDENTIFIED BY '<your-password-here>';
GRANT ALL PRIVILEGES ON nidaan_kosha.* TO 'nidaan_user'@'localhost';
FLUSH PRIVILEGES;
```

### Step 5.4: Create the LOINC dictionary
A hand-curated mapping of 70 LOINC codes to 9 clinical categories (cbc, lipid, diabetes, liver, kidney, thyroid, electrolytes, iron, vitamins). The full mapping is in `notebooks/01_data_ingestion.ipynb` cell 4.

### Step 5.5: Build the DuckDB v_labs view
Run `mysql/01a_rebuild_duckdb.py` (created in this project):
- Persists `loinc_dict` (70 rows) as a real DuckDB table (not temp — survives restart)
- Creates `v_labs` as a view joining parquet + loinc_dict
- Result: 6,844,304 rows × 11 columns

### Step 5.6: Load MySQL (lean, BI-ready only)
Run `mysql/01c_load_lean_mysql.py`:
- Creates 3 tables: `patients` (100K), `disease_cohorts` (100K), `prevalence_by_demographics` (100)
- Coalesces nulls in test_name + loinc (avoids 3-row edge case)
- Total: ~30 sec, ~20 MB

**Why not load the 6.8M lab_results to MySQL?** Power BI never queries raw lab values — it queries the curated aggregates. Loading 6.8M rows to MySQL = 5-10 min load time, 700 MB DB, zero benefit.

### Step 5.7: Export CSVs as backup (used in this project)
Run `mysql/01e_export_to_csv.py` to export the 4 MySQL tables to CSVs in `data/processed/`. This is the fallback path when the MySQL connector doesn't work in Power BI (which it didn't for us — see Phase 10).

---

## 6. PHASE 3 — SQL EDA IN DUCKDB

The `disease_cohorts` table is the centerpiece. It applies standard clinical cutoffs:

| Condition | Definition |
|---|---|
| has_anemia | (gender=F AND hemoglobin<12) OR (gender=M AND hemoglobin<13) |
| has_diabetes | hba1c ≥ 6.5 |
| has_prediabetes | 5.7 ≤ hba1c < 6.5 |
| has_high_cholesterol | total_cholesterol ≥ 200 |
| has_high_triglycerides | triglycerides ≥ 150 |
| has_low_hdl | (F: hdl<50) OR (M: hdl<40) |
| has_high_ldl | ldl ≥ 130 |
| has_thyroid_disorder | tsh < 0.4 OR tsh > 4.0 |
| has_liver_issue | alt > 40 OR ast > 40 |
| has_ckd | egfr < 90 |

**Overall prevalence** (from our run):
- Low HDL: 48.4% • High Trig: 39.5% • High Chol: 31.2% • Anemia: 28.4% • Diabetes: 25.2% • High LDL: 25.2% • Thyroid: 23.6% • Prediabetes: 21.1% • Liver: 20.1% • CKD: 10.2%

**Key clinical findings:**
- Liver issues **3-4× higher in males** (33-38% vs 5-12% in females)
- Anemia much higher in females (36-55% vs 7-33% in males)
- CKD rises from 1% in 18-29 to 30% in 75+

---

## 7. PHASE 5+6 — FEATURE ENGINEERING

**Script:** `src/feature_engineering.py`

**Steps:**
1. **Pivot** v_labs to 1 row per patient with 37 lab values
2. **Derive** 6 ratio features (TC/HDL, LDL/HDL, BUN/Cr, AST/ALT, Trig/HDL, Non-HDL)
3. **Encode** gender as `is_male` (0/1)
4. **Count** tests done per patient (panel richness signal)
5. **Attach** 10 disease labels from `disease_cohorts`
6. **Save** to DuckDB table + Parquet + CSV

**Output shape:** 99,998 rows × 61 columns

**Lab coverage (key for portfolio):**
- Hemoglobin 99.6%, Total Cholesterol 99.6%, RBC 97.8% — most patients have these
- Vitamin D 45.5%, eGFR 39.8%, Bicarbonate 3.2% — sparse
- Glucose 0% (LOINC code 2345-7 not in our 70-code dictionary — but HbA1c covers diabetes)

---

## 8. PHASE 7 — PREVALENCE ATLAS + CO-OCCURRENCE

### 8.1 Prevalence heatmap
`src/cooccurrence.py` and `reports/figures/01_prevalence_heatmap.png`:
- Rows: age groups (18-29, 30-44, 45-59, 60-74, 75+)
- Columns: conditions
- Cells: percentage of patients in that demographic with that condition
- **Color scale:** red = high, blue = low

### 8.2 Co-occurrence
`src/cooccurrence_heatmap.py` → `reports/figures/02_cooccurrence_heatmap.png`:
- Self-join `disease_cohorts` on `document_id`
- Compute **lift** = P(A ∩ B) / (P(A) × P(B))
- Top associations (lift):
  - High chol × High LDL: **2.83** (same molecule)
  - High chol × High trig: 1.45 (atherogenic)
  - **CKD × Diabetes: 1.42** (diabetic nephropathy)
  - High trig × Liver: 1.32 (NAFLD)
  - **Anemia × CKD: 1.29** (CKD-induced, low EPO)

---

## 9. PHASE 8 — XGBoost MODELING

**Script:** `src/modeling.py`

### 9.1 The leakage fix (critical)
First run gave AUC=1.0 for every model — **suspicious**. The issue: the label `has_anemia` is defined as `hemoglobin < threshold`, and `hemoglobin` is a feature. The model cheats by reading the threshold.

**Fix:** For each condition, exclude the lab value(s) that directly define the label:

| Condition | Excluded features |
|---|---|
| anemia | hemoglobin, hematocrit, RBC, MCH, MCHC |
| diabetes / prediabetes | hba1c, glucose |
| high_chol | total_cholesterol, non_hdl, tc_hdl_ratio |
| high_trig | triglycerides, trig_hdl_ratio |
| low_hdl | hdl, *_hdl_ratio |
| high_ldl | ldl, ldl_hdl_ratio |
| thyroid | tsh |
| liver | alt_sgpt, ast_sgot, ast_alt_ratio, bilirubin, albumin, ALP |
| ckd | creatinine, egfr, bun, uric_acid, calcium, albumin |

Defined in `LEAKY_FEATURES` dict in `modeling.py`.

### 9.2 Final model leaderboard (realistic AUCs)

| Condition | Prevalence | AUC-ROC | F1 |
|---|---|---|---|
| Low HDL | 48.4% | **0.999** | 0.982 |
| High LDL | 25.2% | 0.986 | 0.892 |
| High Cholesterol | 31.2% | 0.983 | 0.906 |
| High Triglycerides | 39.5% | 0.946 | 0.853 |
| Diabetes | 25.2% | 0.901 | 0.687 |
| Anemia | 28.4% | 0.880 | 0.691 |
| CKD | 10.2% | 0.857 | 0.451 |
| Liver Issue | 20.1% | 0.805 | 0.523 |
| Prediabetes | 21.1% | 0.803 | 0.514 |
| Thyroid | 23.6% | 0.729 | 0.474 |

### 9.3 Implementation details
- 80/20 train-test split, stratified
- `scale_pos_weight` for class imbalance
- `early_stopping_rounds=30`, `eval_metric='auc'`
- Models saved to `models/xgb_<condition>.json`

---

## 10. PHASE 9 — SHAP EXPLAINABILITY

**Script:** `src/shap_analysis.py`

For 4 conditions (CKD, Diabetes, Anemia, Liver Issue), generates 3 figures each:
1. **Bar plot** — top 15 global features by mean |SHAP|
2. **Beeswarm** — feature value vs SHAP value (direction + magnitude)
3. **Waterfall** — one positive + one negative patient breakdown

**Total: 16 SHAP figures** in `reports/figures/`

**Critical fix:** The original SHAP script failed with "expected 48 features, got 41" because the model was trained on the **leakage-excluded** feature subset. Fix: import `get_feature_columns(condition=...)` from `modeling.py` so SHAP uses the SAME features the model was trained on.

---

## 11. PHASE 10 — POWER BI DASHBOARD (CURRENT STEP)

### 11.1 The MySQL connector problem
**Issue:** Power BI's "MySQL database" connector requires the MySQL .NET Connector. We installed MySQL Connector/NET 8.4.0 and copied `MySql.Data.dll` to Power BI's `bin\` directory. Connection still failed with "Unable to connect to any of the specified MySQL hosts" — likely a `caching_sha2_password` (MySQL 8.0 default) vs .NET connector compatibility issue.

**Resolution:** Switched to **Option B — CSV export**. We exported the 4 MySQL tables to CSVs (12 MB total) and import those into Power BI via "Get Data → Text/CSV".

### 11.2 Step-by-step: what we did

1. **Ran the CSV exporter:**
   ```bash
   python mysql\01e_export_to_csv.py
   ```
   Output: 4 CSVs in `data/processed/`

2. **Opened Power BI Desktop** (installed at `D:\Microsoft Power BI Desktop\bin\PBIDesktop.exe`)

3. **Imported 4 CSVs** (one at a time):
   - `patients.csv` → Transform Data → verify types → Close & Apply
   - `disease_cohorts.csv` → Transform Data → verify `has_*` columns are Whole Number → Close & Apply
   - `prevalence_by_demographics.csv` → Load
   - `disease_cooccurrence.csv` → Load

4. **Did NOT fix null values** in Power Query. They are correct — not every patient gets every test. Power BI handles them in aggregations.

5. **Created the relationship** in Model view:
   - `patients[document_id]` ↔ `disease_cohorts[document_id]` — **1:1** (auto-detected)
   - Summary tables (`prevalence_by_demographics`, `disease_cooccurrence`) intentionally unconnected — they're aggregates

6. **Switched to Report view** and renamed Page 1 to `Executive Summary`

7. **Added first visual: Total Patients card** — dragged the `Card` visual, checked `patients[document_id]`, should show `100K`

### 11.3 What's next (in progress)

Building the 4 dashboard pages — see `app/POWER_BI_BUILD_GUIDE.md` for the full spec:

| Page | Title | Key visuals |
|---|---|---|
| 1 | Executive Summary | 4 KPI cards, bar chart of prevalence, donut of gender, column of age, slicer |
| 2 | Prevalence Atlas | Matrix heatmap (age × condition), bar chart by gender, slicer |
| 3 | Co-occurrence | Top 15 lift table, scatter (n_both vs lift), slicer |
| 4 | Patient Drill-Down | Searchable patient table with all 10 has_* flags, slicers, lab value card |

### 11.4 DAX measures
Provided in `app/POWER_BI_BUILD_GUIDE.md`. Key pattern:
```dax
Anemia Cases  = SUM(disease_cohorts[has_anemia])
Anemia Prev % = DIVIDE([Anemia Cases], [Total Patients], 0)
Total Patients = COUNTROWS(disease_cohorts)
```

---

## 12. PHASE 11 — PORTFOLIO POLISH (PENDING)

- [ ] Update `README.md` with final results + figures + architecture diagram
- [ ] Write a blog post (Medium / dev.to): "Building a Population Health Atlas for India on 6.8M Lab Readings"
- [ ] Push to GitHub with clean commit history
- [ ] Take screenshots of all 4 Power BI pages
- [ ] Optional: Deploy to Power BI Service (free)

---

## 13. KEY CONCEPTS & LESSONS LEARNED

### 13.1 Why DuckDB instead of just MySQL
- DuckDB reads parquet natively — no ETL, no schema conversion
- Full SQL on 6.8M rows in <1 sec (vs 5-10 min in MySQL)
- MySQL is for Power BI only (BI delivery layer), not for analytics

### 13.2 The 3-layer lakehouse pattern
- **Bronze** (parquet): immutable source
- **Silver** (DuckDB): cleaned, joined, queryable
- **Gold** (MySQL/CSV): aggregated, BI-ready
- Same pattern as Databricks medallion architecture

### 13.3 Data leakage in feature engineering
- If your label is a function of a feature, the model has perfect info to cheat
- Always: identify which features define which labels, exclude them per-condition
- Always: check for AUC=1.0 — it's a red flag, not a success

### 13.4 The MySQL Connector/NET issue
- Power BI needs the .NET driver in its `bin\` directory (not just GAC)
- MySQL 8.0 `caching_sha2_password` has compatibility issues with older .NET drivers
- Fallback: export CSVs from MySQL, import those into Power BI

### 13.5 Null values in medical data
- Null ≠ zero ≠ missing
- Null means "not tested" — medically meaningful
- Don't impute in Power Query; let the model handle it (median imputation) or let Power BI show "(Blank)"

### 13.6 Why the subprocess orchestrator
- `exec()` in the same Python process = memory accumulates across phases
- `subprocess.run()` = each phase gets its own process, OS reclaims memory on exit
- Always: prefer subprocess for multi-step data pipelines

### 13.7 Anaconda Prompt as Administrator
- Required on Windows because conda needs admin to create envs
- Use a second Anaconda Prompt for non-Jupyter commands; never Ctrl+C the running Jupyter prompt
- Use full Python path (`C:\Users\abhay\anaconda3\envs\nidaan\python.exe`) when running scripts outside Anaconda Prompt

---

## 14. WHAT WAS GENERATED (FILE INVENTORY)

### Code files
- `README.md` — portfolio-facing project description
- `requirements.txt` — pip dependencies
- `.env` — MySQL credentials (gitignored)
- `.gitignore` — standard Python + data ignores
- `run_pipeline.py` — top-level orchestrator (subprocess per phase)

### MySQL scripts (`mysql/`)
- `01a_rebuild_duckdb.py` — persist loinc_dict + v_labs
- `01b_recreate_lab_results.py` — recreate MySQL lab_results (not used; CSV path)
- `01c_load_lean_mysql.py` — load 3 BI tables to MySQL
- `01d_add_cooccurrence.py` — add 4th table (co-occurrence)
- `01e_export_to_csv.py` — export 4 tables to CSV (used in Power BI)
- `02_load_lab_results.py` — original 6.8M load (deprecated)
- `03_export_for_powerbi.py` — original export script (superseded)

### Source code (`src/`)
- `cooccurrence.py` — pairwise co-occurrence + lift
- `cooccurrence_heatmap.py` — co-occurrence visualization
- `cooccurrence_network.py` — network graph (needs networkx)
- `feature_engineering.py` — wide pivot + derived features
- `modeling.py` — XGBoost per condition (with leakage fix)
- `shap_analysis.py` — SHAP bar + beeswarm + waterfall

### Notebooks (`notebooks/`)
- `00_env_setup.ipynb` — initial environment test
- `01_data_ingestion.ipynb` — original data exploration + DuckDB + MySQL schema

### Generated figures (`reports/figures/`)
- `01_prevalence_heatmap.png` — age × gender × condition heatmap
- `02_cooccurrence_heatmap.png` — pairwise disease co-occurrence
- `03_xgb_roc_curves.png` — all 10 model ROC curves
- `04_shap_bar_<condition>.png` × 4 — SHAP global importance
- `05_shap_beeswarm_<condition>.png` × 4 — SHAP value distribution
- `06_shap_waterfall_<condition>_<positive|negative>.png` × 8 — per-patient explanations

### Generated data (`data/processed/`)
- `patients.csv` (4.9 MB)
- `disease_cohorts.csv` (12 MB)
- `prevalence_by_demographics.csv` (4 KB)
- `disease_cooccurrence.csv` (2.6 KB)
- `patient_features.parquet` (8.8 MB)
- `patient_features.csv` (30 MB)
- `lab_coverage.csv` (1 KB)
- `model_metrics.csv` (862 B)

### Saved models (`models/`)
- `xgb_<condition>.json` × 10 — one per disease condition (~2.5-2.7 MB each)

### Power BI (`app/`)
- `POWER_BI_BUILD_GUIDE.md` — step-by-step dashboard build spec
- `india_health_atlas.pbix` — final dashboard (to be created)

---

## TOTAL: 30+ files, 19 figures, 10 models, 4 Power BI pages, 1 polished portfolio repo.

**Last updated:** End of Phase 10 (Power BI Page 1 in progress).
