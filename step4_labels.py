import pandas as pd

pd.set_option("display.width", 200)

# load the issue table
issues = pd.read_parquet("data/OSSGameBench/issue.parquet")

print("Number of issues:", len(issues))
print("Number of projects:", issues["project"].nunique())
print("Columns:", list(issues.columns))
print("Example of the labels column:", repr(issues["labels"].iloc[0]))

# count how often each label is used, and show the 40 most common
labels = issues["labels"].explode()
print(labels.value_counts().head(40))