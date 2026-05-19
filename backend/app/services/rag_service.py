from app.retrieval.loader import load_markdown_documents
from app.retrieval.chunker import chunk_documents
from app.retrieval.vectorstore import add_chunks
from app.retrieval.retriever import retrieve
from app.artifacts.engine import (
    ToolCall,
    classify_request,
    run_tool,
)

from app.llm.groq_client import generate_answer
import re

from app.memory.store import (
    add_message,
    get_history,
    get_active_state,
    set_active_state
)


# Load documents once at startup
documents = load_markdown_documents()

# Chunk documents
chunks = chunk_documents(documents)

# Add chunks to vector store
add_chunks(chunks)


STATE_ALIASES = {
    "odisha": ["odisha", "orissa"],
    "karnataka": ["karnataka"],
    "madhya pradesh": ["madhya pradesh", "mp", "m p"],
}


def state_aliases(state):
    return STATE_ALIASES.get(state.lower(), [state.lower()])


def infer_state(question, history):
    question_text = question.lower()
    history_text = " ".join(message["content"] for message in history).lower()

    # Prefer an explicit state mentioned in the current question over older chat turns.
    for doc in documents:
        state = doc["state"]
        if any(alias in question_text for alias in state_aliases(state)):
            return state

    for doc in documents:
        state = doc["state"]
        if any(alias in history_text for alias in state_aliases(state)):
            return state

    return None


def mentioned_states(question):
    q = question.lower()
    matches = []
    for doc in documents:
        state = doc["state"]
        if any(alias in q for alias in state_aliases(state)) and state not in matches:
            matches.append(state)
    return matches


def is_artifact_relevant_chunk(chunk):
    text = chunk["text"].lower()
    if "contents" in text and "page" in text and "literacy" not in text:
        return False

    numeric_signals = [
        "%",
        "per cent",
        "literacy",
        "population",
        "male",
        "female",
        "urban",
        "rural"
    ]
    return any(signal in text for signal in numeric_signals)


def gather_artifact_chunks(question, preferred_state=None, limit=6):
    candidates = retrieve(question, top_k=20, preferred_state=preferred_state)
    filtered = [chunk for chunk in candidates if is_artifact_relevant_chunk(chunk)]
    if not filtered:
        filtered = candidates
    return filtered[:limit]


def build_state_evidence(question, limit_per_state=3):
    states = mentioned_states(question)
    if not states:
        return gather_artifact_chunks(question, preferred_state=get_active_state("default"), limit=6)

    combined = []
    seen = set()
    for state in states:
        chunks = gather_artifact_chunks(question, preferred_state=state, limit=limit_per_state)
        for chunk in chunks:
            key = (chunk["source"], chunk.get("page"), chunk["text"][:120])
            if key not in seen:
                seen.add(key)
                combined.append(chunk)
    return combined[: max(6, len(states) * limit_per_state)]


def build_citations(retrieved_chunks):
    evidence_blocks = []
    citations = []

    for idx, chunk in enumerate(retrieved_chunks, start=1):
        citation = {
            "id": idx,
            "source": chunk["source"],
            "page": chunk.get("page"),
            "snippet": chunk["text"][:300].replace("\n", " ").strip()
        }
        citations.append(citation)
        evidence_blocks.append(
            f"[{idx}] SOURCE: {citation['source']} | PAGE: {citation['page']} | SNIPPET: {citation['snippet']}"
        )

    return citations, "\n\n".join(evidence_blocks)


def build_trace(retrieved_chunks, citations, request_type, tool_call=None, tool_result=None):
    return {
        "request_type": request_type,
        "retrieved_chunks": [
            {
                "source": chunk["source"],
                "page": chunk.get("page"),
                "state": chunk.get("state"),
                "score": chunk.get("score"),
                "snippet": chunk["text"][:220].replace("\n", " ").strip()
            }
            for chunk in retrieved_chunks
        ],
        "citations": citations,
        "tool_call": tool_call,
        "tool_result": tool_result
    }


def extract_literacy_fact(chunk):
    text = chunk["text"]
    patterns = [
        (
            r"literacy rate of the state has increased from ([0-9.]+) per cent in 2001 to ([0-9.]+) per cent in 2011",
            "overall"
        ),
        (
            r"effective literacy rate in [^\.]*?works out to ([0-9.]+) percent",
            "overall"
        ),
        (
            r"female literacy rate has increased from ([0-9.]+) per cent in 2001 to ([0-9.]+) per cent in 2011",
            "female"
        ),
        (
            r"male literacy rate has increased from ([0-9.]+) per cent in 2001 to ([0-9.]+) per cent in 2011",
            "male"
        ),
    ]

    for pattern, metric in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            if metric == "overall":
                if len(match.groups()) == 2:
                    return {
                        "metric": "overall literacy",
                        "value_2001": match.group(1),
                        "value_2011": match.group(2)
                    }
                return {
                    "metric": "overall literacy",
                    "value_2011": match.group(1)
                }
            return {
                "metric": f"{metric} literacy",
                "value_2001": match.group(1),
                "value_2011": match.group(2)
            }

    return None


