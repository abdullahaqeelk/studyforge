"""
Unit tests for src/vector_store.py (SF-11).

No live API call is made anywhere in this file: chunk embeddings are written
directly into the store fixtures, and query embedding is stubbed. Stores are
built under tmp_path so the repository is never touched.
"""

import json
from types import SimpleNamespace

import numpy as np
import pytest

import vector_store
from config import StudyForgeError
from vector_store import (VectorStoreError, document_id, get_store, load_store,
                          search, store_path)

# Three orthogonal-ish vectors so ranking is unambiguous without a real model.
NETWORKS = [1.0, 0.0, 0.0]
CALCULUS = [0.0, 1.0, 0.0]
HISTORY = [0.0, 0.0, 1.0]


def make_store(*rows):
    """rows: (chunk_id, page, text, embedding, topics?)"""
    chunks = []
    for row in rows:
        chunk_id, page, text, embedding = row[:4]
        chunk = {"chunk_id": chunk_id, "page": page, "text": text,
                 "embedding": embedding}
        if len(row) > 4:
            chunk["topics"] = row[4]
        chunks.append(chunk)
    return {"format": 2, "document_id": "test", "source_name": "test.pdf",
            "indexing": {"embedding_model": "gemini-embedding-001",
                         "chunk_size": 1200, "chunk_overlap": 200},
            "chunks": chunks}


@pytest.fixture
def stub_query(monkeypatch):
    def install(vector):
        monkeypatch.setattr(vector_store, "_embed_query", lambda text: vector)
    return install


@pytest.fixture
def pdf(tmp_path):
    f = tmp_path / "lecture.pdf"
    f.write_bytes(b"%PDF-1.4 fake contents for hashing")
    return f


# --------------------------------------------------------------------------
# Ranking
# --------------------------------------------------------------------------

def test_results_are_ordered_by_similarity(stub_query):
    stub_query([1.0, 0.2, 0.0])
    store = make_store(
        (0, 1, "history", HISTORY),
        (1, 2, "networks", NETWORKS),
        (2, 3, "calculus", CALCULUS),
    )
    hits = search(store, "networks question", min_similarity=0.0)
    assert [h["text"] for h in hits] == ["networks", "calculus", "history"]
    assert hits[0]["similarity"] > hits[1]["similarity"] > hits[2]["similarity"]


def test_k_limits_the_number_returned(stub_query):
    stub_query(NETWORKS)
    store = make_store(*[(i, i + 1, f"c{i}", NETWORKS) for i in range(10)])
    assert len(search(store, "q", k=3, min_similarity=0.0)) == 3


def test_k_defaults_to_configuration(stub_query, monkeypatch):
    monkeypatch.setenv("RETRIEVAL_K", "2")
    stub_query(NETWORKS)
    store = make_store(*[(i, i + 1, f"c{i}", NETWORKS) for i in range(10)])
    assert len(search(store, "q", min_similarity=0.0)) == 2


def test_k_below_one_is_rejected(stub_query):
    stub_query(NETWORKS)
    with pytest.raises(VectorStoreError, match="at least 1"):
        search(make_store((0, 1, "c", NETWORKS)), "q", k=0)


# --------------------------------------------------------------------------
# The empty result — the decision that matters most
# --------------------------------------------------------------------------

def test_an_unrelated_query_returns_nothing_not_the_least_bad_match(stub_query):
    """SF-12 cites what retrieval returns. A least-bad match becomes a wrong citation."""
    stub_query(HISTORY)
    store = make_store((0, 1, "networks", NETWORKS), (1, 2, "calculus", CALCULUS))
    assert search(store, "who won the war?", min_similarity=0.45) == []


def test_the_floor_comes_from_configuration(stub_query, monkeypatch):
    stub_query([0.8, 0.6, 0.0])
    store = make_store((0, 1, "networks", NETWORKS))

    monkeypatch.setenv("MIN_SIMILARITY", "0.9")
    assert search(store, "q") == []
    monkeypatch.setenv("MIN_SIMILARITY", "0.5")
    assert len(search(store, "q")) == 1


def test_partial_results_when_only_some_chunks_clear_the_floor(stub_query):
    stub_query(NETWORKS)
    store = make_store((0, 1, "networks", NETWORKS), (1, 2, "history", HISTORY))
    hits = search(store, "q", min_similarity=0.45)
    assert [h["text"] for h in hits] == ["networks"]


# --------------------------------------------------------------------------
# What a hit carries
# --------------------------------------------------------------------------

def test_every_hit_carries_its_page_number(stub_query):
    stub_query(NETWORKS)
    store = make_store((0, 7, "networks", NETWORKS))
    assert search(store, "q", min_similarity=0.0)[0]["page"] == 7


