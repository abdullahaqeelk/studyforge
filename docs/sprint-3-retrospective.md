# Sprint 3 Retrospective

**Project:** StudyForge — Agentic Exam-Preparation System
**Course:** EC-360 Software Engineering — Fall 2026
**Sprint:** SF Sprint 3 — 16 to 26 November 2026 (closed 25 November)
**Facilitated by:** Usman Irshad (Scrum Master, Sprint 3)
**Present:** Abdullah Aqeel Khan, Mubeen Malik, Usman Irshad, Muhammad Husnain

---

## 1. Sprint data

| Measure | Value |
|---|---|
| Sprint goal | Close the practice loop: a student can answer a generated question, have the answer marked against the source material, and receive an explanation of what was missing |
| Goal met | Yes |
| Stories committed / completed | 4 / 4 |
| Story points committed / completed | 16 / 16 |
| Velocity (Sprint 1 → 2 → 3) | 25 → 16 → 16, average 19 |
| Scope changes during the sprint | One, at planning: SF-14 widened (see §2) |
| Pull requests opened / merged | 4 / 4 |
| Pull requests requiring changes before approval | 4 |
| Defects found in review | 10 |
| Defects found after merge | 0 |
| Automated tests at sprint close | 333 (121 added this sprint) |
| Sprint closed | 25 November, one day early |

---

## 2. A story that could not be built as written

The product backlog recorded SF-14 as "multiple-choice answer evaluation".
Planning found that nothing in the system produced a multiple-choice question:
`question_generator.py` declared `"question_type": {"enum": ["short_answer"]}`
and no question carried options or an answer key. There was nothing for an
evaluator to mark against.

The Product Owner widened SF-14 to cover generation and evaluation together,
re-estimated it from 3 points to 5, and reduced SF-16 from 5 to 3 to hold the
commitment at 16. The alternative — inserting a separate generation story — was
rejected as a fifth story in a ten-day sprint.

This is recorded because the backlog item had existed unexamined since Sprint 0
and was only tested against the code when someone tried to start it. The
Definition of Ready requires acceptance criteria and dependencies before a
story enters a sprint; it does not require that the story be checked against
what the system actually does. For Sprint 4 the Product Owner reads the
relevant module before refining a story that touches it.

---

## 3. What went well

**Agreeing the data contract unblocked two stories at once.**
SF-16 depended on SF-15's output and could not begin without it. On
21 November the exact structure SF-15 returns and SF-16 consumes was written
down as `docs/grading-contract.md`, together with executable fixtures in
`tests/fixtures/grading.py`. From that point both members built in parallel
against the same shape, and SF-16 was implemented, reviewed and merged before
SF-15 landed. Thirteen of the sprint's sixteen points closed in the three days
that followed.

**Peer review found ten defects, in both directions, and none reached `main`.**

| PR | Finding | Consequence if merged |
|---|---|---|
| #11 SF-16 | The citation allowlist included `source_page`, which is never sent to the model | Feedback citing a page the model was never shown passed the grounding check |
| #12 SF-15 | `answer_quote` was a bare substring test | A wrong answer scored 5 of 5 when the model quoted the word "the" |
| #12 SF-15 | No retry on a malformed grading response, unlike every other agent | A single rubric arithmetic slip failed the student's grading outright |
| #13 SF-14 | The marked option was not passed to the grounding judge | An incorrect answer key was marked grounded and the student marked wrong |
| #13 SF-14 | Multiple-choice questions rendered without their choices | "Which of the following?" displayed with nothing to choose |
| #13 SF-14 | The v2 batch minimum was not enforced | All-short-answer batches accepted, so the retry never fired |
| #13 SF-14 | An ungrounded question still disclosed its answer key and scored the student | The warning was shown and contradicted in the same view |
| #13 SF-14 | Saved questions and radio selections were not scoped to the upload | A new document showed the previous document's questions |
| #13 SF-14 | Two PDFs with the same name and byte length shared a cache key | Stale questions survived a replacement upload |
| #14 SF-17 | The grounding ledger was not updated after SF-15 merged | The suite would have turned `main` red on merge |

All four pull requests required changes before approval. Every finding was
reproduced before it was fixed, and every fix was re-verified by the reviewer
rather than accepted on the author's summary. Two of the ten were caught by
each of the project's two most active reviewers in the other's work — the same
class of defect, a check that passed on evidence the model had never been
shown, found independently in SF-15 and SF-16.

**A test caught a gap mechanically that no person had noticed.**
SF-17's final assertion scans `src/agents/` and fails if a generative module
has no grounding assertion recorded against it. When SF-15 merged, the suite
turned red naming `agents/answer_grader.py`. The gap was closed before SF-17
itself merged. This is the first check in the project that notices a missing
safeguard rather than a broken one.

