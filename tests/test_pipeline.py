"""
Unit tests for src/pipeline.py (SF-8).

The pipeline's own logic is the ordering of the two stages and the labelling of
their failures, so generation is stubbed throughout: these tests must run on a
clean clone with no API key and no network. The live path is covered by the
smoke test in SF-7.
"""

from pathlib import Path

import pytest

import pipeline
from config import QuotaExceededError
from extract import ExtractionError

FIXTURE = Path(__file__).parent / "fixtures" / "sample.pdf"

QUESTIONS = [
    {"question": f"Explain concept {i}.", "question_type": "short_answer",
     "source_page": 1}
    for i in range(5)
]


@pytest.fixture
def generated(monkeypatch):
    """Stub generation and record the pages it was handed."""
    captured = {}

    def fake_generate(pages):
        captured["pages"] = pages
        return QUESTIONS

    monkeypatch.setattr(pipeline, "generate_questions", fake_generate)
    return captured


# --------------------------------------------------------------------------
# Happy path
# --------------------------------------------------------------------------

def test_returns_questions_from_a_pdf(generated):
    assert pipeline.generate_from_pdf(str(FIXTURE)) == QUESTIONS


def test_extraction_output_is_passed_to_generation(generated):
    """The stages must be wired in order, with SF-3's shape reaching SF-4."""
    pipeline.generate_from_pdf(str(FIXTURE))

    pages = generated["pages"]
    assert pages, "generation should receive the extracted pages"
    assert all(set(page) == {"page", "text"} for page in pages)
    assert [page["page"] for page in pages] == list(range(1, len(pages) + 1))


# --------------------------------------------------------------------------
# Stage labelling — the reason this module exists
# --------------------------------------------------------------------------

def test_extraction_failure_names_the_reading_stage(tmp_path, generated):
    notes = tmp_path / "notes.txt"
    notes.write_text("not a pdf")

    with pytest.raises(pipeline.PipelineError, match="Reading the document failed"):
        pipeline.generate_from_pdf(str(notes))


def test_extraction_failure_keeps_the_original_cause(tmp_path, generated):
    """The underlying error is preserved, so detail is not lost in relabelling."""
    notes = tmp_path / "notes.txt"
    notes.write_text("not a pdf")

    with pytest.raises(pipeline.PipelineError) as info:
        pipeline.generate_from_pdf(str(notes))

    assert isinstance(info.value.__cause__, ExtractionError)
    assert "is not a PDF" in str(info.value)


def test_generation_failure_names_the_generating_stage(monkeypatch):
    def fail(pages):
        raise QuotaExceededError("The Google AI free-tier quota is exhausted.")

    monkeypatch.setattr(pipeline, "generate_questions", fail)

    with pytest.raises(pipeline.PipelineError, match="Generating questions failed"):
        pipeline.generate_from_pdf(str(FIXTURE))


def test_generation_is_not_called_when_extraction_fails(tmp_path, monkeypatch):
    """A bad upload must not spend an API call."""
    calls = []
    monkeypatch.setattr(pipeline, "generate_questions",
                        lambda pages: calls.append(pages) or QUESTIONS)

    notes = tmp_path / "notes.txt"
    notes.write_text("not a pdf")

    with pytest.raises(pipeline.PipelineError):
        pipeline.generate_from_pdf(str(notes))
    assert calls == []


def test_pipeline_error_is_a_studyforge_error(tmp_path, generated):
    """One catch in the interface covers every failure the pipeline can raise."""
    from config import StudyForgeError

    notes = tmp_path / "notes.txt"
    notes.write_text("x")

    with pytest.raises(StudyForgeError):
        pipeline.generate_from_pdf(str(notes))


# --------------------------------------------------------------------------
# describe_source
# --------------------------------------------------------------------------

def test_describe_source_counts_pages_and_characters():
    summary = pipeline.describe_source(str(FIXTURE))

    assert set(summary) == {"pages", "characters"}
    assert summary["pages"] > 0
    assert summary["characters"] > 0


def test_describe_source_makes_no_api_call(monkeypatch):
    def fail(pages):
        raise AssertionError("describe_source must not call the model")

    monkeypatch.setattr(pipeline, "generate_questions", fail)
    pipeline.describe_source(str(FIXTURE))


def test_describe_source_reports_a_bad_file(tmp_path):
    notes = tmp_path / "notes.txt"
    notes.write_text("not a pdf")

    with pytest.raises(pipeline.PipelineError, match="Reading the document failed"):
        pipeline.describe_source(str(notes))
