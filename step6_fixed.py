import pandas as pd

bugs = pd.read_parquet("data/closed_bugs.parquet")
issue_pr = pd.read_parquet("data/OSSGameBench/issue_pr.parquet")
pr = pd.read_parquet("data/OSSGameBench/pr.parquet",
                     columns=["project", "number", "merged_at"])

print("issue_pr columns:", list(issue_pr.columns))
print("Issue-PR links in dataset:", len(issue_pr))

# PRs that were merged (accepted)
merged = pr[pr["merged_at"].notna()].rename(columns={"number": "pr_number"})
print("Merged PRs:", len(merged), "of", len(pr))

# closed bug -> linked PR -> keep only merged PRs
links = bugs[["project", "number"]].rename(columns={"number": "issue_number"})
links = links.merge(issue_pr, on=["project", "issue_number"])
links = links.merge(merged[["project", "pr_number"]], on=["project", "pr_number"])

fixed = links[["project", "issue_number"]].drop_duplicates()
print("Closed bugs:", len(bugs))
print("Closed bugs with a merged PR (fixed with evidence):", len(fixed),
      f"({100 * len(fixed) / len(bugs):.1f}%)", "in", fixed["project"].nunique(), "projects")

links.to_parquet("data/bug_pr_links.parquet")
print("Saved data/bug_pr_links.parquet")