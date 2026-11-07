# Sprint 1 Retrospective

**Project:** StudyForge — Agentic Exam-Preparation System
**Course:** EC-360 Software Engineering — Fall 2026
**Sprint:** SF Sprint 1 — 12 to 23 October 2026
**Held:** 23 October 2026
**Facilitated by:** Abdullah Aqeel Khan (Scrum Master, Sprint 1)
**Present:** Abdullah Aqeel Khan, Mubeen Malik, Usman Irshad, Muhammad Husnain

---

## 1. Sprint data

| Measure | Value |
|---|---|
| Sprint goal | Establish a working vertical slice: a user can upload a course document and receive AI-generated practice questions from its content |
| Goal met | Yes |
| Stories committed / completed | 7 / 7 |
| Story points committed / completed | 25 / 25 |
| Scope changes during the sprint | None |
| Pull requests opened / merged | 5 / 5 |
| Pull requests requiring changes before approval | 2 |
| Defects found in review | 1 |
| Defects found after merge | 0 |
| Automated tests at sprint close | 56 |
| Remaining work reached zero | 22 October, one day before the sprint boundary |

---

## 2. What went well

**Scheduling the configuration story first paid for itself.**
SF-9 centralised the model identifier and the API client before any agent was
written. When the provider retired `gemini-2.0-flash` mid-development, the fix
was one line in `.env` rather than a change in every module that talks to the
API. Had SF-9 been scheduled late, the same event would have been a refactor
across four files.

**Code review caught a defect that the author's own tests did not.**
In PR #1 the reviewer found that a password-protected PDF escaped the project's
error contract: `PdfReader()` succeeds on an encrypted file and the failure only
surfaces when the page tree is touched, which happened outside the try block.
The reviewer supplied reproduction steps and withheld approval until the fix
and two regression tests landed. Two of five pull requests required changes
before approval, which suggests review was substantive rather than procedural.

**Versioning prompts from the first sprint was the right call.**
Keeping prompts in `prompts/` as files with version headers, rather than as
string literals, means a change in model behaviour can be attributed to a
specific prompt revision. This costs almost nothing to set up in Sprint 1 and
would be painful to retrofit in Sprint 3.

**Typed error handling made failures legible.**
Five distinct failure modes — rejected key, exhausted quota, retired model,
provider overload, network failure — each produce a message naming the actual
cause. When the provider returned 503 during the sprint, the error told the
reader explicitly that the key, quota and network were not at fault.

---

## 3. What did not go well

**A dependency chain stalled the Product Owner for two days.**
SF-5 (interface) depended on SF-8 (pipeline), which depended on SF-3 and SF-4.
The build order correctly placed SF-8 after the two stories it needs, but did
not account for SF-5 needing SF-8 in turn. The result is the visible plateau in
the burndown between 17 and 19 October, during which the member assigned SF-5
had nothing to merge. The team sequenced by story priority rather than by the
full dependency graph.

**One change reached `main` without a pull request.**
`src/app.py` was pushed directly to `main` on 16 October, outside the branching
policy the team had documented in the README two days earlier. It was noticed,
moved onto a branch and resubmitted through review. The policy existed only as
an agreement; nothing in the tooling enforced it.

**The four modules were not executed together until day seven.**
Every story had passing unit tests from the day it merged, but the end-to-end
path — upload, extract, generate, render — was not run once until 18 October.
It worked on the first attempt. That outcome was partly fortunate: four people
built against a shared contract for a week with no integration checkpoint, and
a mismatch would have surfaced with three days left rather than seven.

**The Jira board was created after work had already begun.**
Development started on 12 October; the sprint was created and started on the
board on 14 October. The sprint dates recorded are the real ones, but for two
days the board did not reflect the state of the work, and no burndown data
exists for the opening of the sprint.

**Commit attribution needed manual management.**
Team members shared one machine for part of the sprint. Without resetting the
local Git identity between sessions, commits were attributed to whoever had
configured the repository last. This was caught and corrected, but it was
corrected by vigilance rather than by any mechanism.

---

## 4. What we are changing

| # | Action | Owner | By |
|---|---|---|---|
| 1 | Sequence the sprint backlog by the full dependency graph, not by story priority. Identify the longest chain at planning and schedule its head first. | Scrum Master, each sprint | Sprint 2 planning |
| 2 | Enable branch protection on `main` requiring one approving review, so the branching policy is enforced by the tool rather than by agreement. | Abdullah Aqeel Khan (repository owner) | Before Sprint 2's first PR |
| 3 | Add an integration checkpoint at the midpoint of each sprint: run the full end-to-end path with whatever is on `main` and record the result. | Scrum Master, each sprint | Sprint 2 midpoint |
| 4 | Create and start the sprint in Jira before the first commit of that sprint, not after. | Scrum Master, each sprint | Sprint 2 start |
| 5 | On a shared machine, set `user.name` and `user.email` at the start of each session and verify with `git config user.email` before the first commit. | All members | Ongoing |

---

## 5. Velocity and estimation

Sprint 1 completed 25 of 25 committed points, but it completed them in seven
working days of eleven. The commitment was met in full and the goal was
achieved, so the sprint is a success on its own terms — but the margin
indicates the estimates were conservative rather than that the team's capacity
is exactly 25 points.

This is a first sprint with no prior velocity to calibrate against, so
conservative estimates were the correct choice. For Sprint 2 the team now has
a completed five-point story (SF-3) to anchor against, which should produce
tighter estimates. A single sprint is not a reliable velocity measurement; the
figure becomes meaningful after three iterations.

---

## 6. Carried into Sprint 2

Sprint 1 generates questions from raw extracted text with no retrieval layer,
so grounding is enforced by prompt instruction rather than guaranteed by
architecture. This was a deliberate scope decision recorded as AID-2 before
development began, not an oversight. A manual grounding review on SF-4 found
five of five generated questions traceable to their cited page, which
establishes that the citation mechanism works but does not establish a
hallucination rate.

Sprint 2 replaces that manual check with a structural one: chunking and
embedding (SF-10), a retrieval layer (SF-11) and source citation on every
question (SF-12).
