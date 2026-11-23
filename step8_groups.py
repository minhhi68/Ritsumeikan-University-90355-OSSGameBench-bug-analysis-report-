import pandas as pd

links = pd.read_parquet("data/bug_pr_links.parquet")
files = pd.read_parquet("data/fix_commit_files.parquet")

ASSET = {
    # images
    "png", "jpg", "jpeg", "gif", "bmp", "tga", "psd", "svg", "webp", "dds", "ktx",
    "exr", "hdr", "ico", "tif", "tiff", "xcf", "aseprite", "ase", "kra",
    # audio
    "ogg", "wav", "mp3", "flac", "aiff", "aif", "opus", "m4a", "mid", "midi",
    "mod", "xm", "it", "s3m",
    # 3D models / animation
    "fbx", "obj", "blend", "gltf", "glb", "dae", "3ds", "max", "ma", "mb", "mtl",
    "ply", "stl", "md2", "md3", "md5mesh", "md5anim", "iqm", "b3d",
    # fonts
    "ttf", "otf", "fnt", "woff", "woff2",
    # engine scenes / resources (Unity, Godot, Unreal, Tiled, LDtk)
    "unity", "prefab", "mat", "asset", "anim", "controller", "physicmaterial",
    "spriteatlas", "tscn", "tres", "scn", "res", "uasset", "umap", "tmx", "ldtk",
    # shaders
    "shader", "glsl", "hlsl", "frag", "vert", "gdshader", "fx", "cg", "compute", "wgsl",
}
CODE = {
    "c", "h", "cc", "cpp", "cxx", "hpp", "hh", "hxx", "inl", "cs", "java", "kt", "kts",
    "scala", "groovy", "js", "mjs", "cjs", "ts", "jsx", "tsx", "py", "lua", "gd", "rs",
    "go", "swift", "m", "mm", "rb", "php", "hx", "gml", "dart", "zig", "nim", "d",
    "pas", "pp", "vala", "vb", "fs", "clj", "ex", "exs", "erl", "hs", "ml", "asm", "s",
}
IGNORE = {"meta", "import"}     # Unity/Godot side files that follow other files

def extension(path):
    name = str(path).rsplit("/", 1)[-1].lower()
    return name.rsplit(".", 1)[-1] if "." in name else ""

def kind(path):
    ext = extension(path)
    if ext in IGNORE:
        return "ignore"
    if ext in ASSET:
        return "asset"
    if ext in CODE:
        return "code"
    return "other"

# one row per (bug, fixing commit, changed file)
bf = links.merge(files, on=["project", "pr_number"])
bf = bf.explode("files").dropna(subset=["files"])
bf["ext"] = bf["files"].map(extension)
bf["kind"] = bf["files"].map(kind)

# count per bug
uniq = bf.drop_duplicates(subset=["project", "issue_number", "files"])
per_bug = uniq.groupby(["project", "issue_number"]).agg(
    n_files=("files", "size"),
    n_asset=("kind", lambda k: (k == "asset").sum()),
    n_code=("kind", lambda k: (k == "code").sum()),
).reset_index()
size = bf.groupby(["project", "issue_number"]).agg(
    n_commits=("sha", "nunique"), n_prs=("pr_number", "nunique")).reset_index()
per_bug = per_bug.merge(size, on=["project", "issue_number"])

def group(row):
    if row["n_asset"] > 0:
        return "asset"
    if row["n_code"] > 0:
        return "code_only"
    return "neither"

per_bug["group"] = per_bug.apply(group, axis=1)
print("Bugs per group:", per_bug["group"].value_counts().to_dict())
print("Projects with both groups:",
      (per_bug.groupby("project")["group"].apply(lambda g: {"asset", "code_only"} <= set(g))).sum())

print("\nMost common asset extensions:")
print(uniq.loc[uniq["kind"] == "asset", "ext"].value_counts().head(15))
print("\nMost common 'other' extensions (check we did not miss assets):")
print(uniq.loc[uniq["kind"] == "other", "ext"].value_counts().head(25))

per_bug.to_parquet("data/bug_groups.parquet")
print("Saved data/bug_groups.parquet")