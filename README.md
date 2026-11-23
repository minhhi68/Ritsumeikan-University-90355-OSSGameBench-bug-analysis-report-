# OSSGameBench Bug Analysis Report

Assignment for Ritsumeikan University (course 90355). This project analyses bug reports in open-source game projects from the **OSSGameBench** dataset and asks one question:

> Do bugs whose fix touches **non-code assets** (images, audio, models, etc.) take longer to resolve than bugs fixed by changing **code only**?

## Main findings

| Measure | Median (asset fix) | Median (code-only fix) | Cliff's delta | Holm-adjusted p |
|---|---|---|---|---|
| Time to close (days) | 22.2 | 7.0 | 0.22 | < 0.001 |
| Issue comments | 1 | 1 | -0.06 | 0.0025 |
| PR comments | 1 | 0 | 0.09 | < 0.001 |

- Analysed **11,100 closed bugs**: 826 asset-related (125 projects) and 10,274 code-only (312 projects).
- Asset-related bugs take about three times longer to close in the raw comparison.
- Fix size is a confounder: asset fixes touch far more files (median 28.5 vs 2). Once fix size and project are controlled for, the regression shows no clear effect (-0.9 %, 95 % CI -23.9 % to +29.1 %, p = 0.95).
- Within the 47 projects that have both kinds of bugs, asset bugs are slower in 74 % of projects (median difference 9.4 days).

See the full write-up in the report files below.

## Repository contents

| Path | Description |
|---|---|
| `OSSGameBench_OptionA_Report-updated.docx` | Final report (latest version) |
| `OSSGameBench_OptionA_Report.docx` | Earlier version of the report |
| `step2*` - `step12*.py` | Analysis pipeline, run in order (see below) |
| `data/` | Small processed tables (`analysis_table`, `bug_groups`, `bug_pr_links`, `fix_commit_files`) |
| `results/` | Output tables (`*.csv`) and figures (`*.svg`) |

## Pipeline

| Step | Script | Purpose |
|---|---|---|
| 2 | `step2_look.py`, `step2b_unwrap.py` | Inspect and unpack the downloaded dataset zip |
| 3 | `step3_tables.py` | List the tables in the dataset |
| 4 | `step4_labels.py` | Explore issue labels |
| 5 | `step5_bugs.py` | Select closed bug issues using label rules |
| 6 | `step6_fixed.py` | Link bugs to merged fixing pull requests |
| 7 | `step7_check.py`, `step7_files.py` | Collect the files changed by each fix |
| 8 | `step8_groups.py` | Classify each bug as `asset` or `code_only` by file extension |
| 9 | `step9_measures.py` | Compute time-to-close and comment counts |
| 10 | `step10_stats.py` | Mann-Whitney tests, Cliff's delta, bootstrap CIs, Holm correction, stratified and within-project analysis, regression |
| 11 | `step11_figures.py` | Draw the figures as SVG (no plotting library needed) |
| 12 | `step12_sample.py` | Draw a random sample of 50 bugs for manual validation |

Random seed is fixed (42), so results are reproducible.

## Reproducing the analysis

1. Download the OSSGameBench dataset (not included here because it is about 65 GB) and place the zip files in the project root.
2. Install the requirements: `pip install pandas numpy pyarrow`
3. Run the scripts in step order from the project root, e.g. `python step10_stats.py`.

The processed tables in `data/` are included, so steps 10-12 can be run without the raw dataset.

## Data source

OSSGameBench: a dataset of issues, pull requests, comments and commits from open-source game projects on GitHub.
