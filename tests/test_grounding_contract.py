"""
SF-17 — the grounding contract, asserted across every generative path.

Each agent already has its own test file, and each of those proves that *that*
agent behaves. This module exists for a different reason: to state the one rule
the whole system rests on, in one place, and to prove every path obeys it.

    Nothing reaches a student that cannot be traced to the material they
    uploaded. Output citing anything else is rejected or flagged — never
    passed through.

Every test here feeds a path output that is deliberately ungrounded: a citation
to a page that was never supplied, a quote that appears in no chunk, a label
for a chunk that was never sent. The assertion is always about StudyForge's
response, never about the model's — the model is stubbed and is *expected* to
misbehave, because in production it sometimes will.

No API key, no network. If this file ever needs either, the system has lost the
ability to prove its own grounding offline and the change that caused it is the
bug.
"""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

import topics
import vector_store
from agents import answer_grader, feedback, grounding_validator
from agents.feedback import FeedbackError
from agents.question_generator import QuestionGenerationError, parse_questions
from topics import TopicTaggingError

# --------------------------------------------------------------------------
# The paths under contract
# --------------------------------------------------------------------------
# Every module that turns model output into something a student sees belongs
# here. The ledger test at the bottom fails when a new one appears and is not
# listed, so a future agent cannot quietly ship without a grounding assertion.

GENERATIVE_PATHS = {
    "questions": "agents/question_generator.py",
    "grounding_validation": "agents/grounding_validator.py",
    "topics": "topics.py",
    "feedback": "agents/feedback.py",
    "grading": "agents/answer_grader.py",
}

SOURCE_PAGE = 3
SUPPLIED_TEXT = "UDP does not guarantee delivery."
CHUNKS = [{"chunk_id": 4, "page": SOURCE_PAGE, "text": SUPPLIED_TEXT, "embedding": [1.0, 0.0]}]


def stub_client(module, monkeypatch, text):
    """Point a module's client at a canned response. The model is the adversary here."""
    class Client:
        def __init__(self):
            self.calls = 0
            outer = self

            class Models:
                def generate_content(self, model, contents, config):
                    outer.calls += 1
                    return SimpleNamespace(text=text)

            self.models = Models()

        def close(self):
            pass

    client = Client()
    monkeypatch.setattr(module, "get_client", lambda: client)
    if hasattr(module, "get_model"):
        monkeypatch.setattr(module, "get_model", lambda: "test-model")
    return client


# --------------------------------------------------------------------------
# 1. A citation to a page that was never supplied
# --------------------------------------------------------------------------

def test_questions_reject_a_citation_to_an_unsupplied_page():
    """SF-4. The question may be perfect; the page it points at does not exist here."""
    body = json.dumps([
        {"question": f"Q{i}?", "question_type": "short_answer", "source_page": 99}
        for i in range(5)
    ])
    with pytest.raises(QuestionGenerationError, match="cites a page that was not provided"):
        parse_questions(body, {1, 2, 3})


def test_feedback_rejects_a_citation_to_an_unsupplied_page(monkeypatch):
    """SF-16. The explanation reads well and points the student at nothing."""
    stub_client(feedback, monkeypatch, json.dumps(
        {"feedback": "See the derivation on page 99.", "cited_pages": [99]}))
    result = {
        "question": "Does UDP guarantee delivery?", "answer": "No.",
        "source_page": SOURCE_PAGE, "graded": True, "reason": None,
        "score": 1, "max_score": 5,
        "covered": [{"chunk_id": 4, "page": SOURCE_PAGE, "point": SUPPLIED_TEXT}],
        "missed": [],
    }
    with pytest.raises(FeedbackError, match="was not among the pages supplied"):
        feedback.generate_feedback(result)


# --------------------------------------------------------------------------
# 2. A quote that appears in no supplied chunk
# --------------------------------------------------------------------------

def test_grounding_validation_flags_a_quote_that_is_not_in_the_chunk(monkeypatch):
    """SF-12 flags rather than raises: the question survives, carrying a warning.

    This is the one path that does not reject. A question whose evidence fails
    verification is still shown, marked ungrounded, so the student is told the
    citation could not be verified instead of silently losing the question.
    """
    stub_client(grounding_validator, monkeypatch, json.dumps([{
        "item_index": 0, "grounded": True,
        "evidence": [{"chunk_id": 4, "quote": "UDP guarantees ordered delivery."}],
    }]))
    items = [{"question": "Does UDP guarantee delivery?", "source_page": SOURCE_PAGE}]
    result = grounding_validator.validate_grounding(items, CHUNKS)

    assert result[0]["grounded"] is False, "a quote absent from the chunk is not evidence"
    assert result[0]["grounding_score"] == 0
    assert result[0]["source_evidence"] == []
    assert result[0]["grounding_warning"] == grounding_validator.WARNING


def test_a_positive_verdict_cannot_override_local_verification(monkeypatch):
    """The model saying "grounded: true" is an opinion. The quote check is the fact."""
    stub_client(grounding_validator, monkeypatch, json.dumps([{
        "item_index": 0, "grounded": True,
        "evidence": [{"chunk_id": 4, "quote": "Invented supporting sentence."}],
    }]))
    items = [{"question": "Does UDP guarantee delivery?", "source_page": SOURCE_PAGE}]
    assert grounding_validator.validate_grounding(items, CHUNKS)[0]["grounded"] is False


