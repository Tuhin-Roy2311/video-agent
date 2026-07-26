"""
Streamlit UI for the CLI video/meeting analyzer.

Run with:
    streamlit run streamlit_app.py

Expects the same project structure as your CLI script (utils/, core/ packages
importable from this file's directory).
"""

import os
import tempfile

import streamlit as st
from dotenv import load_dotenv

load_dotenv()

for _proxy_key in (
    "HTTP_PROXY",
    "HTTPS_PROXY",
    "ALL_PROXY",
    "http_proxy",
    "https_proxy",
    "all_proxy",
):
    os.environ.pop(_proxy_key, None)
os.environ["NO_PROXY"] = "*"
os.environ["no_proxy"] = "*"

from utils.audio_processor import process_input
from core.transcriber import transcribe_all
from core.summarizer import summarize, generate_title
from core.extractor import extract_action_items, extract_key_decisions, extract_questions
from core.rag_engine import build_rag_chain, ask_question

load_dotenv()

st.set_page_config(page_title="Video/Meeting Analyzer", page_icon="🎥", layout="wide")


# --------------------------------------------------------------------------
# Pipeline (same logic as run_pipeline in your CLI script)
# --------------------------------------------------------------------------
def run_pipeline(source: str, language: str = "english") -> dict:
    chunks = process_input(source)
    transcript = transcribe_all(chunks, language=language)
    title = generate_title(transcript)
    summary = summarize(transcript)
    action_items = extract_action_items(transcript)
    decisions = extract_key_decisions(transcript)
    questions = extract_questions(transcript)
    rag_chain = build_rag_chain(transcript)

    return {
        "title": title,
        "transcript": transcript,
        "summary": summary,
        "action_items": action_items,
        "decisions": decisions,
        "questions": questions,
        "rag_chain": rag_chain,
    }


# --------------------------------------------------------------------------
# Session state
# --------------------------------------------------------------------------
if "result" not in st.session_state:
    st.session_state.result = None
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []  # list of (role, text)


# --------------------------------------------------------------------------
# Sidebar — input controls
# --------------------------------------------------------------------------
with st.sidebar:
    st.header("🎥 Analyze a video/meeting")

    input_mode = st.radio("Source type", ["YouTube URL", "Upload a file"])

    source = None
    tmp_path = None

    if input_mode == "YouTube URL":
        url = st.text_input("YouTube URL", placeholder="https://youtube.com/watch?v=...")
        if url:
            source = url
    else:
        uploaded = st.file_uploader(
            "Upload audio/video file", type=["mp4", "mp3", "wav", "m4a", "mov", "mkv"]
        )
        if uploaded is not None:
            suffix = os.path.splitext(uploaded.name)[1]
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
            tmp.write(uploaded.read())
            tmp.close()
            tmp_path = tmp.name
            source = tmp_path

    language = st.selectbox("Language", ["english", "hinglish"])

    analyze_clicked = st.button("🚀 Analyze", type="primary", use_container_width=True, disabled=not source)

    if st.session_state.result is not None:
        if st.button("🔄 Start over", use_container_width=True):
            st.session_state.result = None
            st.session_state.chat_history = []
            st.rerun()

if analyze_clicked and source:
    with st.spinner("Processing input, transcribing, and running analysis... this can take a while"):
        try:
            st.session_state.result = run_pipeline(source, language=language)
            st.session_state.chat_history = []
        except Exception as e:
            st.error(f"Something went wrong while processing: {e}")
        finally:
            if tmp_path and os.path.exists(tmp_path):
                os.remove(tmp_path)


# --------------------------------------------------------------------------
# Main area
# --------------------------------------------------------------------------
result = st.session_state.result

if result is None:
    st.title("🎥 Video / Meeting Analyzer")
    st.write(
        "Paste a YouTube URL or upload a local audio/video file in the sidebar, "
        "then click **Analyze** to get a transcript, summary, action items, "
        "key decisions, open questions — and a chat interface to ask questions "
        "about the content."
    )
else:
    st.title(f"📌 {result['title']}")

    tab_summary, tab_actions, tab_decisions, tab_questions, tab_transcript, tab_chat = st.tabs(
        ["📋 Summary", "✅ Action Items", "🔑 Key Decisions", "❓ Open Questions", "📝 Transcript", "💬 Chat"]
    )

    with tab_summary:
        st.markdown(result["summary"])

    with tab_actions:
        st.markdown(result["action_items"])

    with tab_decisions:
        st.markdown(result["decisions"])

    with tab_questions:
        st.markdown(result["questions"])

    with tab_transcript:
        st.text_area("Full transcript", result["transcript"], height=500)

    with tab_chat:
        st.caption("Ask questions about the content — answered using RAG over the transcript.")

        for role, text in st.session_state.chat_history:
            with st.chat_message(role):
                st.markdown(text)

        question = st.chat_input("Ask a question about this video/meeting...")
        if question:
            st.session_state.chat_history.append(("user", question))
            with st.chat_message("user"):
                st.markdown(question)

            with st.chat_message("assistant"):
                with st.spinner("Thinking..."):
                    try:
                        answer = ask_question(result["rag_chain"], question)
                    except Exception as e:
                        answer = f"Error while answering: {e}"
                    st.markdown(answer)
            st.session_state.chat_history.append(("assistant", answer))
