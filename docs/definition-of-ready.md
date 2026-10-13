# Definition of Ready (DoR)

**Project:** StudyForge — Agentic Exam-Preparation System
**Applies to:** All four sprints
**Owner:** Product Owner (rotates each sprint)
**Agreed by:** Abdullah Aqeel Khan, Mubeen Malik, Usman Irshad, Muhammad Husnain

A backlog item may only be pulled into a sprint when every condition below is
met. The Definition of Ready protects the sprint commitment: an item that is
not Ready cannot be reliably estimated, so accepting one puts the sprint goal
at risk. Items that fail these checks stay in the product backlog and are
refined before the next planning session.

---

## 1. Format

- [ ] Written as a user story: "As a &lt;role&gt;, I want &lt;capability&gt;, so that &lt;benefit&gt;"
- [ ] The benefit clause states real user value, not a restatement of the capability
- [ ] Title is a short noun phrase describing the outcome, not a task

## 2. Clarity

- [ ] Acceptance criteria are written and each one is independently verifiable
- [ ] Anyone on the team can state what "done" looks like without asking the author
- [ ] Domain-specific terms are defined or already in common use by the team

## 3. Estimation

- [ ] Story points assigned by the whole team using the agreed scale (1, 2, 3, 5, 8, 13)
- [ ] Estimate is 5 points or fewer; anything larger is split before entering a sprint
- [ ] The team believes it can be completed within a single two-week iteration

## 4. Dependencies

- [ ] Dependencies on other stories are identified and recorded on the Jira issue
- [ ] Any blocking story is already complete, or scheduled earlier in the same sprint
- [ ] Required external access is available (API key, free-tier quota, sample documents)

## 5. AI-Specific Readiness

- [ ] The prompt approach is outlined, even if the final wording is not fixed
- [ ] Expected output shape is defined (schema, format, or a worked example)
- [ ] A validation strategy exists for the model's output
- [ ] Known hallucination or non-determinism risks are noted on the issue

## 6. Ownership

- [ ] The story is assigned to a named team member at sprint planning
- [ ] The Product Owner has reviewed and accepted it into the sprint backlog

---

## Notes

Ready and Done are deliberately separate gates. The Definition of Ready is
checked before work starts and governs what may enter a sprint; the Definition
of Done is checked before a story is closed and governs what may be called
complete.

Both are fixed for all four sprints so that velocity remains comparable across
iterations. Any change must be agreed in a sprint retrospective and recorded
here with the sprint number at which it took effect.

Product backlog items are intentionally captured without story points or
acceptance criteria (see `docs/product-backlog.md`). They are refined to meet
this Definition of Ready during the planning session for the sprint that picks
them up, not at the moment they are first recorded.
