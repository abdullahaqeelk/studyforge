"""
StudyForge — topic tagging of course material (SF-13).

Labels each chunk produced by SF-10 with the topics it covers, so that a
student can practise one area of a document rather than the whole thing.

Labels live on the chunk itself, under a "topics" key, rather than in a
separate structure. That way whatever SF-11 persists for a chunk carries its
topics with it, and a store rebuild cannot separate a passage from its labels.

Usage:

    from chunking import chunk_pages
    from extract import extract_pages
    from topics import document_topics, tag_chunks

    chunks = tag_chunks(chunk_pages(extract_pages("samples/lecture.pdf")))
    chunks[0]["topics"]      # ["Forward Difference Operators"]
    document_topics(chunks)  # ["Forward Difference Operators", "Interpolation"]
"""

from __future__ import annotations

import json

from config import StudyForgeError, classify_api_error, get_client, get_model
from prompt_loader import load_prompt

PROMPT_FILE = "topic_tagging_v1.md"

# A passage covering more than three topics is usually a sign the labels have
# become vague rather than that the passage is unusually rich. Capping forces
# the model to pick the topics the text actually centres on.
MAX_TOPICS_PER_CHUNK = 3

TOPIC_SCHEMA = {
    "type": "ARRAY",
    "items": {
        "type": "OBJECT",
        "properties": {
            "chunk_id": {"type": "INTEGER"},
            "topics": {"type": "ARRAY", "items": {"type": "STRING"}},
        },
        "required": ["chunk_id", "topics"],
    },
}


class TopicTaggingError(StudyForgeError):
    """Chunks or generated labels did not meet the contract."""


def _prepare(chunks: list[dict]) -> list[dict]:
    """Validate chunks and reduce them to what the model needs to see."""
    if not isinstance(chunks, list) or not chunks:
        raise TopicTaggingError("Provide a non-empty list of chunks.")

    payload, seen = [], set()
    for chunk in chunks:
        if (not isinstance(chunk, dict)
                or type(chunk.get("chunk_id")) is not int
                or not isinstance(chunk.get("text"), str)):
            raise TopicTaggingError(
                "Each chunk needs an integer chunk_id and a text string, as "
                "returned by chunking.chunk_pages()."
            )
        if chunk["chunk_id"] in seen:
            raise TopicTaggingError("Chunk ids must be unique.")
        seen.add(chunk["chunk_id"])
        if chunk["text"].strip():
            payload.append({"chunk_id": chunk["chunk_id"],
                            "text": chunk["text"].strip()})

    if not payload:
        raise TopicTaggingError("The chunks contain no text to label.")
    return payload


def parse_topics(response_text: str, valid_ids: set[int]) -> dict[int, list[str]]:
    """Validate a tagging response and return {chunk_id: [topic, ...]}.

    Args:
        response_text: raw JSON text returned by the model.
        valid_ids: the chunk ids actually sent in this request.

    Returns:
        A label list for every id in valid_ids.

    Raises:
        TopicTaggingError: the response is malformed, labels an id that was not
            sent, omits an id that was, or returns unusable labels.
    """
    if not isinstance(response_text, str) or not response_text.strip():
        raise TopicTaggingError("The model returned an empty response.")
    try:
        entries = json.loads(response_text)
    except json.JSONDecodeError as exc:
        raise TopicTaggingError(f"The model did not return valid JSON: {exc}") from exc
    if not isinstance(entries, list):
        raise TopicTaggingError("The model must return a list of chunk labels.")

    result: dict[int, list[str]] = {}
    for entry in entries:
        if not isinstance(entry, dict) or type(entry.get("chunk_id")) is not int:
            raise TopicTaggingError("Each entry needs an integer chunk_id.")
        chunk_id = entry["chunk_id"]
        # Same check as SF-4 makes on source_page: a label attached to a chunk
        # that was never sent is ungrounded, whatever it says.
        if chunk_id not in valid_ids:
            raise TopicTaggingError(
                f"The model labelled chunk {chunk_id}, which was not supplied."
            )
        if chunk_id in result:
            raise TopicTaggingError(f"Chunk {chunk_id} was labelled twice.")

        labels = entry.get("topics")
        if not isinstance(labels, list) or not labels:
            raise TopicTaggingError(f"Chunk {chunk_id} received no topics.")
        if len(labels) > MAX_TOPICS_PER_CHUNK:
            raise TopicTaggingError(
                f"Chunk {chunk_id} received {len(labels)} topics; the limit is "
                f"{MAX_TOPICS_PER_CHUNK}."
            )

        cleaned: list[str] = []
        for label in labels:
            if not isinstance(label, str) or not label.strip():
                raise TopicTaggingError(f"Chunk {chunk_id} has an empty topic label.")
            text = " ".join(label.split())
            # Case-insensitive dedupe within a chunk, matching SF-4's handling
            # of duplicate questions.
            if text.casefold() not in {c.casefold() for c in cleaned}:
                cleaned.append(text)
        result[chunk_id] = cleaned

    missing = valid_ids - set(result)
    if missing:
        raise TopicTaggingError(
            f"{len(missing)} chunk(s) were left unlabelled, including chunk "
            f"{min(missing)}."
        )
    return result


