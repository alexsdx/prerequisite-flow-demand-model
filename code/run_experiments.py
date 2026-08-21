"""Run the two retrospective validation experiments of Section 5.

Reproduces the headline coverage and MAE figures listed in Section 5 and
in Listing B.1 of Supplement B:

    Experiment 1: 17 validated courses, coverage 117.4%, MAE 13.1
                  (25 non-predictable courses offered in S5).
    Experiment 2: 12 validated courses, coverage 111.3%, MAE 9.9
                  (31 non-predictable courses offered in S6).

Revision note (v1.1.0): the originally submitted version reported
34 courses / 53.7% / 38.8 for Experiment 1. That figure mixed 17 courses
with a defined prerequisite flow and 17 courses for which only the retake
count was reported as the estimate. The latter are now classified as
non-predictable (Section 3.2, Eq. 3), and the comparison against
forecasting baselines is produced by run_baselines.py.

All inputs are read from data/. The model implementation is in
code/algorithm1.py. Reruns are bit-identical because the model is
deterministic and uses exact integer arithmetic.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

from algorithm1 import compute_prerequisite_flow_demand_full

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "data"

SEMESTERS = ["S1", "S2", "S3", "S4", "S5", "S6"]


def _load_enrolments(path: Path) -> dict:
    enrolments: dict = {}
    with path.open(encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            key = (row["course_id"], row["semester"])
            enrolments[key] = int(row["enrolment_n"])
    return enrolments


def _load_failures_S4(path: Path) -> dict:
    failures: dict = {}
    with path.open(encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            failures[(row["course_id"], "S4")] = int(row["failures_f"])
    return failures


def _load_graph(path: Path) -> dict:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def _evaluate(predictions: dict, non_predictable: set, enrolments: dict,
              target_semester: str):
    """Return validated-set, non-predictable-offered, sum(d), sum(n), coverage%, MAE.

    The validated set V* is the set of courses with a defined estimate
    (Eq. 3) that were actually offered in the target semester (n_c > 0).
    Residuals are e_c = n_c - d_c (observed minus estimated; e_c > 0 is
    an under-estimate).
    """
    validated = []
    sum_d = 0
    sum_n = 0
    err_total = 0
    for course, d in predictions.items():
        n = enrolments.get((course, target_semester), 0)
        if n <= 0:
            continue
        validated.append(course)
        sum_d += d
        sum_n += n
        err_total += abs(n - d)
    offered = {c for (c, s), n in enrolments.items() if s == target_semester and n > 0}
    unpred_offered = sorted(non_predictable & offered)
    coverage = round(sum_d / sum_n * 100, 1) if sum_n else 0.0
    mae = round(err_total / len(validated), 1) if validated else 0.0
    return validated, unpred_offered, sum_d, sum_n, coverage, mae


def _print_result(name: str, t: str, t_plus_1: str, note: str, result):
    validated, unpred, sum_d, sum_n, coverage, mae = result
    print(f"{name}: {t} -> {t_plus_1} {note}")
    print(f"  Validated courses:        {len(validated)}")
    print(f"  Non-predictable offered:  {len(unpred)}")
    print(f"  Sum predicted demand:     {sum_d}")
    print(f"  Sum observed enrollment:  {sum_n}")
    print(f"  Coverage:                 {coverage}%")
    print(f"  MAE:                      {mae} students per course")


def main():
    enrolments = _load_enrolments(DATA_DIR / "enrollments_anonymized.csv")
    failures_S4 = _load_failures_S4(DATA_DIR / "failures_S4.csv")
    graph = _load_graph(DATA_DIR / "prerequisite_graph.json")

    # Experiment 1: S4 -> S5 with observed failures.
    pred_exp1, unpred1 = compute_prerequisite_flow_demand_full(
        graph=graph, enrolments=enrolments, failures=failures_S4, t="S4",
    )
    result1 = _evaluate(pred_exp1, unpred1, enrolments, target_semester="S5")
    _print_result(
        "Experiment 1", "S4", "S5", "with observed failures", result1,
    )

    print()

    # Experiment 2: S5 -> S6 under f = 0.
    pred_exp2, unpred2 = compute_prerequisite_flow_demand_full(
        graph=graph, enrolments=enrolments, failures={}, t="S5",
    )
    result2 = _evaluate(pred_exp2, unpred2, enrolments, target_semester="S6")
    _print_result(
        "Experiment 2", "S5", "S6", "with f = 0", result2,
    )


if __name__ == "__main__":
    main()
