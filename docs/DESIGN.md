# Design

## Overview

This system is a small agentic document Q&A chatbot for census reports. The design is intentionally modular so that retrieval, memory, tool execution, and UI rendering can be reasoned about independently.

## Architecture

### Backend

The backend is a FastAPI service that exposes a single chat endpoint. It:

- loads markdown documents at startup
- chunks them into retrievable passages
- retrieves relevant chunks with BM25
- maintains per-session chat memory
- builds citations from source/page/snippet
- routes chart and table requests to tools

### Frontend

The frontend is a Chainlit chat UI. It:

- creates a session id for each chat
- sends the session id with each backend request
- renders text answers
- renders charts inline
- renders tables as markdown
- displays a trace block for debugging

## Why This Architecture

### FastAPI for the backend

FastAPI is a good fit because the system needs a small API surface and clear request/response contracts. It also works cleanly with a separate UI process.

### Chainlit for the UI

Chainlit is useful for agentic chat because it can display conversational responses and inline artifacts without building a custom frontend from scratch.

### BM25 retrieval

The corpus is relatively small and the tasks are heavily lexical. BM25 is simple, fast, and easy to debug. It also avoids the overhead of embedding infrastructure for this take-home.

### Session-scoped memory

Memory is scoped by session id so follow-up questions stay anchored to the current conversation while avoiding cross-user interference.

### Tool-based artifacts

Table and chart generation are modeled as tools. This makes the system closer to an agentic workflow:

1. classify the request
2. gather evidence
3. call a tool
4. return the artifact

### Traceability

The backend returns a trace object containing:

- retrieved chunks
- citations
- tool call
- tool result

This makes it easier to defend the system in review and understand what happened for each turn.

## Citations

Every answer is grounded in a citation list built from the retrieved chunks. Each citation includes:

- source filename
- page number
- snippet

This is the primary evidence payload that the LLM receives and the UI shows.

## Artifact Workflow

Artifact requests use a slightly different path than normal Q&A.

### Table requests

For comparison tables, the service:

- detects the mentioned states
- retrieves evidence for each state
- extracts literacy facts from the chunks
- passes structured facts to the table tool
- renders a markdown table from the extracted facts

### Chart requests

Chart requests:

- retrieve evidence
- ask the LLM for chart spec JSON
- execute a Python plotting script
- return the chart image back to the UI

## Memory

Memory is stored in-process by session id. It stores:

- recent conversation history
- active state/topic

This keeps follow-up questions coherent, but it is not persistent across restarts.

## Tradeoffs

- BM25 is easy to debug, but it is less semantic than embeddings.
- In-process memory is simple, but not durable.
- Tool execution is flexible, but depends on the quality of retrieved evidence and the model's structured output.

## What I Skipped

I kept the implementation lightweight and skipped persistent storage, a full agent framework, and a separate tracing backend. With more time, those would be the next improvements.

## Simplifications

Some parts of the service are intentionally heuristic:

- state inference uses the current question and recent history
- artifact retrieval filters out obvious contents-like pages
- literacy fact extraction uses regex over retrieved snippets

These choices keep the system easy to debug and fast to set up, but they are the first areas I would replace with stronger structured extraction or a more formal agent planner.
