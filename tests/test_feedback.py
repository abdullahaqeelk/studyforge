"""
Unit tests for src/agents/feedback.py (SF-16).

The model is stubbed throughout and SF-15 is not imported: every input comes
from tests/fixtures/grading.py, which is the executable form of
docs/grading-contract.md. The suite runs on a clean clone with no API key and
no network, and it will keep running unchanged when SF-15 merges.
"""

import json
from types import SimpleNamespace

import pytest

from agents import feedback
from agents.feedback import FeedbackError, explain_all, generate_feedback, parse_feedback
from fixtures import grading


def reply(text="You correctly identified that it is a difference between two "
               "tabulated values. You did not say that the difference is taken "
               "with the preceding value.", pages=(4,)):
    return json.dumps({"feedback": text, "cited_pages": list(pages)})


class StubClient:
    """Returns a queued response per call, so retry behaviour can be observed."""

    def __init__(self, *responses, raises=None):
        self._responses = list(responses)
        self._raises = raises
        self.calls = 0
        self.closed = False
        self.last_config = None
        self.last_contents = None
        outer = self

        class Models:
            def generate_content(self, model, contents, config):
                outer.calls += 1
                outer.last_config = config
                outer.last_contents = contents
                if outer._raises:
                    raise outer._raises
                return SimpleNamespace(text=outer._responses.pop(0))

        self.models = Models()

    def close(self):
        self.closed = True


@pytest.fixture
def stub(monkeypatch):
    def install(*responses, raises=None):
        client = StubClient(*responses, raises=raises)
        monkeypatch.setattr(feedback, "get_client", lambda: client)
        return client
    return install


# --------------------------------------------------------------------------
# The ordinary case
# --------------------------------------------------------------------------

def test_feedback_is_added_to_the_grading_result(stub):
    stub(reply())
    result = generate_feedback(grading.partially_correct())
    assert result["feedback"].startswith("You correctly identified")
    assert result["cited_pages"] == [4]


def test_the_grading_result_is_carried_through_untouched(stub):
    """A caller holds one object per answer: score, points and explanation together."""
    stub(reply())
    original = grading.partially_correct()
    result = generate_feedback(original)
    assert result["score"] == original["score"]
    assert result["covered"] == original["covered"]
    assert result["missed"] == original["missed"]


def test_the_caller_s_result_is_not_mutated(stub):
    stub(reply())
    original = grading.partially_correct()
    generate_feedback(original)
    assert "feedback" not in original


def test_one_request_per_answer_not_one_per_missed_point(stub):
    """Free-tier quota is shared by four people; a point-by-point loop burns it."""
    client = stub(reply())
    result = grading.partially_correct()
    assert len(result["missed"]) == 2
    generate_feedback(result)
    assert client.calls == 1


def test_the_versioned_prompt_is_used_as_the_system_instruction(stub):
    client = stub(reply())
    generate_feedback(grading.partially_correct())
    assert "Feedback generation" in client.last_config["system_instruction"]


def test_the_model_is_not_shown_chunk_ids(stub):
    """It cites pages, not internal ids; sending them invites citing one back."""
    client = stub(reply())
    generate_feedback(grading.partially_correct())
    assert "chunk_id" not in client.last_contents


def test_a_full_marks_answer_is_confirmed_not_criticised(stub):
    stub(reply("You covered every point: it is the difference with the preceding "
               "tabulated value, written as nabla f(x) = f(x) - f(x - h).", pages=(4,)))
    result = generate_feedback(grading.fully_correct())
    assert result["missed"] == []
    assert result["feedback"]


def test_a_wholly_incorrect_answer_is_still_explained(stub):
    stub(reply("Your answer described integration. The material defines it as a "
               "difference between two tabulated values.", pages=(4,)))
    result = generate_feedback(grading.wholly_incorrect())
    assert result["score"] == 0
    assert result["feedback"]


# --------------------------------------------------------------------------
# The ungraded case — the decision that matters most
# --------------------------------------------------------------------------

def test_an_ungraded_answer_gets_no_feedback_and_no_api_call(stub):
    """Retrieval found nothing. Explaining it would describe material never found."""
    client = stub(reply())
    result = generate_feedback(grading.ungraded())
    assert result["feedback"] is None
    assert result["cited_pages"] == []
    assert client.calls == 0


def test_an_ungraded_answer_keeps_its_reason(stub):
    stub(reply())
    result = generate_feedback(grading.ungraded())
    assert "similarity floor" in result["reason"]


def test_an_empty_answer_gets_no_feedback_and_no_api_call(stub):
    client = stub(reply())
    result = generate_feedback(grading.empty_answer())
    assert result["feedback"] is None
    assert client.calls == 0


# --------------------------------------------------------------------------
# Citations — SF-16's half of the grounding contract
# --------------------------------------------------------------------------

def test_a_page_that_was_not_supplied_is_rejected(stub):
    """Mirrors SF-12's evidence check: an unsupplied citation is ungrounded."""
    stub(reply(pages=(9,)), reply(pages=(9,)))
    with pytest.raises(FeedbackError, match="was not among the pages supplied"):
        generate_feedback(grading.partially_correct())


def test_cited_pages_are_deduplicated_and_sorted():
    assert parse_feedback(reply(pages=(4, 4, 2)), {2, 4})["cited_pages"] == [2, 4]


def test_the_question_s_own_page_is_always_citable():
    """source_page is where the question came from, even if no point names it."""
    assert parse_feedback(reply(pages=(4,)), {4})["cited_pages"] == [4]


