"""
StudyForge — document chunking and embedding (SF-10).

Turns the per-page output of SF-3 into overlapping passages, and embeds each
one so that SF-11 can retrieve by similarity. This is the first half of the
retrieval layer: chunking and embedding live here, the store and the search
live in SF-11.

Usage:

    from extract import extract_pages
    from chunking import chunk_pages, embed_chunks

    chunks = chunk_pages(extract_pages("samples/lecture-sample.pdf"))
    chunks = embed_chunks(chunks)
    chunks[0]
    # {"chunk_id": 0, "page": 1, "text": "...", "embedding": [0.01, ...]}

Chunk and embedding settings come from configuration (CHUNK_SIZE,
CHUNK_OVERLAP, EMBEDDING_MODEL), never from literals here — see AID-1.
"""

from __future__ import annotations

from config import (StudyForgeError, classify_api_error, get_chunk_overlap,
                    get_chunk_size, get_client, get_embedding_model)


class ChunkingError(StudyForgeError):
    """The document could not be split into usable chunks."""


def chunk_pages(pages: list[dict]) -> list[dict]:
    """Split extracted pages into overlapping chunks.

    A chunk never spans a page boundary. That costs some chunks their ideal
    length on short pages, but it keeps the page number on every chunk exactly
    correct — which is the whole point of the retrieval layer, since SF-12
    cites that page back to the student. A chunk drawn from two pages could
    only cite one of them, and would be wrong half the time.

    Args:
        pages: output of extract.extract_pages() — [{"page": 1, "text": "..."}].

    Returns:
        [{"chunk_id": 0, "page": 1, "text": "..."}, ...], chunk_id running from
        zero across the whole document in reading order.

    Raises:
        ChunkingError: pages is not the expected shape, or contains no text.
    """
    if not isinstance(pages, list) or not pages:
        raise ChunkingError("No pages were supplied to chunk.")

    size = get_chunk_size()
    overlap = get_chunk_overlap()
    if overlap >= size:
        raise ChunkingError(
            f"CHUNK_OVERLAP ({overlap}) must be smaller than CHUNK_SIZE ({size}), "
            "otherwise chunking cannot advance through the document."
        )

    chunks: list[dict] = []
    for page in pages:
        if not isinstance(page, dict) or "page" not in page or "text" not in page:
            raise ChunkingError(
                "Each page must be a dict with 'page' and 'text' keys, as "
                "returned by extract_pages()."
            )
        text = (page["text"] or "").strip()
        if not text:
            continue  # an empty page carries no passages; SF-3 keeps it for numbering

        for piece in _split(text, size, overlap):
            chunks.append({
                "chunk_id": len(chunks),
                "page": page["page"],
                "text": piece,
            })

    if not chunks:
        raise ChunkingError(
            "The document produced no chunks because no page contained text."
        )
    return chunks


def _split(text: str, size: int, overlap: int) -> list[str]:
    """Split one page's text into overlapping windows, preferring word breaks."""
    if len(text) <= size:
        return [text]

    step = size - overlap
    pieces: list[str] = []
    start = 0
    while start < len(text):
        end = start + size
        if end < len(text):
            # Back off to the last space so a chunk does not end mid-word.
            space = text.rfind(" ", start + step, end)
            if space != -1:
                end = space
        piece = text[start:end].strip()
        if piece:
            pieces.append(piece)
        if end >= len(text):
            break
        start = end - overlap
    return pieces


def embed_chunks(chunks: list[dict]) -> list[dict]:
    """Attach an embedding vector to every chunk.

    Args:
        chunks: output of chunk_pages().

    Returns:
        The same chunks, each with an added "embedding" key.

    Raises:
        ChunkingError: chunks is empty or malformed.
        StudyForgeError: the provider rejected the request. The specific
            subclass names the cause, via config.classify_api_error().
    """
    if not chunks:
        raise ChunkingError("No chunks were supplied to embed.")

    client = get_client()
    try:
        response = client.models.embed_content(
            model=get_embedding_model(),
            contents=[c["text"] for c in chunks],
        )
    except Exception as exc:  # noqa: BLE001 - provider raises untyped errors
        raise classify_api_error(exc) from exc
    finally:
        client.close()

    vectors = getattr(response, "embeddings", None)
    if not vectors or len(vectors) != len(chunks):
        raise ChunkingError(
            f"The embedding service returned {len(vectors) if vectors else 0} "
            f"vectors for {len(chunks)} chunks. The document was not indexed."
        )

    for chunk, vector in zip(chunks, vectors):
        chunk["embedding"] = list(getattr(vector, "values", vector))
    return chunks


def index_document(pdf_path: str) -> list[dict]:
    """Chunk and embed a PDF in one call — the entry point SF-11 will use."""
    from extract import extract_pages

    return embed_chunks(chunk_pages(extract_pages(pdf_path)))
