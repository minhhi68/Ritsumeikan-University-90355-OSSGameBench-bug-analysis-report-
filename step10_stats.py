import math
import numpy as np
import pandas as pd

pd.set_option("display.width", 200)
rng = np.random.default_rng(42)          # fixed seed, so results can be reproduced
df = pd.read_parquet("data/analysis_table.parquet")
measures = ["ttc_days", "n_issue_comments", "n_pr_comments"]

# ---------- statistics written with numpy only ----------
def p_from_z(z):
    """two-sided p-value from a z score (normal approximation)"""
    return math.erfc(abs(z) / math.sqrt(2))

def mann_whitney(x, y):
    """returns (U, p) for two groups; ties handled"""
    x, y = np.asarray(x, float), np.asarray(y, float)
    n1, n2 = len(x), len(y)
    ranks = pd.Series(np.concatenate([x, y])).rank().values
    u = ranks[:n1].sum() - n1 * (n1 + 1) / 2
    n = n1 + n2
    _, t = np.unique(np.concatenate([x, y]), return_counts=True)
    var = n1 * n2 / 12 * ((n + 1) - (t ** 3 - t).sum() / (n * (n - 1)))
    z = (u - n1 * n2 / 2 - 0.5 * np.sign(u - n1 * n2 / 2)) / math.sqrt(var)
    return u, p_from_z(z)

def cliffs_delta(x, y):
    """+1: asset always larger, 0: no difference, -1: asset always smaller"""
    u, _ = mann_whitney(x, y)
    return 2 * u / (len(x) * len(y)) - 1

def wilcoxon_signed_rank(d):
    """p-value for 'median difference = 0' (zero differences dropped)"""
    d = np.asarray(d, float)
    d = d[d != 0]
    n = len(d)
    r = pd.Series(np.abs(d)).rank().values
    w = r[d > 0].sum()
    _, t = np.unique(np.abs(d), return_counts=True)
    var = n * (n + 1) * (2 * n + 1) / 24 - (t ** 3 - t).sum() / 48
    z = (w - n * (n + 1) / 4 - 0.5 * np.sign(w - n * (n + 1) / 4)) / math.sqrt(var)
    return p_from_z(z)

def bootstrap_ci(data, m, B=1000):
    """95% confidence interval for Cliff's delta, resampling whole projects"""
    per = [(g.loc[g["group"] == "asset", m].values, g.loc[g["group"] == "code_only", m].values)
           for _, g in data.groupby("project")]
    est = []
    for _ in range(B):
        idx = rng.integers(0, len(per), len(per))
        a = np.concatenate([per[i][0] for i in idx])
        c = np.concatenate([per[i][1] for i in idx])
        if len(a) and len(c):
            est.append(cliffs_delta(a, c))
    return np.percentile(est, [2.5, 97.5])

def fixed_effects_ols(data, y, xs, cluster):
    """OLS with one dummy per project (done by subtracting project means),
    standard errors clustered by project"""
    cols = [y] + xs
    dm = data[cols] - data.groupby(cluster)[cols].transform("mean")
    Y, X = dm[y].values, dm[xs].values
    XtX_inv = np.linalg.inv(X.T @ X)
    beta = XtX_inv @ X.T @ Y
    u = Y - X @ beta
    meat = np.zeros((len(xs), len(xs)))
    for _, idx in data.groupby(cluster).indices.items():
        s = X[idx].T @ u[idx]
        meat += np.outer(s, s)
    G, N = data[cluster].nunique(), len(Y)
    K = len(xs) + G          # slopes + one intercept per project
    V = XtX_inv @ meat @ XtX_inv * (G / (G - 1)) * ((N - 1) / (N - K))
    se = np.sqrt(np.diag(V))
    return beta, se

