# Prerequisite-Flow Demand Model — Reproducibility release

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.20254356.svg)](https://doi.org/10.5281/zenodo.20254356)

Companion repository to the article

> *A Prerequisite-Flow Demand Model for Hybrid Augmented Intelligence in
> Academic Course Planning.*
> A. Estrada-Padilla, F. A. Balderas-Jaramillo, M. A. Aguirre Lam,
> L. T. Contreras Alvarez, J. F. F. Rodriguez Zapata.
> *International Journal of Combinatorial Optimization Problems and
> Informatics* (IJCOPI), Special section "Hybrid Augmented Intelligence
> in Action", 2027.

This release contains the anonymised dataset, the reference
implementations of Algorithm 1 (`ComputePrerequisiteFlowDemand`) and
Algorithm 2 (`HybridDemandPlan`), and the top-level scripts that
reproduce every quantitative result reported in Section 5 of the
article.

## Repository contents

| Path | Description |
|------|-------------|
| `data/enrollments_anonymized.csv` | Per-course per-semester enrolment counts *n*<sub>c</sub>(*t*) for all courses across the six semesters *S*<sub>1</sub> ... *S*<sub>6</sub>, with abstract labels (R1)-(R2) of Supplement A applied. |
| `data/failures_S4.csv` | Per-course failure counts *f*<sub>c</sub>(*S*<sub>4</sub>) for the single semester for which failure data are available. |
| `data/prerequisite_graph.json` | Prerequisite graph *G* as an edge list, with vertices identified by abstract labels. The graph is a forest of in-trees. |
| `code/algorithm1.py` | Reference implementation of Algorithm 1. |
| `code/algorithm2.py` | Reference implementation of Algorithm 2 (batch form: the interactive elicitation of line 4 of the pseudocode is replaced by per-course inputs). |
| `code/run_experiments.py` | Top-level script that reproduces Experiments 1 and 2 of Section 5 and prints the headline coverage and MAE figures. |
| `code/run_validation_workbook.py` | Generates `Validation_and_Trends.xlsx` with the per-course validation tables that underlie Sections 5 and 7. |
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
code is used. The model is deterministic and uses exact integer
arithmetic, so reruns are bit-identical.

## Replication

```bash
# 1. Clone the repository at the published commit hash.
git clone https://github.com/alexsdx/prerequisite-flow-demand-model.git
cd prerequisite-flow-demand-model

# 2. Create a Python 3.11 virtual environment.
python3.11 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

# 3. Install pinned dependencies.
pip install -r requirements.txt

# 4. Run the experiments.
python code/run_experiments.py

# 5. (Optional) Regenerate the full validation workbook.
python code/run_validation_workbook.py
```

The expected output of step 4 is:

```
Experiment 1: S4 -> S5 with observed failures
  Validated courses:        34
  Sum predicted demand:     1107
  Sum observed enrollment:  2063
  Coverage:                 53.7%
  MAE:                      38.8 students per course

Experiment 2: S5 -> S6 with f = 0
  Validated courses:        12
  Sum predicted demand:     938
  Sum observed enrollment:  843
  Coverage:                 111.3%
  MAE:                      9.9 students per course
```

The numerical agreement with the figures reported in Section 5 of the
article is exact at the precision shown.

## Anonymisation

Course and semester identities are reported with the abstract labels
defined in Supplement A of the article: `C{sem}.{pos}` for core courses,
`E{track}.{n}` for specialty-track courses, `X.{n}` for cross-programme
shared courses, and `S{1..6}` for semesters. The bidirectional mapping
between abstract labels and real institutional codes is held privately
by the authors as part of the institutional anonymisation agreement.

## License

- Code (`code/` and top-level Python scripts): MIT License (see `LICENSE`).
- Data (`data/`): Creative Commons Attribution 4.0 International
  (see `DATA_LICENSE`).

Both licenses permit unrestricted research, teaching, and commercial
reuse subject to attribution. See `CITATION.cff` for the canonical
citation.
