# StudyForge

An agentic exam-prep system that ingests course material, generates cited
practice questions via retrieval, grades free-text answers against source
content, and adapts topic selection based on performance. Built on Google
AI Platform with a multi-agent RAG architecture.

## Course

EC-360 Software Engineering — Fall 2026  
Department of Computer Engineering, CEME, NUST  
Complex Engineering Problem (CEP)

## Overview

StudyForge turns a student's own course material into an adaptive practice
loop. Uploaded lecture slides, notes, and past papers are indexed into a
retrieval layer, over which a set of specialised LLM agents operate:

| Agent | Responsibility |
|---|---|
| Indexer | Chunks, embeds, and topic-tags uploaded course material |
| Question Generator | Produces practice questions grounded in retrieved source chunks |
| Grader | Evaluates free-text answers against source content and returns feedback |
| Planner | Tracks topic-level performance and selects what to serve next |

Grounding every generated question and grading judgement in retrieved course
content is the system's primary defence against hallucination: any output
that cannot be traced to source material is treated as a failure case and
surfaced during testing.

## Tech Stack

- Python 3.13
- Google GenAI SDK (Gemini)
- Streamlit (UI)
- pypdf (document text extraction) · pytest (test suite)
- Jira (sprint tracking) · GitHub (version control)

The Gemini model identifier is read from `GEMINI_MODEL` rather than hardcoded.
The provider retired the model originally targeted midway through Sprint 0; the
reasoning behind moving it into configuration is recorded in
[docs/ai-decisions.md](docs/ai-decisions.md).

## Team

| Name | Role (Sprint 1) | GitHub |
|---|---|---|
| Abdullah Aqeel Khan | Scrum Master | @abdullahaqeelk |
| Mubeen Malik | Product Owner | @Mubeen-11 |
| Usman Irshad | Developer | @usman-irshad1 |
| M. Husnain | Developer | @coder-og |

Role rotation across all four sprints: [docs/team-roles.md](docs/team-roles.md)

## Repository Structure

| Path | Contents |
|---|---|
| `src/` | Agent implementations, retrieval layer, API clients |
| `prompts/` | Versioned prompt templates |
| `docs/` | Roles, Definition of Ready and Done, AI decisions, sprint records |
| `tests/` | Unit, integration, and prompt tests |

### Process documentation

| Document | Purpose |
|---|---|
| [docs/definition-of-ready.md](docs/definition-of-ready.md) | Criteria a story must meet before entering a sprint |
| [docs/definition-of-done.md](docs/definition-of-done.md) | Criteria a story must meet before being marked Done |
| [docs/product-backlog.md](docs/product-backlog.md) | Full backlog across all four sprints |
| [docs/sprint-1-backlog.md](docs/sprint-1-backlog.md) | Sprint 1 commitment, estimates, and allocation |
| [docs/ai-decisions.md](docs/ai-decisions.md) | Decisions forced by AI platform behaviour and API limits |

## Setup

```bash
git clone git@github.com:abdullahaqeelk/studyforge.git
cd studyforge
pip install -r requirements.txt
cp .env.example .env   # add your GOOGLE_API_KEY
python src/api_test.py          # verify the API connection
python -m pytest tests/ -v      # run the test suite
streamlit run src/app.py       # launch the Streamlit web interface
```

## Contributing

SF-12 source validation, bounded regeneration, warning behavior and live-check
instructions: [docs/grounding-validation.md](docs/grounding-validation.md).

One branch per story, named `feature/SF-<id>-<short-description>`. Every change
reaches `main` through a pull request reviewed by another team member. Commit
messages begin with the Jira key (`SF-3 ...`) so that commits link back to the
board automatically.

## Status

**Sprint 2 complete** (7–16 November 2026) — 16 of 16 points delivered, closed
one day early. **Sprint 3 begins 17 November.**

Delivered and running on `main`:

| Story | Capability |
|---|---|
| SF-9 | Centralised configuration and typed API error handling |
| SF-3 | PDF text extraction with page numbers preserved |
| SF-4 | Question generation — five validated, page-cited questions |
| SF-6 | Versioned prompt files loaded at runtime |
| SF-7 | Test suite, including a live API smoke test |
| SF-8 | Pipeline orchestration with stage-labelled failures |
| SF-5 | Streamlit interface |
| SF-10 | Text chunking and vector store indexing |
| SF-11 | Retrieval-augmented generation over the student's own material |
| SF-12 | Source citation and grounding validation |
| SF-13 | Topic tagging and categorisation |

212 automated tests. Every generated question is validated against a retrieved
passage from its cited page and carries the supporting quotation; questions
that cannot be supported are shown with an explicit warning rather than
presented as verified. See [docs/grounding-validation.md](docs/grounding-validation.md).

**Sprint 3 — grading and evaluation** (17–26 November 2026): answer evaluation
(SF-14, SF-15), targeted feedback (SF-16) and an automated grounding and
hallucination test suite (SF-17).

Live task status: [Jira board](https://abdullahaqeelk.atlassian.net/jira/software/projects/SF/boards/2)

Sprint records:
[Sprint 1 backlog](docs/sprint-1-backlog.md) ·
[Sprint 1 retrospective](docs/sprint-1-retrospective.md) ·
[Sprint 2 backlog](docs/sprint-2-backlog.md) ·
[Sprint 2 retrospective](docs/sprint-2-retrospective.md) ·
[schedule to P-3](docs/sprint-schedule.md)
