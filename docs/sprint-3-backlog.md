# Sprint 3 Backlog

**Sprint Goal:** Close the practice loop — a student can answer a generated
question, have the answer marked against the source material, and receive an
explanation of what was missing.

**Duration:** 16 Nov 2026 — 26 Nov 2026 (10 days)
**Scrum Master:** Usman Irshad
**Product Owner:** Muhammad Husnain
**Committed Story Points:** 16
**Completed Story Points:** 16 (sprint closed 25 November, one day early)

> Scope note: the product backlog recorded SF-14 as "multiple-choice answer
> evaluation". Planning found that no multiple-choice question existed to
> evaluate — `question_generator.py` emitted only `short_answer` items, with no
> options and no answer key. The Product Owner widened SF-14 to cover
> generation and evaluation together, re-estimating it from 3 points to 5, and
> reduced SF-16 from 5 to 3 so that the commitment stayed at 16. The
> alternative, a separate generation story, was rejected as a fifth story in a
> ten-day iteration.

> Capacity note: Sprint 2 delivered 16 points across ten days. Sprint 3 is the
> same length and committed the same figure rather than the 20.5 two-sprint
> average, which is inflated by Sprint 1's twelve-day iteration.

---

## SF-14 — Multiple-choice generation and answer evaluation
**Points:** 5 · **Assignee:** Mubeen Malik · **Priority:** High

**User story**
As a student, I want my multiple-choice answers marked instantly so that I get
immediate feedback without waiting for a model call.

**Acceptance criteria**
- `question_type` accepts `multiple_choice` in addition to `short_answer`; a
  short-answer question keeps its existing three-key shape unchanged
- A multiple-choice question carries exactly four distinct non-empty options and
  a `correct_option` index in range, alongside its `source_page`
- A response failing any of those checks is rejected rather than repaired, and
  triggers the existing retry
- Evaluation of a submitted answer is local and deterministic: no model call,
  no network, no quota spent marking a letter against a letter
- An option index that was never offered raises rather than returning
  "incorrect"
- Unit tests cover correct, incorrect, out-of-range, malformed and
  missing-options cases, with the provider stubbed

**Dependencies:** builds on SF-4 and SF-12.

---

## SF-15 — Free-text answer grading agent
**Points:** 5 · **Assignee:** Muhammad Husnain · **Priority:** High

**User story**
As a student, I want my written answers graded against the source material so
that I learn what I missed rather than what a model assumes I should know.

**Acceptance criteria**
- Grades a free-text answer against the passages retrieved for the question's
  cited page, never against whole-document text and never against the model's
  own knowledge
- Returns a structured verdict: a score, the source points the answer covered,
  and the points it missed
- Every point is tied to a `chunk_id` that was actually supplied to the grader;
  anything else is rejected
- An empty answer is scored without a model call
- When retrieval returns nothing above the similarity floor the answer is
  returned ungraded with an explicit reason, never scored zero
- Provider and configuration failures propagate as typed errors, not as a low
  score
- Unit tests stub the model throughout; the suite runs with no API key

**Dependencies:** builds on SF-11 and SF-12. Blocks SF-16.

---

## SF-16 — Targeted feedback generation
**Points:** 3 · **Assignee:** Abdullah Aqeel Khan · **Priority:** Medium

**User story**
As a student, I want an explanation of what my answer was missing so that I can
correct my understanding rather than just seeing a score.

**Acceptance criteria**
- Takes a grading result from SF-15 and returns feedback written to the student
- Feedback draws only on the points supplied to it, and cites the page the
  student can turn to
- Every cited page is checked against the points actually supplied; a citation
  to anything else is rejected
- A correct answer produces brief confirming feedback, not invented criticism
- One model call per submitted answer, not one per missed point
- An ungraded answer produces no feedback; the reason is surfaced instead
- Unit tests cover correct, partially correct, incorrect and ungraded answers

**Dependencies:** blocked by SF-15. The interface between them was agreed before
either was written — see `docs/grading-contract.md`.

---

## SF-17 — Grounding and hallucination test suite
**Points:** 3 · **Assignee:** Usman Irshad · **Priority:** High

**User story**
As a developer, I want automated checks that every student-facing output traces
back to source material so that unfounded content is caught before it reaches a
student.

**Acceptance criteria**
- One module asserting the grounding contract across every generative path:
  questions, grounding validation, topics, grading and feedback
- Each path is tested with a stubbed model returning deliberately ungrounded
  output; the assertion is on StudyForge's response, never the model's
- Covers a citation to a page never supplied, a quote absent from the cited
  chunk, a reference to a chunk outside the payload, and empty retrieval
- Runs in the existing suite with no API key and no network
- A generative module with no grounding assertion fails the suite

**Dependencies:** soft dependency on SF-15 and SF-16. Begun against the paths
already on `main` and extended as the others merged.

---

## Allocation

| Member | Role (Sprint 3) | Stories | Points |
|--------|-----------------|---------|--------|
| Mubeen Malik | Developer | SF-14 | 5 |
| Muhammad Husnain | Product Owner | SF-15 | 5 |
| Abdullah Aqeel Khan | Developer | SF-16 | 3 |
| Usman Irshad | Scrum Master | SF-17 | 3 |
| | | **Total** | **16** |

SF-17 was assigned to the one member who wrote neither SF-15 nor SF-16, so the
grounding assertions were not written by the authors of the code they test.

---

## Build order and dependency risk

The sprint contained one hard sequence: **SF-15 → SF-16**. SF-17 depended
softly on both.

The planned mitigation was the one that worked in Sprint 2 — agree the data
contract before either side is written, so both can proceed in parallel. It was
not done at planning. SF-16 was blocked for the first five days and no story
closed in that time.

On 21 November the structure SF-15 returns and SF-16 consumes was written down
as `docs/grading-contract.md`, with executable fixtures in
`tests/fixtures/grading.py`. SF-16 was then built, reviewed and merged against
those fixtures before SF-15 landed. Thirteen of sixteen points closed in the
three days following.

The midpoint integration checkpoint was scheduled for 21 November and was not
held as a ceremony, for the third sprint running.

---

## Outcome

All four stories completed. The sprint was closed on 25 November, one day
before its boundary, with nothing carried over.

| Measure | Value |
|---|---|
| Story points committed / completed | 16 / 16 |
| Stories committed / completed | 4 / 4 |
| Pull requests opened / merged | 4 / 4 |
| Pull requests requiring changes before approval | 4 |
| Defects found in review / after merge | 10 / 0 |
| Automated tests at sprint close | 333 (332 offline, 1 live API) |
| Scope changes during the sprint | One, at planning (SF-14) |

Every generative path in the system is now asserted against the grounding
contract automatically. Retrospective: `docs/sprint-3-retrospective.md`.
