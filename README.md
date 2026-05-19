# Census Chatbot

Document Q&A chatbot for census markdown/PDF-derived content. The backend uses FastAPI, the chat UI uses Chainlit, and answers are grounded in retrieved document snippets with page-level citations.

## What It Does

- Answers factual questions over census documents.
- Supports follow-up questions with chat memory.
- Returns citations with source, page, and snippet.
- Can generate simple artifacts such as tables and charts.

## Quick Start

### 1. Set Environment Variables

Create a `.env` file in the repo root with:

```env
GROQ_API_KEY=your_groq_key_here
```

### 2. Run the App

```bash
docker compose up --build
```

This starts:

- Backend on `http://localhost:8000`
- Chainlit UI on `http://localhost:8501`

### 3. Open the UI

Open the Chainlit URL and ask questions such as:

- `What is the literacy rate in Karnataka?`
- `What about bangalore literacy?`
- `Summarize the key findings in Karnataka.`
- `Build a table comparing Karnataka and Odisha literacy.`

## Local Data

The documents are read from:

- `/workspace/documents` in Docker
- `workspace/documents` when run locally outside Docker

## Project Structure

- `backend/app/api` - FastAPI routes
- `backend/app/services` - main RAG orchestration
- `backend/app/retrieval` - document loading, chunking, retrieval
- `backend/app/artifacts` - table/chart tool execution
- `backend/app/memory` - per-session chat memory
- `frontend/app.py` - Chainlit chat UI
- `workspace/documents` - markdown census documents

## How It Works

1. The backend loads the markdown documents at startup.
2. It chunks and indexes them with BM25.
3. On each question, it retrieves relevant chunks.
4. It builds citations from source/page/snippet.
5. If the request is an artifact request, it routes to a tool.
6. The tool returns a table or chart artifact.
7. The UI renders the response and any artifact inline.

## Requirements

- Python 3.11+
- Docker and Docker Compose
- A Groq API key

## Notes

- Chat memory is session-scoped in-process memory, so it resets when the backend restarts.
- Artifact generation is designed for demo use and depends on the quality of retrieved evidence.

