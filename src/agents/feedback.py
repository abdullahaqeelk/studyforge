"""
StudyForge — targeted feedback on a graded answer (SF-16).

Turns a grading result from SF-15 into a short explanation written to the
student: what their answer covered, and what it missed. The explanation is
built only from the points SF-15 extracted from the student's own course
material, and cites the pages those points came from.

Two things this module deliberately does not do.

It does not retrieve. Every point arrives from SF-15 carrying its chunk_id and
its page (docs/grading-contract.md, rule 2). Calling search() again would spend
quota and could return a different passage than the one the grade was based on,
so the feedback would cite a page the grade did not come from.

It does not invent. The model is given the points and nothing else, and every
page it cites is checked against the points it was given. A model explaining a
missed point from its own knowledge of the subject is the exact failure
StudyForge exists to prevent: the student is revising one document, and a
correct-sounding explanation of material that is not in it is worse than no
explanation at all.

Usage:

    from agents.feedback import generate_feedback

    result = grade_answer(question, answer, store)   # SF-15
    explained = generate_feedback(result)
    explained["feedback"]       # "You correctly identified ..."
    explained["cited_pages"]    # [4]
"""

from __future__ import annotations

import json
import logging

from config import StudyForgeError, classify_api_error, get_client, get_model
from prompt_loader import load_prompt

PROMPT_FILE = "feedback_generation_v1.md"
LOGGER = logging.getLogger(__name__)

FEEDBACK_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "feedback": {"type": "STRING"},
        "cited_pages": {"type": "ARRAY", "items": {"type": "INTEGER"}},
    },
    "required": ["feedback", "cited_pages"],
}


class FeedbackError(StudyForgeError):
    """The grading result or the generated feedback did not meet the contract."""


# --------------------------------------------------------------------------
# Input validation — docs/grading-contract.md
# --------------------------------------------------------------------------

def _check_points(points, label: str) -> None:
    """Every point must name a chunk and carry its own page (contract rule 2)."""
    if not isinstance(points, list):
        raise FeedbackError(f"'{label}' must be a list of points.")
    for point in points:
        if (not isinstance(point, dict)
                or type(point.get("chunk_id")) is not int
                or type(point.get("page")) is not int
                or point["page"] < 1
                or not isinstance(point.get("point"), str)
                or not point["point"].strip()):
            raise FeedbackError(
                f"Each point in '{label}' needs an integer chunk_id, a positive "
                "page and non-empty text. A point without its page would force a "
                "second retrieval; see docs/grading-contract.md rule 2."
            )


def _validate(result) -> None:
    """Reject a grading result that breaks the contract, rather than papering over it."""
    if not isinstance(result, dict):
        raise FeedbackError("Provide a grading result from SF-15.")

    if (not isinstance(result.get("question"), str) or not result["question"].strip()
            or not isinstance(result.get("answer"), str)
            or type(result.get("source_page")) is not int or result["source_page"] < 1):
        raise FeedbackError(
            "A grading result needs a question, an answer and a positive source_page.")

    if type(result.get("graded")) is not bool:
        raise FeedbackError("A grading result needs a boolean 'graded'.")

    if (type(result.get("score")) is not int or type(result.get("max_score")) is not int
            or result["max_score"] < 1 or not 0 <= result["score"] <= result["max_score"]):
        raise FeedbackError("'score' must be an integer between 0 and 'max_score'.")

    _check_points(result.get("covered"), "covered")
    _check_points(result.get("missed"), "missed")

    if not result["graded"]:
        if not isinstance(result.get("reason"), str) or not result["reason"].strip():
            raise FeedbackError("An ungraded result must say why, in 'reason'.")
        if result["score"] or result["covered"] or result["missed"]:
            raise FeedbackError(
                "An ungraded result carries no score and no points; it is the "
                "absence of a grade, not a grade of zero.")
        return

    # Contract rule 4. A score the source cannot account for is not something to
    # explain to a student — there is nothing to point them at.
    if result["score"] > 0 and not result["covered"]:
        raise FeedbackError(
            f"Score is {result['score']} but no covered points were supplied. A "
            "score must be justified by the points it was awarded for; see "
            "docs/grading-contract.md rule 4.")


# --------------------------------------------------------------------------
# Response validation
# --------------------------------------------------------------------------