# --------------------------------------------------------------------------
# 3. A reference to a chunk that was never sent
# --------------------------------------------------------------------------

def test_grounding_validation_rejects_evidence_from_an_unsent_chunk(monkeypatch):
    stub_client(grounding_validator, monkeypatch, json.dumps([{
        "item_index": 0, "grounded": True,
        "evidence": [{"chunk_id": 999, "quote": SUPPLIED_TEXT}],
    }]))
    items = [{"question": "Does UDP guarantee delivery?", "source_page": SOURCE_PAGE}]
    assert grounding_validator.validate_grounding(items, CHUNKS)[0]["grounded"] is False


def test_grading_rejects_a_point_citing_an_unsent_chunk(monkeypatch):
    """SF-15. A rubric point crediting a passage the grader never saw is not evidence."""
    monkeypatch.setattr(vector_store, "_embed_query", lambda t: [1.0, 0.0])
    store = {"format": 1, "document_id": "d", "source_name": "d.pdf",
             "embedding_model": "gemini-embedding-001",
             "chunks": [dict(CHUNKS[0])]}
    stub_client(answer_grader, monkeypatch, json.dumps({
        "covered": [], "missed": [{"chunk_id": 999, "point": "invented",
                                   "source_quote": SUPPLIED_TEXT, "weight": 5}]}))
    with pytest.raises(answer_grader.GradingError):
        answer_grader.grade_answer("Does UDP guarantee delivery?", "No.", SOURCE_PAGE, store)


def test_topics_reject_a_label_for_a_chunk_that_was_never_sent():
    """SF-13. A label is a claim about a passage; it needs a passage to be about."""
    body = json.dumps([{"chunk_id": 0, "topics": ["Transport Layer"]},
                       {"chunk_id": 99, "topics": ["Routing"]}])
    with pytest.raises(TopicTaggingError, match="not supplied"):
        topics.parse_topics(body, {0})


# --------------------------------------------------------------------------
# 4. Empty retrieval — nothing in the document supports the question
# --------------------------------------------------------------------------

def test_retrieval_returns_nothing_rather_than_its_least_bad_match(monkeypatch):
    """SF-11. The floor is what stops an unrelated passage becoming a citation.

    Without it every path above still passes: the evidence *is* a supplied
    chunk, the quote *is* in it. The grounding would be real and the answer
    still wrong, because the passage has nothing to do with the question.
    """
    monkeypatch.setattr(vector_store, "_embed_query", lambda text: [0.0, 1.0])
    store = {"format": 1, "document_id": "t", "source_name": "t.pdf",
             "embedding_model": "gemini-embedding-001",
             "chunks": [{"chunk_id": 0, "page": 1, "text": "UDP", "embedding": [1.0, 0.0]}]}
    assert vector_store.search(store, "unrelated question", min_similarity=0.45) == []


def test_feedback_is_withheld_when_nothing_was_retrieved(monkeypatch):
    """SF-16. No evidence means no explanation, not an explanation without evidence."""
    client = stub_client(feedback, monkeypatch, json.dumps(
        {"feedback": "should never be produced", "cited_pages": []}))
    ungraded = {
        "question": "Does UDP guarantee delivery?", "answer": "No idea",
        "source_page": SOURCE_PAGE, "graded": False,
        "reason": "No passage on page 3 cleared the similarity floor.",
        "score": 0, "max_score": 5, "covered": [], "missed": [],
    }
    result = feedback.generate_feedback(ungraded)
    assert result["feedback"] is None
    assert client.calls == 0, "an ungrounded answer must not reach the model at all"


# --------------------------------------------------------------------------
# 5. Rejected output is never fed back as instructions (AID-3)
# --------------------------------------------------------------------------

@pytest.mark.parametrize("module,prompt_attr", [
    (grounding_validator, "PROMPT_FILE"),
    (topics, "PROMPT_FILE"),
    (feedback, "PROMPT_FILE"),
    (answer_grader, "PROMPT_FILE"),
])
def test_every_path_instructs_from_a_versioned_prompt_file(module, prompt_attr):
    """The instruction channel is a file under version control, never model output."""
    name = getattr(module, prompt_attr)
    assert name.endswith(".md")
    assert (Path(__file__).parent.parent / "prompts" / name).is_file()


# --------------------------------------------------------------------------
# 6. The ledger — a new generative path cannot ship without a grounding test
# --------------------------------------------------------------------------

def test_every_generative_module_is_listed_in_this_contract():
    """Fails when an agent appears in src/ and is not covered above.

    This is deliberate. SF-15's grading agent will trip it the moment it merges,
    which is the point: the suite should go red until grading is asserted here
    too, rather than quietly covering three paths out of four.
    """
    source = Path(__file__).parent.parent / "src"
    found = {p.relative_to(source).as_posix() for p in source.glob("agents/*.py")
             if p.name != "__init__.py"}
    found.add("topics.py")

    listed = set(GENERATIVE_PATHS.values())
    missing = found - listed
    assert not missing, (
        f"These generative modules have no grounding assertion in SF-17's contract: "
        f"{sorted(missing)}. Add a test above and list the module in GENERATIVE_PATHS.")
