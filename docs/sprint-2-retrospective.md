# Sprint 2 Retrospective

**Project:** StudyForge — Agentic Exam-Preparation System
**Course:** EC-360 Software Engineering — Fall 2026
**Sprint:** SF Sprint 2 — 7 to 16 November 2026 (closed 15 November)
**Facilitated by:** Mubeen Ahmed Malik (Scrum Master, Sprint 2)
**Present:** Abdullah Aqeel Khan, Mubeen Malik, Usman Irshad, Muhammad Husnain

---

## 1. Sprint data

| Measure | Value |
|---|---|
| Sprint goal | Implement document text chunking, local vector indexing, RAG-grounded question generation, citation validation and topic categorization |
| Goal met | Yes |
| Stories committed / completed | 4 / 4 |
| Story points committed / completed | 16 / 16 |
| Velocity (Sprint 1 → 2) | 25 → 16, average 20.5 |
| Scope changes during the sprint | None |
| Pull requests opened / merged | 4 / 4 |
| Pull requests requiring changes before approval | 3 |
| Defects found in review | 4 |
| Defects found after merge | 0 |
| Automated tests at sprint close | 212 (156 added this sprint) |
| Sprint closed | 15 November, one day early |

---

## 2. Context: the fourteen-day gap

No work was committed between 22 October and 7 November. Sprint 2 was planned
to begin shortly after P-2 was submitted and did not. The gap is visible in the
repository history and in the interval between the two sprints' dates.

It is recorded here rather than explained away. The corrective action was to
set the remaining schedule explicitly — `docs/sprint-schedule.md` now fixes the
dates of Sprints 3 and 4 and the report-writing week against the P-3 deadline,
so that the start of an iteration is a calendar commitment rather than a
decision taken when someone happens to raise it.

---

## 3. What went well

**The dependency chain did not stall this time.**
Sprint 2's critical path was SF-10 → SF-11 → SF-12, three deep in a ten-day
sprint. Sprint 1's retrospective identified sequencing by priority rather than
by the dependency graph as the cause of a two-day stall. Applying that lesson,
the chunk contract `{chunk_id, page, text, embedding}` was agreed between SF-10
and SF-11 before either was written, so SF-11 was built and tested against
stubbed chunks while SF-10 was still in review. The same was done for SF-12.
No member waited on another member's merge to begin work.

**Review found four real defects, none of which the authors' own tests caught.**

| PR | Finding | Consequence if merged |
|---|---|---|
| SF-10 | `chunk_pages` never terminated when `CHUNK_OVERLAP` exceeded half of `CHUNK_SIZE` | A hang with no error message, triggered by a documented `.env` value |
| SF-11 | Cache validity checked the embedding model but not chunk size or overlap | Stale passages served silently after a configuration change |
| SF-11 | Concurrent builds shared one temporary file | An unhandled `FileNotFoundError` on the second build |
| SF-11 | A structurally broken cache loaded successfully | `get_store()` would return it forever while `search()` demanded a rebuild nothing would perform |

Three of four pull requests required changes before approval, and every
reported finding was reproduced before the fix. Two reviewers supplied
executable reproductions rather than descriptions.

**Grounding became a measurable property.**
SF-12 validates each generated question against the passages SF-11 retrieves
and requires an exact quotation from a chunk on the cited page. The judge's own
verdict is not trusted on its own: a positive verdict with an unverifiable
quote is rejected locally. The live check on a 27-page document returned 5 of 5
grounded, each with a supporting quotation from its cited page.

**Branch protection is now enforced rather than agreed.**
Action item 2 from Sprint 1's retrospective was completed. `main` requires one
approving review; the Sprint 1 incident of a direct push cannot recur.

---

## 4. What did not go well

