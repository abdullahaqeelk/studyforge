"""SF-15 producer checks, with real ranking and a stubbed provider."""

import json
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

import vector_store
from agents import answer_grader as grader
from config import QuotaExceededError

QUESTION = "What does the backward difference compute?"
STORE = {"chunks": [
    {"page": 1, "chunk_id": 0, "text": "Background.", "embedding": [1, 0]},
    {"page": 4, "chunk_id": 7, "text": "Subtract the preceding value.", "embedding": [1, 0]},
    {"page": 4, "chunk_id": 8, "text": "Other course material.", "embedding": [0, 1]},
]}
POINT = {"chunk_id": 7, "point": "Subtract the preceding value."}


@pytest.fixture
def provider(monkeypatch):
    client = Mock()
    monkeypatch.setattr(grader, "get_client", lambda: client)
    monkeypatch.setattr(vector_store, "_embed_query", Mock(return_value=[1, 0]))
    monkeypatch.setattr(vector_store, "get_retrieval_k", lambda: 1)
    monkeypatch.setattr(vector_store, "get_min_similarity", lambda: 0.45)
    return client


def grade(answer="  subtract the preceding value  "):
    return grader.grade_answer(QUESTION, answer, 4, STORE)


@pytest.mark.parametrize("score,covered,missed", [(0, [], [POINT]), (5, [POINT], [])])
def test_gradable_answers_preserve_input_and_resolve_page(provider, score, covered, missed):
    provider.models.generate_content.return_value = SimpleNamespace(text=json.dumps(
        dict(score=score, covered=covered, missed=missed)))
    answer = "  submitted verbatim  "
    assert grade(answer) == dict(question=QUESTION, answer=answer, source_page=4, graded=True,
        reason=None, score=score, max_score=5, covered=[dict(p, page=4) for p in covered],
        missed=[dict(p, page=4) for p in missed])
    provider.models.generate_content.assert_called_once()
    payload = json.loads(provider.models.generate_content.call_args.kwargs["contents"])
    assert payload["sources"] == [{"chunk_id": 7, "page": 4, "text": "Subtract the preceding value."}]
    assert payload["answer"] == answer
    vector_store._embed_query.assert_called_once_with(QUESTION)
    provider.close.assert_called_once()


def test_blank_submission_needs_neither_retrieval_nor_grading(provider):
    assert grade("  ") == dict(question=QUESTION, answer="  ", source_page=4, graded=False,
        reason="No answer was submitted.", score=0, max_score=5, covered=[], missed=[])
    vector_store._embed_query.assert_not_called()
    provider.models.generate_content.assert_not_called()


def test_no_passage_above_floor_is_not_a_grade(provider, monkeypatch):
    monkeypatch.setattr(vector_store, "_embed_query", Mock(return_value=[-1, 0]))
    assert grade("No idea") == dict(question=QUESTION, answer="No idea", source_page=4,
        graded=False, reason="No passage on page 4 cleared the similarity floor.", score=0,
        max_score=5, covered=[], missed=[])
    provider.models.generate_content.assert_not_called()


@pytest.mark.parametrize("payload", [
    None, "bad JSON", json.dumps(dict(score=1, covered=[], missed=[])),
    json.dumps(dict(score=True, covered=[POINT], missed=[])),
    json.dumps(dict(score=6, covered=[POINT], missed=[])),
    json.dumps(dict(score=1, covered=[dict(POINT, chunk_id=8)], missed=[])),
    json.dumps(dict(score=1, covered=[dict(POINT, page=9)], missed=[])),
])
def test_invalid_model_result_raises_without_a_grade(provider, payload):
    provider.models.generate_content.return_value = SimpleNamespace(text=payload)
    with pytest.raises(grader.GradingError):
        grade()
    provider.close.assert_called_once()


def test_provider_failure_stays_an_exception(provider):
    provider.models.generate_content.side_effect = RuntimeError("429 quota exceeded")
    with pytest.raises(QuotaExceededError):
        grade()
    provider.models.generate_content.assert_called_once()
