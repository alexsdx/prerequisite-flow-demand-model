"""Algorithm 2 in batch mode: reproduces the last row of Table 3.

The workflow is run with no administrator input: for predictable courses
the structural estimate d_c is used as is; for non-predictable courses the
dominant channel carries the prior of Eq. (11) seeded with the two previous
semesters of the same kind (lambda = 0.5, i.e. their mean). Expected output:

    S4 -> S5: 42 courses, MAE 11.6, coverage 105.4%
    S5 -> S6: 33 courses, MAE  9.9, coverage 105.9%

It then performs one prior update (Eqs. 10-11) with the realised S5 to show
the closed loop, printing the priors for the chain root C1.2.
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "code"))
from algorithm1 import compute_prerequisite_flow_demand_full  # noqa: E402
from algorithm2 import hybrid_demand_plan, update_priors, CHANNELS  # noqa: E402

SEM = ["S1", "S2", "S3", "S4", "S5", "S6"]


def load():
    enr, fail = {}, {}
    with (REPO / "data/enrollments_anonymized.csv").open(encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            enr[(r["course_id"], r["semester"])] = int(r["enrolment_n"])
    with (REPO / "data/failures_S4.csv").open(encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            fail[(r["course_id"], "S4")] = int(r["failures_f"])
    graph = json.loads((REPO / "data/prerequisite_graph.json").read_text(encoding="utf-8"))
    return enr, fail, graph


def dominant(graph, course):
    children = {e["to"] for e in graph["edges"]}
    if course.startswith("X"):
        return "X"
    if course not in children:
        return "I" if not course.startswith("E") else "E"
    return "L"


def seeded_priors(enr, graph, t, t1):
    """Prior for the dominant channel of every course: mean of the previous
    same-kind semesters (Eq. 11 with lambda = 0.5 from two observations)."""
    it = SEM.index(t)
    same = [s for s in SEM[: it + 1] if SEM.index(s) % 2 == SEM.index(t1) % 2]
    priors = {}
    for c in graph["vertices"]:
        hist = [enr[(c, s)] for s in same if enr.get((c, s), 0) > 0]
        priors[c] = {k: 0.0 for k in CHANNELS}
        if hist:
            priors[c][dominant(graph, c)] = sum(hist) / len(hist)
    return priors


def run(enr, fail, graph, t, t1, use_fail):
    priors = seeded_priors(enr, graph, t, t1)
    # batch mode: channel values = priors, but only for non-predictable courses
    _, U = compute_prerequisite_flow_demand_full(graph, enr, fail if use_fail else {}, t)
    plan, U = hybrid_demand_plan(graph, enr, fail if use_fail else {}, t,
                                 channel_values={c: {k: round(v) for k, v in priors[c].items()}
                                                 for c in priors if c in U})
    rows = [(c, plan[c]["n_aug"], enr[(c, t1)]) for c in plan
            if enr.get((c, t1), 0) > 0 and (c not in U or any(priors[c].values()))]
    mae = sum(abs(n - a) for _, a, n in rows) / len(rows)
    cov = 100 * sum(a for _, a, _ in rows) / sum(n for _, _, n in rows)
    print(f"{t} -> {t1}: {len(rows)} courses, MAE {mae:.1f}, coverage {cov:.1f}%  "
          f"({len([c for c, *_ in rows if c not in U])} structural + "
          f"{len([c for c, *_ in rows if c in U])} prior-only)")
    return plan, U, priors


def main():
    enr, fail, graph = load()
    plan5, U5, priors5 = run(enr, fail, graph, "S4", "S5", True)
    run(enr, fail, graph, "S5", "S6", False)

    realised = {c: n for (c, s), n in enr.items() if s == "S5"}
    dom = {c: dominant(graph, c) for c in graph["vertices"]}
    updated = update_priors(priors5, plan5, realised, dom, lam=0.5)
    c = "C1.2"
    print(f"\nClosed loop, course {c} (root, dominant channel I): prior {priors5[c]['I']:.1f} "
          f"-> realised {realised[c]} -> updated prior {updated[c]['I']:.1f}")


if __name__ == "__main__":
    main()
