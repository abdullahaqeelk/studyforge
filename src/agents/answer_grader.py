"""Grade a short answer and return the SF-15 → SF-16 grading contract."""

import json

from config import StudyForgeError, classify_api_error, get_client, get_model
from prompt_loader import load_prompt
from vector_store import search

MAX_SCORE = 5
PROMPT_FILE = "answer_grading_v1.md"
_POINT_SCHEMA = {
    "type": "OBJECT",
    "properties": {"chunk_id": {"type": "INTEGER"}, "point": {"type": "STRING"}},
    "required": ["chunk_id", "point"],
}
_SCHEMA = {
    "type": "OBJECT",
    "properties": {"score": {"type": "INTEGER"},
                   "covered": {"type": "ARRAY", "items": _POINT_SCHEMA},
                   "missed": {"type": "ARRAY", "items": _POINT_SCHEMA}},
    "required": ["score", "covered", "missed"],
}


class GradingError(StudyForgeError):
    """The grading request or model response did not meet the contract."""


def _parse_grade(raw: str, pages_by_chunk: dict[int, int]) -> dict:
    """Validate a score and attach trusted page numbers to its points."""
    try:
        result = json.loads(raw)
    except (TypeError, ValueError, RecursionError) as exc:
        raise GradingError("The grading model did not return valid JSON.") from exc
    if not isinstance(result, dict) or result.keys() != {"score", "covered", "missed"}:
        raise GradingError("The model did not return the required grading fields.")
    score = result["score"]
    if type(score) is not int or not 0 <= score <= MAX_SCORE:
        raise GradingError("The grading score must be an integer from 0 to 5.")
    checked = {"score": score}
    for field in ("covered", "missed"):
        if not isinstance(result[field], list):
            raise GradingError(f"Grading field {field} must be a list.")
        points = []
        for entry in result[field]:
            if (not isinstance(entry, dict) or entry.keys() != {"chunk_id", "point"}
                    or type(entry["chunk_id"]) is not int
                    or entry["chunk_id"] not in pages_by_chunk
                    or not isinstance(entry["point"], str) or not entry["point"].strip()):
                raise GradingError("A grading point did not cite a supplied source chunk or had no text.")
            points.append({"chunk_id": entry["chunk_id"], "page": pages_by_chunk[entry["chunk_id"]],
                           "point": entry["point"].strip()})
        checked[field] = points
    if score > 0 and not checked["covered"]:
        raise GradingError("A positive score requires at least one covered source point.")
    return checked


def grade_answer(question: str, answer: str, source_page: int, store: dict) -> dict:
    """Grade a submitted answer against retrieved chunks from its cited page.

    `store` is the SF-11 vector store. Blank submissions and empty retrieval
    return ungraded results; retrieval, provider and malformed-output failures
    raise StudyForgeError. The submitted question and answer are preserved.
    """
    if (not isinstance(question, str) or not question.strip() or not isinstance(answer, str)
            or type(source_page) is not int or source_page < 1):
        raise GradingError("Provide a question, answer text and a positive source page.")
    base = {"question": question, "answer": answer, "source_page": source_page,
            "graded": False, "reason": None, "score": 0, "max_score": MAX_SCORE,
            "covered": [], "missed": []}
    if not answer.strip():
        return dict(base, reason="No answer was submitted.")

    chunks = store.get("chunks") if isinstance(store, dict) else None
    if not isinstance(chunks, list) or not chunks or any(not isinstance(c, dict) for c in chunks):
        raise GradingError("A valid document vector store is required.")
    page_chunks = [chunk for chunk in chunks if chunk.get("page") == source_page]
    # Restrict candidates before top-k so other pages cannot crowd out the citation.
    # Query by question alone so an incorrect answer cannot steer retrieval.
    hits = search({**store, "chunks": page_chunks}, question) if page_chunks else []
    if not hits:
        return dict(base, reason=f"No passage on page {source_page} cleared the similarity floor.")

    sources = [{field: hit[field] for field in ("chunk_id", "page", "text")} for hit in hits]
    payload = json.dumps({"question": question, "answer": answer, "sources": sources}, ensure_ascii=False)
    prompt = load_prompt(PROMPT_FILE)
    client = get_client()
    try:
        try:
            response = client.models.generate_content(
                model=get_model(), contents=payload,
                config={"system_instruction": prompt, "response_mime_type": "application/json",
                        "response_schema": _SCHEMA},
            )
        except Exception as exc:
            raise classify_api_error(exc) from exc
        grade = _parse_grade(response.text, {c["chunk_id"]: c["page"] for c in sources})
    finally:
        client.close()
    return {**base, **grade, "graded": True}
