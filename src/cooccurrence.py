
# ---------- Phase 7a: pairwise disease co-occurrence with lift ----------
import duckdb
import pandas as pd

con = duckdb.connect(r"E:/NidaanKosha-100k/data/nidaan.duckdb")

# Auto-detect disease columns (has_* prefix) so this never breaks if names change
cols = con.execute("""
    SELECT column_name FROM information_schema.columns
    WHERE table_name = 'disease_cohorts' AND column_name LIKE 'has_%'
    ORDER BY column_name
""").fetchdf()["column_name"].tolist()

print(f"Found {len(cols)} disease columns: {cols}")
assert len(cols) >= 2, "Need at least 2 disease columns in disease_cohorts"

# Build (display_name, column_name) pairs
DISEASES = [(c.replace("has_", ""), c) for c in cols]

# 1) Marginal prevalence per disease -> temp table
marginal_parts = []
for display, col in DISEASES:
    marginal_parts.append(f"""
        SELECT '{display}' AS condition,
               SUM({col})::INT        AS n_pos,
               COUNT(*)::INT          AS n_total,
               ROUND(100.0*SUM({col})/COUNT(*), 2) AS pct
        FROM disease_cohorts
    """)
con.execute("CREATE OR REPLACE TEMP TABLE marginals AS\n" + "\nUNION ALL\n".join(marginal_parts))

# 2) Pairwise co-occurrence (n, % of a, % of b, confidence, lift)
co_occ_sql = """
    SELECT
        '{a}' AS condition_a,
        '{b}' AS condition_b,
        COUNT(*)::INT AS n_both,
        ROUND(100.0 * COUNT(*) / (SELECT n_total FROM marginals WHERE condition='{a}'), 2) AS pct_of_a,
        ROUND(100.0 * COUNT(*) / (SELECT n_total FROM marginals WHERE condition='{b}'), 2) AS pct_of_b,
        ROUND(1.0 * COUNT(*) / (SELECT n_pos FROM marginals WHERE condition='{a}'), 4)   AS conf_a_given_b,
        ROUND(1.0 * COUNT(*) / (SELECT n_pos FROM marginals WHERE condition='{b}'), 4)   AS conf_b_given_a,
        ROUND(
            (1.0 * COUNT(*)) /
            ( (SELECT n_pos   FROM marginals WHERE condition='{a}')::DOUBLE *
              (SELECT n_pos   FROM marginals WHERE condition='{b}')::DOUBLE /
              (SELECT n_total FROM marginals WHERE condition='{a}')::DOUBLE )
        , 2) AS lift
    FROM disease_cohorts
    WHERE {col_a}=1 AND {col_b}=1
    GROUP BY 1, 2
    ORDER BY n_both DESC
"""

rows = []
for i, (a_name, a_col) in enumerate(DISEASES):
    for b_name, b_col in DISEASES[i+1:]:
        sql = co_occ_sql.format(a=a_name, b=b_name, col_a=a_col, col_b=b_col)
        rows.append(con.execute(sql).fetchdf())

cooc = pd.concat(rows, ignore_index=True)
cooc.to_csv(r"E:/NidaanKosha-100k/data/processed/disease_cooccurrence.csv", index=False)
con.execute("CREATE OR REPLACE TABLE disease_cooccurrence AS SELECT * FROM cooc")
con.close()

print(f"\nPairwise combinations computed: {len(cooc)}")
print("\n--- Top 10 strongest associations (lift, min n_both=100) ---")
print(cooc[cooc.n_both>=100].sort_values("lift", ascending=False).head(10).to_string(index=False))
print("\n--- Top 10 most common pairs (n_both) ---")
print(cooc.sort_values("n_both", ascending=False).head(10).to_string(index=False))
print("\nSaved -> data/processed/disease_cooccurrence.csv  +  DuckDB table disease_cooccurrence")