def test_hits_carry_topics_added_by_sf13(stub_query):
    """Any key on the chunk round-trips; SF-13's labels are not special-cased."""
    stub_query(NETWORKS)
    store = make_store((0, 1, "networks", NETWORKS, ["Routing"]))
    assert search(store, "q", min_similarity=0.0)[0]["topics"] == ["Routing"]


def test_raw_embeddings_are_not_returned_to_callers(stub_query):
    stub_query(NETWORKS)
    store = make_store((0, 1, "networks", NETWORKS))
    assert "embedding" not in search(store, "q", min_similarity=0.0)[0]


def test_the_stored_chunk_is_not_mutated_by_a_search(stub_query):
    stub_query(NETWORKS)
    store = make_store((0, 1, "networks", NETWORKS))
    search(store, "q", min_similarity=0.0)
    assert "similarity" not in store["chunks"][0]
    assert "embedding" in store["chunks"][0]


# --------------------------------------------------------------------------
# Bad input and bad stores
# --------------------------------------------------------------------------

@pytest.mark.parametrize("bad", ["", "   ", None, 42])
def test_empty_query_is_rejected(bad):
    with pytest.raises(VectorStoreError, match="non-empty query"):
        search(make_store((0, 1, "c", NETWORKS)), bad)


@pytest.mark.parametrize("bad", [{}, {"chunks": []}, None, "store"])
def test_unusable_store_is_rejected(bad):
    with pytest.raises(VectorStoreError, match="no chunks"):
        search(bad, "q")


def test_chunks_without_embeddings_are_rejected(stub_query):
    stub_query(NETWORKS)
    store = {"format": 1, "chunks": [{"chunk_id": 0, "page": 1, "text": "c"}]}
    with pytest.raises(VectorStoreError, match="missing usable embeddings"):
        search(store, "q")


def test_ragged_embeddings_are_rejected(stub_query):
    stub_query(NETWORKS)
    store = make_store((0, 1, "a", [1.0, 0.0, 0.0]), (1, 2, "b", [1.0, 0.0]))
    with pytest.raises(VectorStoreError, match="same length"):
        search(store, "q")


def test_dimension_mismatch_names_the_model_change(stub_query):
    """Vectors from two models are not comparable; say so rather than ranking noise."""
    stub_query([1.0, 0.0])
    store = make_store((0, 1, "c", [1.0, 0.0, 0.0]))
    with pytest.raises(VectorStoreError, match="embedding model has changed"):
        search(store, "q")


def test_zero_vectors_score_zero_rather_than_nan(stub_query):
    stub_query(NETWORKS)
    store = make_store((0, 1, "blank", [0.0, 0.0, 0.0]), (1, 2, "networks", NETWORKS))
    hits = search(store, "q", min_similarity=0.0)
    assert hits[0]["text"] == "networks"
    assert all(not np.isnan(h["similarity"]) for h in hits)


def test_provider_failure_on_the_query_is_typed(monkeypatch):
    class Boom:
        def __init__(self):
            self.closed = False
            self.models = SimpleNamespace(
                embed_content=lambda model, contents: (_ for _ in ()).throw(
                    RuntimeError("401 api key rejected")))

        def close(self):
            self.closed = True

    boom = Boom()
    monkeypatch.setattr(vector_store, "get_client", lambda: boom)
    with pytest.raises(StudyForgeError):
        search(make_store((0, 1, "c", NETWORKS)), "q")
    assert boom.closed


# --------------------------------------------------------------------------
# Persistence and rebuild
# --------------------------------------------------------------------------

def test_the_same_document_always_maps_to_the_same_store(pdf, tmp_path):
    copy = tmp_path / "renamed.pdf"
    copy.write_bytes(pdf.read_bytes())
    assert document_id(str(pdf)) == document_id(str(copy))


def test_an_edited_document_maps_to_a_different_store(pdf, tmp_path):
    edited = tmp_path / "edited.pdf"
    edited.write_bytes(pdf.read_bytes() + b" extra")
    assert document_id(str(pdf)) != document_id(str(edited))


def test_build_then_load_round_trips_every_chunk_key(pdf, tmp_path, monkeypatch):
    built = [{"chunk_id": 0, "page": 4, "text": "networks",
              "embedding": NETWORKS, "topics": ["Routing"]}]
    monkeypatch.setattr(vector_store, "STORE_DIRECTORY", tmp_path / "stores")
    monkeypatch.setitem(__import__("sys").modules, "chunking",
                        SimpleNamespace(index_document=lambda path: built))

    vector_store.build_store(str(pdf))
    loaded = load_store(str(pdf))
    assert loaded["chunks"][0]["topics"] == ["Routing"]
    assert loaded["chunks"][0]["page"] == 4


