# Product Backlog

**Project:** StudyForge — Agentic Exam-Preparation System
**Owner:** Product Owner (rotates each sprint)
**Mirrors:** Jira project `SF` — https://abdullahaqeelk.atlassian.net/jira/software/projects/SF

This document records the full product scope across all four sprints. It is
the single ordered list of everything the team believes the product needs, and
it is the source from which each sprint backlog is drawn.

Items below are deliberately recorded **without story points or acceptance
criteria**. Under the team's Definition of Ready (`docs/definition-of-ready.md`),
an item is refined, estimated and given acceptance criteria during the planning
session for the sprint that picks it up. Estimating work months ahead of
execution produces numbers the team cannot defend, so the backlog carries
intent and ordering only until an item approaches a sprint.

---

## Completed — Sprint 0

| ID | Title | Status |
|----|-------|--------|
| SF-1 | Repository scaffolding and project structure | Done |
| SF-2 | Google AI API connection and configuration management | Done |

---

## Committed — Sprint 1 (12–23 Oct 2026)

Fully refined with story points and acceptance criteria in
`docs/sprint-1-backlog.md`.

| ID | Title | Points | Assignee |
|----|-------|--------|----------|
| SF-3 | Course material upload and text extraction | 5 | Usman Irshad |
| SF-4 | Basic question generation agent | 5 | Muhammad Husnain |
| SF-5 | Minimal Streamlit interface | 5 | Mubeen Malik |
| SF-6 | Prompt versioning structure | 2 | Muhammad Husnain |
| SF-7 | Test suite foundation | 3 | Usman Irshad |
| SF-8 | Pipeline orchestration | 3 | Abdullah Aqeel Khan |
| SF-9 | Centralised configuration and API error handling | 2 | Abdullah Aqeel Khan |

**Sprint 1 commitment: 25 story points.**

---

## Unrefined — Retrieval layer (anticipated Sprint 2)

Sprint 2 introduces the retrieval-augmented architecture. Until this epic lands,
questions are generated from raw extracted text with no grounding guarantee.

**SF-10 — Document chunking and embedding**
As a student, I want my uploaded material split and indexed so that questions
can be grounded in specific passages.

**SF-11 — Vector store and retrieval layer**
As a developer, I want a retrieval layer over the indexed material so that
agents can fetch relevant context on demand.

**SF-12 — Source citation on generated questions**
As a student, I want every question to cite the passage it came from so that I
can check it against my notes.

**SF-13 — Topic tagging of course material**
As a student, I want my material organised by topic so that I can practise a
specific area.

---

## Unrefined — Grading and evaluation (anticipated Sprint 3)

Sprint 3 closes the practice loop by evaluating what the student writes back.

**SF-14 — Multiple-choice answer evaluation**
As a student, I want my multiple-choice answers marked instantly so that I get
immediate feedback.

**SF-15 — Free-text answer grading agent**
As a student, I want my written answers graded against the source material so
that I learn what I missed.

**SF-16 — Targeted feedback generation**
As a student, I want an explanation of what my answer was missing so that I can
correct my understanding.

**SF-17 — Grounding and hallucination test suite**
As a developer, I want automated checks that every output traces back to source
material so that unfounded content is caught before release.

---

## Unrefined — Adaptation and integration (anticipated Sprint 4)

Sprint 4 makes the loop adaptive and brings the whole system together behind one
interface.

**SF-18 — Topic-level performance tracking**
As a student, I want my performance recorded per topic so that the system knows
where I am weak.

**SF-19 — Adaptive topic selection (Planner agent)**
As a student, I want practice concentrated on my weak topics so that my study
time goes where it is needed.

**SF-20 — Session history and progress view**
As a student, I want to see my progress over time so that I can tell whether I
am improving.

**SF-21 — Full UI integration and polish**
As a student, I want a coherent interface across upload, practice and feedback
so that the system is usable end to end.

---

## Ordering rationale

The backlog is ordered by architectural dependency rather than by perceived
user value alone. Retrieval (Sprint 2) precedes grading (Sprint 3) because the
Grading agent evaluates answers against retrieved source content and cannot
function without it. Adaptation (Sprint 4) comes last because the Planner agent
consumes grading results to decide what to serve next.

This ordering also means each sprint produces a working increment that is
demonstrably more capable than the last, as required by the project brief.

Sprint assignments above are the team's current expectation, not a commitment.
Items move between sprints at planning based on the velocity actually achieved.
