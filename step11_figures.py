import math
import numpy as np
import pandas as pd

# Figures are written as SVG (plain text), so no drawing library is needed.
# Open the .svg files in a web browser, or insert them into Word.

df = pd.read_parquet("data/analysis_table.parquet")
NAMES = {"code_only": "Code-only fix", "asset": "Fix touches assets"}
COLORS = {"code_only": "#2a6fdb", "asset": "#e07b00"}
FONT = 'font-family="Arial, Helvetica, sans-serif"'


def text(x, y, s, size=12, anchor="middle", extra=""):
    return f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" text-anchor="{anchor}" {FONT} {extra}>{s}</text>'


def line(x1, y1, x2, y2, color="#000", width=1, extra=""):
    return f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{color}" stroke-width="{width}" {extra}/>'


def save(path, w, h, parts):
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
           f'viewBox="0 0 {w} {h}"><rect width="100%" height="100%" fill="white"/>'
           + "".join(parts) + "</svg>")
    with open(path, "w", encoding="utf-8") as f:
        f.write(svg)
    print("Saved", path)


# ---------- Figure 1: share of bugs closed after N days (log scale) ----------
W, H = 640, 400
L, R, T, B = 70, 20, 20, 60                    # margins
pw, ph = W - L - R, H - T - B
xmin, xmax = math.log10(1 / 24), math.log10(max(df["ttc_days"].max(), 10))
X = lambda d: L + (math.log10(max(d, 1 / 24)) - xmin) / (xmax - xmin) * pw
Y = lambda p: T + (1 - p) * ph

parts = [line(L, T + ph, L + pw, T + ph), line(L, T, L, T + ph)]
for p in [0, 0.25, 0.5, 0.75, 1]:
    parts += [line(L, Y(p), L + pw, Y(p), "#ddd"), text(L - 8, Y(p) + 4, f"{p:.2f}", 11, "end")]
for d, lab in [(1 / 24, "1 hour"), (1, "1 day"), (7, "1 week"), (30, "1 month"),
               (365, "1 year"), (3650, "10 years")]:
    if math.log10(d) <= xmax:
        parts += [line(X(d), T, X(d), T + ph, "#ddd"), text(X(d), T + ph + 18, lab, 11)]
parts += [text(L + pw / 2, H - 15, "Time from bug report to closure (log scale)", 13),
          text(18, T + ph / 2, "Share of bug reports closed", 13, extra=f'transform="rotate(-90 18 {T + ph / 2})"')]

for k, g in enumerate(["code_only", "asset"]):
    x = np.sort(df.loc[df["group"] == g, "ttc_days"].values)
    qs = np.linspace(0, 1, 400)
    pts = [(X(np.quantile(x, q)), Y(q)) for q in qs]
    parts.append(f'<polyline fill="none" stroke="{COLORS[g]}" stroke-width="2.2" points="'
                 + " ".join(f"{a:.1f},{b:.1f}" for a, b in pts) + '"/>')
    ly = T + 20 + k * 20
    parts += [line(L + 15, ly - 4, L + 40, ly - 4, COLORS[g], 3),
              text(L + 46, ly, f"{NAMES[g]} (n={len(x):,}, median {np.median(x):.1f} days)", 12, "start")]
save("results/fig1_time_to_close.svg", W, H, parts)

# ---------- Figure 2: fix size (a) and time to close for same-size fixes (b) ----------
labels = ["1-2", "3-10", "11-50", ">50"]
df["size_bin"] = pd.cut(df["n_files"], [0, 2, 10, 50, np.inf], labels=labels)
count = df.groupby(["size_bin", "group"], observed=False).size().unstack()
share = 100 * count / count.sum()
median = df.groupby(["size_bin", "group"], observed=False)["ttc_days"].median().unstack()
print("\nShare of bugs per fix size (%):\n", share.round(1))
print("\nMedian days to close per fix size:\n", median.round(1))

W, H = 980, 420
panel_w = 400
parts = []


def bar_panel(x0, title, values, ylabel, fmt, sublabel=None):
    L, T, ph = x0 + 60, 40, 280
    top = max(values.max().max(), 1) * 1.15
    step = 10 ** math.floor(math.log10(top / 4))
    step = step * (5 if top / step > 20 else 2 if top / step > 8 else 1)
    Y = lambda v: T + ph - v / top * ph
    out = [text(x0 + 60 + panel_w / 2, 22, title, 14, extra='font-weight="bold"'),
           line(L, T + ph, L + panel_w, T + ph), line(L, T, L, T + ph)]
    v = 0
    while v <= top:
        out += [line(L, Y(v), L + panel_w, Y(v), "#ddd"), text(L - 8, Y(v) + 4, f"{v:g}", 11, "end")]
        v += step
    gw = panel_w / len(labels)
    bw = gw * 0.35
    for i, lab in enumerate(labels):
        cx = L + gw * (i + 0.5)
        out.append(text(cx, T + ph + 18, lab, 12))
        if sublabel is not None:
            out.append(text(cx, T + ph + 32, sublabel(lab), 9, extra='fill="#555"'))
        for k, g in enumerate(["code_only", "asset"]):
            val = values.loc[lab, g]
            if pd.isna(val):
                continue
            bx = cx + (k - 1) * bw
            out.append(f'<rect x="{bx:.1f}" y="{Y(val):.1f}" width="{bw:.1f}" '
                       f'height="{Y(0) - Y(val):.1f}" fill="{COLORS[g]}"/>')
            out.append(text(bx + bw / 2, Y(val) - 4, fmt(val), 10))
    out += [text(L + panel_w / 2, T + ph + 50, "Files changed by the fix", 12),
            text(x0 + 16, T + ph / 2, ylabel, 12, extra=f'transform="rotate(-90 {x0 + 16} {T + ph / 2})"')]
    return out


parts += bar_panel(0, "(a) Size of the fix", share, "Share of bug reports (%)", lambda v: f"{v:.0f}%")
parts += bar_panel(490, "(b) Time to close, same-size fixes", median, "Median days to close",
                   lambda v: f"{v:.1f}",
                   sublabel=lambda lab: f"n = {count.loc[lab, 'code_only']:,} / {count.loc[lab, 'asset']:,}")
for k, g in enumerate(["code_only", "asset"]):
    x = 300 + k * 200
    parts += [f'<rect x="{x}" y="{H - 22}" width="14" height="14" fill="{COLORS[g]}"/>',
              text(x + 20, H - 10, NAMES[g], 12, "start")]
save("results/fig2_fix_size.svg", W, H, parts)