def test_get_store_builds_once_then_loads(pdf, tmp_path, monkeypatch):
    calls = []

    def fake_index(path):
        calls.append(path)
        return [{"chunk_id": 0, "page": 1, "text": "c", "embedding": NETWORKS}]

    monkeypatch.setattr(vector_store, "STORE_DIRECTORY", tmp_path / "stores")
    monkeypatch.setitem(__import__("sys").modules, "chunking",
                        SimpleNamespace(index_document=fake_index))

    get_store(str(pdf))
    get_store(str(pdf))
    assert len(calls) == 1, "the second call must load, not re-embed"


def test_rebuild_forces_a_fresh_build(pdf, tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(vector_store, "STORE_DIRECTORY", tmp_path / "stores")
    monkeypatch.setitem(__import__("sys").modules, "chunking",
                        SimpleNamespace(index_document=lambda p: (
                            calls.append(p),
                            [{"chunk_id": 0, "page": 1, "text": "c", "embedding": NETWORKS}])[1]))

    get_store(str(pdf))
    get_store(str(pdf), rebuild=True)
    assert len(calls) == 2


def test_a_store_from_another_embedding_model_is_discarded(pdf, tmp_path, monkeypatch):
    """Vectors from two models are not comparable; a stale store must not be served."""
    monkeypatch.setattr(vector_store, "STORE_DIRECTORY", tmp_path / "stores")
    target = store_path(str(pdf))
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps({
        "format": 2, "document_id": document_id(str(pdf)), "source_name": "x",
        "indexing": {"embedding_model": "some-older-model",
                     "chunk_size": 1200, "chunk_overlap": 200},
        "chunks": [{"chunk_id": 0, "page": 1, "text": "c", "embedding": NETWORKS}],
    }), encoding="utf-8")

    assert load_store(str(pdf)) is None


def test_a_corrupt_store_is_discarded_rather_than_raising(pdf, tmp_path, monkeypatch):
    monkeypatch.setattr(vector_store, "STORE_DIRECTORY", tmp_path / "stores")
    target = store_path(str(pdf))
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("{ not json", encoding="utf-8")
    assert load_store(str(pdf)) is None


def test_load_returns_none_when_no_store_exists(pdf, tmp_path, monkeypatch):
    monkeypatch.setattr(vector_store, "STORE_DIRECTORY", tmp_path / "stores")
    assert load_store(str(pdf)) is None


def test_unreadable_document_is_reported(tmp_path):
    with pytest.raises(VectorStoreError, match="Could not read"):
        document_id(str(tmp_path / "absent.pdf"))


# --------------------------------------------------------------------------
# Cache validity — regressions from the SF-11 review
# --------------------------------------------------------------------------

def _stub_indexer(monkeypatch, calls):
    """Record every index_document() call and return one usable chunk."""
    def index(path):
        calls.append(path)
        return [{"chunk_id": 0, "page": 1, "text": "c", "embedding": NETWORKS}]
    monkeypatch.setitem(__import__("sys").modules, "chunking",
                        SimpleNamespace(index_document=index))


@pytest.mark.parametrize("setting,first,second",
                         [("CHUNK_SIZE", "100", "200"),
                          ("CHUNK_OVERLAP", "20", "40")])
def test_changing_chunking_config_rebuilds_the_store(
        pdf, tmp_path, monkeypatch, setting, first, second):
    """Regression: the model is not the only thing that decides a store's contents.

    CHUNK_SIZE and CHUNK_OVERLAP decide where passages begin and end, so a
    store built under one setting and served under another returns passages
    that do not match what re-indexing would produce.
    """
    calls = []
    monkeypatch.setattr(vector_store, "STORE_DIRECTORY", tmp_path / "stores")
    _stub_indexer(monkeypatch, calls)

    monkeypatch.setenv(setting, first)
    get_store(str(pdf))
    monkeypatch.setenv(setting, second)
    get_store(str(pdf))

    assert len(calls) == 2, f"changing {setting} must re-index, not serve stale chunks"


def test_unchanged_config_still_loads_without_reindexing(pdf, tmp_path, monkeypatch):
    """The fingerprint must not make every call a rebuild."""
    calls = []
    monkeypatch.setattr(vector_store, "STORE_DIRECTORY", tmp_path / "stores")
    _stub_indexer(monkeypatch, calls)

    get_store(str(pdf))
    get_store(str(pdf))
    assert len(calls) == 1


