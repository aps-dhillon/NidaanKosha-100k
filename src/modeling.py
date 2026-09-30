"""
Phase 8: Predictive modeling with XGBoost.
- Trains one classifier per disease condition
- Handles class imbalance with scale_pos_weight
- Reports AUC-ROC, PR-AUC, accuracy, F1
- Saves models to models/ + ROC curves to reports/figures/
"""
import json, time
from pathlib import Path
import numpy as np
import pandas as pd
import duckdb
from sklearn.model_selection import train_test_split
from sklearn.metrics import (roc_auc_score, average_precision_score,
                             accuracy_score, f1_score, confusion_matrix,
                             roc_curve, precision_recall_curve)
import xgboost as xgb
import matplotlib.pyplot as plt

FEATURES_PARQUET = r"E:/NidaanKosha-100k/data/processed/patient_features.parquet"
MODELS_DIR       = Path(r"E:/NidaanKosha-100k/models")
FIGURES_DIR      = Path(r"E:/NidaanKosha-100k/reports/figures")
MODELS_DIR.mkdir(parents=True, exist_ok=True)
FIGURES_DIR.mkdir(parents=True, exist_ok=True)

DISEASE_COLS = [
    "has_anemia", "has_diabetes", "has_prediabetes",
    "has_high_cholesterol", "has_high_triglycerides",
    "has_low_hdl", "has_high_ldl", "has_thyroid_disorder",
    "has_liver_issue", "has_ckd",
]
LABEL_DISPLAY = {
    "has_anemia":            "Anemia",
    "has_diabetes":          "Diabetes",
    "has_prediabetes":       "Prediabetes",
    "has_high_cholesterol":  "High Cholesterol",
    "has_high_triglycerides":"High Triglycerides",
    "has_low_hdl":           "Low HDL",
    "has_high_ldl":          "High LDL",
    "has_thyroid_disorder":  "Thyroid Disorder",
    "has_liver_issue":       "Liver Issue",
    "has_ckd":               "CKD",
}

def get_feature_columns(df, condition=None):
    """Numeric lab + derived features (not age/gender dummies, not label cols).
    Excludes LEAKY features per condition — features that directly determine the label.
    Example: predicting has_anemia from hemoglobin < 12 is trivial; we drop hemoglobin."""
    drop = set(DISEASE_COLS + ["document_id", "gender", "age_group"])
    if condition:
        drop |= LEAKY_FEATURES.get(condition, set())
    return [c for c in df.columns if c not in drop]


# Features that directly determine the label — must be excluded to avoid data leakage
LEAKY_FEATURES = {
    "has_anemia":              {"hemoglobin", "hematocrit", "rbc", "mch", "mchc"},
    "has_diabetes":            {"hba1c", "glucose"},
    "has_prediabetes":         {"hba1c", "glucose"},
    "has_high_cholesterol":    {"total_cholesterol", "non_hdl_cholesterol",
                                "non_hdl_calc", "tc_hdl_ratio"},
    "has_high_triglycerides":  {"triglycerides", "trig_hdl_ratio"},
    "has_low_hdl":             {"hdl", "tc_hdl_ratio", "ldl_hdl_ratio", "trig_hdl_ratio"},
    "has_high_ldl":            {"ldl", "ldl_hdl_ratio", "non_hdl_calc", "non_hdl_cholesterol"},
    "has_thyroid_disorder":    {"tsh"},
    "has_liver_issue":         {"alt_sgpt", "ast_sgot", "ast_alt_ratio",
                                "bilirubin_total", "albumin", "alkaline_phosphatase"},
    "has_ckd":                 {"creatinine", "egfr", "bun", "bun_creat_ratio",
                                "uric_acid", "calcium", "albumin"},
}


