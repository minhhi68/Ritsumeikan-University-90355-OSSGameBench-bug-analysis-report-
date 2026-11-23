import os
import re
import shutil
import zipfile
import pandas as pd

links = pd.read_parquet("data/bug_pr_links.parquet")
pr_commit = pd.read_parquet("data/OSSGameBench/pr_commit.parquet")
need = links.merge(pr_commit, on=["project", "pr_number"])

project = need["project"].value_counts().index[0]
print("Checking project:", project)

zf = zipfile.ZipFile("dataset.zip")
key = re.escape(project.replace("/", "|"))
pattern = re.compile(r"commits?\|" + key + r"(\|\d+)?\.parquet$", re.IGNORECASE)
member = [n for n in zf.namelist() if pattern.search(os.path.basename(n))
          and not n.startswith("__MACOSX")][0]
with zf.open(member) as src, open("data/check.parquet", "wb") as dst:
    shutil.copyfileobj(src, dst, 16 * 1024 * 1024)
commits = pd.read_parquet("data/check.parquet", columns=["sha", "message", "files"])

# Idea 1: cut " master~1" off the ID, keep the 40-character ID
commits["sha_clean"] = commits["sha"].str.split().str[0]
a = set(need.loc[need["project"] == project, "commit_sha"])
print("Idea 1 - ID matches:", len(a & set(commits["sha_clean"])), "of", len(a))

# Idea 2: find "(#1234)" in the commit message
fix_prs = set(links.loc[links["project"] == project, "pr_number"])
commits["pr_in_message"] = commits["message"].str.extract(r"\(#(\d+)\)", expand=False)
commits["pr_in_message"] = pd.to_numeric(commits["pr_in_message"], errors="coerce")
found = commits[commits["pr_in_message"].isin(fix_prs)]
print("Idea 2 - fixing PRs found via message:", found["pr_in_message"].nunique(),
      "of", len(fix_prs))
print("Example message:", found["message"].head(2).tolist())