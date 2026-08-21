"""Synthetic sensitivity study (Section 5.4) and bootstrap intervals (Section 5.2).

Part A - synthetic curricula
----------------------------
Random prerequisite forests are generated and a cohort is propagated through
them for five semesters under a factorial design:

    phi   failure rate per course            {0.10, 0.30}
    a     flow attrition (share of passers    {0.00, 0.10, 0.20}
          who do not enrol in the consequent)
    delta intake drift per academic year     {-0.20, 0.00, +0.20}
    rho   retake immediacy (share of failed  {1.0, 0.7}
          students who retake the next semester)

For each cell, R replicates are drawn. In every replicate the model of
Eqs. (1)-(3) estimates semester 5 from semester 4, and the baselines LY
(semester 3) and P-mean (mean of semesters 1 and 3) are computed from the
same synthetic history. Metrics: MAPE and the share of courses whose
recommended group count at tau = 18 is within one group of the realised
count.

Part B - bootstrap intervals on the real data
---------------------------------------------
Percentile bootstrap (B resamples of courses with replacement) of the MAE of
the model and of the two strongest baselines on the validated sets of
Experiments 1 and 2, and of the paired MAE difference model - baseline.

Both parts use a fixed seed; rerunning reproduces the numbers in the article.
"""
from __future__ import annotations

import csv
import json
import math
import sys
from itertools import product
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "code"))
from algorithm1 import compute_prerequisite_flow_demand_full  # noqa: E402

SEED = 20260821
TAU = 18
R_REPL = 200
B_BOOT = 10_000


# ----------------------------------------------------------------- Part A
def make_forest(rng, n_chains=10):
    """Chains of length U{2..6}; returns (vertices, parent_of, roots)."""
    parent_of, roots, vertices = {}, [], []
    for k in range(n_chains):
        L = int(rng.integers(2, 7))
        prev = None
        for j in range(L):
            c = f"K{k}.{j}"
            vertices.append(c)
            if prev is None:
                roots.append(c)
            else:
                parent_of[c] = prev
            prev = c
    return vertices, parent_of, roots


def simulate(rng, phi, a, delta, rho, n_sem=5, intake0=90, sigma=0.10):
    """Propagate a cohort; return n[c][s], f[c][s] for s = 1..n_sem."""
    vertices, parent_of, roots = make_forest(rng)
    n = {c: [0] * (n_sem + 1) for c in vertices}
    f = {c: [0] * (n_sem + 1) for c in vertices}
    # semester 0 "warm start": fill each course with a noisy cohort so that
    # every course is populated from semester 1 onward
    for c in vertices:
        n[c][0] = max(1, int(round(intake0 * (1 + sigma * rng.standard_normal()))))
        f[c][0] = int(rng.binomial(n[c][0], phi))
    for s in range(1, n_sem + 1):
        year = (s - 1) // 2
        for c in vertices:
            if c in parent_of:
                p = parent_of[c]
                flow = rng.binomial(n[p][s - 1] - f[p][s - 1], 1 - a)
            else:
                intake = intake0 * (1 + delta) ** year * (1 + sigma * rng.standard_normal())
                flow = max(0, int(round(intake)))
            retake = rng.binomial(f[c][s - 1], rho)
            n[c][s] = int(flow + retake)
            f[c][s] = int(rng.binomial(n[c][s], phi))
    return vertices, parent_of, n, f


def groups(x):
    return math.ceil(x / TAU)


def eval_cell(rng, phi, a, delta, rho):
    out = {"model": [], "ly": [], "pmean": []}
    g_out = {"model": [], "ly": [], "pmean": []}
    for _ in range(R_REPL):
        vertices, parent_of, n, f = simulate(rng, phi, a, delta, rho)
        for c in vertices:
            if c not in parent_of:
                continue  # non-predictable root; excluded as in Section 5.1
            truth = n[c][5]
            if truth <= 0:
                continue
            p = parent_of[c]
            d = (n[p][4] - f[p][4]) + f[c][4]          # Eqs. (1)-(3)
            ly = n[c][3]
            pm = round((n[c][1] + n[c][3]) / 2)
            for k, est in (("model", d), ("ly", ly), ("pmean", pm)):
                out[k].append(abs(truth - est) / truth)
                g_out[k].append(abs(groups(est) - groups(truth)) <= 1)
    return {k: (100 * float(np.mean(out[k])), 100 * float(np.mean(g_out[k])))
            for k in out}


def part_a():
    rng = np.random.default_rng(SEED)
    rows = []
    for phi, a, delta, rho in product((0.10, 0.30), (0.0, 0.10, 0.20),
                                      (-0.20, 0.0, 0.20), (1.0, 0.7)):
        r = eval_cell(rng, phi, a, delta, rho)
        rows.append({"phi": phi, "a": a, "delta": delta, "rho": rho, **{
            f"{k}_{m}": v for k, (mape, g1) in r.items()
            for m, v in (("mape", mape), ("g1", g1))}})
    return rows


