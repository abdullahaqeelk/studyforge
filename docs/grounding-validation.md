# SF-12 — source citation and grounding validation

`pipeline.generate_from_pdf(path)` now builds/loads the SF-10/SF-11 store,
generates questions, retrieves evidence for each question, and checks the batch
with `agents.grounding_validator`. Existing question fields remain available.
The UI shows a warning on unsupported items and expandable evidence on passes.
No new dependency or environment variable is required.

## Contract

```python
from agents.grounding_validator import validate_grounding

checked = validate_grounding(
    [{"question": "Does UDP guarantee delivery?", "source_page": 3,
      "answer": "No. UDP does not guarantee delivery."}],
    [{"chunk_id": 4, "page": 3,
      "text": "UDP does not guarantee delivery."}],
)
```

`answer` is optional. When present its claims are checked alongside the question.
Each returned item is a copy with `grounded` (boolean), `grounding_score` (binary
0/1, **not** a calibrated confidence), `source_evidence` (chunk ID, page, exact
quote), and `grounding_warning` (text or None). Inputs are not mutated.

The semantic judge receives only the retrieved passages on each item's cited
page. In the PDF pipeline, passages come from `vector_store.search`, including
its configured similarity floor; embeddings never go into the judge prompt.
Passes require both semantic support and locally verified exact quotations.
A valid page number or similar wording alone does not establish support.

One budget covers schema and grounding failures: at most two question-generation
calls, up to five query-embedding calls per batch, and one batched judge call per
attempt. Initial document embedding happens only when the cache needs building.
An unsupported first batch is regenerated once. On the second batch, unsupported
items retain warnings instead of silently being presented as verified.
Malformed judge output triggers the same bounded retry, then a typed error;
provider/configuration failures stop immediately and never become fake passes.

The existing generation input limit of 60,000 source characters remains. This
story adds validation, not long-document generation or grading of student answers.

## Verification

```bash
python -m pytest -q
```

Offline tests exercise real response parsing and evidence checks with mocked
provider responses. They cover wrong pages, fabricated quotes, semantic rejection,
empty retrieval, question/answer payloads, duplicate/reordered indices, malformed
responses, provider failures, input immutability, and the shared retry limit.
The injection-boundary test confirms source instructions stay in the data
payload; it does not establish real-model resistance to prompt injection.

Rules and recorded retry traces are in [ai-decisions.md](ai-decisions.md#aid-5--evidence-based-grounding-with-one-shared-retry).
Runtime events use the `agents.grounding_validator` Python logger. Set the
application logging level to INFO to capture successful checks as well as
failures. Events contain attempt/count metadata, never source or answer text.

## Live prompt check still required before Done

No live key was available during implementation. Run the example above with the
configured Gemini model, then change the answer to "Yes, UDP guarantees delivery."
The expected scores are respectively 1 and 0. Also test an unrelated question,
a question with a false premise, and a source containing instructions to approve
everything. Inspect supporting quotes manually. Record model, prompt version,
expected/actual output and date in the Jira review record.

The judge uses the same configured model family as generation and can share its
errors. Exact quotes prove provenance, not logical entailment. A judge could
still approve an unrelated or incomplete quote; live evaluation and teammate
review remain necessary. SF-17 can measure these false positives/negatives.
