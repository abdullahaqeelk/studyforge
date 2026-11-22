"""
Grading-result fixtures for SF-16 (docs/grading-contract.md).

SF-16 is written against these rather than against SF-15 itself, so the two
stories proceed in parallel. Nothing here calls a model or touches the network.

When SF-15 merges, these fixtures stay: they are what lets the SF-16 test suite
run with no API key, and they are the executable statement of the contract. If
SF-15 ever stops producing something that matches these, the contract changed
and docs/grading-contract.md changes with it.
"""

from __future__ import annotations

MAX_SCORE = 5


def _result(**overrides) -> dict:
    base = {
        "question": "What does the backward difference operator compute?",
        "answer": "It finds the difference between two values.",
        "source_page": 4,
        "graded": True,
        "reason": None,
        "score": 2,
        "max_score": MAX_SCORE,
        "covered": [],
        "missed": [],
    }
    base.update(overrides)
    return base


def partially_correct() -> dict:
    """Some source points made, some missed — the ordinary case."""
    return _result(
        score=2,
        covered=[
            {"chunk_id": 7, "page": 4,
             "point": "a difference between two tabulated values"},
        ],
        missed=[
            {"chunk_id": 7, "page": 4,
             "point": "the difference is taken with the preceding value, not the following one"},
            {"chunk_id": 8, "page": 4,
             "point": "written as nabla f(x) = f(x) - f(x - h)"},
        ],
    )


def fully_correct() -> dict:
    """Full marks, nothing missed. Feedback must confirm, not invent criticism."""
    return _result(
        answer="It is f(x) minus f(x - h) — the difference with the preceding tabulated value.",
        score=MAX_SCORE,
        covered=[
            {"chunk_id": 7, "page": 4,
             "point": "a difference between two tabulated values"},
            {"chunk_id": 7, "page": 4,
             "point": "the difference is taken with the preceding value"},
            {"chunk_id": 8, "page": 4,
             "point": "written as nabla f(x) = f(x) - f(x - h)"},
        ],
        missed=[],
    )


def wholly_incorrect() -> dict:
    """Graded, but nothing from the source was covered."""
    return _result(
        answer="It computes the integral under the curve.",
        score=0,
        covered=[],
        missed=[
            {"chunk_id": 7, "page": 4,
             "point": "a difference between two tabulated values"},
            {"chunk_id": 8, "page": 4,
             "point": "written as nabla f(x) = f(x) - f(x - h)"},
        ],
    )


def ungraded() -> dict:
    """Retrieval found nothing. SF-16 surfaces the reason and produces no feedback."""
    return _result(
        answer="No idea",
        graded=False,
        reason="No passage on page 4 cleared the similarity floor.",
        score=0,
        covered=[],
        missed=[],
    )


def empty_answer() -> dict:
    """Blank submission — graded locally by SF-15 with no model call."""
    return _result(
        answer="   ",
        graded=False,
        reason="No answer was submitted.",
        score=0,
        covered=[],
        missed=[],
    )


# ---------------------------------------------------------------------------
# Contract violations. SF-16 must raise on these, not paper over them.
# ---------------------------------------------------------------------------

def score_without_covered() -> dict:
    """Rule 4: a score above zero must be justified by covered points."""
    return _result(score=3, covered=[], missed=[
        {"chunk_id": 7, "page": 4, "point": "a difference between two tabulated values"},
    ])


def missing_page_on_point() -> dict:
    """Rule 2: every point carries its page, so SF-16 never re-retrieves."""
    return _result(
        score=1,
        covered=[{"chunk_id": 7, "point": "a difference between two tabulated values"}],
    )
