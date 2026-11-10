"""
Unit tests for src/chunking.py (SF-10).

The provider is stubbed throughout, so the suite still runs on a clean clone
with no API key and no network. The live path stays covered by SF-7's smoke
test.
"""

from pathlib import Path
from types import SimpleNamespace

import pytest

import chunking
from chunking import ChunkingError, chunk_pages, embed_chunks
from config import ConfigurationError, QuotaExceededError, StudyForgeError

FIXTURE = Path(__file__).parent / "fixtures" / "sample.pdf"


def pages(*texts):
    return [{"page": i, "text": t} for i, t in enumerate(texts, start=1)]


# --------------------------------------------------------------------------
# Chunk boundaries
# --------------------------------------------------------------------------

def test_short_page_becomes_one_chunk():
    result = chunk_pages(pages("A short page."))
    assert len(result) == 1
    assert result[0]["text"] == "A short page."


def test_long_page_is_split(monkeypatch):
    monkeypatch.setenv("CHUNK_SIZE", "100")
    monkeypatch.setenv("CHUNK_OVERLAP", "20")
    result = chunk_pages(pages("word " * 200))
    assert len(result) > 1
    assert all(len(c["text"]) <= 100 for c in result)


def test_consecutive_chunks_overlap(monkeypatch):
    """Overlap exists so a concept split across a boundary survives in one piece."""
    monkeypatch.setenv("CHUNK_SIZE", "100")
    monkeypatch.setenv("CHUNK_OVERLAP", "30")
    result = chunk_pages(pages("alpha beta gamma delta epsilon zeta " * 20))

    first_tail = result[0]["text"][-20:]
    assert first_tail.split()[-1] in result[1]["text"]


def test_chunks_do_not_end_mid_word(monkeypatch):
    monkeypatch.setenv("CHUNK_SIZE", "80")
    monkeypatch.setenv("CHUNK_OVERLAP", "10")
    source = "interpolation " * 40
    for chunk in chunk_pages(pages(source)):
        assert not chunk["text"].endswith("interpol")


# --------------------------------------------------------------------------
# Page-number preservation — the reason chunks never cross pages
# --------------------------------------------------------------------------

def test_every_chunk_carries_its_page_number():
    result = chunk_pages(pages("page one text", "page two text", "page three text"))
    assert [c["page"] for c in result] == [1, 2, 3]


def test_a_chunk_never_spans_two_pages(monkeypatch):
    """A chunk drawn from two pages could only cite one, and would be wrong half the time."""
    monkeypatch.setenv("CHUNK_SIZE", "10000")
    monkeypatch.setenv("CHUNK_OVERLAP", "0")
    result = chunk_pages(pages("first page body", "second page body"))

    assert len(result) == 2
    assert "second" not in result[0]["text"]
    assert "first" not in result[1]["text"]


def test_chunk_ids_are_contiguous_across_the_document(monkeypatch):
    monkeypatch.setenv("CHUNK_SIZE", "60")
    monkeypatch.setenv("CHUNK_OVERLAP", "10")
    result = chunk_pages(pages("alpha " * 40, "beta " * 40))
    assert [c["chunk_id"] for c in result] == list(range(len(result)))


def test_empty_pages_are_skipped_but_numbering_is_unaffected():
    """SF-3 keeps empty pages so list position matches page number; we drop them here."""
    result = chunk_pages(pages("text on one", "", "text on three"))
    assert [c["page"] for c in result] == [1, 3]


# --------------------------------------------------------------------------
# Bad input
# --------------------------------------------------------------------------

@pytest.mark.parametrize("bad", [[], None, "not pages", [{"page": 1}], [{"text": "x"}]])
def test_malformed_input_raises(bad):
    with pytest.raises(ChunkingError):
        chunk_pages(bad)


def test_document_with_no_text_raises():
    with pytest.raises(ChunkingError, match="no chunks"):
        chunk_pages(pages("", "   ", ""))