@pytest.mark.parametrize("broken", [
    [{"page": 1, "text": "no embedding"}],
    [{"chunk_id": 0, "page": 1, "text": "empty vector", "embedding": []}],
    [{"chunk_id": 0, "page": 1, "text": "not numbers", "embedding": ["a", "b"]}],
    [{"chunk_id": 0, "page": 1, "text": "a", "embedding": [1.0, 0.0]},
     {"chunk_id": 1, "page": 2, "text": "b", "embedding": [1.0, 0.0, 0.0]}],
    [{"chunk_id": "zero", "page": 1, "text": "bad id", "embedding": NETWORKS}],
    [{"chunk_id": 0, "text": "no page", "embedding": NETWORKS}],
])
def test_a_structurally_broken_cache_is_discarded_on_load(
        pdf, tmp_path, monkeypatch, broken):
    """Regression: a cache that loads but cannot be searched is worse than none.

    Previously load_store() accepted any store whose chunks list was non-empty,
    so get_store() returned it forever and search() told the caller to rebuild
    on every call, with nothing in the system willing to do the rebuild.
    """
    monkeypatch.setattr(vector_store, "STORE_DIRECTORY", tmp_path / "stores")
    target = store_path(str(pdf))
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps({
        "format": 2, "document_id": document_id(str(pdf)), "source_name": "x",
        "indexing": {"embedding_model": vector_store.get_embedding_model(),
                     "chunk_size": 1200, "chunk_overlap": 200},
        "chunks": broken,
    }), encoding="utf-8")

    assert load_store(str(pdf)) is None


def test_get_store_repairs_a_broken_cache_by_reindexing(pdf, tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(vector_store, "STORE_DIRECTORY", tmp_path / "stores")
    _stub_indexer(monkeypatch, calls)

    target = store_path(str(pdf))
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps({
        "format": 2, "document_id": document_id(str(pdf)), "source_name": "x",
        "indexing": {"embedding_model": vector_store.get_embedding_model(),
                     "chunk_size": 1200, "chunk_overlap": 200},
        "chunks": [{"page": 1, "text": "broken"}],
    }), encoding="utf-8")

    store = get_store(str(pdf))
    assert calls, "a broken cache must be repaired, not returned"
    assert store["chunks"][0]["embedding"] == NETWORKS


# --------------------------------------------------------------------------
# Concurrency — regression from the SF-11 review
# --------------------------------------------------------------------------

def test_concurrent_builds_of_one_document_do_not_collide(pdf, tmp_path, monkeypatch):
    """Regression: both builds shared one .tmp path.

    The first replace() moved it away and the second raised FileNotFoundError.
    Each build now writes its own temporary file, and os.replace is atomic, so
    whichever finishes last simply wins.
    """
    import threading
    from concurrent.futures import ThreadPoolExecutor

    monkeypatch.setattr(vector_store, "STORE_DIRECTORY", tmp_path / "stores")
    barrier = threading.Barrier(2)

    def index(path):
        chunk = [{"chunk_id": 0, "page": 1, "text": "c", "embedding": NETWORKS}]
        barrier.wait(timeout=5)   # both builds reach the write together
        return chunk

    monkeypatch.setitem(__import__("sys").modules, "chunking",
                        SimpleNamespace(index_document=index))

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(vector_store.build_store, str(pdf)) for _ in range(2)]
        results = [f.result() for f in futures]

    assert all(r["chunks"] for r in results)
    assert load_store(str(pdf)) is not None


def test_a_failed_build_leaves_no_temporary_file_behind(pdf, tmp_path, monkeypatch):
    monkeypatch.setattr(vector_store, "STORE_DIRECTORY", tmp_path / "stores")

    def explode(path):
        return [{"chunk_id": 0, "page": 1, "text": "c",
                 "embedding": [object()]}]   # not JSON-serialisable

    monkeypatch.setitem(__import__("sys").modules, "chunking",
                        SimpleNamespace(index_document=explode))

    with pytest.raises(TypeError):
        vector_store.build_store(str(pdf))

    leftovers = list((tmp_path / "stores").glob("*.tmp"))
    assert leftovers == [], f"temporary files left behind: {leftovers}"


def test_a_failed_build_leaves_the_previous_store_intact(pdf, tmp_path, monkeypatch):
    monkeypatch.setattr(vector_store, "STORE_DIRECTORY", tmp_path / "stores")
    calls = []
    _stub_indexer(monkeypatch, calls)
    get_store(str(pdf))

    monkeypatch.setitem(__import__("sys").modules, "chunking",
                        SimpleNamespace(index_document=lambda p: [
                            {"chunk_id": 0, "page": 1, "text": "c",
                             "embedding": [object()]}]))
    with pytest.raises(TypeError):
        vector_store.build_store(str(pdf))

    assert load_store(str(pdf)) is not None, "the previous store must survive"
