"""
Phase 9: SHAP explainability.
- Global: mean |SHAP| bar + beeswarm for each condition
- Per-patient: waterfall for one positive + one negative case
"""
import warnings
warnings.filterwarnings("ignore")
import sys
from pathlib import Path
import numpy as np
import pandas as pd
import shap
import xgboost as xgb
import matplotlib.pyplot as plt

# Reuse the modeling module's feature-selection logic (must match the trained model)
sys.path.insert(0, str(Path(__file__).resolve().parent))
from modeling import get_feature_columns, LEAKY_FEATURES   # noqa: E402

FEATURES_PARQUET = r"E:/NidaanKosha-100k/data/processed/patient_features.parquet"
MODELS_DIR       = Path(r"E:/NidaanKosha-100k/models")
FIGURES_DIR      = Path(r"E:/NidaanKosha-100k/reports/figures")
FIGURES_DIR.mkdir(parents=True, exist_ok=True)

LABEL_DISPLAY = {
    "anemia": "Anemia", "diabetes": "Diabetes", "prediabetes": "Prediabetes",
    "high_cholesterol": "High Cholesterol", "high_triglycerides": "High Triglycerides",
    "low_hdl": "Low HDL", "high_ldl": "High LDL",
    "thyroid_disorder": "Thyroid Disorder", "liver_issue": "Liver Issue", "ckd": "CKD",
}

# Conditions that have strong lab-based signals (best for SHAP demo)
SHAP_TARGETS = ["ckd", "diabetes", "anemia", "liver_issue"]


def get_features(df, condition_full):
    """Use the SAME feature set the model was trained on (with leakage exclusion)."""
    return get_feature_columns(df, condition=condition_full)


def explain(condition):
    print(f"\n--- SHAP for {LABEL_DISPLAY[condition]} ---")
    condition_full = f"has_{condition}"   # e.g. has_ckd
    model = xgb.XGBClassifier()
    model.load_model(MODELS_DIR / f"xgb_{condition}.json")

    df = pd.read_parquet(FEATURES_PARQUET)
    feats = get_features(df, condition_full)

    # Use a 5,000-row sample for speed (SHAP is slow on big N)
    sample = df.sample(n=min(5000, len(df)), random_state=42)
    X = sample[feats].astype(np.float32)

    explainer  = shap.TreeExplainer(model)
    shap_values = explainer.shap_values(X)

    # --- 1) Global importance bar ---
    plt.figure(figsize=(10, 6))
    shap.summary_plot(shap_values, X, plot_type="bar", show=False, max_display=15)
    plt.title(f"SHAP — {LABEL_DISPLAY[condition]} — top 15 drivers",
              fontsize=12, fontweight="bold")
    plt.tight_layout()
    bar = FIGURES_DIR / f"04_shap_bar_{condition}.png"
    plt.savefig(bar, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close()
    print(f"  -> {bar}")

    # --- 2) Beeswarm ---
    plt.figure(figsize=(10, 7))
    shap.summary_plot(shap_values, X, show=False, max_display=15)
    plt.title(f"SHAP beeswarm — {LABEL_DISPLAY[condition]}", fontsize=12, fontweight="bold")
    plt.tight_layout()
    bee = FIGURES_DIR / f"05_shap_beeswarm_{condition}.png"
    plt.savefig(bee, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close()
    print(f"  -> {bee}")

    # --- 3) Per-patient waterfall (one positive, one negative) ---
    pos_idx = sample[sample[condition_full] == 1].index
    neg_idx = sample[sample[condition_full] == 0].index
    if len(pos_idx) > 0 and len(neg_idx) > 0:
        # pick highest-probability positive and lowest-probability negative
        pp = model.predict_proba(X)[:, 1]
        i_pos = pos_idx[np.argmax(pp[sample.index.get_indexer(pos_idx)])]
        i_neg = neg_idx[np.argmin(pp[sample.index.get_indexer(neg_idx)])]

        for label, idx in [("positive_case", i_pos), ("negative_case", i_neg)]:
            try:
                plt.figure(figsize=(11, 6))
                shap.plots.waterfall(
                    shap.Explanation(values=shap_values[sample.index.get_loc(idx)],
                                     base_values=explainer.expected_value,
                                     data=X.iloc[sample.index.get_loc(idx)],
                                     feature_names=feats),
                    max_display=12, show=False
                )
                plt.title(f"SHAP waterfall — {LABEL_DISPLAY[condition]} — {label} "
                          f"(p={pp[sample.index.get_loc(idx)]:.2f})",
                          fontsize=11, fontweight="bold")
                plt.tight_layout()
                wf = FIGURES_DIR / f"06_shap_waterfall_{condition}_{label}.png"
                plt.savefig(wf, dpi=150, bbox_inches="tight", facecolor="white")
                plt.close()
                print(f"  -> {wf}")
            except Exception as e:
                print(f"  waterfall skip ({label}): {e}")

    return model, shap_values, X


if __name__ == "__main__":
    print("=" * 60)
    print("Phase 9: SHAP explainability")
    print("=" * 60)
    for cond in SHAP_TARGETS:
        try:
            explain(cond)
        except Exception as e:
            print(f"  {cond} FAILED: {e}")
    print("\nDONE.")
