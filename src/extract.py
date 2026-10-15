"""
StudyForge — course material upload and text extraction (SF-3).

Reads an uploaded PDF and returns its text one page at a time, with page
numbers preserved. Downstream agents cite those page numbers on every
generated question, so the mapping between a page number and its text has to
stay exact: pages that extract to nothing are kept in the result with empty
text rather than dropped, otherwise list position would stop matching the
real page number.

Usage:

    from extract import extract_pages

    pages = extract_pages("samples/lecture-sample.pdf")
    print(pages[0])     # {"page": 1, "text": "Computer Networks (EC-330)..."}
"""

from __future__ import annotations

import os

from pypdf import PdfReader
from pypdf.errors import PdfReadError

from config import StudyForgeError


class ExtractionError(StudyForgeError):
    """The uploaded file could not be read as a PDF, or contained no text."""


def extract_pages(pdf_path: str) -> list[dict]:
    """Extract the text of every page in a PDF.

    Args:
        pdf_path: path to a .pdf file.

    Returns:
        A list of dicts, one per page, in document order:
        [{"page": 1, "text": "..."}, {"page": 2, "text": ""}, ...]
        Page numbers are 1-based. A page with no text layer is returned with
        an empty string rather than omitted.

    Raises:
        ExtractionError: the path does not exist, is not a .pdf, cannot be
            parsed as a PDF, or contains no extractable text on any page.
    """
    if not pdf_path.lower().endswith(".pdf"):
        raise ExtractionError(
            f"'{os.path.basename(pdf_path)}' is not a PDF. "
            "Upload course material as a .pdf file."
        )

    if not os.path.isfile(pdf_path):
        raise ExtractionError(f"No such file: {pdf_path}")

    try:
        reader = PdfReader(pdf_path)
    except (PdfReadError, OSError, ValueError) as exc:
        raise ExtractionError(
            f"'{os.path.basename(pdf_path)}' could not be read as a PDF. "
            "The file may be corrupt."
        ) from exc

    # Constructing the reader succeeds for an encrypted PDF; the failure only
    # surfaces when the page tree is touched. Check explicitly so the caller
    # gets a message naming the real problem rather than a decryption error.
    if reader.is_encrypted:
        raise ExtractionError(
            f"'{os.path.basename(pdf_path)}' is password-protected. "
            "Remove the password and upload the file again."
        )

    try:
        total_pages = len(reader.pages)
    except (PdfReadError, OSError, ValueError) as exc:
        raise ExtractionError(
            f"The page structure of '{os.path.basename(pdf_path)}' could not "
            "be read. The file may be corrupt."
        ) from exc

    if total_pages == 0:
        raise ExtractionError(
            f"'{os.path.basename(pdf_path)}' contains no pages."
        )

    pages: list[dict] = []
    for index, page in enumerate(reader.pages, start=1):
        try:
            text = page.extract_text() or ""
        except Exception:  # noqa: BLE001 - a bad page must not kill the document
            text = ""
        pages.append({"page": index, "text": text.strip()})

    if not any(p["text"] for p in pages):
        raise ExtractionError(
            f"No text could be extracted from '{os.path.basename(pdf_path)}'. "
            "The document is likely a scan or made of page images. "
            "StudyForge needs a PDF with a text layer."
        )

    return pages


def page_count(pdf_path: str) -> int:
    """Return the number of pages in a PDF without extracting its text."""
    if not os.path.isfile(pdf_path):
        raise ExtractionError(f"No such file: {pdf_path}")
    try:
        reader = PdfReader(pdf_path)
        if reader.is_encrypted:
            raise ExtractionError(
                f"'{os.path.basename(pdf_path)}' is password-protected."
            )
        return len(reader.pages)
    except ExtractionError:
        raise
    except (PdfReadError, OSError, ValueError) as exc:
        raise ExtractionError(
            f"'{os.path.basename(pdf_path)}' could not be read as a PDF."
        ) from exc
