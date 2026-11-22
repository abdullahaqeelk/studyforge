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
    return [
        {
            "question": f"Explain concept {i}.",
            "question_type": "short_answer",
            "source_page": 3,
        }
        for i in range(5)
    ]


@pytest.fixture
def client(monkeypatch, questions):
    stub = Mock()
    stub.models.generate_content.return_value = SimpleNamespace(
        text=json.dumps(questions)
    )
    monkeypatch.setattr(generator, "get_client", lambda: stub)
    monkeypatch.setattr(generator, "get_model", lambda: "configured-test-model")
    return stub


def test_valid_json(questions):
    assert generator.parse_questions(json.dumps(questions), {3}) == questions


@pytest.mark.parametrize(
    "output", [None, "", "not json", "```json\n[]\n```", "{}", "[]", "null"]
)
def test_invalid_response(output):
    with pytest.raises(generator.QuestionGenerationError):
        generator.parse_questions(output, {3})


@pytest.mark.parametrize(
    "field,value",
    [
        ("question", " "),
        ("question", 42),
        ("question_type", "mcq"),
        ("source_page", 99),
        ("source_page", True),
        ("source_page", "3"),
    ],
)
def test_invalid_fields(questions, field, value):
    questions[0][field] = value
    with pytest.raises(generator.QuestionGenerationError):
        generator.parse_questions(json.dumps(questions), {3})


def test_extra_and_missing_fields(questions):
    for invalid in [
        dict(questions[0], answer="extra"),
        {"question": "Missing fields?"},
    ]:
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
        SimpleNamespace(text="bad json"),
        SimpleNamespace(text=json.dumps(questions)),
    ]
    assert generator.generate_questions([{"page": 3, "text": "Notes"}]) == questions
    assert client.models.generate_content.call_count == 2


def test_invalid_page_citation_retried(client):
    # The mock cites page 3, but page 3 is blank and was not sent to the model.
    with pytest.raises(generator.QuestionGenerationError, match="two attempts"):
        generator.generate_questions(
            [{"page": 1, "text": "Notes"}, {"page": 3, "text": ""}]
        )
    assert client.models.generate_content.call_count == 2


def test_two_invalid_responses_fail_without_third_call(client):
    client.models.generate_content.return_value = SimpleNamespace(text=None)
    with pytest.raises(generator.QuestionGenerationError, match="two attempts"):
        generator.generate_questions([{"page": 3, "text": "Notes"}])
    assert client.models.generate_content.call_count == 2
    client.close.assert_called_once()


def test_sf12_can_own_the_retry_budget(client):
    client.models.generate_content.return_value = SimpleNamespace(text="bad JSON")
    with pytest.raises(generator.QuestionGenerationError, match="one attempt"):
        generator.generate_questions([{"page": 3, "text": "Notes"}], max_attempts=1)
    client.models.generate_content.assert_called_once()


@pytest.mark.parametrize("attempts", [0, 3, True, "2"])
def test_invalid_retry_budget_fails_before_api_call(client, attempts):
    with pytest.raises(generator.QuestionGenerationError, match="max_attempts"):
        generator.generate_questions(
            [{"page": 3, "text": "Notes"}], max_attempts=attempts
        )
    client.models.generate_content.assert_not_called()


def test_quota_error_is_typed_and_not_retried(client):
    client.models.generate_content.side_effect = RuntimeError("429 quota exceeded")
    with pytest.raises(QuotaExceededError):
        generator.generate_questions([{"page": 3, "text": "Notes"}])
    client.models.generate_content.assert_called_once()
    client.close.assert_called_once()


@pytest.mark.parametrize(
    "pages",
    [
        [],
        None,
        "not pages",
        [{"page": True, "text": "x"}],
        [{"page": 0, "text": "x"}],
        [{"page": 1, "text": None}],
        [{"page": 1, "text": " "}],
        [{"page": 1, "text": "a"}, {"page": 1, "text": "b"}],
        [{"page": 1, "text": "x" * (generator.MAX_SOURCE_CHARACTERS + 1)}],
    ],
)
def test_invalid_source_does_not_call_api(client, pages):
    with pytest.raises(generator.QuestionGenerationError):
        generator.generate_questions(pages)
    client.models.generate_content.assert_not_called()


def test_prompt_works_outside_repository(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    prompt = load_prompt(generator.PROMPT_FILE)
    for field in ["Version:", "Author:", "Date:", "Change note:"]:
        assert field in prompt


@pytest.mark.parametrize(
    "name", ["../config.md", "sub/file.md", "..\\config.md", "file.txt", None]
)
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


# --- SF-14 Multiple-Choice Generation Tests ---


def _valid_mcq(idx: int = 1) -> dict:
    return {
        "question": f"Sample multiple choice question {idx}?",
        "question_type": "multiple_choice",
        "source_page": 3,
        "options": [
            f"Option A{idx}",
            f"Option B{idx}",
            f"Option C{idx}",
            f"Option D{idx}",
        ],
        "correct_option": 2,
    }


def test_valid_multiple_choice_json():
    mcqs = [_valid_mcq(i) for i in range(5)]
    assert generator.parse_questions(json.dumps(mcqs), {3}) == mcqs


def test_short_answer_regression_exact_three_keys(questions):
    parsed = generator.parse_questions(json.dumps(questions), {3})
    assert len(parsed) == 5
    for item in parsed:
        assert set(item.keys()) == {"question", "question_type", "source_page"}


@pytest.mark.parametrize("option_count", [3, 5])
def test_mcq_rejects_wrong_option_count(option_count):
    mcqs = [_valid_mcq(i) for i in range(5)]
    mcqs[0]["options"] = [f"Choice {j}" for j in range(option_count)]
    with pytest.raises(generator.QuestionGenerationError):
        generator.parse_questions(json.dumps(mcqs), {3})


def test_mcq_rejects_case_insensitive_duplicate_options():
    mcqs = [_valid_mcq(i) for i in range(5)]
    mcqs[0]["options"] = ["Nabla", "nabla", "Laplacian", "Divergence"]
    with pytest.raises(generator.QuestionGenerationError):
        generator.parse_questions(json.dumps(mcqs), {3})


@pytest.mark.parametrize("bad_correct", [-1, 4, "1", True, None])
def test_mcq_rejects_invalid_correct_option(bad_correct):
    mcqs = [_valid_mcq(i) for i in range(5)]
    mcqs[0]["correct_option"] = bad_correct
    with pytest.raises(generator.QuestionGenerationError):
        generator.parse_questions(json.dumps(mcqs), {3})


def test_mcq_rejects_empty_or_whitespace_option():
    mcqs = [_valid_mcq(i) for i in range(5)]
    mcqs[0]["options"] = ["Valid A", "   ", "Valid C", "Valid D"]
    with pytest.raises(generator.QuestionGenerationError):
        generator.parse_questions(json.dumps(mcqs), {3})


def test_mcq_malformed_response_retried_once(client):
    bad_mcqs = [_valid_mcq(i) for i in range(5)]
    bad_mcqs[0]["options"] = ["Only one", "Two", "Three"]
    good_mcqs = [_valid_mcq(i) for i in range(5)]

    client.models.generate_content.side_effect = [
        SimpleNamespace(text=json.dumps(bad_mcqs)),
        SimpleNamespace(text=json.dumps(good_mcqs)),
    ]
    result = generator.generate_questions([{"page": 3, "text": "Notes"}])
    assert result == good_mcqs
    assert client.models.generate_content.call_count == 2
