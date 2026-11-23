import os
import re
import shutil
import zipfile
import numpy as np
import pandas as pd

links = pd.read_parquet("data/bug_pr_links.parquet")
pr_commit = pd.read_parquet("data/OSSGameBench/pr_commit.parquet")
need = links.merge(pr_commit, on=["project", "pr_number"])

zf = zipfile.ZipFile("dataset.zip")
commit_members = [n for n in zf.namelist()
                  if "/commits/" in n and not n.startswith("__MACOSX")]

# "(#1234)" (squash merge) or "Merge pull request #1234" (merge commit)
PR_IN_MSG = re.compile(r"\(#(\d+)\)|Merge pull request #(\d+)")

def to_list(x):
    if isinstance(x, np.ndarray):
        return x.tolist()
    if isinstance(x, list):
        return x
    return []

os.makedirs("data/tmp", exist_ok=True)
tmp = "data/tmp/current.parquet"
results = []
projects = links["project"].unique()

for i, project in enumerate(projects, 1):
    key = re.escape(project.replace("/", "|"))
    pattern = re.compile(r"commits?\|" + key + r"(\|\d+)?\.parquet$", re.IGNORECASE)
    parts = [m for m in commit_members if pattern.search(os.path.basename(m))]
    p_need = need.loc[need["project"] == project, ["pr_number", "commit_sha"]].drop_duplicates()
    p_prs = set(links.loc[links["project"] == project, "pr_number"])

    for m in parts:
        with zf.open(m) as src, open(tmp, "wb") as dst:
            shutil.copyfileobj(src, dst, 16 * 1024 * 1024)
        df = pd.read_parquet(tmp, columns=["sha", "message", "files"])
        df["sha"] = df["sha"].str.split().str[0]              # cut off " master~1"
        df["files"] = df["files"].map(to_list)

        # Method 1: commit ID listed in pr_commit
        a = df.merge(p_need, left_on="sha", right_on="commit_sha")
        a["method"] = "id"

        # Method 2: PR number in the first line of the commit message
        first_line = df["message"].fillna("").str.split("\n").str[0]
        nums = first_line.str.extract(PR_IN_MSG)
        df["pr_number"] = pd.to_numeric(nums[0].fillna(nums[1]), errors="coerce")
        b = df[df["pr_number"].isin(p_prs)].copy()
        b["pr_number"] = b["pr_number"].astype(int)
        b["method"] = "message"

        both = pd.concat([a[["sha", "pr_number", "files", "method"]],
                          b[["sha", "pr_number", "files", "method"]]])
        both.insert(0, "project", project)
        results.append(both)
    print(f"{i}/{len(projects)} {project}")

os.remove(tmp)
files = pd.concat(results, ignore_index=True)
files = files.drop_duplicates(subset=["project", "sha", "pr_number"])   # keep "id" if both found it
print("Fixing commits found:", len(files))
print("By method:", files["method"].value_counts().to_dict())

covered = links.merge(files[["project", "pr_number"]].drop_duplicates(),
                      on=["project", "pr_number"])[["project", "issue_number"]].drop_duplicates()
print("Bugs with changed files found:", len(covered), "of",
      len(links[["project", "issue_number"]].drop_duplicates()))

files.to_parquet("data/fix_commit_files.parquet")
print("Saved data/fix_commit_files.parquet")