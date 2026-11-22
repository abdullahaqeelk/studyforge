"""SF-4: generate five page-cited questions using the shared Gemini client."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from config import StudyForgeError, classify_api_error, get_client, get_model
from prompt_loader import load_prompt

PROMPT_FILE = "question_generation_v2.md"
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
            "question_type": {
                "type": "STRING",
                "enum": ["short_answer", "multiple_choice"],
            },
            "source_page": {"type": "INTEGER"},
            "options": {"type": "ARRAY", "items": {"type": "STRING"}},
            "correct_option": {"type": "INTEGER"},
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
        if (
            not isinstance(page, dict)
            or type(page.get("page")) is not int
            or page["page"] < 1
            or not isinstance(page.get("text"), str)
        ):
            raise QuestionGenerationError(
                "Each page needs a positive integer page and text string."
            )
        if page["page"] in seen:
            raise QuestionGenerationError("Source page numbers must be unique.")
        seen.add(page["page"])
        if page["text"].strip():
            result.append({"page": page["page"], "text": page["text"].strip()})
    if not result:
        raise QuestionGenerationError("The source contains no extractable text.")
    if sum(len(page["text"]) for page in result) > MAX_SOURCE_CHARACTERS:
        raise QuestionGenerationError(
            "Source is too long for Sprint 1. Use a smaller PDF or page selection."
        )
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
        raise QuestionGenerationError(
            "The model must return exactly five questions; the source may be insufficient."
        )
    result, seen = [], set()
    for item in items:
        if not isinstance(item, dict) or "question_type" not in item:
            raise QuestionGenerationError(
                "Each question must be an object with a question_type."
            )

        q_type = item["question_type"]

        if q_type == "short_answer":
            if set(item) != {"question", "question_type", "source_page"}:
                raise QuestionGenerationError(
                    "Each short_answer question needs question, question_type, and source_page only."
                )
        elif q_type == "multiple_choice":
            if set(item) != {
                "question",
                "question_type",
                "source_page",
                "options",
                "correct_option",
            }:
                raise QuestionGenerationError(
                    "Each multiple_choice question needs question, question_type, source_page, options, and correct_option."
                )
            options = item["options"]
            if not isinstance(options, list) or len(options) != 4:
                raise QuestionGenerationError(
                    "Multiple-choice options must be a list of exactly four strings."
                )
            if any(not isinstance(opt, str) or not opt.strip() for opt in options):
                raise QuestionGenerationError(
                    "All four multiple-choice options must be non-empty strings."
                )
            if len({opt.strip().casefold() for opt in options}) != 4:
                raise QuestionGenerationError(
                    "All four multiple-choice options must be distinct."
                )
            if type(item["correct_option"]) is not int or item[
                "correct_option"
            ] not in range(4):
                raise QuestionGenerationError(
                    "correct_option must be an integer in range(4)."
                )
        else:
            raise QuestionGenerationError(
                "Question type must be short_answer or multiple_choice."
            )

        if not isinstance(item["question"], str) or not item["question"].strip():
            raise QuestionGenerationError("Question text must be a non-empty string.")
        if (
            type(item["source_page"]) is not int
            or item["source_page"] not in source_pages
        ):
            raise QuestionGenerationError(
                "A question cites a page that was not provided with text."
            )
        question = item["question"].strip()
        normalized = " ".join(question.casefold().split())
        if normalized in seen:
            raise QuestionGenerationError("The model returned duplicate questions.")
        seen.add(normalized)

        if q_type == "short_answer":
            result.append(
                {
                    "question": question,
                    "question_type": "short_answer",
                    "source_page": item["source_page"],
                }
            )
        else:
            result.append(
                {
                    "question": question,
                    "question_type": "multiple_choice",
                    "source_page": item["source_page"],
                    "options": [opt.strip() for opt in item["options"]],
                    "correct_option": item["correct_option"],
                }
            )
    return result


def generate_questions(pages: list[dict], *, max_attempts: int = 2) -> list[dict]:
    """Generate five questions from extract_pages() output, retrying bad output once.

    Args:
        pages: [{"page": 1, "text": "..."}, ...], preserving original page IDs.
        max_attempts: one or two calls; SF-12 uses one so its outer validation
            loop owns the single retry budget across schema and grounding.
    Returns:
        Five dictionaries with question, question_type, and source_page.
    Raises:
        QuestionGenerationError: input is invalid or both model outputs fail validation.
        StudyForgeError: prompt/configuration/provider failure; API errors are not retried.
    """
    if type(max_attempts) is not int or max_attempts not in (1, 2):
        raise QuestionGenerationError("max_attempts must be 1 or 2.")
    source = _prepare_pages(pages)
    prompt = load_prompt(PROMPT_FILE)
    payload = json.dumps({"pages": source}, ensure_ascii=False)
    valid_pages = {page["page"] for page in source}
    client = get_client()
    model = get_model()
    # Both attempts use the same source and versioned prompt. Invalid generated
    # text is never fed back into the instruction channel.
    try:
        for attempt in range(max_attempts):
            try:
                response = client.models.generate_content(
                    model=model,
                    contents=payload,
                    config={
                        "system_instruction": prompt,
                        "response_mime_type": "application/json",
                        "response_schema": QUESTION_SCHEMA,
                    },
                )
            except Exception as exc:
                raise classify_api_error(exc) from exc
            try:
                return parse_questions(response.text, valid_pages)
            except QuestionGenerationError as exc:
                if attempt == max_attempts - 1:
                    raise QuestionGenerationError(
                        f"Question generation failed after {'two attempts' if max_attempts == 2 else 'one attempt'}: {exc}"
                    ) from exc
    finally:
        client.close()


def main() -> int:
    """Run a live generation smoke check on an extracted-pages JSON file."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "pages_json", type=Path, help="UTF-8 JSON array of page/text objects"
    )
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
