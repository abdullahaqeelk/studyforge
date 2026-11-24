"""
StudyForge — Local deterministic multiple-choice answer evaluation (SF-14).
"""

from config import StudyForgeError


class AnswerCheckError(StudyForgeError):
    """Raised when a question or submitted option cannot be evaluated."""


def evaluate_answer(question: dict, submitted_option: int) -> dict:
    """Mark a submitted multiple-choice answer. Local, deterministic, no model call."""
    if not isinstance(question, dict):
        raise AnswerCheckError("Question must be a dictionary.")

    if question.get("question_type") != "multiple_choice":
        raise AnswerCheckError("Only 'multiple_choice' questions can be evaluated.")

    options = question.get("options")
    if not isinstance(options, list) or len(options) != 4:
        raise AnswerCheckError("Question is missing a valid 4-item 'options' list.")

    correct_option = question.get("correct_option")
    if type(correct_option) is not int or correct_option not in range(len(options)):
        raise AnswerCheckError("Question has an invalid 'correct_option' index.")

    if type(submitted_option) is not int or submitted_option not in range(len(options)):
        raise AnswerCheckError(
            f"submitted_option {submitted_option!r} is out of range for {len(options)} options."
        )

    return {
        "submitted_option": submitted_option,
        "correct_option": correct_option,
        "is_correct": submitted_option == correct_option,
        "source_page": question.get("source_page"),
    }