\# Sprint 1 Backlog



\*\*Sprint Goal:\*\* Establish a working vertical slice — a user can upload a

course document and receive AI-generated practice questions from its content,

with the repository, tooling, and prompt-versioning discipline in place.



\*\*Duration:\*\* 22 Sep 2026 — 05 Oct 2026 (2 weeks)

\*\*Scrum Master:\*\* Abdullah Aqeel Khan

\*\*Product Owner:\*\* Mubeen Malik

\*\*Committed Story Points:\*\* 25



> Scope note: retrieval (RAG), grading, and adaptive planning are deliberately

> \*\*out of scope\*\* for Sprint 1. Sprint 1 generates questions from raw extracted

> text. Retrieval is introduced in Sprint 2 as a measurable increment.



\---



\## SF-1 — Repository scaffolding and project structure

\*\*Points:\*\* 2 · \*\*Assignee:\*\* Abdullah Aqeel Khan · \*\*Priority:\*\* Highest



\*\*User Story\*\*

As a developer, I want a structured repository with documented conventions so

that the team can contribute consistently from the first day of the sprint.



\*\*Acceptance Criteria\*\*

\- Repository is public and contains `src/`, `docs/`, `prompts/`, `tests/`

\- README documents project overview, tech stack, team, and setup steps

\- `.gitignore` excludes `.env`, `\_\_pycache\_\_/`, and virtual environments

\- `docs/team-roles.md` and `docs/definition-of-done.md` are committed



\---



\## SF-2 — Google AI API connection and configuration management

\*\*Points:\*\* 3 · \*\*Assignee:\*\* Abdullah Aqeel Khan · \*\*Priority:\*\* Highest



\*\*User Story\*\*

As a developer, I want a verified connection to the Google AI Platform with

externalised configuration so that agent features can be built on a reliable

and secure foundation.



\*\*Acceptance Criteria\*\*

\- `src/api\_test.py` sends a prompt to Gemini and prints a valid response

\- API key is read from `.env` via environment variable, never hardcoded

\- `.env.example` documents required variables without exposing secrets

\- `requirements.txt` lists all dependencies with pinned versions

\- API errors (invalid key, quota exceeded, network failure) are caught and

&#x20; reported with a readable message rather than a raw traceback



\---



\## SF-3 — Course material upload and text extraction

\*\*Points:\*\* 5 · \*\*Assignee:\*\* Usman Irshad · \*\*Priority:\*\* High



\*\*User Story\*\*

As a student, I want to upload my lecture slides or notes as a PDF so that the

system can work from my actual course material.



\*\*Acceptance Criteria\*\*

\- Accepts `.pdf` upload and rejects other file types with a clear message

\- Extracts text page by page and returns it with page numbers preserved

\- Handles a multi-page document of at least 20 pages without failure

\- Returns an explicit "no extractable text" result for scanned/image-only PDFs

\- Unit test covers a valid PDF, an empty PDF, and a non-PDF input



\---



\## SF-4 — Basic question generation agent

\*\*Points:\*\* 5 · \*\*Assignee:\*\* M. Husnain · \*\*Priority:\*\* High



\*\*User Story\*\*

As a student, I want the system to generate practice questions from my uploaded

material so that I can test my understanding of what I actually studied.



\*\*Acceptance Criteria\*\*

\- Given extracted text, returns 5 practice questions in structured JSON

\- Each question object contains: question text, question type, and the source

&#x20; page number it was derived from

\- Output is parsed and validated; malformed model output triggers one retry

&#x20; before surfacing an error

\- Prompt is stored in `prompts/question\_generation\_v1.md`, not inline in code

\- Generated questions are manually reviewed against the source document and the

&#x20; review recorded in the Jira issue



\---



\## SF-5 — Minimal Streamlit interface

\*\*Points:\*\* 5 · \*\*Assignee:\*\* Mubeen Malik · \*\*Priority:\*\* Medium



\*\*User Story\*\*

As a student, I want a simple web interface so that I can upload a document and

read the generated questions without using the command line.



\*\*Acceptance Criteria\*\*

\- Single-page Streamlit app with a file uploader and a results area

\- Displays a loading indicator while the agent call is in progress

\- Renders the generated questions in a readable list with source page shown

\- Displays a friendly error message if generation fails, without crashing

\- App launches with a single documented command



\---



\## SF-6 — Prompt versioning structure

\*\*Points:\*\* 2 · \*\*Assignee:\*\* M. Husnain · \*\*Priority:\*\* Medium



\*\*User Story\*\*

As a developer, I want prompts stored as versioned files so that prompt changes

are traceable in version control alongside code changes.



\*\*Acceptance Criteria\*\*

\- `prompts/` contains one Markdown file per prompt

\- Each prompt file header records: version, author, date, and change note

\- Code loads prompts from file at runtime rather than embedding strings

\- `docs/prompt-versioning.md` documents the convention in half a page



\---



\## SF-7 — Test suite foundation

\*\*Points:\*\* 3 · \*\*Assignee:\*\* Usman Irshad · \*\*Priority:\*\* Medium



\*\*User Story\*\*

As a developer, I want an automated test suite so that regressions are caught

before code reaches `main`.



\*\*Acceptance Criteria\*\*

\- `pytest` configured and runnable via a single command

\- Unit tests cover text extraction and JSON response parsing

\- One smoke test verifies the Gemini API returns a non-empty response

\- All tests pass on a clean clone

\- Test run output captured as evidence for the sprint review



\---



\## Sprint 1 Summary



| Story | Title | Points | Assignee |

|-------|-------|--------|----------|

| SF-1 | Repository scaffolding | 2 | Abdullah |

| SF-2 | Google AI API connection | 3 | Abdullah |

| SF-3 | Upload \& text extraction | 5 | Usman |

| SF-4 | Question generation agent | 5 | Husnain |

| SF-5 | Streamlit interface | 5 | Mubeen |

| SF-6 | Prompt versioning | 2 | Husnain |

| SF-7 | Test suite foundation | 3 | Usman |

| | \*\*Total\*\* | \*\*25\*\* | |



\*\*Story point scale:\*\* modified Fibonacci (1, 2, 3, 5, 8, 13)

1 = trivial · 2 = small, well understood · 3 = moderate, some unknowns ·

5 = substantial, spans multiple components · 8+ = split it



\*\*Expected velocity baseline:\*\* 25 points. This becomes the reference for

Sprint 2 planning and the first data point in the velocity chart.

