
# ---------- Phase 7b: co-occurrence network graph ----------
import pandas as pd
import networkx as nx
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

cooc = pd.read_csv(r"E:/NidaanKosha-100k/data/processed/disease_cooccurrence.csv")

# Filter: clinically meaningful associations
G = nx.Graph()
for _, r in cooc.iterrows():
    if r["n_both"] >= 200 and r["lift"] >= 1.20:
        G.add_edge(
            r["condition_a"], r["condition_b"],
            weight=r["lift"], n=int(r["n_both"])
        )

# Sizes proportional to condition prevalence
prev = {
    "anemia": 0.284, "diabetes": 0.252, "prediabetes": 0.211,
    "high_cholesterol": 0.312, "high_triglycerides": 0.395,
    "low_hdl": 0.484, "high_ldl": 0.252, "thyroid_disorder": 0.236,
    "liver_issue": 0.201, "ckd": 0.102,
}
sizes = [prev.get(n, 0.1) * 6000 for n in G.nodes()]
widths = [G[u][v]["weight"] * 0.6 for u, v in G.edges()]

fig, ax = plt.subplots(figsize=(14, 10))
pos = nx.spring_layout(G, k=2.2, seed=42, weight="weight")

# Color by clinical category
colors = {
    "anemia": "#e74c3c", "diabetes": "#9b59b6", "prediabetes": "#b07ecc",
    "high_cholesterol": "#f39c12", "high_triglycerides": "#f1c40f",
    "low_hdl": "#e67e22", "high_ldl": "#d35400",
    "thyroid_disorder": "#1abc9c", "liver_issue": "#2ecc71", "ckd": "#3498db",
}
node_colors = [colors.get(n, "#95a5a6") for n in G.nodes()]

nx.draw_networkx_nodes(G, pos, node_size=sizes, node_color=node_colors,
                       alpha=0.85, edgecolors="white", linewidths=2, ax=ax)
nx.draw_networkx_labels(G, pos, font_size=10, font_weight="bold", ax=ax)
nx.draw_networkx_edges(G, pos, width=widths, alpha=0.6, edge_color="#34495e", ax=ax)

# Edge labels for the top 5
top5 = sorted(G.edges(data=True), key=lambda e: e[2]["weight"], reverse=True)[:5]
edge_labels = {(u, v): f"lift={d['weight']:.2f}" for u, v, d in top5}
nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels, font_size=8, ax=ax)

ax.set_title("India Health Atlas — Disease Co-occurrence Network\n"
             "(edge width = lift, node size = prevalence, min n=200, lift≥1.20)",
             fontsize=14, fontweight="bold")
ax.axis("off")
plt.tight_layout()
out = r"E:/NidaanKosha-100k/reports/figures/02_cooccurrence_network.png"
plt.savefig(out, dpi=150, bbox_inches="tight", facecolor="white")
plt.show()
print(f"Saved -> {out}")
print(f"  Nodes (conditions): {G.number_of_nodes()}")
print(f"  Edges (associations): {G.number_of_edges()}")