def summarise(rows, by):
    """Average metrics over the factors not in `by`."""
    keys = sorted({tuple(r[b] for b in by) for r in rows})
    out = []
    for key in keys:
        sub = [r for r in rows if tuple(r[b] for b in by) == key]
        agg = {b: k for b, k in zip(by, key)}
        for col in ("model_mape", "ly_mape", "pmean_mape",
                    "model_g1", "ly_g1", "pmean_g1"):
            agg[col] = float(np.mean([r[col] for r in sub]))
        out.append(agg)
    return out


# ----------------------------------------------------------------- Part B
def load_real():
    enr, fail = {}, {}
    with (REPO / "data/enrollments_anonymized.csv").open(encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            enr[(r["course_id"], r["semester"])] = int(r["enrolment_n"])
    with (REPO / "data/failures_S4.csv").open(encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            fail[(r["course_id"], "S4")] = int(r["failures_f"])
    graph = json.loads((REPO / "data/prerequisite_graph.json").read_text(encoding="utf-8"))
    return enr, fail, graph


def real_errors(enr, fail, graph, t, t1, use_fail):
    d, _ = compute_prerequisite_flow_demand_full(graph, enr, fail if use_fail else {}, t)
    sems = ["S1", "S2", "S3", "S4", "S5", "S6"]
    it = sems.index(t)
    same = [s for s in sems[: it + 1] if sems.index(s) % 2 == sems.index(t1) % 2]
    E = {"model": [], "ly": [], "pmean": []}
    for c, dv in sorted(d.items()):
        n = enr.get((c, t1), 0)
        if n <= 0:
            continue
        ly = enr.get((c, sems[it - 1]), 0)
        hist = [enr[(c, s)] for s in same if enr.get((c, s), 0) > 0]
        pm = round(sum(hist) / len(hist))
        E["model"].append(abs(n - dv)); E["ly"].append(abs(n - ly)); E["pmean"].append(abs(n - pm))
    return {k: np.array(v, dtype=float) for k, v in E.items()}


def bootstrap(E, rng):
    N = len(E["model"])
    idx = rng.integers(0, N, size=(B_BOOT, N))
    res = {}
    for k, v in E.items():
        m = v[idx].mean(axis=1)
        res[k] = (float(v.mean()), float(np.percentile(m, 2.5)), float(np.percentile(m, 97.5)))
    for k in ("ly", "pmean"):
        diff = (E["model"] - E[k])[idx].mean(axis=1)
        res[f"model-{k}"] = (float((E["model"] - E[k]).mean()),
                             float(np.percentile(diff, 2.5)), float(np.percentile(diff, 97.5)),
                             float((diff < 0).mean()))
    return res


def main():
    print("=== Part A: synthetic curricula ===")
    rows = part_a()
    print(f"{len(rows)} cells x {R_REPL} replicates")
    for by, title in (
        (("a", "delta"), "by attrition a and intake drift delta (averaged over phi, rho)"),
        (("phi",), "by failure rate phi"),
        (("rho",), "by retake immediacy rho"),
        (("a",), "by attrition a"),
        (("delta",), "by intake drift delta"),
    ):
        print(f"\n-- {title}")
        hdr = " ".join(f"{b:>6}" for b in by) + "   MAPE% model    LY  P-mean | groups+-1% model    LY  P-mean"
        print(hdr)
        for r in summarise(rows, by):
            print(" ".join(f"{r[b]:>6}" for b in by) +
                  f"          {r['model_mape']:6.1f} {r['ly_mape']:6.1f} {r['pmean_mape']:6.1f}"
                  f"   |          {r['model_g1']:6.1f} {r['ly_g1']:6.1f} {r['pmean_g1']:6.1f}")
    overall = summarise(rows, ())[0]
    print("\n-- overall:", {k: round(v, 1) for k, v in overall.items()})

    print("\n=== Part B: bootstrap on real data ===")
    enr, fail, graph = load_real()
    rng = np.random.default_rng(SEED)
    for name, t, t1, uf in (("Exp 1", "S4", "S5", True), ("Exp 2", "S5", "S6", False)):
        E = real_errors(enr, fail, graph, t, t1, uf)
        res = bootstrap(E, rng)
        print(f"\n{name} (N = {len(E['model'])}, B = {B_BOOT})")
        for k in ("model", "ly", "pmean"):
            m, lo, hi = res[k]
            print(f"  MAE {k:6}: {m:5.1f}  95% CI [{lo:5.1f}, {hi:5.1f}]")
        for k in ("model-ly", "model-pmean"):
            m, lo, hi, pneg = res[k]
            print(f"  dMAE {k:12}: {m:+5.1f}  95% CI [{lo:+5.1f}, {hi:+5.1f}]  P(model better) = {pneg:.2f}")

    # persist
    import pandas as pd
    with pd.ExcelWriter(REPO / "Synthetic_and_Bootstrap.xlsx") as w:
        pd.DataFrame(rows).to_excel(w, sheet_name="synthetic_cells", index=False)
        pd.DataFrame(summarise(rows, ("a", "delta"))).to_excel(w, sheet_name="by_a_delta", index=False)
    print("\nwrote Synthetic_and_Bootstrap.xlsx")


if __name__ == "__main__":
    main()
