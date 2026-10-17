"""
StudyForge — end-to-end question generation pipeline (SF-8).

Joins the two halves of the Sprint 1 vertical slice: extraction (SF-3) reads a
PDF into per-page text, generation (SF-4) turns that text into page-cited
practice questions. Callers — the Streamlit interface in particular — use this
module rather than calling the agents directly, so that the order of the stages
and the handling of their failures lives in one place.

Usage:

    from pipeline import generate_from_pdf

    questions = generate_from_pdf("samples/lecture-sample.pdf")
    print(questions[0])
    # {"question": "...", "question_type": "short_answer", "source_page": 12}

Streamlit note: st.file_uploader() yields an in-memory object, not a path.
Write it to a temporary file and pass that path in; extraction reads from disk
so that a large document is not held in memory twice.
"""

from __future__ import annotations

from agents.question_generator import generate_questions
from config import StudyForgeError
from extract import extract_pages


class PipelineError(StudyForgeError):
    """A pipeline stage failed. The message names which one."""


def generate_from_pdf(pdf_path: str) -> list[dict]:
    """Produce practice questions from a PDF in one call.

    Args:
        pdf_path: path to a .pdf file of course material.

    Returns:
        Five question dicts, each with question, question_type and
        source_page, where source_page is a real page number in the document.

    Raises:
        PipelineError: either stage failed. The message begins with the stage
            name, so the interface can show the user which half went wrong.
    """
    try:
        pages = extract_pages(pdf_path)
    except StudyForgeError as exc:
        # Re-raised rather than propagated so that the caller never has to know
        # which module an error came from to describe it to the user. Without
        # this, a password-protected PDF and an exhausted API quota arrive at
        # the interface as the same opaque StudyForgeError.
        raise PipelineError(f"Reading the document failed. {exc}") from exc

    try:
        return generate_questions(pages)
    except StudyForgeError as exc:
        raise PipelineError(f"Generating questions failed. {exc}") from exc
