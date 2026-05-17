"""Algorithm 1: ComputePrerequisiteFlowDemand.

Reference implementation of the structural prerequisite-flow demand model
described in Section 3.2 of the article. The model is a deterministic,
linear-time pass over the curricular prerequisite graph that predicts the
per-course demand for the upcoming semester (t + 1) from observed
enrolments and failures in the current semester (t).

The implementation uses exact integer arithmetic and contains no random
component, so reruns are bit-identical to the figures reported in the
article.

Equations implemented (§3.2 of the article):

    p_c(t) = n_c(t) - f_c(t)                              (1)
    r_c(t+1) = sum_{j=1..k} f_c(t-j+1)                    (2)
    d_c(t+1) = sum_{c' in pred(c)} p_{c'}(t) + r_c(t+1)   (3)
    d_c(t+1) is defined when pre(c) was offered in t or
    r_c(t+1) > 0; otherwise c is non-predictable           (4)

For this article's dataset, failure data are only available for one
semester (S4). When k > 1 is requested but earlier-semester failures are
absent, the missing terms in (2) are taken as zero, which makes the k > 1
prediction collapse to the k = 1 prediction. This is faithful to the
article's discussion of the asymptotic equivalence of the two regimes.
"""

from __future__ import annotations

from typing import Dict, Iterable, Tuple

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
    """p_c(t) = n_c(t) - f_c(t), clipped at zero."""
    n = enrolments.get((course_id, semester), 0)
    f = failures.get((course_id, semester), 0)
    return max(n - f, 0)


def _retake_demand(
    failures: FailureTable,
    course_id: CourseId,
    target_semester: Semester,
    prior_semesters: Iterable[Semester],
    k: int,
) -> int:
    """r_c(t+1) = sum of f_c over the k most recent semesters preceding t+1."""
    total = 0
    for j, sem in enumerate(prior_semesters):
        if j >= k:
            break
        total += failures.get((course_id, sem), 0)
    return total


def compute_prerequisite_flow_demand(
    graph: dict,
    enrolments: EnrolmentTable,
    failures: FailureTable,
    t: Semester,
    t_plus_1: Semester,
    semester_order: Iterable[Semester],
    k: int = 1,
) -> Dict[CourseId, int]:
    """Predict d_c(t + 1) for every course c in the graph.

    Parameters
    ----------
    graph:
        Prerequisite graph as parsed from `prerequisite_graph.json`.
    enrolments:
        Dict keyed by (course_id, semester) returning n_c(semester).
    failures:
        Dict keyed by (course_id, semester) returning f_c(semester).
    t:
        The current semester. Predictions are made for `t_plus_1`.
    t_plus_1:
        The target semester.
    semester_order:
        Full list of semester ids in chronological order (e.g.,
        ['S1', 'S2', 'S3', 'S4', 'S5', 'S6']). Used to identify the k
        semesters preceding `t_plus_1` for the retake summation.
    k:
        Retry-cap parameter from §3.2 of the article.

    Returns
    -------
    Dict mapping each course c with a defined prediction to the integer
    d_c(t + 1). Courses without a defined prediction (per §3.2 line (4))
    are omitted; callers should treat them as non-predictable.
    """
    parent_of = _build_predecessor_index(graph)
    semester_order = list(semester_order)

    # The k most recent semesters strictly before t_plus_1, newest first.
    idx = semester_order.index(t_plus_1)
    prior = list(reversed(semester_order[:idx]))

    courses_offered_in_t = {
        course_id for (course_id, sem) in enrolments if sem == t
    }

    demand: Dict[CourseId, int] = {}
    for course in graph["vertices"]:
        parent = parent_of.get(course)
        retake = _retake_demand(failures, course, t_plus_1, prior, k)

        if parent is not None and parent in courses_offered_in_t:
            flow_in = _passing_flow(enrolments, failures, parent, t)
            demand[course] = flow_in + retake
        elif retake > 0:
            # Root or isolated course with retake demand only.
            demand[course] = retake
        # Otherwise: non-predictable, omitted.

    return demand
