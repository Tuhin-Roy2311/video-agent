# Video/Meeting Analyzer

A RAG-powered tool that takes a YouTube URL or a local audio/video file and generates a transcript, summary, action items, key decisions, and open questions — plus a chat interface to ask questions about the content.

## Features

- Accepts YouTube URLs or local audio/video files
- Transcribes audio (English/Hinglish)
- Generates a title and summary
- Extracts action items, key decisions, and open questions
- Chat with the transcript via a RAG pipeline
- Available as a CLI (`main.py`) or a Streamlit web UI (`streamlit_app.py`)

## Setup

1. Clone the repo and install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Install [ffmpeg](https://ffmpeg.org/download.html) and make sure it's on your PATH (or set `FFMPEG_BIN` in `.env` to its `bin` folder).

3. Create a `.env` file in the project root with your API keys, e.g.:
   ```
   OPENAI_API_KEY=your_key_here
   ```

## Usage

**CLI:**
```bash
python main.py
```

**Streamlit UI:**
```bash
streamlit run streamlit_app.py
```

## Project Structure

```
core/           # transcription, summarization, extraction, RAG engine
utils/          # audio processing (download/convert/chunk)
main.py         # CLI entry point
streamlit_app.py / app.py   # Streamlit UI
requirements.txt
```

## Notes

- `downloads/` and `vector_db/` are generated at runtime and are gitignored.
- `.env` holds secrets and is gitignored — never commit it.