import hashlib
import os
import tempfile
import streamlit as st

from answer_check import evaluate_answer
from config import StudyForgeError
from pipeline import generate_from_pdf
from topics import topics_for_pdf

# Set page layout
st.set_page_config(page_title="StudyForge", page_icon="📚", layout="centered")

st.title("📚 StudyForge")
st.caption("Agentic Exam-Preparation System — NUST CoEME")

st.markdown("---")

# 1. Document Upload Section
st.header("1. Upload Course Material")
uploaded_file = st.file_uploader(
    "Upload a course PDF to generate practice questions", type=["pdf"]
)

if uploaded_file is not None:
    content_digest = hashlib.sha256(uploaded_file.getbuffer()).hexdigest()
    upload_key = (getattr(uploaded_file, "name", None), content_digest)
    if st.session_state.get("uploaded_pdf_key") != upload_key:
        st.session_state["uploaded_pdf_key"] = upload_key
        st.session_state.pop("questions", None)

    st.success(f"File uploaded: **{uploaded_file.name}**")

    # SF-13: topics in this document. Kept as its own action so that a student
    # can see what a document covers without spending a generation call.
    if st.button("Identify Topics"):
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(uploaded_file.getbuffer())
            topic_path = tmp.name
        try:
            with st.spinner("Reading the document and identifying topics..."):
                found = topics_for_pdf(topic_path)
        except StudyForgeError as exc:
            st.error(str(exc))
            found = None
        finally:
            if os.path.exists(topic_path):
                os.unlink(topic_path)

        if found:
            st.subheader("Topics in this document")
            st.write(" \u00b7 ".join(f"`{topic}`" for topic in found))
            st.caption(f"{len(found)} topics identified.")

    # Action Button
    if st.button("Generate Questions", type="primary"):
        # Write Streamlit uploaded file to a temporary disk location for pipeline execution
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(uploaded_file.getbuffer())
            tmp_path = tmp.name

        try:
            with st.spinner("Analyzing document and generating questions..."):
                st.session_state["questions"] = generate_from_pdf(tmp_path)
                st.session_state["batch_id"] = st.session_state.get("batch_id", 0) + 1
        except StudyForgeError as exc:
            st.error(str(exc))
            st.session_state.pop("questions", None)
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    # 2. Display Results
    questions = st.session_state.get("questions")
    batch_id = st.session_state.get("batch_id", 0)
    if questions:
        st.markdown("---")
        st.header("2. Practice Questions")

        for idx, q in enumerate(questions, start=1):
            with st.container():
                # Display Question Type Badge and Source Page Citation
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.caption(f"**TYPE:** `{q['question_type'].upper()}`")
                with col2:
                    st.caption(f"📍 **Source:** Page {q['source_page']}")

                # Render Question Text
                st.subheader(f"Q{idx}. {q['question']}")

                is_ungrounded = (
                    bool(q.get("grounding_warning")) or q.get("grounded") is False
                )

                if q.get("question_type") == "multiple_choice":
                    options = q.get("options", [])
                    selected = st.radio(
                        "Choose an option:",
                        options=range(len(options)),
                        format_func=lambda i, opts=options: opts[i],
                        index=None,
                        key=f"mcq_choice_{batch_id}_{idx}",
                    )
                    if selected is not None:
                        if is_ungrounded:
                            st.info(
                                "Answer checking is withheld because this question or answer key failed source grounding."
                            )
                        else:
                            verdict = evaluate_answer(q, selected)
                            if verdict["is_correct"]:
                                st.success("Correct!")
                            else:
                                st.error(
                                    f"Incorrect. Correct answer: {options[verdict['correct_option']]}"
                                )

                if q.get("grounding_warning"):
                    st.warning(q["grounding_warning"])
                elif q.get("grounded"):
                    st.caption("Source support checked")
                    with st.expander("View supporting passages"):
                        for evidence in q["source_evidence"]:
                            st.write(evidence["quote"])
                            st.caption(f"Page {evidence['page']}")
                st.divider()

else:
    st.session_state.pop("uploaded_pdf_key", None)
    st.session_state.pop("questions", None)
    st.info("Please upload a PDF file to get started.")
