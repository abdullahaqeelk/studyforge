"""Offline contract and retry tests for SF-4/SF-6; no key or network needed."""

import json
from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

import prompt_loader
from agents import question_generator as generator
from config import QuotaExceededError
from prompt_loader import PromptError, load_prompt


@pytest.fixture
def questions():
    return [{"question": f"Explain concept {i}.", "question_type": "short_answer",
             "source_page": 3} for i in range(5)]


@pytest.fixture
def client(monkeypatch, questions):
    stub = Mock()
    stub.models.generate_content.return_value = SimpleNamespace(text=json.dumps(questions))
    monkeypatch.setattr(generator, "get_client", lambda: stub)
    monkeypatch.setattr(generator, "get_model", lambda: "configured-test-model")
    return stub


def test_valid_json(questions):
    assert generator.parse_questions(json.dumps(questions), {3}) == questions


@pytest.mark.parametrize("output", [None, "", "not json", "```json\n[]\n```", "{}", "[]", "null"])
def test_invalid_response(output):
    with pytest.raises(generator.QuestionGenerationError):
        generator.parse_questions(output, {3})


@pytest.mark.parametrize("field,value", [
    ("question", " "), ("question", 42), ("question_type", "mcq"),
    ("source_page", 99), ("source_page", True), ("source_page", "3"),
])
def test_invalid_fields(questions, field, value):
    questions[0][field] = value
    with pytest.raises(generator.QuestionGenerationError):
        generator.parse_questions(json.dumps(questions), {3})


def test_extra_and_missing_fields(questions):
    for invalid in [dict(questions[0], answer="extra"), {"question": "Missing fields?"}]:
        changed = deepcopy(questions)
        changed[0] = invalid
        with pytest.raises(generator.QuestionGenerationError):
            generator.parse_questions(json.dumps(changed), {3})


def test_duplicates_ignore_case_and_whitespace(questions):
    questions[1]["question"] = "  EXPLAIN   CONCEPT 0.  "
    with pytest.raises(generator.QuestionGenerationError, match="duplicate"):
        generator.parse_questions(json.dumps(questions), {3})


def test_shared_model_prompt_and_page_contract(client, questions):
    pages = [{"page": 1, "text": ""}, {"page": 3, "text": "Course content"}]
    assert generator.generate_questions(pages) == questions
    call = client.models.generate_content.call_args.kwargs
    assert call["model"] == "configured-test-model"
    assert json.loads(call["contents"]) == {"pages": [pages[1]]}
    assert call["config"]["system_instruction"] == load_prompt(generator.PROMPT_FILE)
    assert call["config"]["response_mime_type"] == "application/json"
    assert call["config"]["response_schema"] == generator.QUESTION_SCHEMA
    client.close.assert_called_once()


def test_retry_once_then_success(client, questions):
    client.models.generate_content.side_effect = [
        SimpleNamespace(text="bad json"), SimpleNamespace(text=json.dumps(questions))]
    assert generator.generate_questions([{"page": 3, "text": "Notes"}]) == questions
    assert client.models.generate_content.call_count == 2


def test_invalid_page_citation_retried(client):
    # The mock cites page 3, but page 3 is blank and was not sent to the model.
    with pytest.raises(generator.QuestionGenerationError, match="two attempts"):
        generator.generate_questions([{"page": 1, "text": "Notes"}, {"page": 3, "text": ""}])
    assert client.models.generate_content.call_count == 2


def test_two_invalid_responses_fail_without_third_call(client):
    client.models.generate_content.return_value = SimpleNamespace(text=None)
    with pytest.raises(generator.QuestionGenerationError, match="two attempts"):
        generator.generate_questions([{"page": 3, "text": "Notes"}])
    assert client.models.generate_content.call_count == 2
    client.close.assert_called_once()


def test_quota_error_is_typed_and_not_retried(client):
    client.models.generate_content.side_effect = RuntimeError("429 quota exceeded")
    with pytest.raises(QuotaExceededError):
        generator.generate_questions([{"page": 3, "text": "Notes"}])
    client.models.generate_content.assert_called_once()
    client.close.assert_called_once()


@pytest.mark.parametrize("pages", [
    [], None, "not pages", [{"page": True, "text": "x"}],
    [{"page": 0, "text": "x"}], [{"page": 1, "text": None}],
    [{"page": 1, "text": " "}],
    [{"page": 1, "text": "a"}, {"page": 1, "text": "b"}],
    [{"page": 1, "text": "x" * (generator.MAX_SOURCE_CHARACTERS + 1)}],
])
def test_invalid_source_does_not_call_api(client, pages):
    with pytest.raises(generator.QuestionGenerationError):
        generator.generate_questions(pages)
    client.models.generate_content.assert_not_called()


def test_prompt_works_outside_repository(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    prompt = load_prompt(generator.PROMPT_FILE)
    for field in ["Version:", "Author:", "Date:", "Change note:"]:
        assert field in prompt


@pytest.mark.parametrize("name", ["../config.md", "sub/file.md", "..\\config.md", "file.txt", None])
def test_invalid_prompt_filename(name):
    with pytest.raises(PromptError):
        load_prompt(name)


def test_prompt_missing_empty_and_runtime_reload(monkeypatch, tmp_path):
    monkeypatch.setattr(prompt_loader, "PROMPT_DIRECTORY", tmp_path)
    with pytest.raises(PromptError):
        load_prompt("missing.md")
    path = tmp_path / "test.md"
    path.write_text(" ", encoding="utf-8")
    with pytest.raises(PromptError, match="empty"):
        load_prompt("test.md")
    path.write_text("First version", encoding="utf-8")
    assert load_prompt("test.md") == "First version"
    path.write_text("Second version", encoding="utf-8")
    assert load_prompt("test.md") == "Second version"
