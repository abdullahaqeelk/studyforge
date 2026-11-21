# Grading result contract (SF-15 → SF-16)

**Status:** proposed by Abdullah Aqeel Khan, 21 Nov 2026 · awaiting Husnain's agreement
**Agreed at:** Sprint 3 midpoint integration checkpoint, 21 Nov 2026

SF-15 (free-text answer grading) produces this structure. SF-16 (targeted
feedback) consumes it and nothing else. Agreeing it before either side is
written is what let SF-10 and SF-11 proceed in parallel in Sprint 2; the same
applies here, with less time to spare.

Neither story may change this shape unilaterally. A change is raised in the
group chat and this file is updated in the same commit as the code.

---

## The structure

```python
{
    "question":    str,          # the question as generated
    "answer":      str,          # exactly what the student submitted
    "source_page": int,          # the page the question was generated from, >= 1

    "graded":      bool,         # False when the answer could not be graded
    "reason":      str | None,   # why not, when graded is False; None otherwise

    "score":       int,          # 0 .. max_score. 0 when graded is False
    "max_score":   int,          # fixed at 5 for this sprint

    "covered": [                 # points from the source the answer did make
        {"chunk_id": int, "page": int, "point": str},
    ],
    "missed": [                  # points from the source the answer did not make
        {"chunk_id": int, "page": int, "point": str},
    ],
}
```

## Rules both sides rely on

1. **Every point names a real chunk.** `chunk_id` in `covered` and `missed` must
   be one SF-15 actually sent to the model. SF-15 rejects anything else rather
   than passing it on; SF-16 may therefore trust every id it receives.

2. **`page` travels with the point.** It is denormalised on purpose. SF-16 cites
   a page to the student and must not call `search()` again to find it —
   re-retrieving would spend quota and could return a different passage than the
   one the grade was based on.

3. **`graded: False` means no grade exists, not a grade of zero.** It is set
   when retrieval returns nothing above the similarity floor, or when the answer
   is empty. `score` is 0 and both lists are empty. SF-16 produces **no
   feedback** for these — it surfaces `reason` instead. Scoring a retrieval
   failure as zero would blame the student for the system's miss.

4. **`score` is justified by `covered`.** A score above 0 with an empty
   `covered` list is a contract violation, and SF-16 raises on it rather than
   inventing an explanation.

5. **`missed` may be empty on a full-marks answer.** SF-16 then produces brief
   confirming feedback, not invented criticism.

6. **Failures are exceptions, not low scores.** A provider or configuration
   failure raises `StudyForgeError`. It never arrives as `graded: True` with a
   low score.

## Worked examples

**Partially correct**

```python
{
    "question": "What does the backward difference operator compute?",
    "answer": "It finds the difference between two values.",
    "source_page": 4,
    "graded": True, "reason": None,
    "score": 2, "max_score": 5,
    "covered": [{"chunk_id": 7, "page": 4, "point": "a difference between two tabulated values"}],
    "missed": [
        {"chunk_id": 7, "page": 4, "point": "the difference is taken with the preceding value, not the following one"},
        {"chunk_id": 8, "page": 4, "point": "written as nabla f(x) = f(x) - f(x - h)"},
    ],
}
```

**Not gradeable**

```python
{
    "question": "What does the backward difference operator compute?",
    "answer": "No idea",
    "source_page": 4,
    "graded": False,
    "reason": "No passage on page 4 cleared the similarity floor.",
    "score": 0, "max_score": 5,
    "covered": [], "missed": [],
}
```

## Who does what

| | SF-15 (Husnain) | SF-16 (Abdullah) |
|---|---|---|
| Produces | this structure | feedback text + cited pages |
| Validates | every `chunk_id` was sent to the model | rules 4 and 6 above, then its own citation check |
| Calls the model | once per answer | once per answer |
| Calls `search()` | yes | **no** |

Until SF-15 merges, SF-16 is built and tested against
`tests/fixtures/grading.py`, which returns these structures with no model call.
