# Retrieval Design (SF-11)

**Project:** StudyForge — Agentic Exam-Preparation System
**Sprint:** 2
**Author:** Abdullah Aqeel Khan
**Date:** 12 November 2026

SF-11's acceptance criteria require the choice of store to be recorded with its
reason. This document is that record.

---

## 1. What was chosen

A **JSON file per document, searched in memory with NumPy cosine similarity**.
One store per document, held under `.stores/` and named by a SHA-256 hash of
the document's bytes.

No vector database, no index structure, no external service.

---

## 2. What was considered

| Option | Why not |
|---|---|
| **FAISS** | An approximate-nearest-neighbour index earns its cost at millions of vectors. A lecture PDF produces roughly 30. The index would be slower to build than an exhaustive scan is to run, and it adds a compiled dependency that four students install on four different machines. |
| **Chroma / Qdrant / pgvector** | A running service, or an embedded database with its own schema and migration story, for a dataset that fits in a few hundred kilobytes of JSON. The operational cost lands on every team member and on the demonstration. |
| **SQLite with a vector extension** | Adds an extension dependency and a query language for a problem that is one matrix multiplication. |
| **Pure Python similarity, no NumPy** | Avoids a dependency, but NumPy is already present transitively through Streamlit, and a vectorised dot product over a matrix is both shorter and clearer than nested loops. The dependency is now declared explicitly in `requirements.txt` rather than relied on by accident. |

---

## 3. Why exhaustive search is the right answer here

A 15-page lecture produces about 15 chunks; an 83-page deck about 30. Cosine
similarity against 30 vectors of a few thousand dimensions is a single matrix
multiplication — microseconds. The entire value of an ANN index is avoiding
work that, at this scale, does not exist.

The honest framing for the report: the project's retrieval problem is small, and
choosing infrastructure sized for a problem the project does not have would be
the engineering error, not the conservative choice. If StudyForge later indexed
a whole semester of material across many documents, this decision should be
revisited — and the store is deliberately a single module behind
`get_store()` / `search()`, so replacing it would not touch SF-12.

---

## 4. Decisions inside the store

**Documents are identified by content hash, not by filename.** Two copies of
the same lecture under different names share a store, and an edited lecture
gets a new one. Naming by path would do neither, and would serve stale vectors
for edited material.

**A chunk is persisted whole.** Every key SF-10 or SF-13 puts on a chunk —
`page`, `topics`, anything added later — round-trips untouched. A separate
metadata table could fall out of sync with the vectors; a key on the chunk
cannot. This is what satisfies SF-13's "labels survive a store rebuild".

**A store is discarded when the indexing configuration changed.** The stored
fingerprint covers the embedding model *and* `CHUNK_SIZE` and `CHUNK_OVERLAP`.
Vectors from two models are not comparable, and passages cut at different
boundaries are not the passages re-indexing would produce; either way the store
is rebuilt rather than served. Raised in the SF-11 review, which found that
checking the model alone left a changed chunk size serving stale passages.

**A store that loads but cannot be searched is also discarded.** Chunk shape
and embedding consistency are validated on load, not only at search time. A
structurally broken cache that passed the old load check would be returned by
`get_store()` forever, with `search()` telling the caller to rebuild on every
call and nothing in the system willing to do it. Also from the SF-11 review.

**Writes go to a uniquely named temporary file and are moved into place.**
An interrupted build leaves the previous store intact instead of a half-written
one, and a failed build removes its own temporary file. The name is unique per
build rather than derived from the target: two concurrent builds of the same
document would otherwise share one path, and the second `replace()` would fail
on a file the first had already moved away. `os.replace` is atomic, so the
build that finishes last simply wins. Raised in the SF-11 review.

---

## 5. The similarity floor

`search()` returns an empty list when nothing clears `MIN_SIMILARITY`,
defaulting to 0.45.

This is the most consequential decision in the module. Top-k retrieval always
returns something: ask a networks document about the French Revolution and it
will hand back its least-bad match. SF-12 then cites that passage as the source
of a generated question, and the student is shown a confident citation to
material that does not support it — exactly the failure AID-2 exists to
prevent. An empty result is the honest answer to a question the document does
not cover.

**The number is model-dependent and is not a universal constant.** It was
chosen as a starting point, not calibrated against a labelled set. Changing
`EMBEDDING_MODEL` invalidates it. Before the Sprint 2 review it should be
checked against a handful of known-unrelated queries on a real document, and
SF-17's grounding test suite in Sprint 3 is where it should be pinned down
properly.

---

## 6. Interfaces

```python
get_store(pdf_path, rebuild=False) -> dict   # builds on first call, loads after
search(store, query, k=None, min_similarity=None) -> list[dict]
retrieve(pdf_path, query, k=None) -> list[dict]   # both in one call
```

A hit is a copy of the stored chunk with `similarity` added and `embedding`
removed. Callers never see raw vectors, and a search never mutates the store.

Configuration: `RETRIEVAL_K` (default 5), `MIN_SIMILARITY` (default 0.45),
`EMBEDDING_MODEL` (shared with SF-10).
