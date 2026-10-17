import streamlit as st

# Set page layout
st.set_page_config(page_title="StudyForge", page_icon="📚", layout="centered")

st.title(" StudyForge")
st.caption("Agentic Exam-Preparation System — NUST CoEME")

st.markdown("---")

# 1. Document Upload Section
st.header("1. Upload Course Material")
uploaded_file = st.file_uploader("Upload a course PDF to generate practice questions", type=["pdf"])

if uploaded_file is not None:
    st.success(f"File uploaded: **{uploaded_file.name}**")
    
    # Action Button
    if st.button("Generate Questions", type="primary"):
        with st.spinner("Analyzing document and generating questions..."):
            
            # TODO: Replace with live call to SF-8 pipeline once merged into main
            # Example payload contract matching SF-4 / docs/question-generation.md
            mock_questions = [
                {
                    "question": "Which tree traversal technique processes the nodes of a Binary Search Tree (BST) in ascending sorted order?",
                    "question_type": "multiple_choice",
                    "source_page": 1
                },
                {
                    "question": "What is the primary defense mechanism against AI hallucinations in StudyForge?",
                    "question_type": "short_answer",
                    "source_page": 2
                },
                {
                    "question": "Explain how the Definition of Ready (DoR) protects sprint velocity.",
                    "question_type": "free_text",
                    "source_page": 4
                }
            ]

        # 2. Display Results
        st.markdown("---")
        st.header("2. Practice Questions")

        for idx, q in enumerate(mock_questions, start=1):
            with st.container():
                # Display Question Type Badge and Source Page Citation
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.caption(f"**TYPE:** `{q['question_type'].upper()}`")
                with col2:
                    st.caption(f" **Source:** Page {q['source_page']}")

                # Render Question Text
                st.subheader(f"Q{idx}. {q['question']}")
                st.divider()

else:
    st.info("Please upload a PDF file to get started.")