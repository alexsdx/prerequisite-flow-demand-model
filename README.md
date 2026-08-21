# Prerequisite-Flow Demand Estimation — Reproducibility release

[![DOI v1.1.0](https://zenodo.org/badge/DOI/10.5281/zenodo.22042483.svg)](https://doi.org/10.5281/zenodo.22042483) [![DOI v1.0.0](https://zenodo.org/badge/DOI/10.5281/zenodo.20254356.svg)](https://doi.org/10.5281/zenodo.20254356)

Companion repository to the article

> *Prerequisite-Flow Demand Estimation for Academic Course Planning:
> A Hybrid Augmented Intelligence Workflow.*
> A. Estrada-Padilla, F. A. Balderas-Jaramillo, M. A. Aguirre Lam,
> L. T. Contreras Alvarez, J. F. F. Rodriguez Zapata.
> *International Journal of Combinatorial Optimization Problems and
> Informatics* (IJCOPI), Special section "Hybrid Augmented Intelligence
> in Action", 2027 (under revision).

This release contains the anonymised dataset, the reference
implementations of Algorithm 1 (`ComputePrerequisiteFlowDemand`) and
Algorithm 2 (`HybridDemandPlan`), and the scripts that reproduce every
quantitative result of Sections 5 and 6 of the article: the two
retrospective experiments, the baseline comparison (Table 3), the
synthetic sensitivity study (Table 5), the bootstrap intervals, and the
workflow run in batch mode.

## Versions

| Version | Zenodo DOI | Status |
|---|---|---|
| v1.0.0 (2026-05-17) | [10.5281/zenodo.20254356](https://doi.org/10.5281/zenodo.20254356) | Release evaluated at first submission. Kept unchanged for the record. |
| v1.1.0 (2026-08-21) | [10.5281/zenodo.22042483](https://doi.org/10.5281/zenodo.22042483) | Revised release accompanying the revised manuscript. |

**What changed in v1.1.0.** Peer review identified that the originally
submitted version (a) accumulated retake demand over a retry cap *k*
whereas the code used a one-step recurrence, and (b) reported the retake
count alone as the demand estimate for courses whose prerequisite was not
offered, which produced an aggregate coverage of 53.7 % over 34 courses.
In v1.1.0 the model is the one-step recurrence (Eq. 2), courses without an
offered prerequisite are *non-predictable* (Eq. 3), and the validated set
of Experiment 1 is the 17 courses with a defined prerequisite flow. The
track share in Algorithm 2 now multiplies the passing flow as written in
Eq. (9). Baseline, synthetic and bootstrap scripts are new. See Sections
3.2 and 5.2 of the revised article.

## Repository contents

| Path | Description |
|------|-------------|
| `data/enrollments_anonymized.csv` | Per-course per-semester enrolment counts *n*<sub>c</sub>(*t*) for all courses across the six semesters *S*<sub>1</sub> ... *S*<sub>6</sub>, with abstract labels (R1)-(R2) of Supplement A applied. |
| `data/failures_S4.csv` | Per-course failure counts *f*<sub>c</sub>(*S*<sub>4</sub>) for the single semester for which failure data are available. |
| `data/prerequisite_graph.json` | Prerequisite graph *G* as an edge list, with vertices identified by abstract labels. The graph is a forest of in-trees. |
| `code/algorithm1.py` | Algorithm 1: Eqs. (1)-(3). Returns the estimate *d* for predictable courses and the non-predictable set *U*. |
| `code/algorithm2.py` | Algorithm 2: Eqs. (7)-(11). Channel combination, track share, group sizing, and the per-channel prior update. Batch form: the interactive elicitation is replaced by dictionaries. |
| `code/run_experiments.py` | Experiments 1 and 2 of Section 5.2 (headline figures, Listing B.1 of Supplement B). |
| `code/run_baselines.py` | Model versus the six forecasting baselines on the validated sets and on all offered courses (Table 3; Supplement C). Writes `Baselines_Comparison.xlsx`. |
| `code/run_synthetic.py` | Synthetic sensitivity study (Section 5.4, Table 5) and bootstrap intervals (Section 5.2). Fixed seed. Writes `Synthetic_and_Bootstrap.xlsx`. |
| `code/run_workflow_batch.py` | Algorithm 2 with priors only and no human input: last row of Table 3, plus one prior update to illustrate the closed loop. |
| `code/run_validation_workbook.py` | Generates `Validation_and_Trends.xlsx` with per-course validation tables. |
| `requirements.txt` | Pinned package versions. |
| `LICENSE` | MIT license for code. |
| `DATA_LICENSE` | CC-BY-4.0 license for data. |
| `CITATION.cff` | Canonical citation for both the dataset and the article. |

## Software environment

The reference implementation runs on Python 3.11. Pinned dependencies:

```
pandas == 2.1.4
numpy  == 1.26.4
openpyxl == 3.1.2
```

The implementation has been tested on Windows 11. No platform-specific
code is used. Algorithms 1 and 2 are deterministic and use exact integer
arithmetic; the synthetic study and the bootstrap use `numpy`'s
default generator with a fixed seed (20260821), so reruns reproduce the
reported figures.

## Replication

```bash
# 1. Clone the repository at the published tag.
git clone https://github.com/alexsdx/prerequisite-flow-demand-model.git
cd prerequisite-flow-demand-model
git checkout v1.1.0

# 2. Create a Python 3.11 virtual environment.
python3.11 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

# 3. Install pinned dependencies.
pip install -r requirements.txt

# 4. Experiments 1 and 2 (Section 5.2).
python code/run_experiments.py

# 5. Baseline comparison, Table 3 and Supplement C.
python code/run_baselines.py

# 6. Synthetic study (Table 5) and bootstrap intervals (~15 s).
python code/run_synthetic.py

# 7. Workflow in batch mode (last row of Table 3).
python code/run_workflow_batch.py

# 8. (Optional) Per-course validation workbook.
python code/run_validation_workbook.py
```

The expected output of step 4 is:

```
Experiment 1: S4 -> S5 with observed failures
  Validated courses:        17
  Non-predictable offered:  25
  Sum predicted demand:     945
  Sum observed enrollment:  805
  Coverage:                 117.4%
  MAE:                      13.1 students per course

Experiment 2: S5 -> S6 with f = 0
  Validated courses:        12
  Non-predictable offered:  31
  Sum predicted demand:     938
  Sum observed enrollment:  843
  Coverage:                 111.3%
  MAE:                      9.9 students per course
```

and of step 7:

```
S4 -> S5: 42 courses, MAE 11.6, coverage 105.4%  (17 structural + 25 prior-only)
S5 -> S6: 33 courses, MAE 9.9, coverage 105.9%  (12 structural + 21 prior-only)
```

The numerical agreement with the figures reported in the article is
exact at the precision shown.

## Anonymisation

Course and semester identities are reported with the abstract labels
defined in Supplement A of the article: `C{sem}.{pos}` for core courses,
`E{track}.{n}` for specialty-track courses, `X.{n}` for cross-programme
shared courses, and `S{1..6}` for semesters. The bidirectional mapping
between abstract labels and real institutional codes is held privately
by the authors as part of the institutional anonymisation agreement.
Every released value is an aggregate count of seats per course and
semester; the smallest released cell is above 10.

## License

- Code (`code/` and top-level Python scripts): MIT License (see `LICENSE`).
- Data (`data/`): Creative Commons Attribution 4.0 International
  (see `DATA_LICENSE`).

Both licenses permit unrestricted research, teaching, and commercial
reuse subject to attribution. See `CITATION.cff` for the canonical
citation.