---

## 4. What did not go well

**No story closed for the first five days.**
The burndown is flat at 16 points from 17 to 21 November — half the iteration.
The cause is in §3: the contract that let SF-15 and SF-16 proceed in parallel
was written on day 5, not at planning. Sprint 2's retrospective closed with the
action "continue agreeing data contracts between dependent stories before
either is written". The practice was known, carried forward in writing, and
still applied five days late.

**Burndown snapshots were first captured on day 9.**
Section 3 of `docs/team-roles.md` makes twice-weekly capture a Scrum Master
duty. Sprint 2's retrospective recorded the same omission. The mid-sprint shape
of this sprint survives only because the day-9 capture happened to be taken
before the final three days of burn-down.

**The repository's own schedule disagreed with Jira for the whole sprint.**
`docs/team-roles.md` recorded Sprint 3 as 9–22 November throughout an iteration
that Jira ran from 16–26 November. Three different Sprint 3 start dates existed
across the planning documents, the schedule table and the board. Jira is the
system of record and the documents were corrected at sprint close rather than
during it.

**`.gitattributes` is still absent.**
Action item 1 from Sprint 2's retrospective, owned and unstarted for two
sprints. Line-ending warnings appeared again on SF-16's first push. The reason
it was deferred the second time is legitimate — renormalising every file while
four feature branches are open would conflict with all of them — but that
window is now open and the action has to be taken before the first Sprint 4
branch is cut.

**Commit identity on the shared laptop was wrong three times.**
Four members share one machine. `git config user.name` was left on the previous
member's name on three occasions and caught before committing each time, once
only because the reviewer asked. A single misattributed commit would be
invisible in the code and visible in the contribution record.

**The midpoint integration checkpoint was not held as a ceremony.**
Carried from Sprint 1 and Sprint 2, now three sprints unheld. The contract
discussion on 21 November did the work the checkpoint exists to do, but it
happened because a dependency was blocking, not because it was scheduled.

---

## 5. What we are changing

| # | Action | Owner | By |
|---|---|---|---|
| 1 | Add `.gitattributes` with `* text=auto eol=lf` and renormalise, in a standalone commit on `main` | Mubeen Malik | Before the first Sprint 4 branch |
| 2 | Data contracts between dependent stories are written into the sprint backlog **at planning**, not when the dependency blocks | Product Owner, each sprint | Sprint 4 planning |
| 3 | Burndown captured every Monday and Thursday, with a calendar reminder rather than intent | Scrum Master, each sprint | Sprint 4 day 1 |
| 4 | `git config user.name` is the first command after taking the laptop; each member uses one identity | All members | Immediate |
| 5 | The Product Owner reads the module a story touches before refining it | Product Owner | Sprint 4 planning |

Carried forward: the midpoint integration checkpoint, now explicitly scheduled
for **2 December** rather than left to intent; and query-embedding batching,
raised in Sprint 2 and still not written as a story.

---

## 6. Velocity and estimation

| Sprint | Days | Committed | Completed |
|---|---|---|---|
| Sprint 1 | 12 | 25 | 25 |
| Sprint 2 | 10 | 16 | 16 |
| Sprint 3 | 10 | 16 | 16 |
| **Average** | | | **19** |

The average is the less useful number. Two ten-day iterations have now both
delivered exactly 16 points, which makes 16 the figure Sprint 4 should be
planned against. Sprint 1's 25 came from a twelve-day iteration with smaller,
better-understood stories and is not a precedent for a ten-day sprint.

Sprint 4 runs 27 November to 6 December — ten days, the same shape. The
commitment should be 16 points, and the retrospective will be able to say
whether a third identical result is capacity or coincidence.

---

## 7. Carried into Sprint 4

Sprint 3 closed the practice loop: a student can upload a document, receive
grounded questions in both short-answer and multiple-choice form, submit an
answer, have it marked against the source material, and read an explanation of
what the answer missed. The grounding contract is now asserted automatically
across all five generative paths.

What the system still lacks is the adaptive half of its own description. Topic
tagging exists (SF-13) and grading exists (SF-15), but nothing connects them:
performance is not tracked per topic and nothing selects what to serve next.
That is Sprint 4's epic, and it is the capability the product was named for.

Roles rotate at the sprint boundary: **Muhammad Husnain** takes Scrum Master
and **Abdullah Aqeel Khan** takes Product Owner for Sprint 4. This completes
the rotation — every member will have served once in each role.
