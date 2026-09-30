"""
India Health Atlas — master pipeline.
Each step runs in a fresh subprocess so memory is fully released between phases.
Usage:
  python run_pipeline.py                # run all
  python run_pipeline.py --skip-mysql   # skip step 1 (MySQL already loaded)
  python run_pipeline.py --from 3       # resume from step 3 (modeling)
"""
import argparse
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PY   = sys.executable

STEPS = [
    ("STEP 1/4 — Lean MySQL load (patients + cohorts + prevalence)",
     "mysql/01c_load_lean_mysql.py"),
    ("STEP 2/4 — Feature engineering (wide pivot + derived)",
     "src/feature_engineering.py"),
    ("STEP 3/4 — XGBoost modeling (10 conditions)",
     "src/modeling.py"),
    ("STEP 4/4 — SHAP explainability (4 conditions)",
     "src/shap_analysis.py"),
]

def banner(s):
    print("\n" + "=" * 70)
    print(f"  {s}")
    print("=" * 70)

def run_step(idx, label, script):
    banner(label)
    t0 = time.time()
    proc = subprocess.run([PY, script], cwd=str(ROOT))
    elapsed = time.time() - t0
    if proc.returncode != 0:
        print(f"\n!!! Step {idx+1} FAILED with exit code {proc.returncode} ({elapsed:.1f}s)")
        sys.exit(proc.returncode)
    print(f"\n>>> Step {idx+1} OK ({elapsed:.1f}s, exit 0)")

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-mysql", action="store_true",
                    help="Skip step 1 (MySQL warehouse already loaded)")
    ap.add_argument("--from", type=int, default=1, dest="start",
                    help="Resume from step N (1..4)")
    args = ap.parse_args()

    t0 = time.time()
    for i, (label, script) in enumerate(STEPS):
        n = i + 1
        if n < args.start:
            continue
        if n == 1 and args.skip_mysql:
            print(f"--- skipping {label} (--skip-mysql) ---")
            continue
        run_step(i, label, script)

    print("\n" + "=" * 70)
    print(f"  PIPELINE COMPLETE — total wall time {time.time()-t0:.1f}s")
    print("=" * 70)
    print(f"\nOutputs:")
    print(f"  MySQL:  nidaan_kosha.patients, disease_cohorts, prevalence_by_demographics")
    print(f"  DuckDB: data/nidaan.duckdb tables: v_labs, disease_cohorts, patient_features, ...")
    print(f"  Models: models/xgb_*.json (10 conditions)")
    print(f"  Figures: reports/figures/*.png")
    print(f"  Metrics: data/processed/model_metrics.csv")
