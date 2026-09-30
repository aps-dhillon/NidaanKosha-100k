# India Health Atlas — Power BI Build Guide

This guide walks you through building the 4-page interactive dashboard in Power BI Desktop from the MySQL warehouse. Estimated time: **30-60 min**.

---

## Prerequisites

- **Power BI Desktop** — https://powerbi.microsoft.com/desktop/ (free, Windows-only)
- MySQL server running locally with the `nidaan_kosha` database (already set up)
- The 4 MySQL tables populated (run the MySQL loader first)

---

## Step 1 — Connect to MySQL (5 min)

1. Open Power BI Desktop
2. **Home → Get Data → MySQL database**
3. Server: `localhost`
4. Database: `nidaan_kosha`
5. In the Navigator, select all 4 tables:
   - `patients` (100K rows)
   - `disease_cohorts` (100K rows)
   - `prevalence_by_demographics` (100 rows)
   - `disease_cooccurrence` (45 rows)
6. Click **Transform Data** to open Power Query Editor.

---

## Step 2 — Power Query transformations (10 min)

### 2a. `patients` table
- Rename `document_id` → `PatientID` (right-click → Rename, **avoid `document_id` collisions later**)
- Set data type: `age` = Whole Number, `age_group` = Text, `gender` = Text
- Close & Apply

### 2b. `disease_cohorts` table
- Rename `document_id` → `PatientID`
- All `has_*` columns: type = **Whole Number** (so they aggregate as COUNT)
- All lab value columns (`hba1c`, `hemoglobin`, etc.): type = Decimal Number
- `age`, `age_group`, `gender` — same as patients

### 2c. `prevalence_by_demographics` table
- `condition` has a backtick in the name in SQL — Power BI will show it as `` `condition` ``
- Rename to `condition_name` in Power Query (right-click → Rename)
- `pct`, `n_patients`, `n_positive`: Whole Number / Decimal

### 2d. `disease_cooccurrence` table
- No changes needed
- All numeric columns should auto-detect as Whole Number or Decimal

### 2e. Create a relationship
- **Model view** (left sidebar icon)
- Drag `patients[PatientID]` to `disease_cohorts[PatientID]`
- Cardinality: One-to-Many (1 patient → 1 cohort row)
- Cross filter: Single

---

## Step 3 — DAX measures (5 min)

In **Table view**, click on the `disease_cohorts` table → **New Measure**:

```dax
Total Patients = COUNTROWS(disease_cohorts)

Anemia Prev % = DIVIDE([Anemia Cases], [Total Patients], 0)
Anemia Cases = SUM(disease_cohorts[has_anemia])

Diabetes Prev % = DIVIDE([Diabetes Cases], [Total Patients], 0)
Diabetes Cases = SUM(disease_cohorts[has_diabetes])

Prediabetes Prev % = DIVIDE([Prediabetes Cases], [Total Patients], 0)
Prediabetes Cases = SUM(disease_cohorts[has_prediabetes])

High Chol Prev % = DIVIDE([High Chol Cases], [Total Patients], 0)
High Chol Cases = SUM(disease_cohorts[has_high_cholesterol])

High Trig Prev % = DIVIDE([High Trig Cases], [Total Patients], 0)
High Trig Cases = SUM(disease_cohorts[has_high_triglycerides])

Low HDL Prev % = DIVIDE([Low HDL Cases], [Total Patients], 0)
Low HDL Cases = SUM(disease_cohorts[has_low_hdl])

High LDL Prev % = DIVIDE([High LDL Cases], [Total Patients], 0)
High LDL Cases = SUM(disease_cohorts[has_high_ldl])

Thyroid Prev % = DIVIDE([Thyroid Cases], [Total Patients], 0)
Thyroid Cases = SUM(disease_cohorts[has_thyroid_disorder])

Liver Prev % = DIVIDE([Liver Cases], [Total Patients], 0)
Liver Cases = SUM(disease_cohorts[has_liver_issue])

CKD Prev % = DIVIDE([CKD Cases], [Total Patients], 0)
CKD Cases = SUM(disease_cohorts[has_ckd])
```

(Or use a single measure with a parameter — see "Advanced" below.)

---

## Step 4 — Page 1: Executive Summary (10 min)

Insert these visuals:

