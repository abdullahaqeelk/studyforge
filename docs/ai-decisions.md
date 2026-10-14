# AI Architecture & Constraint Decisions

**Project:** StudyForge — Agentic Exam-Preparation System
**Course:** EC-360 Software Engineering — Fall 2026

A running record of decisions forced by the behaviour of the AI platform rather
than by product requirements. The project brief asks the team to manage
non-deterministic AI behaviour and API limits as a constraint of the problem,
and to justify engineering decisions with documented rationale. This file is
that record, and it feeds the AI-constraints section of the final report.

---

## AID-1 — Model identifier externalised to configuration

**Date:** 20 September 2026
**Sprint:** 0
**Status:** Implemented in Sprint 1 (SF-9)

### Context

The project initially targeted `gemini-2.0-flash`, with the model name written
directly into `src/api_test.py`.

### What happened

On the first live run of the connection test, the provider returned:

```
404 NOT_FOUND: This model models/gemini-2.0-flash is no longer available.
Please update your code to use models/gemini-3.6-flash for the latest
features and improvements.
```

The model had been retired between the project being planned and the first
request being sent. The API key, network path and SDK were all correct; only
the identifier was stale.

### Decision

Migrate to `gemini-3.6-flash`, and move the model identifier out of source code
into the `GEMINI_MODEL` environment variable, read through `src/config.py`.

### Rationale

A model retirement is not a defect in our code, and it should not require a code
change to absorb. Any provider can retire a model mid-semester, and we have
three sprints still to run. With the identifier in configuration, the same event
becomes a one-line edit in `.env` with no redeploy and no risk of one module
being updated while another is missed.

### Consequences

- `src/config.py` is the single source of the model identifier and the API key.
- No module constructs its own client; all obtain one from `get_client()`.
- `classify_api_error()` detects the `404 NOT_FOUND` signature specifically and
  raises `ModelUnavailableError`, whose message tells the reader to update
  `GEMINI_MODEL` and quotes the provider's own replacement suggestion. If this
  recurs, the error itself explains the fix.

### Evidence

Terminal output of both the failed and successful runs is reproduced in the P-1
submission document.

---

## AID-2 — Grounding as the hallucination control

**Date:** 20 September 2026
**Sprint:** 0
**Status:** Accepted; enforced from Sprint 2 (SF-10 to SF-12)

### Context

The product generates practice questions and grades free-text answers. Both are
failure-prone in the same way: a language model will produce a fluent, plausible
question about material the student never uploaded, and will mark an answer
against knowledge that is not in their course.

### Decision

Every generated question and every grading judgement must be traceable to a
retrieved chunk of the student's own uploaded material. Output that cannot be
traced to source is treated as a test failure, not as a cosmetic flaw.

### Rationale

Prompt instructions alone ("only use the provided text") reduce the frequency of
ungrounded output but cannot be verified. Traceability is checkable: a question
either carries a valid source reference or it does not, and that check can be
automated. This converts a vague quality concern into a pass/fail test.

### Consequences

- Sprint 1 generates questions from raw extracted text and therefore has **no
  grounding guarantee**. This is a known, accepted limitation of the first
  increment, recorded here rather than discovered during the demo.
- Retrieval (SF-10, SF-11) and source citation (SF-12) are scheduled in Sprint 2
  specifically to close this gap.
- SF-17 adds an automated grounding test suite in Sprint 3.

---

## AID-3 — Non-determinism handled by schema validation and one retry

**Date:** 9 October 2026
**Sprint:** 1 planning
**Status:** Accepted; implemented in SF-4

### Context

The question generation agent is asked to return structured JSON. Language
models return malformed or partially formatted JSON intermittently, and the same
prompt may succeed on one call and fail on the next.

### Decision

Parse and validate every model response against the expected shape. On a
validation failure, retry exactly once; if the retry also fails, surface a clear
error rather than degraded output.

### Rationale

One retry absorbs the common transient case at negligible cost. Retrying
repeatedly would hide a genuine prompt defect behind a loop, consume free-tier
quota, and make the failure harder to diagnose. Returning partial or
best-effort output would push malformed data into the rest of the pipeline.

### Consequences

- This uncertainty is reflected in SF-4's estimate: it is a 5-point story partly
  because the output is non-deterministic, not because the code volume is large.
- Prompt changes are versioned under `prompts/` (SF-6) so that a change in
  failure rate can be attributed to a specific prompt revision.

---

## AID-4 — Provider availability treated as a distinct failure mode

**Date:** 14 October 2026
**Sprint:** 1
**Status:** Implemented in SF-9

### Context

During Sprint 1 the connection test failed with:

```
503 UNAVAILABLE: This model is currently experiencing high demand.
Spikes in demand are usually temporary. Please try again later.
```

Nothing was wrong with the API key, the configured model, the free-tier quota
or the network. The provider was simply overloaded at that moment.

### Problem

The first implementation of `classify_api_error()` recognised four failure
modes: rejected key, exhausted quota, retired model and network failure. A 503
matched none of them and fell through to the generic "Unexpected Google AI
error". A developer reading that message would reasonably start checking their
key and their quota — neither of which was the cause — and waste time on a
fault that was not theirs.

### Decision

Add `ServiceUnavailableError` as a fifth failure mode, matched on 503,
`UNAVAILABLE`, `overloaded` and `high demand`, and check it **before** the quota
case. Its message states explicitly that the key, quota and network are not at
fault and that the request should be retried later.

### Rationale

Quota exhaustion and provider overload both present as "try again later", but
they demand opposite responses: one requires the team to change something, the
other requires them to change nothing. Collapsing them into one message would
send developers chasing a problem they cannot fix.

More broadly, this is the API-limit constraint the CEP declaration names. The
system depends on a third-party service whose availability the team does not
control, so availability failures have to be a first-class, named condition
rather than an unhandled exception.

### Consequences

- Five typed failure modes are now distinguished in `src/config.py`.
- The ordering of checks in `classify_api_error()` is significant and is
  commented in the source, since 503 text can also contain quota-like wording.
- No automatic retry was added. A transient outage can last minutes, and a
  blocking retry loop inside a Streamlit request would appear to the user as a
  hang. The decision is to fail fast with an accurate message and let the user
  retry. This may be revisited in Sprint 3 if outages prove frequent.