**Four days of the sprint produced no burn-down.**
Nothing was marked Done between 7 and 11 November. SF-10 is the head of the
dependency chain and nothing could complete before it did. This is the same
shape as Sprint 1, where SF-9 occupied the opening days for the same reason.
Parallel work was happening — the contract-first approach meant SF-11 and SF-13
were being written — but no story could close, so the chart shows a flat line
for 40% of the iteration.

**One team member worked without an API key for two sprints.**
Live verification of SF-4 was deferred in Sprint 1 and SF-12 in Sprint 2 for
the same reason: the member responsible had no Gemini key configured, so every
live smoke test reported as skipped. This was not discovered as a cause until
the final evening of Sprint 2. Two sprints of live validation were deferred by
something that took two minutes to fix.

**Line endings corrupted a reviewable diff.**
SF-13 replaced `src/app.py` wholesale, converting it from CRLF to LF, so a
twenty-two line addition appeared as a hundred and forty changed lines. The
diff could not be reviewed on its merits and would have conflicted with SF-12's
edits to the same file. It was caught in review and corrected, but the
repository still has no `.gitattributes`, so the next cross-platform edit will
reproduce it.

**Velocity fell from 25 to 16 and the reason is not visible in the chart.**
Sprint 2 was a ten-day iteration against Sprint 1's twelve, and followed a
fourteen-day gap. Read without that context the velocity report suggests a
slowing team. It is recorded here so the P-3 report can state the cause rather
than leave it to inference.

---

## 5. What we are changing

| # | Action | Owner | By |
|---|---|---|---|
| 1 | Add `.gitattributes` with `* text=auto eol=lf` in a standalone maintenance commit on `main`, and renormalise existing files | Mubeen Ahmed Malik | Before Sprint 3's first PR |
| 2 | Every member configures their own Gemini API key and confirms the live smoke test passes locally, rather than skipped | All members | Sprint 3 day 1 |
| 3 | Split the first story of each sprint so that something small can close on day two, instead of the entire opening depending on one foundational story | Scrum Master, each sprint | Sprint 3 planning |
| 4 | Batch query embeddings in retrieval. SF-12 currently issues one embedding call per question, seven API calls per generation and up to thirteen on a retry, against a free-tier quota | Raise as a Sprint 3 story | Sprint 3 planning |
| 5 | Continue agreeing data contracts between dependent stories before either is written | All members | Ongoing |

Carried forward from Sprint 1: sequencing by the dependency graph (done, and
effective), and the midpoint integration checkpoint (not formally held this
sprint — the end-to-end path was exercised only on the final evening).

---

## 6. Velocity and estimation

| Sprint | Days | Committed | Completed |
|---|---|---|---|
| Sprint 1 | 12 | 25 | 25 |
| Sprint 2 | 10 | 16 | 16 |
| **Average** | | | **20.5** |

Sprint 1's retrospective found its estimates conservative — 25 points were
delivered in seven working days of eleven. Sprint 2 was estimated at 16 against
a projection of roughly 21 for a ten-day iteration, and the work filled the
sprint rather than finishing early by days. Taken together, the scale appears
to have been recalibrated in the right direction.

Two sprints remain too few for a reliable figure. Sprint 3 will commit around
the 20.5 average, adjusted for the ten-day length.

---

## 7. Carried into Sprint 3

Grounding is now verified per question against retrieved evidence, which closes
AID-2. What Sprint 2 does not provide is an answer to whether a student's
submitted answer is correct, which is the Sprint 3 epic: multiple-choice
evaluation (SF-14), free-text grading (SF-15), targeted feedback (SF-16) and an
automated grounding and hallucination test suite (SF-17).

SF-17 matters beyond its points. The grounding evidence in this project is
currently a manual check on two documents, one in Sprint 1 and one in Sprint 2.
SF-17 replaces that with a repeatable measurement, and is the story the final
report's hallucination-handling section depends on.

Roles rotate at the sprint boundary: **Usman Irshad** takes Scrum Master and
**Muhammad Husnain** takes Product Owner for Sprint 3.
