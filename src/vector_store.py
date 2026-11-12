"""
StudyForge — vector store and retrieval layer (SF-11).

Persists the chunks produced by SF-10 together with their embeddings, and
returns the passages most similar to a query. SF-12 uses this to ground every
generated question in a retrieved passage rather than in whole-document text.

The store is a single JSON file per document, held under .stores/ and named by
a hash of the document's contents. Two consequences follow, both intentional:
the same PDF always maps to the same store, so rebuilding is idempotent; and a
changed PDF produces a different hash, so stale vectors can never be served for
edited material.

A chunk is persisted whole. Any key SF-10 or SF-13 puts on it — page, topics,
anything added later — round-trips through the store untouched, so a passage
can never be separated from its metadata.

Usage:

    from vector_store import get_store, search

    store = get_store("samples/lecture.pdf")   # builds on first call
    hits = search(store, "How is the backward difference defined?")
    hits[0]["page"], hits[0]["similarity"]
"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from pathlib import Path

import numpy as np

from config import (StudyForgeError, classify_api_error, get_chunk_overlap,
                    get_chunk_size, get_client, get_embedding_model,
                    get_min_similarity, get_retrieval_k)

STORE_DIRECTORY = Path(__file__).resolve().parent.parent / ".stores"
STORE_FORMAT = 2


class VectorStoreError(StudyForgeError):
    """The store could not be built, read, or searched."""


def _indexing_fingerprint() -> dict:
    """Every setting that determines what ends up in the store.

    The embedding model is not the only thing that decides a store's contents:
    CHUNK_SIZE and CHUNK_OVERLAP decide where the passages begin and end. A
    store built under one chunking configuration and searched under another
    returns passages that do not match what the caller would get from
    re-indexing, so all three travel together and are compared on load.
    """
    return {
        "embedding_model": get_embedding_model(),
        "chunk_size": get_chunk_size(),
        "chunk_overlap": get_chunk_overlap(),
    }


def _chunks_are_usable(chunks) -> bool:
    """True when every chunk can actually be searched.

    Checked on load rather than only in search(): a structurally broken cache
    that loads successfully would make get_store() return it forever, and the
    caller would be told to rebuild on every single call with nothing in the
    system willing to do it.
    """
    if not isinstance(chunks, list) or not chunks:
        return False
    width = None
    for chunk in chunks:
        if (not isinstance(chunk, dict)
                or type(chunk.get("chunk_id")) is not int
                or type(chunk.get("page")) is not int
                or not isinstance(chunk.get("text"), str)):
            return False
        vector = chunk.get("embedding")
        if not isinstance(vector, list) or not vector:
            return False
        if not all(isinstance(value, (int, float)) and not isinstance(value, bool)
                   for value in vector):
            return False
        if width is None:
            width = len(vector)
        elif len(vector) != width:
            return False
    return True


# --------------------------------------------------------------------------
# Building and persistence
# --------------------------------------------------------------------------

def document_id(pdf_path: str) -> str:
    """A stable id for a document, derived from its bytes rather than its name.

    Two copies of the same lecture under different filenames share a store; an
    edited lecture gets a new one. Naming by path would do neither.
    """
    try:
        digest = hashlib.sha256(Path(pdf_path).read_bytes()).hexdigest()
    except OSError as exc:
        raise VectorStoreError(f"Could not read '{pdf_path}'.") from exc
    return digest[:16]


def store_path(pdf_path: str, directory: Path | None = None) -> Path:
    return (directory or STORE_DIRECTORY) / f"{document_id(pdf_path)}.json"


def build_store(pdf_path: str, directory: Path | None = None) -> dict:
    """Chunk, embed and persist a document, replacing any existing store.

    Raises:
        VectorStoreError: the document could not be read or produced no chunks.
        StudyForgeError: the provider rejected the embedding request.
    """
    from chunking import index_document

    chunks = index_document(pdf_path)
    if not chunks:
        raise VectorStoreError(f"'{os.path.basename(pdf_path)}' produced no chunks.")

    store = {
        "format": STORE_FORMAT,
        "document_id": document_id(pdf_path),
        "source_name": os.path.basename(pdf_path),
        "indexing": _indexing_fingerprint(),
        "chunks": chunks,
    }

    target = store_path(pdf_path, directory)
    target.parent.mkdir(parents=True, exist_ok=True)
    # Written to a temporary file and moved into place, so an interrupted build
    # leaves the previous store intact rather than a half-written one.
    #
    # The temporary name is unique per build, not derived from the target. Two
    # builds of the same document would otherwise share one path: both write
    # it, the first replaces it away, and the second's replace() fails on a
    # file that no longer exists. os.replace is atomic, so whichever build
    # finishes last simply wins.
    handle, temporary_name = tempfile.mkstemp(
        dir=target.parent, prefix=f"{target.stem}.", suffix=".tmp")
    temporary = Path(temporary_name)
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as stream:
            json.dump(store, stream)
        os.replace(temporary, target)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise
    return store


def load_store(pdf_path: str, directory: Path | None = None) -> dict | None:
    """Return a persisted store, or None if there is none to load.

    A store is discarded, rather than returned, when it was built under a
    different indexing configuration or when its chunks are not searchable.
    Both cases are repaired by get_store(), which rebuilds whatever load
    refuses.
    """
    target = store_path(pdf_path, directory)
    if not target.exists():
        return None
    try:
        store = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None  # a corrupt store is rebuilt, not reported

    if (not isinstance(store, dict)
            or store.get("format") != STORE_FORMAT
            or store.get("indexing") != _indexing_fingerprint()
            or not _chunks_are_usable(store.get("chunks"))):
        return None
    return store


def get_store(pdf_path: str, directory: Path | None = None, rebuild: bool = False) -> dict:
    """Load the store for a document, building it if absent or unusable.

    This is the "rebuilt without manual steps" path: callers never decide
    whether a store exists, only which document they want. A store that is
    missing, corrupt, structurally broken, or built under different chunking
    or embedding settings is rebuilt here rather than reported.
    """
    if not rebuild:
        existing = load_store(pdf_path, directory)
        if existing is not None:
            return existing
    return build_store(pdf_path, directory)


# --------------------------------------------------------------------------
# Search
# --------------------------------------------------------------------------

def _embed_query(text: str) -> list[float]:
    client = get_client()
    try:
        response = client.models.embed_content(
            model=get_embedding_model(), contents=[text]
        )
    except Exception as exc:  # noqa: BLE001 - provider raises untyped errors
        raise classify_api_error(exc) from exc
    finally:
        client.close()

    vectors = getattr(response, "embeddings", None)
    if not vectors:
        raise VectorStoreError("The embedding service returned no vector for the query.")
    return list(getattr(vectors[0], "values", vectors[0]))


def _cosine(matrix: np.ndarray, vector: np.ndarray) -> np.ndarray:
    """Cosine similarity of every row against one vector, zero for zero rows."""
    row_norms = np.linalg.norm(matrix, axis=1)
    query_norm = np.linalg.norm(vector)
    if query_norm == 0:
        return np.zeros(len(matrix))
    denominator = row_norms * query_norm
    # A zero-length chunk vector has no direction; its similarity is undefined,
    # so it is scored zero rather than producing a divide-by-zero NaN that
    # would sort unpredictably.
    with np.errstate(divide="ignore", invalid="ignore"):
        scores = np.where(denominator > 0, (matrix @ vector) / denominator, 0.0)
    return scores


def search(store: dict, query: str, k: int | None = None,
           min_similarity: float | None = None) -> list[dict]:
    """Return the chunks most similar to a query, best first.

    Args:
        store: a store from get_store().
        query: the student's question or topic.
        k: how many chunks to return at most. Defaults to RETRIEVAL_K.
        min_similarity: similarity floor. Defaults to MIN_SIMILARITY.

    Returns:
        Up to k chunks, each a copy of the stored chunk with a "similarity"
        float added and the raw embedding removed. An empty list when nothing
        clears the floor — a query about material the document does not cover
        must return nothing rather than its least-bad match, because SF-12
        would otherwise cite an unrelated passage as the source of a question.

    Raises:
        VectorStoreError: the store is unusable or the query is empty.
        StudyForgeError: the provider rejected the query embedding.
    """
    if not isinstance(store, dict) or not store.get("chunks"):
        raise VectorStoreError("This store holds no chunks. Rebuild it first.")
    if not isinstance(query, str) or not query.strip():
        raise VectorStoreError("Provide a non-empty query.")

    limit = get_retrieval_k() if k is None else k
    if limit < 1:
        raise VectorStoreError(f"k must be at least 1, not {limit}.")
    floor = get_min_similarity() if min_similarity is None else min_similarity

    chunks = store["chunks"]
    try:
        vectors = [list(chunk["embedding"]) for chunk in chunks]
        lengths = {len(vector) for vector in vectors}
    except (KeyError, TypeError) as exc:
        raise VectorStoreError(
            "The store's chunks are missing usable embeddings. Rebuild it."
        ) from exc
    # Checked before conversion: numpy raises the same ValueError for a ragged
    # list as for a non-numeric one, so distinguishing here is what lets the
    # message name the real problem.
    if len(lengths) != 1:
        raise VectorStoreError(
            "The store's embeddings are not all the same length. Rebuild it."
        )
    try:
        matrix = np.asarray(vectors, dtype=float)
    except (TypeError, ValueError) as exc:
        raise VectorStoreError(
            "The store's chunks are missing usable embeddings. Rebuild it."
        ) from exc

    vector = np.asarray(_embed_query(query), dtype=float)
    if vector.shape[0] != matrix.shape[1]:
        raise VectorStoreError(
            f"The query embedding has {vector.shape[0]} dimensions but the "
            f"store has {matrix.shape[1]}. The embedding model has changed; "
            "rebuild the store."
        )

    scores = _cosine(matrix, vector)
    order = np.argsort(-scores)[:limit]

    results = []
    for index in order:
        score = float(scores[index])
        if score < floor:
            break  # scores are sorted, so nothing after this clears the floor
        hit = {key: value for key, value in chunks[index].items() if key != "embedding"}
        hit["similarity"] = round(score, 4)
        results.append(hit)
    return results


def retrieve(pdf_path: str, query: str, k: int | None = None) -> list[dict]:
    """Build-or-load a document's store and search it in one call."""
    return search(get_store(pdf_path), query, k=k)
