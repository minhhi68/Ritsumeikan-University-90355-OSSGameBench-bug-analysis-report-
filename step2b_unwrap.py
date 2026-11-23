import zipfile
import shutil

outer = zipfile.ZipFile("OSSGameBench.zip")        # the Dropbox download
info = outer.getinfo("OSSGameBench.zip")           # the real dataset inside it
print("Size (MB):", round(info.file_size / 1e6, 1))

# copy the inner zip out to a new file, 16 MB at a time
with outer.open(info) as src, open("dataset.zip", "wb") as dst:
    shutil.copyfileobj(src, dst, 16 * 1024 * 1024)

print("Done: dataset.zip created")