| Visual | Type | Data | Format |
|---|---|---|---|
| **Total Patients** | Card | `[Total Patients]` | Large font, bold |
| **Anemia Prevalence** | Card | `[Anemia Prev %]` formatted as % | 28.4% |
| **Diabetes Prevalence** | Card | `[Diabetes Prev %]` | 25.2% |
| **CKD Prevalence** | Card | `[CKD Prev %]` | 10.2% |
| **Prevalence by condition** | Clustered bar chart | Condition = `disease_cohorts` (unpivot manually OR use 10 separate measures), Value = Prevalence % | Sorted desc |
| **Gender split** | Donut chart | Legend: `gender`, Value: `COUNTROWS(patients)` | female vs male |
| **Age group distribution** | Stacked column chart | Axis: `age_group`, Legend: `gender`, Value: `COUNTROWS(patients)` | |
| **Slicer (top of page)** | Slicer | `age_group` | Multi-select |

Title: **"India Health Atlas — Executive Summary"**

---

## Step 5 — Page 2: Prevalence Atlas (10 min)

Heatmap of condition × age × gender (the headline finding).

| Visual | Type | Data |
|---|---|---|
| **Matrix (heatmap)** | Matrix visual | Rows: `age_group`, Columns: `condition` (from prevalence table), Values: `pct` (with conditional formatting: red-yellow-green diverging) |
| **Condition selector** | Slicer | `condition_name` (from prevalence table) — drives the bar chart below |
| **% by age × gender** | Clustered bar chart | Axis: `age_group`, Legend: `gender`, Value: `pct` filtered to selected condition |
| **KPI card** | Card | `pct` of selected condition (single number) |

Title: **"Disease Prevalence Atlas — Age × Gender"**

---

## Step 6 — Page 3: Co-occurrence Network (10 min)

| Visual | Type | Data |
|---|---|---|
| **Top 15 associations table** | Table visual | All columns of `disease_cooccurrence` sorted by `lift` desc |
| **Lift vs Prevalence scatter** | Scatter chart | X: `n_both` (log scale recommended), Y: `lift`, Details: `condition_a` & `condition_b`, Size: `lift` |
| **Slicer** | Slicer | `condition_a` to filter the table |

Title: **"Disease Co-occurrence — Lift Analysis"**

---

## Step 7 — Page 4: Patient Drill-Down (10 min)

| Visual | Type | Data |
|---|---|---|
| **Patient table** | Table visual | `document_id`, `age`, `gender`, all 10 `has_*` columns |
| **Slicer (any condition)** | Slicer | any `has_*` column — filters the table |
| **Age filter** | Slicer | `age` (range slider) |
| **Gender filter** | Slicer | `gender` |
| **Lab value card** | Multi-row card | Click a patient → show their `hba1c`, `hemoglobin`, `total_cholesterol`, `creatinine`, etc. |

Enable **cross-filtering** so clicking a patient filters other visuals.

Title: **"Patient Drill-Down"**

---

## Step 8 — Polish (10 min)

1. **Theme**: View → Themes → choose a clean theme (e.g., "Colorblind Safe")
2. **Logo / Title bar**: Insert → Text Box at top of each page with the page title
3. **Footer**: Add a small text box at bottom-right: *"Data: NidaanKosha-100k (Eka Care, CC BY-SA 4.0) | N=100,000"*
4. **Page navigation buttons**: Insert → Buttons → Blank → Action: Page navigation
5. **Background**: View → Page background → light gray

---

## Step 9 — Save & publish

- **Save as** `E:\NidaanKosha-100k\app\india_health_atlas.pbix`
- (Optional) Publish to Power BI Service for sharing (requires Microsoft account)

---

## Advanced: Single dynamic measure

Instead of 10 measures, use a parameter:

```dax
Selected Prev % = 
VAR _cond = SELECTEDVALUE('Condition Selector'[Condition], "anemia")
RETURN
SWITCH(
    _cond,
    "anemia",            [Anemia Prev %],
    "diabetes",          [Diabetes Prev %],
    ...
    BLANK()
)
```

This lets one card/chart respond to a slicer.

---

## Checklist before saving

- [ ] All 4 pages have titles
- [ ] All slicers work and don't show "no data" 
- [ ] KPI cards show actual percentages
- [ ] Footer cites the data source
- [ ] The .pbix file is < 20 MB (it should be; data is small)

---

**Once saved, share a screenshot of Page 1 (Executive Summary) and I'll update the README with it.**
