"""SF-4: generate five page-cited questions using the shared Gemini client."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from config import StudyForgeError, classify_api_error, get_client, get_model
from prompt_loader import load_prompt

PROMPT_FILE = "question_generation_v1.md"
QUESTION_COUNT = 5
# Sprint 1 sends raw page text, not RAG. Reject large inputs rather than silently
# truncating pages and making the source mapping misleading.
MAX_SOURCE_CHARACTERS = 60_000
QUESTION_SCHEMA = {
    "type": "ARRAY",
    "items": {
        "type": "OBJECT",
        "properties": {
            "question": {"type": "STRING"},
            "question_type": {"type": "STRING", "enum": ["short_answer"]},
            "source_page": {"type": "INTEGER"},
        },
        "required": ["question", "question_type", "source_page"],
    },
}


class QuestionGenerationError(StudyForgeError):
    """Source material or generated questions did not meet the contract."""


def _prepare_pages(pages: list[dict]) -> list[dict]:
    """Validate extraction results and retain non-empty pages with their IDs."""
    if not isinstance(pages, list) or not pages:
        raise QuestionGenerationError("Provide a non-empty list of extracted pages.")
    result, seen = [], set()
    for page in pages:
        if (not isinstance(page, dict) or type(page.get("page")) is not int
                or page["page"] < 1 or not isinstance(page.get("text"), str)):
            raise QuestionGenerationError("Each page needs a positive integer page and text string.")
        if page["page"] in seen:
            raise QuestionGenerationError("Source page numbers must be unique.")
        seen.add(page["page"])
        if page["text"].strip():
            result.append({"page": page["page"], "text": page["text"].strip()})
    if not result:
        raise QuestionGenerationError("The source contains no extractable text.")
    if sum(len(page["text"]) for page in result) > MAX_SOURCE_CHARACTERS:
        raise QuestionGenerationError("Source is too long for Sprint 1. Use a smaller PDF or page selection.")
    return result


def parse_questions(response_text: str, source_pages: set[int]) -> list[dict]:
    """Parse and validate JSON, count, fields, uniqueness, and cited page IDs.

    Args:
        response_text: the model's JSON text.
        source_pages: IDs of non-empty pages actually sent to the model.
    Returns:
        Exactly five normalized question dictionaries.
    Raises:
        QuestionGenerationError: output is malformed or cites unavailable pages.
    """
    if not isinstance(response_text, str) or not response_text.strip():
        raise QuestionGenerationError("The model returned an empty response.")
    try:
        items = json.loads(response_text)
    except (ValueError, RecursionError) as exc:
        raise QuestionGenerationError("The model did not return valid JSON.") from exc
    if not isinstance(items, list) or len(items) != QUESTION_COUNT:
        raise QuestionGenerationError("The model must return exactly five questions; the source may be insufficient.")
    result, seen = [], set()
    for item in items:
        if not isinstance(item, dict) or set(item) != {"question", "question_type", "source_page"}:
            raise QuestionGenerationError("Each question needs question, question_type, and source_page only.")
        if not isinstance(item["question"], str) or not item["question"].strip():
            raise QuestionGenerationError("Question text must be a non-empty string.")
        if item["question_type"] != "short_answer":
            raise QuestionGenerationError("Question type must be short_answer.")
        if type(item["source_page"]) is not int or item["source_page"] not in source_pages:
            raise QuestionGenerationError("A question cites a page that was not provided with text.")
        question = item["question"].strip()
        normalized = " ".join(question.casefold().split())
        if normalized in seen:
            raise QuestionGenerationError("The model returned duplicate questions.")
        seen.add(normalized)
        result.append({"question": question, "question_type": "short_answer", "source_page": item["source_page"]})
    return result


def generate_questions(pages: list[dict]) -> list[dict]:
    """Generate five questions from extract_pages() output, retrying bad output once.

    Args:
        pages: [{"page": 1, "text": "..."}, ...], preserving original page IDs.
    Returns:
        Five dictionaries with question, question_type, and source_page.
    Raises:
        QuestionGenerationError: input is invalid or both model outputs fail validation.
        StudyForgeError: prompt/configuration/provider failure; API errors are not retried.
    """
    source = _prepare_pages(pages)
    prompt = load_prompt(PROMPT_FILE)
    payload = json.dumps({"pages": source}, ensure_ascii=False)
    valid_pages = {page["page"] for page in source}
    client = get_client()
    model = get_model()
    # Both attempts use the same source and versioned prompt. Invalid generated
    # text is never fed back into the instruction channel.
    try:
        for attempt in range(2):
            try:
                response = client.models.generate_content(
                    model=model,
                    contents=payload,
                    config={"system_instruction": prompt,
                            "response_mime_type": "application/json",
                            "response_schema": QUESTION_SCHEMA},
                )
            except Exception as exc:
                raise classify_api_error(exc) from exc
            try:
                return parse_questions(response.text, valid_pages)
            except QuestionGenerationError as exc:
                if attempt == 1:
                    raise QuestionGenerationError(
                        f"Question generation failed after two attempts: {exc}"
                    ) from exc
    finally:
        client.close()


def main() -> int:
    """Run a live generation smoke check on an extracted-pages JSON file."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pages_json", type=Path, help="UTF-8 JSON array of page/text objects")
    args = parser.parse_args()
    try:
        pages = json.loads(args.pages_json.read_text(encoding="utf-8"))
        questions = generate_questions(pages)
    except (StudyForgeError, OSError, ValueError, UnicodeError) as exc:
        parser.exit(1, f"Question generation failed: {exc}\n")
    print(json.dumps(questions, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
