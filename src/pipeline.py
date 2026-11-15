"""
StudyForge — question generation pipeline (SF-8, SF-12).

Extraction reads the PDF into per-page text; SF-10/SF-11 cache its embeddings.
SF-4 generates questions and SF-12 checks them against retrieved passages,
regenerating once or retaining explicit warnings. Callers use this
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

from agents.grounding_validator import generate_validated_questions
from config import StudyForgeError
from extract import extract_pages
from vector_store import get_store


class PipelineError(StudyForgeError):
    """A pipeline stage failed. The message names which one."""


def generate_from_pdf(pdf_path: str) -> list[dict]:
    """Produce practice questions from a PDF in one call.

    Args:
        pdf_path: path to a .pdf file of course material.

    Returns:
        Five question dicts with question, question_type, source_page,
        grounded, grounding_score (0/1), source_evidence and grounding_warning.
        A warning is retained on unsupported items after the single retry.

    Raises:
        PipelineError: reading, evidence preparation, generation or validation
            failed. The message identifies the stage.
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
        store = get_store(pdf_path)
    except StudyForgeError as exc:
        raise PipelineError(f"Preparing source evidence failed. {exc}") from exc

    try:
        return generate_validated_questions(pages, store)
    except StudyForgeError as exc:
        raise PipelineError(f"Generating questions failed. {exc}") from exc