# ---------- 1. Plain comparison ----------
rows = []
for m in measures:
    a = df.loc[df["group"] == "asset", m]
    c = df.loc[df["group"] == "code_only", m]
    _, p = mann_whitney(a, c)
    lo, hi = bootstrap_ci(df, m)
    rows.append({"measure": m, "median_asset": a.median(), "median_code": c.median(),
                 "p_value": p, "cliffs_delta": round(cliffs_delta(a, c), 3),
                 "ci_low": round(lo, 3), "ci_high": round(hi, 3)})
res = pd.DataFrame(rows)
# Holm correction for testing 3 measures
order = res["p_value"].sort_values().index
adj, running = {}, 0
for k, i in enumerate(order):
    running = max(running, (len(res) - k) * res.loc[i, "p_value"])
    adj[i] = min(running, 1)
res["p_holm"] = pd.Series(adj)
print("1. PLAIN COMPARISON (asset vs code-only)")
print(res.to_string(index=False))

# ---------- 2. Inside the same project ----------
print("\n2. WITHIN-PROJECT COMPARISON (projects with >= 3 bugs in each group)")
wp_rows = []
for m in measures:
    med = df.groupby(["project", "group"])[m].agg(["median", "size"]).unstack()
    ok = (med[("size", "asset")] >= 3) & (med[("size", "code_only")] >= 3)
    diff = (med.loc[ok, ("median", "asset")] - med.loc[ok, ("median", "code_only")]).dropna()
    p = wilcoxon_signed_rank(diff) if (diff != 0).sum() >= 5 else np.nan
    wp_rows.append({"measure": m, "projects": len(diff),
                    "median_difference": round(diff.median(), 2),
                    "share_asset_higher": round((diff > 0).mean(), 2), "p_value": p})
wp = pd.DataFrame(wp_rows)
print(wp.to_string(index=False))

# ---------- 3a. Same-size fixes ----------
print("\n3a. MEDIAN DAYS TO CLOSE BY FIX SIZE")
df["size_bin"] = pd.cut(df["n_files"], [0, 2, 10, 50, np.inf],
                        labels=["1-2 files", "3-10", "11-50", ">50"])
strata = []
for b, sub in df.groupby("size_bin", observed=True):
    a = sub.loc[sub["group"] == "asset", "ttc_days"]
    c = sub.loc[sub["group"] == "code_only", "ttc_days"]
    if len(a) >= 5 and len(c) >= 5:
        strata.append({"size": b, "n_asset": len(a), "n_code": len(c),
                       "median_asset": round(a.median(), 1), "median_code": round(c.median(), 1),
                       "cliffs_delta": round(cliffs_delta(a, c), 3),
                       "p_value": mann_whitney(a, c)[1]})
st = pd.DataFrame(strata)
print(st.to_string(index=False))

# ---------- 3b. Regression controlling for fix size and project ----------
print("\n3b. REGRESSION: log(days+1) ~ asset + fix size + project")
both = df.groupby("project")["group"].nunique()
r = df[df["project"].isin(both[both == 2].index)].copy()
r["y"] = np.log1p(r["ttc_days"])
r["asset"] = (r["group"] == "asset").astype(float)
r["log_files"] = np.log1p(r["n_files"])
r["log_commits"] = np.log1p(r["n_commits"])
beta, se = fixed_effects_ols(r, "y", ["asset", "log_files", "log_commits"], "project")
b, s = beta[0], se[0]
reg = pd.DataFrame([{"bugs": len(r), "projects": r["project"].nunique(),
                     "asset_effect_percent": round(100 * (math.exp(b) - 1), 1),
                     "ci_low_percent": round(100 * (math.exp(b - 1.96 * s) - 1), 1),
                     "ci_high_percent": round(100 * (math.exp(b + 1.96 * s) - 1), 1),
                     "p_value": p_from_z(b / s)}])
print(reg.to_string(index=False))

res.to_csv("results/comparison.csv", index=False)
wp.to_csv("results/within_project.csv", index=False)
st.to_csv("results/size_strata.csv", index=False)
reg.to_csv("results/regression.csv", index=False)
print("\nSaved results/*.csv")