def train_one_condition(df, condition, params=None):
    feats = get_feature_columns(df, condition)
    sub = df[feats + [condition]].dropna(subset=[condition])
    if sub[condition].nunique() < 2 or len(sub) < 1000:
        return {"condition": condition, "skipped": True, "reason": "insufficient data"}

    X = sub[feats].astype(np.float32).replace([np.inf, -np.inf], np.nan)
    y = sub[condition].astype(int)

    Xtr, Xte, ytr, yte = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    pos = ytr.sum()
    neg = len(ytr) - pos
    spw = max(1.0, neg / max(1, pos))   # handle class imbalance

    default = dict(
        n_estimators=400, max_depth=6, learning_rate=0.05,
        subsample=0.8, colsample_bytree=0.8,
        scale_pos_weight=spw,
        eval_metric="auc", tree_method="hist", random_state=42,
        early_stopping_rounds=30, n_jobs=-1,
    )
    if params: default.update(params)

    model = xgb.XGBClassifier(**default)
    model.fit(Xtr, ytr, eval_set=[(Xte, yte)], verbose=False)

    yp = model.predict(Xte)
    pp = model.predict_proba(Xte)[:, 1]
    metrics = {
        "condition":      condition,
        "label":          LABEL_DISPLAY[condition],
        "n_train":        int(len(Xtr)),
        "n_test":         int(len(Xte)),
        "prevalence_pct": round(y.mean() * 100, 2),
        "auc_roc":        round(roc_auc_score(yte, pp), 4),
        "auc_pr":         round(average_precision_score(yte, pp), 4),
        "accuracy":       round(accuracy_score(yte, yp), 4),
        "f1":             round(f1_score(yte, yp), 4),
        "best_iteration": int(model.best_iteration) if hasattr(model, "best_iteration") else None,
    }

    # Save model
    safe = condition.replace("has_", "")
    model.save_model(MODELS_DIR / f"xgb_{safe}.json")

    # Save ROC curve
    fpr, tpr, _ = roc_curve(yte, pp)
    return metrics, (fpr, tpr), model


def plot_combined_roc(results):
    plt.figure(figsize=(10, 8))
    for cond, (fpr, tpr), auc in results:
        plt.plot(fpr, tpr, label=f"{LABEL_DISPLAY[cond]} (AUC={auc:.3f})", lw=2)
    plt.plot([0,1], [0,1], "k--", alpha=0.4)
    plt.xlabel("False Positive Rate")
    plt.ylabel("True Positive Rate")
    plt.title("XGBoost — ROC curves for all 10 conditions", fontsize=13, fontweight="bold")
    plt.legend(loc="lower right", fontsize=9)
    plt.grid(alpha=0.3)
    out = FIGURES_DIR / "03_xgb_roc_curves.png"
    plt.tight_layout()
    plt.savefig(out, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close()
    print(f"  -> {out}")


def main():
    print("=" * 60)
    print("Phase 8: XGBoost modeling (one model per condition)")
    print("=" * 60)
    print("Loading patient_features ...")
    df = pd.read_parquet(FEATURES_PARQUET)
    print(f"  shape: {df.shape}")
    feats = get_feature_columns(df)
    print(f"  features (all): {len(feats)}")
    print(f"  leaky features excluded per condition (see LEAKY_FEATURES map)")

    all_metrics = []
    roc_data     = []
    t0 = time.time()
    for cond in DISEASE_COLS:
        ts = time.time()
        out = train_one_condition(df, cond)
        if isinstance(out, dict) and out.get("skipped"):
            print(f"  {cond:30s} SKIPPED ({out.get('reason')})")
            continue
        m, (fpr, tpr), model = out
        all_metrics.append(m)
        roc_data.append((cond, (fpr, tpr), m["auc_roc"]))
        elapsed = time.time() - ts
        print(f"  {m['label']:25s}  AUC={m['auc_roc']:.3f}  F1={m['f1']:.3f}  prev={m['prevalence_pct']:5.1f}%  [{elapsed:.1f}s]")

    print(f"\nTotal training time: {time.time()-t0:.1f}s")
    # Combined ROC plot
    plot_combined_roc(roc_data)
    # Save metrics
    metrics_df = pd.DataFrame(all_metrics).sort_values("auc_roc", ascending=False)
    metrics_df.to_csv(Path(r"E:/NidaanKosha-100k/data/processed/model_metrics.csv"), index=False)
    print("\n=== Model leaderboard (sorted by AUC-ROC) ===")
    print(metrics_df[["label", "prevalence_pct", "auc_roc", "auc_pr", "f1"]].to_string(index=False))
    # Save the LAST model in memory (used by SHAP step)
    return model, df, feats, DISEASE_COLS[-1]   # SHAP on ckd by default


if __name__ == "__main__":
    main()