def build_state_facts(question, limit_per_state=4):
    states = mentioned_states(question)
    if not states:
        states = [get_active_state("default")] if get_active_state("default") else []

    facts = []
    citations = []
    seen_states = set()

    for state in states:
        if not state or state in seen_states:
            continue
        seen_states.add(state)
        chunks = gather_artifact_chunks(question, preferred_state=state, limit=limit_per_state)
        for chunk in chunks:
            fact = extract_literacy_fact(chunk)
            if fact:
                citations.append({
                    "id": len(citations) + 1,
                    "source": chunk["source"],
                    "page": chunk.get("page"),
                    "snippet": chunk["text"][:300].replace("\n", " ").strip()
                })
                facts.append({
                    "state": state,
                    "source": chunk["source"],
                    "page": chunk.get("page"),
                    **fact
                })
                break

    return facts, citations


def ask_question(question, session_id="default"):

    # Get conversation history first so we can keep follow-up questions state-aware
    history = get_history(session_id)

    preferred_state = infer_state(question, history) or get_active_state(session_id)

    if preferred_state:
        set_active_state(session_id, preferred_state)

    request_type = classify_request(question)

    # Retrieve relevant chunks
    if request_type in {"chart", "table"}:
        retrieved_chunks = build_state_evidence(question)
    else:
        retrieved_chunks = retrieve(question, preferred_state=preferred_state)

    citations, context = build_citations(retrieved_chunks)
    state_facts, state_fact_citations = build_state_facts(question)

    history_text = ""

    for message in history:

        history_text += (
            f"{message['role']}: "
            f"{message['content']}\n"
        )

    # Build prompt
    prompt = f"""
You are a helpful census data assistant.

Use conversation history and retrieved context
to answer questions accurately.

Rules:
- Give concise factual answers.
- Answer in 1-3 sentences maximum.
- Do NOT copy long passages from context.
- Summarize information naturally.
- Use ONLY provided context as evidence.
- Cite every factual claim inline using bracketed numbers like [1] or [1][2].
- If answer unavailable, say:
  "I could not find that information in the documents."

CONVERSATION HISTORY:
{history_text}

CONTEXT:
{context}

QUESTION:
{question}

ANSWER:
    """

    # Generate answer or artifact
    if request_type == "chart":
        tool_call = ToolCall(
            name="create_chart",
            arguments={
                "question": question,
                "evidence": context,
                "citations": citations
            }
        )
        try:
            artifact = run_tool(tool_call)
        except Exception as exc:
            artifact = {
                "error": f"chart tool failed: {exc}",
                "citations": citations
            }
        trace = build_trace(
            retrieved_chunks,
            citations,
            request_type,
            tool_call={"name": tool_call.name, "arguments": tool_call.arguments},
            tool_result=artifact
        )
        add_message(session_id, "user", question)
        add_message(session_id, "assistant", "Generated chart artifact.")
        return {
            "answer": "I generated a chart artifact for this question.",
            "sources": list(set([chunk["source"] for chunk in retrieved_chunks])),
            "citations": citations,
            "artifact": artifact,
            "tool_call": {"name": tool_call.name, "arguments": tool_call.arguments},
            "trace": trace,
            "request_type": request_type
        }

    if request_type == "table":
        if not state_facts:
            trace = build_trace(
                retrieved_chunks,
                citations,
                request_type,
                tool_result={"error": "no structured facts could be extracted"}
            )
            add_message(session_id, "user", question)
            add_message(session_id, "assistant", "I could not extract structured facts for the table.")
            return {
                "answer": "I could not extract structured facts for this table request.",
                "sources": list(set([chunk["source"] for chunk in retrieved_chunks])),
                "citations": citations,
                "artifact": {"error": "no structured facts could be extracted", "citations": citations},
                "trace": trace,
                "request_type": request_type
            }

        tool_call = ToolCall(
            name="create_table",
            arguments={
                "question": question,
                "evidence": context,
                "citations": citations,
                "facts": state_facts
            }
        )
        try:
            artifact = run_tool(tool_call)
        except Exception as exc:
            artifact = {
                "error": f"table tool failed: {exc}",
                "citations": citations
            }
        trace = build_trace(
            retrieved_chunks,
            state_fact_citations or citations,
            request_type,
            tool_call={"name": tool_call.name, "arguments": tool_call.arguments},
            tool_result=artifact
        )
        add_message(session_id, "user", question)
        add_message(session_id, "assistant", "Generated table artifact.")
        return {
            "answer": "I generated a table artifact for this question.",
            "sources": list(set([chunk["source"] for chunk in retrieved_chunks])),
            "citations": state_fact_citations or citations,
            "artifact": artifact,
            "tool_call": {"name": tool_call.name, "arguments": tool_call.arguments},
            "trace": trace,
            "request_type": request_type
        }

    # Generate answer
    answer = generate_answer(prompt)

    # Store memory
    add_message(session_id, "user", question)

    add_message(session_id, "assistant", answer)

    # Remove duplicate sources
    unique_sources = list(set([
        chunk["source"]
        for chunk in retrieved_chunks
    ]))

    return {
        "answer": answer,
        "sources": unique_sources,
        "citations": citations,
        "trace": build_trace(retrieved_chunks, citations, request_type),
        "request_type": request_type
    }
