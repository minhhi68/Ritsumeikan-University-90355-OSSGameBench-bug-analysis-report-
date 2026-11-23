import os
import pandas as pd

pd.set_option("display.width", 200)
os.makedirs("results", exist_ok=True)

groups = pd.read_parquet("data/bug_groups.parquet")
groups = groups[groups["group"].isin(["asset", "code_only"])]

issues = pd.read_parquet("data/OSSGameBench/issue.parquet",
                         columns=["project", "number", "title", "labels", "created_at", "closed_at"])
issues = issues.rename(columns={"number": "issue_number"})
df = groups.merge(issues, on=["project", "issue_number"])

# 1. time to close (days)
created = pd.to_datetime(df["created_at"], utc=True)
closed = pd.to_datetime(df["closed_at"], utc=True)
df["ttc_days"] = (closed - created).dt.total_seconds() / 86400
print("Negative or missing times removed:", (~(df["ttc_days"] >= 0)).sum())
df = df[df["ttc_days"] >= 0]

# 2. issue comments
ic = pd.read_parquet("data/OSSGameBench/issue_comment.parquet", columns=["project", "issue_number"])
ic = ic.groupby(["project", "issue_number"]).size().rename("n_issue_comments").reset_index()
df = df.merge(ic, on=["project", "issue_number"], how="left")

# 3. PR comments (all types), summed over the fixing PRs
links = pd.read_parquet("data/bug_pr_links.parquet").drop_duplicates()
pc = pd.read_parquet("data/OSSGameBench/pr_comment.parquet", columns=["project", "pr_number"])
pcs = pc.groupby(["project", "pr_number"]).size().rename("n_pr_comments").reset_index()
per_bug = (links.merge(pcs, on=["project", "pr_number"], how="left").fillna(0)
           .groupby(["project", "issue_number"])["n_pr_comments"].sum().reset_index())
df = df.merge(per_bug, on=["project", "issue_number"], how="left")

for c in ["n_issue_comments", "n_pr_comments"]:
    df[c] = df[c].fillna(0).astype(int)

# descriptive statistics per group
measures = ["ttc_days", "n_issue_comments", "n_pr_comments", "n_files", "n_commits"]
rows = []
for g, sub in df.groupby("group"):
    for m in measures:
        rows.append({"group": g, "measure": m, "bugs": len(sub),
                     "projects": sub["project"].nunique(),
                     "median": round(sub[m].median(), 2), "q1": round(sub[m].quantile(0.25), 2),
                     "q3": round(sub[m].quantile(0.75), 2), "mean": round(sub[m].mean(), 2)})
desc = pd.DataFrame(rows)
print(desc.to_string(index=False))

desc.to_csv("results/descriptive.csv", index=False)
df.to_parquet("data/analysis_table.parquet")
print("Saved results/descriptive.csv and data/analysis_table.parquet")