import zipfile

zf = zipfile.ZipFile("dataset.zip")

tables = ["issue", "pr", "issue_pr", "pr_commit", "commit_metadata",
          "issue_comment", "pr_comment", "project"]

for t in tables:
    name = "OSSGameBench/" + t + ".parquet"
    zf.extract(name, "data")          # copy this one file into the "data" folder
    print("extracted", name)