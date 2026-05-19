# Failure Analysis

This document records three known failure modes, their root causes, and the fixes or mitigations used in the project.

## 1. Wrong Document Chosen for Follow-up Questions

### Symptom

A follow-up question like "What about female literacy?" could drift to the wrong state or answer from an unrelated document.

### Root Cause

The initial retrieval path only used the current question text. It did not reliably preserve the state/topic from the previous turn.

### Fix

Added session-scoped memory that stores the recent chat history and active state. The backend now uses that memory to keep follow-up questions anchored to the correct state.

## 2. Table/Chart Requests Pulled Noisy Pages

### Symptom

Comparison requests such as "Build a table comparing Karnataka and Odisha literacy" sometimes retrieved contents pages or map pages instead of the actual literacy section.

### Root Cause

The artifact workflow originally used the same top-ranked retrieval strategy as ordinary Q&A, which was too noisy for structured outputs.

### Fix

The artifact path now:

- detects the mentioned states
- gathers evidence per state
- extracts literacy facts before calling the table tool
- passes structured facts into the tool

## 3. Backend 500 Errors Broke the UI

### Symptom

If the backend crashed, the Chainlit frontend tried to parse an empty response body as JSON and raised a second error.

### Root Cause

The frontend assumed every backend response would be valid JSON.

### Fix

The frontend now wraps the backend request in `try/except`, checks the HTTP status, and shows a readable backend error message if the request fails.

## Additional Known Limitations

- In-process memory resets when the backend restarts.
- Table/chart generation depends on the model returning usable structured output.
- BM25 retrieval is easy to inspect, but it can still rank noisy pages highly for some prompts.

