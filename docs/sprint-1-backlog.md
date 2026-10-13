# Sprint 1 Backlog

**Sprint Goal:** Establish a working vertical slice — a user can upload a
course document and receive AI-generated practice questions from its content,
with the repository, tooling, and prompt-versioning discipline in place.

**Duration:** 12 Oct 2026 — 23 Oct 2026 (2 weeks)
**Scrum Master:** Abdullah Aqeel Khan
**Product Owner:** Mubeen Malik
**Committed Story Points:** 25

> Scope note: retrieval (RAG), grading, and adaptive planning are deliberately
> **out of scope** for Sprint 1. Sprint 1 generates questions from raw extracted
> text. Retrieval is introduced in Sprint 2 as a measurable increment.

---

## Completed during Sprint 0

SF-1 and SF-2 were completed during Sprint 0 and are therefore **not part of the
Sprint 1 commitment**. They remain in the product backlog marked Done, so that
the Sprint 1 burndown reflects only work actually performed during the
iteration. Including already-finished stories would show a five-point drop on
day one and misrepresent the team's velocity.

| Story | Title | Points | Assignee | Status |
|-------|-------|--------|----------|--------|
| SF-1 | Repository scaffolding and project structure | 2 | Abdullah Aqeel Khan | Done |
| SF-2 | Google AI API connection and configuration management | 3 | Abdullah Aqeel Khan | Done |

---

## SF-3 — Course material upload and text extraction
**Points:** 5 · **Assignee:** Usman Irshad · **Priority:** High

**User Story**
As a student, I want to upload my lecture slides or notes as a PDF so that the
system can work from my actual course material.

**Acceptance Criteria**
- Accepts `.pdf` upload and rejects other file types with a clear message
- Extracts text page by page and returns it with page numbers preserved
- Handles a multi-page document of at least 20 pages without failure
- Returns an explicit "no extractable text" result for scanned/image-only PDFs
- Unit test covers a valid PDF, an empty PDF, and a non-PDF input

---

## SF-4 — Basic question generation agent
**Points:** 5 · **Assignee:** Muhammad Husnain · **Priority:** High

**User Story**
As a student, I want the system to generate practice questions from my uploaded
material so that I can test my understanding of what I actually studied.

**Acceptance Criteria**
- Given extracted text, returns 5 practice questions in structured JSON
- Each question object contains the question text, question type, and the
  source page number it was derived from
- Output is parsed and validated; malformed model output triggers one retry
  before surfacing an error
- Prompt is stored in `prompts/question_generation_v1.md`, not inline in code
- Generated questions are manually reviewed against the source document and the
  review recorded in the Jira issue

---

## SF-5 — Minimal Streamlit interface
**Points:** 5 · **Assignee:** Mubeen Malik · **Priority:** Medium

**User Story**
As a student, I want a simple web interface so that I can upload a document and
read the generated questions without using the command line.

**Acceptance Criteria**
- Single-page Streamlit app with a file uploader and a results area
- Displays a loading indicator while the agent call is in progress
- Renders the generated questions in a readable list with source page shown
- Displays a friendly error message if generation fails, without crashing
- App launches with a single documented command

---

## SF-6 — Prompt versioning structure
**Points:** 2 · **Assignee:** Muhammad Husnain · **Priority:** Medium

**User Story**
As a developer, I want prompts stored as versioned files so that prompt changes
are traceable in version control alongside code changes.

**Acceptance Criteria**
- `prompts/` contains one Markdown file per prompt
- Each prompt file header records version, author, date, and change note
- Code loads prompts from file at runtime rather than embedding strings
- `docs/prompt-versioning.md` documents the convention in half a page

---

## SF-7 — Test suite foundation
**Points:** 3 · **Assignee:** Usman Irshad · **Priority:** Medium

**User Story**
As a developer, I want an automated test suite so that regressions are caught
before code reaches `main`.

