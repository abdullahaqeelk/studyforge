import os
import tempfile
import streamlit as st

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
uploaded_file = st.file_uploader("Upload a course PDF to generate practice questions", type=["pdf"])

if uploaded_file is not None:
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
                questions = generate_from_pdf(tmp_path)
        except StudyForgeError as exc:
            st.error(str(exc))
            questions = None
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

        # 2. Display Results
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
                    st.divider()

else:
    st.info("Please upload a PDF file to get started.")
