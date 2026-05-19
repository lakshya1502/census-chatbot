from pathlib import Path
import re

HERE = Path(__file__).resolve()
REPO_ROOT = HERE.parents[3]
DOCUMENTS_DIR = Path("/workspace/documents")
if not DOCUMENTS_DIR.exists():
    DOCUMENTS_DIR = REPO_ROOT / "workspace" / "documents"


NOISE_PATTERNS = [
    "Government of India",
    "Copyright",
    "Printed and Published by",
    "Data Product Code"
]


def clean_text(text):

    lines = text.splitlines()

    cleaned = []

    for line in lines:

        skip = False

        for pattern in NOISE_PATTERNS:
            if pattern.lower() in line.lower():
                skip = True
                break

        if not skip:
            cleaned.append(line)

    return "\n".join(cleaned)


def infer_state_name(file_name):
    stem = Path(file_name).stem.lower()

    if "karnataka" in stem:
        return "Karnataka"
    if "odisha" in stem:
        return "Odisha"
    if re.search(r"\bmp\b", stem) or "madhya" in stem:
        return "Madhya Pradesh"

    parts = Path(file_name).stem.replace("_", " ").split()
    return parts[-1].title() if parts else Path(file_name).stem


def load_markdown_documents():

    documents = []

    for file in DOCUMENTS_DIR.glob("*.md"):

        text = file.read_text(encoding="utf-8")

        text = clean_text(text)

        documents.append({
            "text": text,
            "source": file.name,
            "state": infer_state_name(file.name)
        })

    return documents