**Acceptance Criteria**
- `pytest` configured and runnable via a single command
- Unit tests cover text extraction and JSON response parsing
- One smoke test verifies the Gemini API returns a non-empty response
- All tests pass on a clean clone
- Test run output captured as evidence for the sprint review

---

## SF-8 — Pipeline orchestration
**Points:** 3 · **Assignee:** Abdullah Aqeel Khan · **Priority:** Medium

**User Story**
As a student, I want the upload, extraction and question generation steps to run
as one flow so that I get questions from a document in a single action.

**Acceptance Criteria**
- `src/pipeline.py` exposes one function taking a PDF and returning questions
- Calls extraction (SF-3) then generation (SF-4) in sequence
- A failure in either stage returns a clear message naming the stage that failed
- The Streamlit interface calls this function rather than the agents directly
- Unit test covers the happy path with a sample PDF

**Dependencies:** blocked by SF-3 and SF-4; blocks SF-5.

---

## SF-9 — Centralised configuration and API error handling
**Points:** 2 · **Assignee:** Abdullah Aqeel Khan · **Priority:** High

**User Story**
As a developer, I want model configuration and API error handling in one place
so that a provider change is a config edit rather than a code change.

**Acceptance Criteria**
- `src/config.py` reads `GEMINI_MODEL` and `GOOGLE_API_KEY` from `.env`
- No module hardcodes a model name, including `src/api_test.py`
- A shared client factory is used by every agent
- Invalid key, exhausted quota and network failure each produce a distinct
  readable message
- The Sprint 0 model deprecation incident is recorded in `docs/ai-decisions.md`

**Dependencies:** none. Scheduled first in the sprint, because every other
story imports from it.

---

## Sprint 1 Summary

| Story | Title | Points | Assignee |
|-------|-------|--------|----------|
| SF-3 | Course material upload and text extraction | 5 | Usman Irshad |
| SF-4 | Basic question generation agent | 5 | Muhammad Husnain |
| SF-5 | Minimal Streamlit interface | 5 | Mubeen Malik |
| SF-6 | Prompt versioning structure | 2 | Muhammad Husnain |
| SF-7 | Test suite foundation | 3 | Usman Irshad |
| SF-8 | Pipeline orchestration | 3 | Abdullah Aqeel Khan |
| SF-9 | Centralised configuration and API error handling | 2 | Abdullah Aqeel Khan |
| | **Total** | **25** | |

### Allocation by member

| Member | Stories | Points | Additional responsibilities |
|--------|---------|--------|-----------------------------|
| Usman Irshad | SF-3, SF-7 | 8 | — |
| Muhammad Husnain | SF-4, SF-6 | 7 | — |
| Abdullah Aqeel Khan | SF-8, SF-9 | 5 | Scrum Master: ceremonies, board upkeep, burndown snapshots |
| Mubeen Malik | SF-5 | 5 | Product Owner: backlog refinement, story acceptance |

The Scrum Master and Product Owner carry fewer story points because their role
responsibilities sit on top of development work. Every member contributes code
in every sprint regardless of role, so that individual contribution remains
visible in the commit history.

### Build order

SF-9 is scheduled first: every other story imports configuration from it, and a
late landing would force the team to hardcode model names and refactor later.
SF-3, SF-4 and SF-6 then proceed in parallel, with SF-6 preferably ahead of
SF-4 since SF-4's acceptance criteria require the prompt to live in a versioned
file. SF-8 follows once extraction and generation both exist, and SF-5
integrates last.

### Estimation

**Story point scale:** modified Fibonacci (1, 2, 3, 5, 8, 13)
1 = trivial · 2 = small, well understood · 3 = moderate, some unknowns ·
5 = substantial, spans multiple components · 8+ = split it

Estimates are relative, anchored on SF-6 (prompt versioning) at 2 points. They
measure size and uncertainty rather than hours. SF-4 is estimated at 5 partly
because the model's output is non-deterministic, which is uncertainty rather
than labour.

**Expected velocity baseline:** 25 points. This becomes the reference for
Sprint 2 planning and the first data point in the velocity chart.
