"""
Unit tests for src/extract.py (SF-3).

Covers the three input classes named in the acceptance criteria: a valid PDF,
a PDF with no extractable text, and a file that is not a PDF at all.

The valid-PDF case uses a committed fixture so the test is deterministic and
runs on a clean clone. The other cases build their inputs in pytest's tmp_path,
since a file with no text layer and a file with the wrong extension are both
trivial to create and not worth committing.
"""

from pathlib import Path

import pytest
from pypdf import PdfWriter

from extract import ExtractionError, extract_pages, page_count

FIXTURE = Path(__file__).parent / "fixtures" / "sample.pdf"


# --------------------------------------------------------------------------
# Valid PDF
# --------------------------------------------------------------------------

def test_valid_pdf_returns_one_entry_per_page():
    pages = extract_pages(str(FIXTURE))
    assert len(pages) == page_count(str(FIXTURE))


def test_valid_pdf_page_numbers_are_one_based_and_contiguous():
    pages = extract_pages(str(FIXTURE))
    assert [p["page"] for p in pages] == list(range(1, len(pages) + 1))


def test_valid_pdf_extracts_text():
    pages = extract_pages(str(FIXTURE))
    assert any(p["text"] for p in pages), "fixture should contain a text layer"


def test_valid_pdf_entries_have_expected_shape():
    pages = extract_pages(str(FIXTURE))
    for page in pages:
        assert set(page) == {"page", "text"}
        assert isinstance(page["page"], int)
        assert isinstance(page["text"], str)


# --------------------------------------------------------------------------
# PDF with no extractable text
# --------------------------------------------------------------------------

def test_pdf_with_no_text_layer_raises(tmp_path):
    """A scan or image-only document must fail loudly, not return empty pages."""
    blank = tmp_path / "scanned.pdf"
    writer = PdfWriter()
    for _ in range(3):
        writer.add_blank_page(width=200, height=200)
    with open(blank, "wb") as handle:
        writer.write(handle)

    with pytest.raises(ExtractionError, match="No text could be extracted"):
        extract_pages(str(blank))


# --------------------------------------------------------------------------
# Not a PDF
# --------------------------------------------------------------------------

def test_non_pdf_extension_raises(tmp_path):
    notes = tmp_path / "notes.txt"
    notes.write_text("some notes")

    with pytest.raises(ExtractionError, match="is not a PDF"):
        extract_pages(str(notes))


def test_file_named_pdf_but_not_a_pdf_raises(tmp_path):
    """The extension check alone is not enough — the content must parse too."""
    fake = tmp_path / "fake.pdf"
    fake.write_bytes(b"this is not a pdf at all")

    with pytest.raises(ExtractionError, match="could not be read as a PDF"):
        extract_pages(str(fake))


def test_missing_file_raises(tmp_path):
    with pytest.raises(ExtractionError, match="No such file"):
        extract_pages(str(tmp_path / "absent.pdf"))


# --------------------------------------------------------------------------
# Error typing
# --------------------------------------------------------------------------

def test_extraction_error_is_a_studyforge_error(tmp_path):
    """Callers should be able to catch every project failure as one type."""
    from config import StudyForgeError

    notes = tmp_path / "notes.txt"
    notes.write_text("x")

    with pytest.raises(StudyForgeError):
        extract_pages(str(notes))
