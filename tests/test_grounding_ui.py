"""The actual Streamlit result view exposes failed checks and verified quotes."""

from io import BytesIO
from pathlib import Path

import pytest
import streamlit as st
from streamlit.testing.v1 import AppTest

import pipeline


@pytest.mark.parametrize("grounded", [False, True])
def test_app_displays_grounding_result(monkeypatch, grounded):
    upload = BytesIO(b"test upload")
    upload.name = "lecture.pdf"
    monkeypatch.setattr(st, "file_uploader", lambda *args, **kwargs: upload)
    monkeypatch.setattr(pipeline, "generate_from_pdf", lambda path: [{
        "question": "Does UDP guarantee delivery?", "question_type": "short_answer",
        "source_page": 3, "grounded": grounded,
        "grounding_warning": None if grounded else "Ungrounded: evidence missing.",
        "source_evidence": [{"page": 3, "chunk_id": 4,
                             "quote": "UDP does not guarantee delivery."}] if grounded else [],
    }])
    app = AppTest.from_file(str(Path(__file__).parents[1] / "src" / "app.py"))
    app.run()
    next(button for button in app.button if button.label == "Generate Questions").click()
    app.run()
    assert not app.exception
    if grounded:
        assert any("Source support checked" in caption.value for caption in app.caption)
        assert any("UDP does not guarantee delivery." in text.value for text in app.markdown)
        assert not app.warning
    else:
        assert app.warning[0].value == "Ungrounded: evidence missing."


def test_replacing_pdf_with_same_name_and_size_clears_previous_questions(monkeypatch):
    first_upload = BytesIO(b"PDF_CONTENT_AAAA")
    first_upload.name = "lecture.pdf"
    second_upload = BytesIO(b"PDF_CONTENT_BBBB")  # Same name and same 16-byte length
    second_upload.name = "lecture.pdf"

    current_upload = {"file": first_upload}
    monkeypatch.setattr(st, "file_uploader", lambda *args, **kwargs: current_upload["file"])
    monkeypatch.setattr(
        pipeline,
        "generate_from_pdf",
        lambda path: [
            {
                "question": "Old question from first PDF?",
                "question_type": "short_answer",
                "source_page": 1,
                "grounded": True,
                "grounding_warning": None,
                "source_evidence": [
                    {"page": 1, "chunk_id": 1, "quote": "First PDF text."}
                ],
            }
        ],
    )

    app = AppTest.from_file(str(Path(__file__).parents[1] / "src" / "app.py"))
    app.run()
    next(button for button in app.button if button.label == "Generate Questions").click()
    app.run()

    assert not app.exception
    assert any("Old question from first PDF?" in sub.value for sub in app.subheader)

    # Swap to a different PDF with the exact same filename and byte length
    current_upload["file"] = second_upload
    app.run()

    assert not app.exception
    assert not any("Old question from first PDF?" in sub.value for sub in app.subheader)