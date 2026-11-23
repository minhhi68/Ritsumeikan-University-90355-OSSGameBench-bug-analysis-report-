import zipfile

zf = zipfile.ZipFile("OSSGameBench.zip")     # open the zip without unpacking
files = zf.infolist()                        # list of everything inside
print("Number of files:", len(files))

# show every file that is NOT a commit file, with its size
for f in files:
    if "commits" not in f.filename:
        print(round(f.file_size / 1e6, 1), "MB  ", f.filename)

# summarise the commit files instead of printing hundreds of lines
commit_files = [f for f in files if "commits" in f.filename]
print("Commit files:", len(commit_files))
print("Commit files total size (GB):", round(sum(f.file_size for f in commit_files) / 1e9, 1))