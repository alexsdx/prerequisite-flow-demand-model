"""Algorithm 1: ComputePrerequisiteFlowDemand.

Reference implementation of the structural prerequisite-flow demand model
described in Section 3.2 of the article (revised version, v1.1.0). The
model is a deterministic pass over the curricular prerequisite graph that
estimates the per-course demand for the upcoming semester (t + 1) from
observed enrolments and failures in the current semester (t).

The implementation uses exact integer arithmetic and contains no random
component, so reruns are bit-identical to the figures reported in the
article.

Equations implemented (Section 3.2 of the article):

    p_c(t)   = n_c(t) - f_c(t)                              (1)
    r_c(t+1) = f_c(t)                                       (2)
    d_c(t+1) = p_{pre(c)}(t) + r_c(t+1)                     (3)
               defined iff pre(c) is defined and pre(c) was
               offered in t; otherwise c is NON-PREDICTABLE.

Change with respect to v1.0.0
-----------------------------
v1.0.0 implemented a k-step retake accumulator and, for courses whose
prerequisite was not offered in t (root courses included), reported the
retake count r_c alone as the demand estimate. Both choices were revised
following peer review: the retake rule is now the one-step recurrence (2)
that the code had in fact always used (k = 1), and courses without an
offered prerequisite are reported as non-predictable instead of receiving
a retake-only estimate. See Section 3.2 and Section 5.2 of the revised
article.
"""

from __future__ import annotations

from typing import Dict, Iterable, Set, Tuple

CourseId = str
Semester = str
EnrolmentTable = Dict[Tuple[CourseId, Semester], int]
FailureTable = Dict[Tuple[CourseId, Semester], int]


def _build_predecessor_index(graph: dict) -> Dict[CourseId, CourseId]:
    """Return {child: parent} for the in-tree forest defined by `graph`.

    The graph is the JSON structure produced by `data/prerequisite_graph.json`:
    {"vertices": [...], "edges": [{"from": parent, "to": child}, ...]}.
    """
    parent_of: Dict[CourseId, CourseId] = {}
    for edge in graph["edges"]:
        parent_of[edge["to"]] = edge["from"]
    return parent_of


def _passing_flow(
    enrolments: EnrolmentTable,
    failures: FailureTable,
    course_id: CourseId,
    semester: Semester,
) -> int:
    """p_c(t) = n_c(t) - f_c(t), Eq. (1).

    f_c(t) <= n_c(t) holds by construction of the academic record; a source
    violating it is rejected at ingestion rather than clipped here.
    """
    n = enrolments.get((course_id, semester), 0)
    f = failures.get((course_id, semester), 0)
    if f > n:
        raise ValueError(
            f"failures exceed enrolment for course {course_id} in {semester}: "
            f"f={f} > n={n}; reject the record at ingestion."
        )
    return n - f


def _retake_demand(
    failures: FailureTable,
    course_id: CourseId,
    t: Semester,
) -> int:
    """r_c(t+1) = f_c(t), Eq. (2)."""
    return failures.get((course_id, t), 0)


def compute_prerequisite_flow_demand_full(
    graph: dict,
    enrolments: EnrolmentTable,
    failures: FailureTable,
    t: Semester,
    offered_in_t: Iterable[CourseId] | None = None,
) -> Tuple[Dict[CourseId, int], Set[CourseId]]:
    """Run Algorithm 1 and return (d, U).

    Parameters
    ----------
    graph:
        Prerequisite graph as parsed from `prerequisite_graph.json`.
    enrolments:
        Dict keyed by (course_id, semester) returning n_c(semester).
    failures:
        Dict keyed by (course_id, semester) returning f_c(semester).
        Pass an empty dict to evaluate the f = 0 boundary case.
    t:
        The current semester. Estimates are made for t + 1.
    offered_in_t:
        Optional explicit set O_t of courses offered in t. When omitted it
        is derived from the enrolment table (courses with a record in t).

    Returns
    -------
    d : dict mapping every predictable course c to the integer d_c(t + 1).
    U : set of non-predictable courses (root courses and courses whose
        prerequisite was not offered in t). Their demand is assembled in
        the human-judgement component (Algorithm 2).
    """
    parent_of = _build_predecessor_index(graph)
    if offered_in_t is None:
        offered = {course for (course, sem) in enrolments if sem == t}
    else:
        offered = set(offered_in_t)

    demand: Dict[CourseId, int] = {}
    non_predictable: Set[CourseId] = set()
    for course in graph["vertices"]:
        parent = parent_of.get(course)
        if parent is not None and parent in offered:
            flow_in = _passing_flow(enrolments, failures, parent, t)
            demand[course] = flow_in + _retake_demand(failures, course, t)
        else:
            non_predictable.add(course)
    return demand, non_predictable


def compute_prerequisite_flow_demand(
    graph: dict,
    enrolments: EnrolmentTable,
    failures: FailureTable,
    t: Semester,
    t_plus_1: Semester | None = None,
    semester_order: Iterable[Semester] | None = None,
    k: int | None = None,
) -> Dict[CourseId, int]:
    """Backward-compatible wrapper returning only the predictable estimates d.

    `t_plus_1`, `semester_order` and `k` are accepted for compatibility with
    v1.0.0 call sites and are ignored: the revised model is one-step (Eq. 2)
    and needs neither a semester ordering nor a retry cap.
    """
    demand, _ = compute_prerequisite_flow_demand_full(graph, enrolments, failures, t)
    return demand
