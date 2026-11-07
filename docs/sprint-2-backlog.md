# Sprint 2 Backlog

**Sprint Goal:** Ground every generated question in a retrieved passage of the
student's own material, so that grounding becomes a verifiable property of the
system rather than an instruction in a prompt.

**Duration:** 7 Nov 2026 — 16 Nov 2026 (10 days)
**Scrum Master:** Mubeen Malik
**Product Owner:** Usman Irshad
**Committed Story Points:** 21

> Cadence note: Sprints 2 to 4 run for ten days rather than two weeks. Three
> further two-week sprints would finish on 20 December, after the P-3 deadline
> of 14 December. The shortened iteration is a deliberate adaptation to the
> remaining calendar, recorded here rather than left to be inferred from
> inconsistent dates. See `docs/sprint-schedule.md`.

> Capacity note: Sprint 1 delivered 25 points across a twelve-day iteration.
> A ten-day iteration at the same rate is roughly 21 points, which is the
> commitment taken here.

---

## SF-10 — Document chunking and embedding
**Points:** 5 · **Assignee:** Usman Irshad · **Priority:** High

**User story**
As a student, I want my uploaded material split and indexed so that questions
can be grounded in specific passages rather than in the whole document.

**Acceptance criteria**
- Splits the output of `extract_pages()` into overlapping chunks, preserving the
  source page number on every chunk
- Chunk size and overlap are read from configuration, not written as literals
- Each chunk is embedded through the shared client in `src/config.py`
- Embedding failures are translated through `classify_api_error()`
- Unit tests cover chunk boundaries, page-number preservation and an empty
  document, with the provider stubbed
- The committed sample document chunks and embeds end to end without error

**Dependencies:** builds on SF-3. Blocks SF-11 and SF-13.

---

## SF-11 — Vector store and retrieval layer
**Points:** 8 · **Assignee:** Abdullah Aqeel Khan · **Priority:** High

**User story**
As a developer, I want a retrieval layer over the indexed material so that
agents can fetch the passages relevant to a query instead of being handed the
whole document.

**Acceptance criteria**
- Persists chunk embeddings for a document and returns the top-k most similar
  chunks for a query
- Every retrieved chunk carries its source page number
- `k` is configurable
- The store can be rebuilt from a document without manual steps
- A query drawn from the document returns relevant chunks; an unrelated query
  returns an explicit empty result rather than the least-bad match
- Unit tests cover ranking order and the empty case with no live API call
- The choice of store is recorded in `docs/` with the reason for it

**Dependencies:** blocked by SF-10. Blocks SF-12.

---

## SF-12 — Source citation on generated questions
**Points:** 5 · **Assignee:** Muhammad Husnain · **Priority:** High

**User story**
As a student, I want every question to cite the passage it came from so that I
can check it against my own notes.

**Acceptance criteria**
- `generate_questions()` accepts retrieved chunks instead of raw page text
- Each question carries the passage it was derived from, in addition to its
  page number
- A question citing a passage that was not supplied fails validation and
  triggers the existing single retry
- The Streamlit interface shows the cited passage under each question
- The prompt is updated and versioned as `prompts/question_generation_v2.md`
  with a change note, per SF-6
- A test asserts that every returned question's citation is one of the chunks
  actually supplied

**Note:** this story replaces the manual grounding review recorded on SF-4 with
an automated check. It closes decision AID-2 in `docs/ai-decisions.md`.

**Dependencies:** blocked by SF-11.

---

## SF-13 — Topic tagging of course material
**Points:** 3 · **Assignee:** Mubeen Malik · **Priority:** Medium

**User story**
As a student, I want my material organised by topic so that I can practise a
specific area rather than the whole document.

**Acceptance criteria**
- Each chunk is assigned one or more topic labels derived from the document
- Labels are produced by a model call using a versioned prompt under `prompts/`
- Labels are stored alongside the chunk and survive a store rebuild
- The interface lists the topics found in an uploaded document
- Unit tests cover label assignment with the model stubbed

**Dependencies:** blocked by SF-10. Nothing depends on this story; it is the
first candidate to drop if capacity proves short.

---

## Allocation

| Member | Role (Sprint 2) | Stories | Points |
|--------|-----------------|---------|--------|
| Abdullah Aqeel Khan | Developer | SF-11 | 8 |
| Muhammad Husnain | Developer | SF-12 | 5 |
| Usman Irshad | Product Owner | SF-10 | 5 |
| Mubeen Malik | Scrum Master | SF-13 | 3 |
| | | **Total** | **21** |

Scrum Master and Product Owner carry a lighter development load because of
their ceremony and refinement duties. All four members contribute code.

---

## Build order and dependency risk

The sprint contains a three-deep chain: **SF-10 → SF-11 → SF-12**.

Sprint 1's retrospective identified sequencing by story priority rather than by
the dependency graph as the cause of a two-day stall. Applying that lesson here:

1. **SF-10 starts first** and should merge by day 3 (Monday 9 November).
2. **SF-10 and SF-11 agree their data contract before either is written**, so
   SF-11 can be built and tested against stubbed chunks in parallel rather than
   waiting for SF-10 to merge. The agreed shape is:
   `{"chunk_id": int, "page": int, "text": str}`
3. **SF-12** likewise builds against stubbed retrieval results.
4. An **integration checkpoint** runs at the sprint midpoint (11–12 November):
   the full end-to-end path is executed against whatever is on `main` and the
   result recorded. This is retrospective action item 3.