def test_overlap_not_smaller_than_size_raises(monkeypatch):
    """Otherwise the window never advances and chunking would loop forever."""
    monkeypatch.setenv("CHUNK_SIZE", "100")
    monkeypatch.setenv("CHUNK_OVERLAP", "100")
    with pytest.raises(ChunkingError, match="must be smaller"):
        chunk_pages(pages("word " * 200))


def test_non_numeric_chunk_size_is_a_configuration_error(monkeypatch):
    monkeypatch.setenv("CHUNK_SIZE", "big")
    with pytest.raises(ConfigurationError, match="whole number"):
        chunk_pages(pages("text"))


# --------------------------------------------------------------------------
# Embedding
# --------------------------------------------------------------------------

class StubClient:
    def __init__(self, vectors=None, raises=None):
        self._vectors = vectors
        self._raises = raises
        self.closed = False
        self.calls = []

        outer = self

        class Models:
            def embed_content(self, model, contents):
                outer.calls.append((model, contents))
                if outer._raises:
                    raise outer._raises
                n = outer._vectors if outer._vectors is not None else len(contents)
                return SimpleNamespace(
                    embeddings=[SimpleNamespace(values=[0.1, 0.2, 0.3])] * n
                )

        self.models = Models()

    def close(self):
        self.closed = True


def test_embedding_attaches_one_vector_per_chunk(monkeypatch):
    stub = StubClient()
    monkeypatch.setattr(chunking, "get_client", lambda: stub)

    result = embed_chunks(chunk_pages(pages("one", "two")))
    assert all(c["embedding"] == [0.1, 0.2, 0.3] for c in result)
    assert len(result) == 2


def test_embedding_sends_one_request_for_the_whole_document(monkeypatch):
    """Batching matters: one call per chunk would exhaust the free tier."""
    stub = StubClient()
    monkeypatch.setattr(chunking, "get_client", lambda: stub)

    embed_chunks(chunk_pages(pages("one", "two", "three")))
    assert len(stub.calls) == 1


def test_embedding_uses_the_configured_model(monkeypatch):
    stub = StubClient()
    monkeypatch.setattr(chunking, "get_client", lambda: stub)
    monkeypatch.setenv("EMBEDDING_MODEL", "some-other-model")

    embed_chunks(chunk_pages(pages("one")))
    assert stub.calls[0][0] == "some-other-model"


def test_client_is_closed_even_when_the_provider_fails(monkeypatch):
    stub = StubClient(raises=RuntimeError("429 quota exceeded"))
    monkeypatch.setattr(chunking, "get_client", lambda: stub)

    with pytest.raises(QuotaExceededError):
        embed_chunks(chunk_pages(pages("one")))
    assert stub.closed


def test_provider_errors_are_typed(monkeypatch):
    """A caller catches StudyForgeError, not a provider exception."""
    stub = StubClient(raises=RuntimeError("401 api key rejected"))
    monkeypatch.setattr(chunking, "get_client", lambda: stub)

    with pytest.raises(StudyForgeError):
        embed_chunks(chunk_pages(pages("one")))


def test_vector_count_mismatch_raises_rather_than_misaligning(monkeypatch):
    """Zipping a short vector list onto chunks would silently mislabel passages."""
    stub = StubClient(vectors=1)
    monkeypatch.setattr(chunking, "get_client", lambda: stub)

    with pytest.raises(ChunkingError, match="was not indexed"):
        embed_chunks(chunk_pages(pages("one", "two", "three")))


def test_embedding_empty_input_raises():
    with pytest.raises(ChunkingError):
        embed_chunks([])


# --------------------------------------------------------------------------
# End to end against the committed fixture
# --------------------------------------------------------------------------

def test_sample_document_chunks_and_embeds(monkeypatch):
    stub = StubClient()
    monkeypatch.setattr(chunking, "get_client", lambda: stub)

    result = chunking.index_document(str(FIXTURE))
    assert result
    assert all(set(c) == {"chunk_id", "page", "text", "embedding"} for c in result)
    assert all(c["page"] >= 1 for c in result)
