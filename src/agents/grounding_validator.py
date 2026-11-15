"""SF-12: check questions/answers against retrieved evidence, with one retry."""

from __future__ import annotations

import json
import logging

from agents.question_generator import QuestionGenerationError, generate_questions
from config import StudyForgeError, classify_api_error, get_client, get_model
from prompt_loader import load_prompt
from vector_store import search

PROMPT_FILE = "grounding_validation_v1.md"
LOGGER = logging.getLogger(__name__)
WARNING = "Ungrounded: this question or answer could not be verified against its cited source."
VERDICT_SCHEMA = {
    "type": "ARRAY",
    "items": {
        "type": "OBJECT",
        "properties": {
            "item_index": {"type": "INTEGER"},
            "grounded": {"type": "BOOLEAN"},
            "evidence": {
                "type": "ARRAY",
                "items": {
                    "type": "OBJECT",
                    "properties": {
                        "chunk_id": {"type": "INTEGER"},
                        "quote": {"type": "STRING"},
                    },
                    "required": ["chunk_id", "quote"],
                },
            },
        },
        "required": ["item_index", "grounded", "evidence"],
    },
}


class GroundingError(StudyForgeError):
    """Validation input or the judge response is malformed; no pass is implied."""


def _prepare(items: list[dict], chunks: list[dict]) -> tuple[list[dict], dict]:
    """Validate caller input and strip embeddings/metadata from judge payloads."""
    if not isinstance(items, list) or not items:
        raise GroundingError("Provide non-empty questions to validate.")
    if not isinstance(chunks, list):
        raise GroundingError("Source chunks must be a list.")
    sources = {}
    for chunk in chunks:
        if (not isinstance(chunk, dict) or type(chunk.get("chunk_id")) is not int
                or type(chunk.get("page")) is not int or chunk["page"] < 1
                or not isinstance(chunk.get("text"), str) or not chunk["text"].strip()
                or chunk["chunk_id"] in sources):
            raise GroundingError("Source chunks need unique integer IDs, positive pages and text.")
        sources[chunk["chunk_id"]] = {
            "chunk_id": chunk["chunk_id"], "page": chunk["page"], "text": chunk["text"]}
    prepared = []
    for index, item in enumerate(items):
        if (not isinstance(item, dict) or not isinstance(item.get("question"), str)
                or not item["question"].strip() or type(item.get("source_page")) is not int
                or item["source_page"] < 1
                or ("answer" in item and (not isinstance(item["answer"], str)
                                          or not item["answer"].strip()))):
            raise GroundingError("Each item needs a question, positive source_page and optional answer text.")
        prepared.append({
            "item_index": index, "question": item["question"],
            **({"answer": item["answer"]} if "answer" in item else {}),
            "source_page": item["source_page"],
            "sources": [c for c in sources.values() if c["page"] == item["source_page"]],
        })
    return prepared, sources


def _parse_verdicts(text: str, items: list[dict], sources: dict) -> list[dict]:
    """Require one binary verdict per item and locally verify its evidence."""
    try:
        verdicts = json.loads(text)
    except (TypeError, ValueError, RecursionError) as exc:
        raise GroundingError("The grounding check did not return valid JSON.") from exc
    if not isinstance(verdicts, list) or len(verdicts) != len(items):
        raise GroundingError("The grounding check must return one verdict per item.")
    by_index = {}
    for verdict in verdicts:
        if (not isinstance(verdict, dict)
                or set(verdict) != {"item_index", "grounded", "evidence"}
                or type(verdict["item_index"]) is not int
                or not 0 <= verdict["item_index"] < len(items)
                or verdict["item_index"] in by_index
                or type(verdict["grounded"]) is not bool
                or not isinstance(verdict["evidence"], list)):
            raise GroundingError("The grounding check returned an invalid verdict.")
        index = verdict["item_index"]
        evidence = []
        valid = bool(verdict["evidence"])
        for reference in verdict["evidence"]:
            if (not isinstance(reference, dict) or set(reference) != {"chunk_id", "quote"}
                    or type(reference["chunk_id"]) is not int
                    or not isinstance(reference["quote"], str)):
                raise GroundingError("The grounding check returned invalid evidence.")
            chunk = sources.get(reference["chunk_id"])
            quote = reference["quote"].strip()
            if (not chunk or chunk["page"] != items[index]["source_page"]
                    or not quote or quote not in chunk["text"]):
                valid = False
            else:
                evidence.append({"chunk_id": chunk["chunk_id"], "page": chunk["page"], "quote": quote})
        grounded = verdict["grounded"] and valid
        by_index[index] = {
            **items[index], "grounded": grounded,
            "grounding_score": int(grounded),
            "source_evidence": evidence if grounded else [],
            "grounding_warning": None if grounded else WARNING,
        }
    return [by_index[index] for index in range(len(items))]


def validate_grounding(items: list[dict], source_chunks: list[dict]) -> list[dict]:
    """Return copies of questions/optional answers with binary grounding scores.

    Only retrieved chunks from each item's cited page are shown to the judge.
    A positive semantic verdict also needs an exact quote from those chunks.
    Empty retrieval fails locally. Provider failures propagate as typed errors;
    a malformed judge response raises GroundingError, never a fabricated pass.
    """
    prepared, sources = _prepare(items, source_chunks)
    # Items with no evidence cannot be grounded, and do not need a model call.
    eligible = [item for item in prepared if item["sources"]]
    if not eligible:
        return [{**item, "grounded": False, "grounding_score": 0,
                 "source_evidence": [], "grounding_warning": WARNING} for item in items]
    prompt = load_prompt(PROMPT_FILE)
    client = get_client()
    try:
        try:
            response = client.models.generate_content(
                model=get_model(), contents=json.dumps({"items": prepared}, ensure_ascii=False),
                config={"system_instruction": prompt, "response_mime_type": "application/json",
                        "response_schema": VERDICT_SCHEMA})
        except Exception as exc:
            raise classify_api_error(exc) from exc
        return _parse_verdicts(response.text, items, sources)
    finally:
        client.close()


def generate_validated_questions(pages: list[dict], store: dict) -> list[dict]:
    """Generate/validate a batch with at most two total generation calls.

    Schema failures and grounding failures share one retry budget. Grounding is
    checked against SF-11 search results (including its similarity floor), not
    the whole document. Final unsupported items retain an explicit warning.
    Provider/configuration failures are not retried or disguised as warnings.
    """
    for attempt in range(2):
        try:
            questions = generate_questions(pages, max_attempts=1)
        except QuestionGenerationError:
            LOGGER.info("SF-12 schema_failed attempt=%s", attempt + 1)
            if attempt:
                raise
            LOGGER.info("SF-12 regeneration_requested attempt=2")
            continue
        chunks = {}
        for item in questions:
            hits = search(store, item["question"])
            for chunk in hits:
                chunks[chunk["chunk_id"]] = chunk
        try:
            checked = validate_grounding(questions, list(chunks.values()))
        except GroundingError:
            LOGGER.warning("SF-12 validator_response_invalid attempt=%s", attempt + 1)
            if attempt:
                raise
            LOGGER.info("SF-12 regeneration_requested attempt=2")
            continue
        failures = sum(not item["grounded"] for item in checked)
        LOGGER.info("SF-12 grounding_checked attempt=%s unsupported=%s", attempt + 1, failures)
        if not failures or attempt:
            if failures:
                LOGGER.warning("SF-12 ungrounded_warning count=%s", failures)
            return checked
        LOGGER.info("SF-12 regeneration_requested attempt=2")
    raise AssertionError("unreachable")
