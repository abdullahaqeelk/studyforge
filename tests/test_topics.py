"""
Unit tests for src/topics.py (SF-13).

The model is stubbed throughout, so the suite still runs on a clean clone with
no API key and no network.
"""

import json
from types import SimpleNamespace

import pytest

import topics
from topics import (MAX_TOPICS_PER_CHUNK, TopicTaggingError, document_topics,
                    parse_topics, tag_chunks)


def chunks(*texts):
    return [{"chunk_id": i, "page": 1, "text": t} for i, t in enumerate(texts)]


def reply(mapping):
    return json.dumps([{"chunk_id": k, "topics": v} for k, v in mapping.items()])


class StubClient:
    """Returns a queued response per call, so retry behaviour can be observed."""

    def __init__(self, *responses, raises=None):
        self._responses = list(responses)
        self._raises = raises
        self.calls = 0
        self.closed = False
        self.last_config = None
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
        monkeypatch.setattr(topics, "get_client", lambda: client)
        return client
    return install


# --------------------------------------------------------------------------
# Labelling
# --------------------------------------------------------------------------

def test_every_chunk_receives_its_labels(stub):
    stub(reply({0: ["Interpolation"], 1: ["Backward Differences"]}))
    result = tag_chunks(chunks("forward text", "backward text"))
    assert result[0]["topics"] == ["Interpolation"]
    assert result[1]["topics"] == ["Backward Differences"]


def test_labels_live_on_the_chunk_so_a_store_cannot_separate_them(stub):
    """SF-11 persists chunks; topics ride along rather than sitting beside them."""
    stub(reply({0: ["Interpolation"]}))
    chunk = tag_chunks(chunks("text"))[0]
    assert set(chunk) == {"chunk_id", "page", "text", "topics"}


def test_one_request_for_the_whole_document(stub):
    client = stub(reply({0: ["A"], 1: ["B"], 2: ["C"]}))
    tag_chunks(chunks("one", "two", "three"))
    assert client.calls == 1


def test_the_versioned_prompt_is_used_as_the_system_instruction(stub):
    client = stub(reply({0: ["A"]}))
    tag_chunks(chunks("text"))
    assert "Topic tagging" in client.last_config["system_instruction"]


def test_blank_chunks_are_labelled_empty_not_dropped(stub):
    """The caller's list must stay aligned with the chunks it passed in."""
    stub(reply({0: ["Interpolation"], 2: ["Differences"]}))
    result = tag_chunks(chunks("text one", "   ", "text three"))
    assert len(result) == 3
    assert result[1]["topics"] == []


def test_client_is_closed_even_when_the_provider_fails(stub):
    client = stub(raises=RuntimeError("503 model is overloaded"))
    with pytest.raises(topics.StudyForgeError):
        tag_chunks(chunks("text"))
    assert client.closed


# --------------------------------------------------------------------------
# Response validation
# --------------------------------------------------------------------------

def test_a_label_for_a_chunk_never_sent_is_rejected():
    """Mirrors SF-4's source_page check: an ungrounded label is still ungrounded."""
    with pytest.raises(TopicTaggingError, match="not supplied"):
        parse_topics(reply({0: ["A"], 99: ["B"]}), {0})


def test_an_unlabelled_chunk_is_rejected():
    with pytest.raises(TopicTaggingError, match="unlabelled"):
        parse_topics(reply({0: ["A"]}), {0, 1})


def test_duplicate_chunk_ids_are_rejected():
    body = json.dumps([{"chunk_id": 0, "topics": ["A"]},
                       {"chunk_id": 0, "topics": ["B"]}])
    with pytest.raises(TopicTaggingError, match="twice"):
        parse_topics(body, {0})


def test_too_many_topics_on_one_chunk_is_rejected():
    many = [f"Topic {i}" for i in range(MAX_TOPICS_PER_CHUNK + 1)]
    with pytest.raises(TopicTaggingError, match="the limit is"):
        parse_topics(reply({0: many}), {0})


@pytest.mark.parametrize("bad", ["", "   ", "not json", "{}", "null", "[1, 2]"])
def test_malformed_responses_are_rejected(bad):
    with pytest.raises(TopicTaggingError):
        parse_topics(bad, {0})


def test_empty_topic_list_is_rejected():
    with pytest.raises(TopicTaggingError, match="no topics"):
        parse_topics(reply({0: []}), {0})


def test_blank_label_is_rejected():
    with pytest.raises(TopicTaggingError, match="empty topic"):
        parse_topics(reply({0: ["  "]}), {0})


