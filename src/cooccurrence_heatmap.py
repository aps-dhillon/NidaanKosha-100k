
# ---------- Phase 7b: co-occurrence heatmap (fixed) ----------
import pandas as pd
import numpy as np
import seaborn as sns
import matplotlib.pyplot as plt

cooc = pd.read_csv(r"E:/NidaanKosha-100k/data/processed/disease_cooccurrence.csv")

# Disease short labels for readability
LABELS = {
    "anemia": "Anemia", "diabetes": "Diabetes", "prediabetes": "Pre-DM",
    "high_cholesterol": "Hi Chol", "high_triglycerides": "Hi Trig",
    "low_hdl": "Low HDL", "high_ldl": "High LDL",
    "thyroid_disorder": "Thyroid", "liver_issue": "Liver", "ckd": "CKD",
}
PREV = {
    "anemia": 0.284, "diabetes": 0.252, "prediabetes": 0.211,
    "high_cholesterol": 0.312, "high_triglycerides": 0.395,
    "low_hdl": 0.484, "high_ldl": 0.252,
    "thyroid_disorder": 0.236, "liver_issue": 0.201, "ckd": 0.102,
}

# Build symmetric NxN lift matrix (numpy, no pandas views)
nodes = sorted(set(cooc.condition_a) | set(cooc.condition_b))
n = len(nodes)
idx = {name: i for i, name in enumerate(nodes)}

lift = np.ones((n, n), dtype=float)         # diagonal = 1.0
support = np.zeros((n, n), dtype=float)     # diagonal = 0.0
for _, r in cooc.iterrows():
    i, j = idx[r.condition_a], idx[r.condition_b]
    lift[i, j] = r["lift"]
    lift[j, i] = r["lift"]
    support[i, j] = r["pct_of_a"]
    support[j, i] = r["pct_of_b"]

# Sort nodes by prevalence (most common first)
order = sorted(range(n), key=lambda i: -PREV.get(nodes[i], 0))
nodes_sorted = [nodes[i] for i in order]
labels = [LABELS.get(n, n) for n in nodes_sorted]
lift_s      = lift[np.ix_(order, order)].copy()
support_s   = support[np.ix_(order, order)].copy()
lift_clip   = np.clip(lift_s, None, 3.0)     # cap at 3 for color

# Marginal prevalence strip
marg = np.array([PREV.get(n, 0) for n in nodes_sorted])

# --- Figure ---
sns.set_style("white")
fig = plt.figure(figsize=(20, 9))
gs = fig.add_gridspec(2, 3, width_ratios=[1, 8, 8], height_ratios=[1, 8],
                      wspace=0.3, hspace=0.3)

# Top marginal bar
ax_top = fig.add_subplot(gs[0, 1:])
ax_top.barh(labels, marg, color="#3498db", alpha=0.8, edgecolor="white")
ax_top.set_xlim(0, 0.55)
ax_top.invert_yaxis()
ax_top.set_yticks([])
ax_top.set_xlabel("Prevalence in cohort")
ax_top.set_title("Disease prevalence (marginal) — bars match heatmap order",
                 fontsize=11, loc="left")
for i, v in enumerate(marg):
    ax_top.text(v + 0.01, i, f"{v*100:.1f}%", va="center", fontsize=9)

# Heatmap 1: LIFT
ax1 = fig.add_subplot(gs[1, 1])
sns.heatmap(
    lift_clip, annot=True, fmt=".2f", cmap="RdYlGn", center=1.0,
    vmin=0.5, vmax=2.5, square=True, linewidths=0.5, linecolor="white",
    cbar_kws={"label": "Lift (1.0 = independent)"},
    xticklabels=labels, yticklabels=labels, ax=ax1, annot_kws={"size": 8}
)
ax1.set_title("LIFT — strength of association", fontsize=12, fontweight="bold")

# Heatmap 2: SUPPORT
ax2 = fig.add_subplot(gs[1, 2])
sns.heatmap(
    support_s, annot=True, fmt=".1f", cmap="YlOrRd",
    square=True, linewidths=0.5, linecolor="white",
    cbar_kws={"label": "% co-occurring"},
    xticklabels=labels, yticklabels=[], ax=ax2, annot_kws={"size": 8}
)
ax2.set_title("SUPPORT — % of patients with both", fontsize=12, fontweight="bold")

# Hide the empty top-left corner
fig.add_subplot(gs[0, 0]).axis("off")

plt.suptitle("India Health Atlas — Disease Co-occurrence (n=100,000 patients)",
             fontsize=15, fontweight="bold", y=1.00)
out = r"E:/NidaanKosha-100k/reports/figures/02_cooccurrence_heatmap.png"
plt.savefig(out, dpi=150, bbox_inches="tight", facecolor="white")
plt.show()
print(f"Saved -> {out}")
print(f"Conditions: {n}    Pairs analyzed: {len(cooc)}")
