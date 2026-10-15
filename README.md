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
```

## Contributing

One branch per story, named `feature/SF-<id>-<short-description>`. Every change
reaches `main` through a pull request reviewed by another team member. Commit
messages begin with the Jira key (`SF-3 ...`) so that commits link back to the
board automatically.

## Status

**Sprint 1 — core generation pipeline** (12–23 October 2026)

Sprint goal: a user can upload a course document and receive AI-generated
practice questions from its content, with repository, tooling, and
prompt-versioning discipline in place.

On `main`:

- **SF-9** Centralised configuration and API error handling — five typed
  failure modes distinguished behind one client factory
- **SF-3** Course material upload and text extraction — per-page text with
  page numbers preserved, 11 tests passing

In progress: question generation (SF-4), prompt versioning (SF-6), test suite
foundation (SF-7), pipeline orchestration (SF-8), Streamlit interface (SF-5).

Retrieval, grading, and adaptive planning are deliberately out of scope for
Sprint 1 and are scheduled for Sprints 2–4. Sprint 1 generates questions from
raw extracted text, which means it carries no grounding guarantee; closing that
gap is the purpose of Sprint 2.

Live task status: [Jira board]https://abdullahaqeelk.atlassian.net/jira/software/projects/SF/boards/2?filter=&groupBy=none ·
[docs/sprint-1-backlog.md](docs/sprint-1-backlog.md)
