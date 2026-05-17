"""Algorithm 2: HybridDemandPlan.

Reference implementation of the Hybrid Augmented Intelligence (HAI)
workflow described in Section 6.2 of the article. Algorithm 2 takes the
structural prediction d_c from Algorithm 1 and combines it with four
administrator-supplied exogenous channels I, L, X, E to produce an
augmented plan with logged deltas.

In the manuscript (line 4 of the pseudocode in §6.2) the channels are
elicited interactively from the administrator. For batch reproduction in
the public repository, the elicitation is replaced by per-course CSV
inputs.

Equations implemented (§6.1-§6.2 of the article):

    n_tilde_c = d_c + I_c + L_c + X_c + E_c                    (7)-(8)
    n_tilde_c <- alpha_track(c) * n_tilde_c   for c in track   (9)
    g_c = ceil(n_tilde_c / tau_c)                              (group sizing)

The "deltas" returned per course summarise the per-channel contributions
so that the augmented plan is auditable, as discussed in §6.2.
"""

from __future__ import annotations

import math
from typing import Dict, Tuple

from algorithm1 import compute_prerequisite_flow_demand

CourseId = str


def hybrid_demand_plan(
    graph: dict,
    enrolments: dict,
    failures: dict,
    t: str,
    t_plus_1: str,
    semester_order,
    human_inputs: Dict[CourseId, Dict[str, int]],
    alpha_track: Dict[CourseId, float],
    tau_overrides: Dict[CourseId, int],
    k: int = 1,
    tau_default: int = 18,
) -> Dict[CourseId, dict]:
    """Produce the augmented plan {course: {d, n_tilde, g, deltas}} for t + 1.

    Parameters
    ----------
    graph, enrolments, failures, t, t_plus_1, semester_order, k:
        Forwarded to Algorithm 1 to obtain the structural prediction d_c.
    human_inputs:
        {course_id: {"I": int, "L": int, "X": int, "E": int}} — the four
        exogenous channels of §6.1. Missing entries default to zero.
    alpha_track:
        {course_id: float in [0, 1]} — the track-allocation share for
        specialty courses. Courses absent from this map are treated as
        alpha = 1.0 (i.e., no track correction).
    tau_overrides:
        {course_id: int} — per-course group-size overrides. Courses
        absent default to `tau_default`.
    tau_default:
        Institutional target group size (18 in the case study).

    Returns
    -------
    Dict keyed by course_id with fields:
        d         -- the structural prediction d_c (Algorithm 1 output).
        n_tilde   -- augmented prediction (eq. (7)-(8), with (9) for
                     specialty courses).
        g         -- ceil(n_tilde / tau) groups to open.
        deltas    -- {"I": int, "L": int, "X": int, "E": int, "track": float}
                     for auditability.
    """
    structural = compute_prerequisite_flow_demand(
        graph=graph,
        enrolments=enrolments,
        failures=failures,
        t=t,
        t_plus_1=t_plus_1,
        semester_order=semester_order,
        k=k,
    )

    plan: Dict[CourseId, dict] = {}
    for course in graph["vertices"]:
        d = structural.get(course, 0)
        inputs = human_inputs.get(course, {})
        I_c = int(inputs.get("I", 0))
        L_c = int(inputs.get("L", 0))
        X_c = int(inputs.get("X", 0))
        E_c = int(inputs.get("E", 0))

        n_tilde = d + I_c + L_c + X_c + E_c

        alpha = alpha_track.get(course, 1.0)
        if alpha != 1.0:
            # Eq. (9): multiplicative track correction.
            n_tilde = max(int(round(alpha * n_tilde)), 0)

        tau = tau_overrides.get(course, tau_default)
        groups = math.ceil(n_tilde / tau) if n_tilde > 0 else 0

        plan[course] = {
            "d": d,
            "n_tilde": n_tilde,
            "g": groups,
            "deltas": {
                "I": I_c, "L": L_c, "X": X_c, "E": E_c, "track": alpha,
            },
        }

    return plan
