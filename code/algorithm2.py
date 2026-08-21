"""Algorithm 2: HybridDemandPlan (revised version, v1.1.0).

Reference implementation of the Hybrid Augmented Intelligence workflow of
Section 6.2 of the article. Algorithm 2 takes the structural estimate d_c
and the non-predictable set U from Algorithm 1, combines d_c with four
channel values I, L, X, E (administrator-confirmed, pre-filled from
per-channel priors), applies the specialty-track share alpha_track, sizes
groups, and - once the semester is realised - updates the priors.

Equations implemented:

    n_aug_c = d_c + I_c + L_c + X_c + E_c,  d_c = 0 for c in U       (7)-(8)
    d_c     = alpha_track(c) * p_pre(c) + r_c   for specialty courses  (9)
    g_c     = ceil(n_aug_c / tau_c)                                     (4)
    h*_c^k  = realised channel value, or attributed residual           (10)
    prior_c^k <- (1 - lambda) * prior_c^k + lambda * h*_c^k            (11)

In the manuscript the channel values are elicited interactively with the
priors as defaults; for batch reproduction the elicitation is replaced by
dictionaries. `run_workflow_batch.py` uses this module to reproduce the
last row of Table 3 (workflow with priors only, no human input).

Change with respect to v1.0.0: the track share now multiplies the passing
flow p_pre(c) as written in Eq. (9) (v1.0.0 multiplied the whole augmented
estimate); non-predictable courses receive d_c = 0 instead of a retake-only
value; the retry cap k is gone; the prior update (10)-(11) is new.
"""

from __future__ import annotations

import math
from typing import Dict, Iterable, Set, Tuple

from algorithm1 import compute_prerequisite_flow_demand_full

CourseId = str
CHANNELS = ("I", "L", "X", "E")


def _passing_and_retake(graph, enrolments, failures, t, course):
    """Return (p_pre(c)(t), r_c(t+1)) for a course with an offered prerequisite."""
    parent = next((e["from"] for e in graph["edges"] if e["to"] == course), None)
    if parent is None:
        return 0, 0
    p = enrolments.get((parent, t), 0) - failures.get((parent, t), 0)
    r = failures.get((course, t), 0)
    return p, r


def hybrid_demand_plan(
    graph: dict,
    enrolments: dict,
    failures: dict,
    t: str,
    channel_values: Dict[CourseId, Dict[str, int]],
    alpha_track: Dict[CourseId, float] | None = None,
    tau_overrides: Dict[CourseId, int] | None = None,
    tau_default: int = 18,
    offered_in_t: Iterable[CourseId] | None = None,
) -> Tuple[Dict[CourseId, dict], Set[CourseId]]:
    """Lines 1-19 of Algorithm 2. Returns (plan, U).

    channel_values: {course: {"I":..,"L":..,"X":..,"E":..}} - the values the
        administrator confirmed (in batch mode: the priors). Missing -> 0.
    alpha_track: {course: share in [0,1]} for specialty courses; absent -> 1.
    tau_overrides: {course: tau_c}; absent -> tau_default.
    plan[c] = {"d", "n_aug", "g", "channels", "alpha", "tau"}.
    """
    alpha_track = alpha_track or {}
    tau_overrides = tau_overrides or {}
    d, U = compute_prerequisite_flow_demand_full(graph, enrolments, failures, t, offered_in_t)

    plan: Dict[CourseId, dict] = {}
    for course in graph["vertices"]:
        dc = d.get(course, 0)                                   # Eq. (7): d = 0 on U
        alpha = alpha_track.get(course, 1.0)
        if course not in U and alpha != 1.0:                    # Eq. (9)
            p, r = _passing_and_retake(graph, enrolments, failures, t, course)
            dc = int(round(alpha * p)) + r
        ch = {k: int(channel_values.get(course, {}).get(k, 0)) for k in CHANNELS}
        n_aug = dc + sum(ch.values())                           # Eqs. (7)-(8)
        tau = tau_overrides.get(course, tau_default)
        g = math.ceil(n_aug / tau) if n_aug > 0 else 0          # Eq. (4)
        plan[course] = {"d": dc, "n_aug": n_aug, "g": g,
                        "channels": ch, "alpha": alpha, "tau": tau}
    return plan, U


def update_priors(
    priors: Dict[CourseId, Dict[str, float]],
    plan: Dict[CourseId, dict],
    realised: Dict[CourseId, int],
    dominant_channel: Dict[CourseId, str],
    realised_channels: Dict[CourseId, Dict[str, int]] | None = None,
    lam: float = 0.5,
) -> Dict[CourseId, Dict[str, float]]:
    """Lines 20-24 of Algorithm 2: Eqs. (10)-(11).

    priors: current {course: {channel: value}}; returns the updated copy.
    realised: observed n_c(t+1).
    dominant_channel: {course: "I"|"L"|"X"|"E"} by course category.
    realised_channels: owner-reported values where available; for the other
        channels of a course, only the dominant channel is scored with the
        attributed residual and the rest keep their prior.
    """
    realised_channels = realised_channels or {}
    out: Dict[CourseId, Dict[str, float]] = {}
    for course, row in plan.items():
        if course not in realised:
            out[course] = dict(priors.get(course, {}))
            continue
        prior = {k: float(priors.get(course, {}).get(k, 0.0)) for k in CHANNELS}
        reported = realised_channels.get(course, {})
        target = dict(prior)
        for k in CHANNELS:
            if k in reported:
                target[k] = float(reported[k])                  # Eq. (10), owner-reported
        dom = dominant_channel.get(course)
        if dom is not None and dom not in reported:
            others = sum(row["channels"][k] for k in CHANNELS if k != dom)
            target[dom] = float(realised[course] - row["d"] - others)   # Eq. (10), residual
        out[course] = {k: (1 - lam) * prior[k] + lam * target[k] for k in CHANNELS}  # Eq. (11)
    return out