def test_feedback_citing_nothing_is_allowed():
    """Confirming a correct answer need not cite; the citation check is a ceiling."""
    assert parse_feedback(reply("Correct.", pages=()), {4})["cited_pages"] == []


@pytest.mark.parametrize("bad", ["", "   ", "not json", "[]", "null", '{"feedback": "x"}',
                                 '{"feedback": "x", "cited_pages": [4], "extra": 1}'])
def test_malformed_responses_are_rejected(bad):
    with pytest.raises(FeedbackError):
        parse_feedback(bad, {4})


@pytest.mark.parametrize("bad", ["", "   "])
def test_empty_feedback_text_is_rejected(bad):
    with pytest.raises(FeedbackError, match="empty feedback"):
        parse_feedback(json.dumps({"feedback": bad, "cited_pages": []}), {4})


def test_a_non_integer_page_is_rejected():
    with pytest.raises(FeedbackError, match="must be an integer"):
        parse_feedback(json.dumps({"feedback": "x", "cited_pages": ["4"]}), {4})


def test_whitespace_in_feedback_is_normalised():
    body = json.dumps({"feedback": "You  covered\n\nthe   definition.", "cited_pages": []})
    assert parse_feedback(body, {4})["feedback"] == "You covered the definition."


# --------------------------------------------------------------------------
# Retry — AID-3
# --------------------------------------------------------------------------

def test_malformed_output_is_retried_once_then_succeeds(stub):
    client = stub("not json", reply())
    result = generate_feedback(grading.partially_correct())
    assert client.calls == 2
    assert result["feedback"]


def test_two_bad_responses_fail_without_a_third_call(stub):
    client = stub("not json", "still not json")
    with pytest.raises(FeedbackError, match="after two attempts"):
        generate_feedback(grading.partially_correct())
    assert client.calls == 2


def test_the_retry_sends_the_same_payload(stub):
    """AID-3: rejected output is never fed back to the model as an instruction."""
    client = stub("not json", reply())
    generate_feedback(grading.partially_correct())
    assert "not json" not in client.last_contents


def test_provider_errors_are_typed_and_not_retried(stub):
    client = stub(raises=RuntimeError("429 quota exceeded"))
    with pytest.raises(feedback.StudyForgeError):
        generate_feedback(grading.partially_correct())
    assert client.calls == 1


def test_a_provider_failure_never_becomes_feedback(stub):
    stub(raises=RuntimeError("503 model is overloaded"))
    with pytest.raises(feedback.StudyForgeError):
        generate_feedback(grading.partially_correct())


def test_client_is_closed_even_when_the_provider_fails(stub):
    client = stub(raises=RuntimeError("401 api key rejected"))
    with pytest.raises(feedback.StudyForgeError):
        generate_feedback(grading.partially_correct())
    assert client.closed


# --------------------------------------------------------------------------
# Contract violations in the grading result
# --------------------------------------------------------------------------

def test_a_score_with_no_covered_points_is_rejected(stub):
    """Contract rule 4. There is nothing to point the student at."""
    client = stub(reply())
    with pytest.raises(FeedbackError, match="rule 4"):
        generate_feedback(grading.score_without_covered())
    assert client.calls == 0


def test_a_point_without_its_page_is_rejected(stub):
    """Contract rule 2. Recovering the page would mean retrieving again."""
    client = stub(reply())
    with pytest.raises(FeedbackError, match="rule 2"):
        generate_feedback(grading.missing_page_on_point())
    assert client.calls == 0


def test_an_ungraded_result_carrying_a_score_is_rejected(stub):
    bad = dict(grading.ungraded(), score=3)
    with pytest.raises(FeedbackError, match="absence of a grade"):
        generate_feedback(bad)


def test_an_ungraded_result_without_a_reason_is_rejected(stub):
    bad = dict(grading.ungraded(), reason="")
    with pytest.raises(FeedbackError, match="must say why"):
        generate_feedback(bad)


@pytest.mark.parametrize("bad", [None, "result", [], 42])
def test_a_non_result_is_rejected(bad):
    with pytest.raises(FeedbackError, match="grading result from SF-15"):
        generate_feedback(bad)


@pytest.mark.parametrize("field,value", [
    ("question", ""), ("question", None), ("source_page", 0), ("source_page", "4"),
    ("graded", "yes"), ("score", "2"), ("max_score", 0),
])
def test_malformed_fields_are_rejected(field, value):
    with pytest.raises(FeedbackError):
        generate_feedback(dict(grading.partially_correct(), **{field: value}))


def test_a_score_above_max_is_rejected():
    with pytest.raises(FeedbackError, match="between 0 and"):
        generate_feedback(dict(grading.partially_correct(), score=9))


def test_no_api_call_is_made_for_invalid_input(stub):
    client = stub(reply())
    with pytest.raises(FeedbackError):
        generate_feedback({})
    assert client.calls == 0


# --------------------------------------------------------------------------
# Batch
# --------------------------------------------------------------------------

def test_explain_all_keeps_the_list_aligned(stub):
    stub(reply(), reply())
    results = explain_all([grading.partially_correct(), grading.ungraded(),
                           grading.fully_correct()])
    assert len(results) == 3
    assert results[1]["feedback"] is None


def test_explain_all_spends_no_request_on_an_ungraded_answer(stub):
    client = stub(reply())
    explain_all([grading.ungraded(), grading.partially_correct()])
    assert client.calls == 1


@pytest.mark.parametrize("bad", [[], None, "results"])
def test_explain_all_rejects_bad_input(bad):
    with pytest.raises(FeedbackError, match="non-empty list"):
        explain_all(bad)
