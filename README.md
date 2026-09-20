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
- Jira (sprint tracking) · GitHub (version control)

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
| `docs/` | Roles, Definition of Done, architecture, sprint records |
| `tests/` | Unit, integration, and prompt tests |

## Setup

```bash
git clone git@github.com:abdullahaqeelk/studyforge.git
cd studyforge
pip install -r requirements.txt
cp .env.example .env   # add your GOOGLE_API_KEY
python src/api_test.py
```

## Status

Sprint 0 — project initialisation