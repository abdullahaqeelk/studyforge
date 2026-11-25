"""Tests for local multiple-choice answer evaluation (SF-14)."""

import pytest

from answer_check import AnswerCheckError, evaluate_answer
from config import StudyForgeError

SAMPLE_MCQ = {
    "question": "Which traversal visits a BST in ascending order?",
    "question_type": "multiple_choice",
    "source_page": 4,
    "options": ["Pre-order", "In-order", "Post-order", "Level-order"],
    "correct_option": 1,
}


def test_evaluate_correct_answer():
    result = evaluate_answer(SAMPLE_MCQ, 1)
    assert result == {
        "submitted_option": 1,
        "correct_option": 1,
        "is_correct": True,
        "source_page": 4,
    }


def test_evaluate_incorrect_answer():
    result = evaluate_answer(SAMPLE_MCQ, 0)
    assert result == {
        "submitted_option": 0,
        "correct_option": 1,
        "is_correct": False,
        "source_page": 4,
    }


@pytest.mark.parametrize("bad_index", [-1, 4, 7, "1", True])
def test_evaluate_out_of_range_raises(bad_index):
    with pytest.raises(AnswerCheckError):
        evaluate_answer(SAMPLE_MCQ, bad_index)


def test_evaluate_short_answer_raises():
    short_q = {
        "question": "Define TCP flow control.",
        "question_type": "short_answer",
        "source_page": 12,
    }
    with pytest.raises(AnswerCheckError):
        evaluate_answer(short_q, 0)


def test_evaluate_missing_options_raises():
    broken_q = {
        "question": "Broken question?",
        "question_type": "multiple_choice",
        "source_page": 2,
        "correct_option": 0,
    }
    with pytest.raises(AnswerCheckError):
        evaluate_answer(broken_q, 0)


def test_answer_check_error_inherits_studyforge_error():
    assert issubclass(AnswerCheckError, StudyForgeError)
