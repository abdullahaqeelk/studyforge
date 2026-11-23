"""Grade a short answer and return the SF-15 → SF-16 grading contract."""

import json

from config import StudyForgeError, classify_api_error, get_client, get_model
from prompt_loader import load_prompt
from vector_store import search

MAX_SCORE = 5
PROMPT_FILE = "answer_grading_v2.md"
_POINT_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "chunk_id": {"type": "INTEGER"},
        "point": {"type": "STRING"},
        "source_quote": {"type": "STRING"},
        "weight": {"type": "INTEGER", "minimum": 1, "maximum": MAX_SCORE},
    },
    "required": ["chunk_id", "point", "source_quote", "weight"],
}
_COVERED_SCHEMA = {
    **_POINT_SCHEMA,
    "properties": {**_POINT_SCHEMA["properties"], "answer_quote": {"type": "STRING"}},
    "required": [*_POINT_SCHEMA["required"], "answer_quote"],
}
_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "covered": {"type": "ARRAY", "items": _COVERED_SCHEMA},
        "missed": {"type": "ARRAY", "items": _POINT_SCHEMA},
    },
    "required": ["covered", "missed"],
}


class GradingError(StudyForgeError):
    """The grading request or model response did not meet the contract."""


def _contains_quote(text: str, quote: object) -> bool:
    """Check a verbatim excerpt while allowing PDF line wraps and spacing."""
    return isinstance(quote, str) and bool(quote.strip()) and (
        " ".join(quote.split()) in " ".join(text.split())
    )


def _parse_grade(raw: str, sources: list[dict], answer: str) -> dict:
    """Validate the rubric and add credit only for verified covered points."""
    try:
        result = json.loads(raw)
    except (TypeError, ValueError, RecursionError) as exc:
        raise GradingError("The grading model did not return valid JSON.") from exc
    if not isinstance(result, dict) or result.keys() != {"covered", "missed"}:
        raise GradingError("The model did not return the required grading fields.")
    chunks = {chunk["chunk_id"]: chunk for chunk in sources}
    checked = {"score": 0}
    seen_points = set()
    rubric_weight = 0
    for field, schema in (("covered", _COVERED_SCHEMA), ("missed", _POINT_SCHEMA)):
        if not isinstance(result[field], list):
            raise GradingError(f"Grading field {field} must be a list.")
        points = []
        for entry in result[field]:
            if (not isinstance(entry, dict) or entry.keys() != set(schema["required"])
                    or type(entry["chunk_id"]) is not int
                    or entry["chunk_id"] not in chunks
                    or not isinstance(entry["point"], str) or not entry["point"].strip()):
                raise GradingError("A grading point did not cite a supplied source chunk or had no text.")
            chunk = chunks[entry["chunk_id"]]
            if not _contains_quote(chunk["text"], entry["source_quote"]):
                raise GradingError("A grading point quoted text missing from its source chunk.")
            weight = entry["weight"]
            if type(weight) is not int or not 1 <= weight <= MAX_SCORE:
                raise GradingError("Each rubric weight must be an integer from 1 to 5.")
            point = entry["point"].strip()
            point_key = " ".join(point.casefold().split())
            if point_key in seen_points:
                raise GradingError("The rubric repeated a grading point.")
            seen_points.add(point_key)
            rubric_weight += weight
            if field == "covered":
                if not _contains_quote(answer, entry["answer_quote"]):
                    raise GradingError("A covered point quoted text missing from the submitted answer.")
                checked["score"] += weight
            points.append({"chunk_id": chunk["chunk_id"], "page": chunk["page"], "point": point})
        checked[field] = points
    if rubric_weight != MAX_SCORE:
        raise GradingError("The rubric weights must total 5.")
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
        grade = _parse_grade(response.text, sources, answer)
    finally:
        client.close()
    return {**base, **grade, "graded": True}
