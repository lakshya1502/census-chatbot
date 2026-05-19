import app.retrieval.vectorstore as vectorstore


SECTION_HINTS = {
    "literacy": ["literates and literacy rate", "literates", "literacy"],
    "female literacy": ["female literacy", "literates and literacy rate"],
    "male literacy": ["male literacy", "literates and literacy rate"],
    "population": ["population"],
    "sex ratio": ["sex ratio"],
    "summary": ["summary", "highlights", "overview"]
}

PHRASE_BOOSTS = {
    "literacy": [
        "the literacy rate of the state has increased",
        "effective literacy rate in",
    ],
    "female literacy": [
        "female literacy rate has increased",
        "female literacy rate",
    ],
    "male literacy": [
        "male literacy has increased",
        "male literacy rate",
    ],
    "population": [
        "population has",
        "population of the state",
    ],
}


def detect_intent(query):
    q = query.lower()
    if any(word in q for word in ["female literacy", "women literacy", "girl literacy"]):
        return "female literacy"
    if any(word in q for word in ["male literacy", "men literacy", "boy literacy"]):
        return "male literacy"
    if "literacy" in q:
        return "literacy"
    if "population" in q:
        return "population"
    if "sex ratio" in q:
        return "sex ratio"
    if any(word in q for word in ["summarize", "summary", "overview", "high level"]):
        return "summary"
    return "general"


def matches_section_hint(section, intent):
    if not section:
        return False
    section_lower = section.lower()
    hints = SECTION_HINTS.get(intent, [])
    return any(hint in section_lower for hint in hints)


def phrase_boost(text, intent):
    boosts = PHRASE_BOOSTS.get(intent, [])
    bonus = 0.0
    for phrase in boosts:
        if phrase in text:
            bonus += 45.0
    return bonus


def demote_noise(text, section):
    penalty = 0.0
    noisy_signals = [
        "contents",
        "chapter-",
        "graph",
        "map",
        "table of contents",
    ]
    if any(signal in text for signal in noisy_signals):
        penalty -= 30.0
    if section and ("contents" in section.lower() or "map" in section.lower()):
        penalty -= 20.0
    if "effective literacy rate has been defined" in text:
        penalty -= 15.0
    return penalty


def retrieve(query, top_k=3, preferred_state=None):

    tokenized_query = vectorstore.tokenize(query)
    query_lower = query.lower()
    intent = detect_intent(query)

    scores = vectorstore.bm25.get_scores(tokenized_query)

    scored_results = []

    for idx in range(len(scores)):

        chunk = vectorstore.document_metadata[idx]

        text = chunk["text"].lower()
        source = chunk["source"].lower()
        state = chunk.get("state", "").lower()
        section = chunk.get("section")

        if preferred_state:
            preferred_state_lower = preferred_state.lower()
            if preferred_state_lower not in text and preferred_state_lower not in source and preferred_state_lower not in state:
                continue

        score = float(scores[idx])

        if state and state in query_lower:
            score += 100.0
        if preferred_state and state == preferred_state.lower():
            score += 50.0
        if intent in {"literacy", "female literacy", "male literacy"}:
            if "literacy" in text:
                score += 15.0
            if matches_section_hint(section, intent):
                score += 25.0
            score += phrase_boost(text, intent)
            score += demote_noise(text, section)
        elif intent == "population":
            if "population" in text:
                score += 20.0
            score += demote_noise(text, section)
        elif intent == "sex ratio":
            if "sex ratio" in text:
                score += 20.0
            score += demote_noise(text, section)
        elif intent == "summary":
            if matches_section_hint(section, intent):
                score += 20.0
            score += demote_noise(text, section)

        scored_results.append({
            "text": chunk["text"],
            "source": chunk["source"],
            "state": chunk.get("state"),
            "page": chunk.get("page"),
            "section": section,
            "score": score
        })

    results = sorted(
        scored_results,
        key=lambda item: item["score"],
        reverse=True
    )

    return results[:top_k]
