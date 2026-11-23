import re
import pandas as pd

issues = pd.read_parquet("data/OSSGameBench/issue.parquet")

# labels that mean "this is a bug"
BUG = re.compile(r"\bbug|crash|defect|regression|error report", re.IGNORECASE)
# labels that mean "not a real bug / not fixed"
NOT_FIX = re.compile(r"wontfix|won't fix|duplicate|invalid|not a bug|question|"
                     r"can't reproduce|cannot reproduce|works for me|enhancement|feature",
                     re.IGNORECASE)

def is_bug(labels):
    labels = list(labels) if labels is not None else []
    has_bug = any(BUG.search(l) for l in labels)
    has_not_fix = any(NOT_FIX.search(l) for l in labels)
    return has_bug and not has_not_fix

issues["is_bug"] = issues["labels"].apply(is_bug)
bugs = issues[issues["is_bug"]]

print("All issues:", len(issues))
print("Bug reports:", len(bugs), "in", bugs["project"].nunique(), "projects")
print("State values:", bugs["state"].value_counts().to_dict())

closed = bugs[bugs["state"].str.lower() == "closed"]
print("Closed bug reports:", len(closed))

# which labels made issues count as bugs (to report in the paper)
lab = bugs["labels"].explode()
print(lab[lab.str.contains(BUG, na=False)].value_counts().head(20))

closed.to_parquet("data/closed_bugs.parquet")
print("Saved data/closed_bugs.parquet")