def tag_chunks(chunks: list[dict]) -> list[dict]:
    """Attach topic labels to every chunk, retrying bad output once.

    Args:
        chunks: output of chunking.chunk_pages(), with or without embeddings.

    Returns:
        The same chunks, each with an added "topics" list. A chunk whose text
        is blank is given an empty list rather than being dropped, so the
        caller's list stays aligned.

    Raises:
        TopicTaggingError: input is invalid, or both responses fail validation.
        StudyForgeError: prompt, configuration or provider failure. Provider
            errors are not retried.
    """
    payload = _prepare(chunks)
    prompt = load_prompt(PROMPT_FILE)
    body = json.dumps({"chunks": payload}, ensure_ascii=False)
    valid_ids = {item["chunk_id"] for item in payload}

    client = get_client()
    model = get_model()
    # One request for the whole document, as in SF-10: a call per chunk would
    # spend free-tier quota for no benefit. Both attempts use the same source
    # and prompt; rejected output is never fed back as instructions (AID-3).
    try:
        for attempt in range(2):
            try:
                response = client.models.generate_content(
                    model=model,
                    contents=body,
                    config={"system_instruction": prompt,
                            "response_mime_type": "application/json",
                            "response_schema": TOPIC_SCHEMA},
                )
            except Exception as exc:  # noqa: BLE001 - provider raises untyped errors
                raise classify_api_error(exc) from exc
            try:
                labels = parse_topics(response.text, valid_ids)
                break
            except TopicTaggingError as exc:
                if attempt == 1:
                    raise TopicTaggingError(
                        f"Topic tagging failed after two attempts: {exc}"
                    ) from exc
    finally:
        client.close()

    for chunk in chunks:
        chunk["topics"] = labels.get(chunk["chunk_id"], [])
    return chunks


def document_topics(chunks: list[dict]) -> list[str]:
    """Return the distinct topics in a document, in order of first appearance.

    Order of appearance rather than alphabetical: it mirrors how the lecture
    itself is structured, so the list reads like a contents page.

    Raises:
        TopicTaggingError: the chunks have not been tagged yet.
    """
    if not chunks or any("topics" not in c for c in chunks):
        raise TopicTaggingError("These chunks have not been tagged. Call tag_chunks() first.")

    seen, ordered = set(), []
    for chunk in chunks:
        for label in chunk["topics"]:
            key = label.casefold()
            if key not in seen:
                seen.add(key)
                ordered.append(label)
    return ordered


def topics_for_pdf(pdf_path: str) -> list[str]:
    """Return the distinct topics in a PDF, for the interface (SF-13).

    Deliberately does not embed: tagging needs the text, not the vectors, and
    embedding here would spend quota on work the topic list never uses.
    """
    from chunking import chunk_pages
    from extract import extract_pages

    return document_topics(tag_chunks(chunk_pages(extract_pages(pdf_path))))
