from langchain_text_splitters import RecursiveCharacterTextSplitter
import re

splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=150
)


def infer_section(text):
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    headings = []
    for line in lines[:40]:
        if line.startswith("### "):
            headings.append(line.replace("### ", "").strip())
        elif line.startswith("## ") and "page" not in line.lower() and "map" not in line.lower():
            headings.append(line.replace("## ", "").strip())

    if not headings:
        return None

    priority_terms = [
        "literacy",
        "literates",
        "population",
        "sex ratio",
        "summary",
        "highlights"
    ]

    for term in priority_terms:
        for heading in headings:
            if term in heading.lower():
                return heading

    return headings[0]


def split_by_pages(text):
    page_pattern = re.compile(r"<!--\s*page\s+(\d+)\s*-->")
    matches = list(page_pattern.finditer(text))

    if not matches:
        return [{"page": None, "text": text}]

    pages = []

    for i, match in enumerate(matches):
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        page_number = int(match.group(1))
        page_text = text[start:end].strip()
        if page_text:
            pages.append({"page": page_number, "text": page_text})

    return pages


def chunk_documents(documents):

    chunks = []

    for doc in documents:
        pages = split_by_pages(doc["text"])

        for page in pages:
            section = infer_section(page["text"])

            split_texts = splitter.split_text(page["text"])

            for chunk in split_texts:
                chunks.append({
                    "text": chunk,
                    "source": doc["source"],
                    "state": doc["state"],
                    "page": page["page"],
                    "section": section
                })

    return chunks
