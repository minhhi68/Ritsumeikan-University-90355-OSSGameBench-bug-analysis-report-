import pandas as pd

df = pd.read_parquet("data/analysis_table.parquet")
links = pd.read_parquet("data/bug_pr_links.parquet").drop_duplicates()

# 25 random asset bugs + 25 random code-only bugs (fixed seed = same sample every time)
sample = pd.concat([df[df["group"] == "asset"].sample(25, random_state=42),
                    df[df["group"] == "code_only"].sample(25, random_state=42)])

first_pr = links.groupby(["project", "issue_number"])["pr_number"].min().reset_index()
sample = sample.merge(first_pr, on=["project", "issue_number"], how="left")

sample["issue_url"] = ("https://github.com/" + sample["project"] + "/issues/"
                       + sample["issue_number"].astype(str))
sample["pr_url"] = ("https://github.com/" + sample["project"] + "/pull/"
                    + sample["pr_number"].astype(str) + "/files")
sample["labels"] = sample["labels"].apply(lambda l: "; ".join(l))
sample["is_real_bug"] = ""        # fill in: yes / no
sample["group_correct"] = ""      # fill in: yes / no
sample["note"] = ""

cols = ["group", "issue_url", "pr_url", "title", "labels", "n_files", "n_asset", "n_code",
        "is_real_bug", "group_correct", "note"]
sample[cols].to_csv("results/validation_sample.csv", index=False, encoding="utf-8-sig")
print("Saved results/validation_sample.csv with", len(sample), "bugs")