def parse_feedback(response_text: str, allowed_pages: set[int]) -> dict:
    """Validate a feedback response and return {"feedback", "cited_pages"}.

    Args:
        response_text: raw JSON text returned by the model.
        allowed_pages: the pages carried by the points actually supplied.

    Returns:
        The feedback text and the pages it cites, de-duplicated and sorted.

    Raises:
        FeedbackError: the response is malformed, or cites a page that was not
            supplied.
    """
    if not isinstance(response_text, str) or not response_text.strip():
        raise FeedbackError("The model returned an empty response.")
    try:
        payload = json.loads(response_text)
    except (TypeError, ValueError, RecursionError) as exc:
        raise FeedbackError(f"The model did not return valid JSON: {exc}") from exc

    if not isinstance(payload, dict) or set(payload) != {"feedback", "cited_pages"}:
        raise FeedbackError("The model must return exactly feedback and cited_pages.")

    text = payload["feedback"]
    if not isinstance(text, str) or not text.strip():
        raise FeedbackError("The model returned empty feedback.")

    pages = payload["cited_pages"]
    if not isinstance(pages, list):
        raise FeedbackError("'cited_pages' must be a list of page numbers.")

    seen: set[int] = set()
    for page in pages:
        if type(page) is not int:
            raise FeedbackError("Each cited page must be an integer.")
        # The same check SF-12 makes on evidence and SF-13 makes on chunk ids:
        # a citation to something that was never supplied is ungrounded,
        # however plausible the sentence around it reads.
        if page not in allowed_pages:
            raise FeedbackError(
                f"The feedback cites page {page}, which was not among the pages "
                "supplied. Feedback may only cite the material it was shown.")
        seen.add(page)

    return {"feedback": " ".join(text.split()), "cited_pages": sorted(seen)}


# --------------------------------------------------------------------------
# Generation
# --------------------------------------------------------------------------

def generate_feedback(result: dict) -> dict:
    """Explain a graded answer to the student, from the source points alone.

    Args:
        result: a grading result from SF-15, as specified in
            docs/grading-contract.md.

    Returns:
        A copy of the result with two keys added:
          feedback     the explanation, or None when the answer was not graded
          cited_pages  the pages the explanation draws on, [] when not graded

        An ungraded result is returned unexplained: there is no grade to
        explain, and 'reason' already says why. Inventing feedback there would
        describe material the retrieval step never found.

    Raises:
        FeedbackError: the grading result breaks the contract, or the model's
            response does after one retry.
        StudyForgeError: prompt, configuration or provider failure. Provider
            errors are not retried and never become feedback.
    """
    _validate(result)

    if not result["graded"]:
        LOGGER.info("SF-16 ungraded_not_explained page=%s", result["source_page"])
        return {**result, "feedback": None, "cited_pages": []}

    points = result["covered"] + result["missed"]
    allowed_pages = {point["page"] for point in points} | {result["source_page"]}

    # One request per answer, not one per missed point. A ten-point answer would
    # otherwise cost ten calls against a free-tier quota the whole team shares.
    body = json.dumps({
        "question": result["question"],
        "student_answer": result["answer"],
        "score": result["score"],
        "max_score": result["max_score"],
        "covered": [{"page": p["page"], "point": p["point"]} for p in result["covered"]],
        "missed": [{"page": p["page"], "point": p["point"]} for p in result["missed"]],
    }, ensure_ascii=False)

    prompt = load_prompt(PROMPT_FILE)
    client = get_client()
    model = get_model()
    try:
        for attempt in range(2):
            try:
                response = client.models.generate_content(
                    model=model,
                    contents=body,
                    config={"system_instruction": prompt,
                            "response_mime_type": "application/json",
                            "response_schema": FEEDBACK_SCHEMA},
                )
            except Exception as exc:  # noqa: BLE001 - provider raises untyped errors
                raise classify_api_error(exc) from exc
            try:
                parsed = parse_feedback(response.text, allowed_pages)
                break
            except FeedbackError as exc:
                LOGGER.warning("SF-16 feedback_rejected attempt=%s: %s", attempt + 1, exc)
                if attempt == 1:
                    raise FeedbackError(
                        f"Feedback generation failed after two attempts: {exc}"
                    ) from exc
                # Both attempts send the same payload and prompt. Rejected output
                # is never fed back as an instruction (AID-3).
                LOGGER.info("SF-16 regeneration_requested attempt=2")
    finally:
        client.close()

    LOGGER.info("SF-16 feedback_generated score=%s/%s missed=%s pages=%s",
                result["score"], result["max_score"], len(result["missed"]),
                parsed["cited_pages"])
    return {**result, **parsed}


def explain_all(results: list[dict]) -> list[dict]:
    """Explain a batch of graded answers, one request per graded answer.

    Ungraded results consume no request. The list returned stays aligned with
    the list passed in, so a caller can zip it against the questions.
    """
    if not isinstance(results, list) or not results:
        raise FeedbackError("Provide a non-empty list of grading results.")
    return [generate_feedback(result) for result in results]