def test_whitespace_in_labels_is_normalised():
    assert parse_topics(reply({0: ["  Newton   Interpolation "]}), {0}) == {
        0: ["Newton Interpolation"]}


def test_case_insensitive_duplicates_within_a_chunk_are_collapsed():
    result = parse_topics(reply({0: ["Interpolation", "INTERPOLATION"]}), {0})
    assert result == {0: ["Interpolation"]}


# --------------------------------------------------------------------------
# Retry — AID-3
# --------------------------------------------------------------------------

def test_malformed_output_is_retried_once_then_succeeds(stub):
    client = stub("not json", reply({0: ["Interpolation"]}))
    result = tag_chunks(chunks("text"))
    assert client.calls == 2
    assert result[0]["topics"] == ["Interpolation"]


def test_two_bad_responses_fail_without_a_third_call(stub):
    client = stub("not json", "still not json")
    with pytest.raises(TopicTaggingError, match="after two attempts"):
        tag_chunks(chunks("text"))
    assert client.calls == 2


def test_provider_errors_are_typed_and_not_retried(stub):
    client = stub(raises=RuntimeError("429 quota exceeded"))
    with pytest.raises(topics.StudyForgeError):
        tag_chunks(chunks("text"))
    assert client.calls == 1


# --------------------------------------------------------------------------
# Bad input
# --------------------------------------------------------------------------

@pytest.mark.parametrize("bad", [[], None, "chunks", [{"chunk_id": 0}], [{"text": "x"}]])
def test_malformed_chunks_raise(bad):
    with pytest.raises(TopicTaggingError):
        tag_chunks(bad)


def test_duplicate_chunk_ids_in_input_raise():
    with pytest.raises(TopicTaggingError, match="unique"):
        tag_chunks([{"chunk_id": 0, "text": "a"}, {"chunk_id": 0, "text": "b"}])


def test_chunks_with_no_text_raise():
    with pytest.raises(TopicTaggingError, match="no text"):
        tag_chunks(chunks("", "   "))


def test_no_api_call_is_made_for_invalid_input(stub):
    client = stub(reply({0: ["A"]}))
    with pytest.raises(TopicTaggingError):
        tag_chunks([])
    assert client.calls == 0


# --------------------------------------------------------------------------
# document_topics
# --------------------------------------------------------------------------

def test_document_topics_are_distinct_and_in_order_of_appearance(stub):
    stub(reply({0: ["Interpolation", "Operators"],
                1: ["Operators"],
                2: ["Backward Differences"]}))
    result = tag_chunks(chunks("a", "b", "c"))
    assert document_topics(result) == [
        "Interpolation", "Operators", "Backward Differences"]


def test_document_topics_dedupes_case_insensitively(stub):
    stub(reply({0: ["Interpolation"], 1: ["INTERPOLATION"]}))
    assert document_topics(tag_chunks(chunks("a", "b"))) == ["Interpolation"]


def test_document_topics_on_untagged_chunks_raises():
    with pytest.raises(TopicTaggingError, match="not been tagged"):
        document_topics(chunks("a", "b"))


# --------------------------------------------------------------------------
# Interface entry point
# --------------------------------------------------------------------------

def test_topics_for_pdf_reads_a_document_end_to_end(stub, monkeypatch):
    """The path the Streamlit interface takes: extract, chunk, tag, list."""
    from pathlib import Path

    fixture = Path(__file__).parent / "fixtures" / "sample.pdf"

    captured = {}

    def fake_tag(chunks):
        captured["count"] = len(chunks)
        for chunk in chunks:
            chunk["topics"] = ["Computer Networks"]
        return chunks

    monkeypatch.setattr(topics, "tag_chunks", fake_tag)
    assert topics.topics_for_pdf(str(fixture)) == ["Computer Networks"]
    assert captured["count"] > 0


def test_topics_for_pdf_does_not_embed(stub, monkeypatch):
    """Embedding here would spend quota on vectors the topic list never uses."""
    import chunking

    def fail(chunks):
        raise AssertionError("topics_for_pdf must not embed")

    monkeypatch.setattr(chunking, "embed_chunks", fail)
    monkeypatch.setattr(topics, "tag_chunks",
                        lambda cs: [dict(c, topics=["T"]) for c in cs])

    from pathlib import Path
    fixture = Path(__file__).parent / "fixtures" / "sample.pdf"
    assert topics.topics_for_pdf(str(fixture)) == ["T"]
