import base64
import json
import subprocess
import tempfile
import re
from pathlib import Path
from dataclasses import dataclass
from typing import Any, Dict, Optional

from app.llm.groq_client import generate_answer
from app.retrieval.retriever import retrieve


@dataclass
class ToolCall:
    name: str
    arguments: Dict[str, Any]


def run_tool(tool_call: ToolCall):
    if tool_call.name == "create_chart":
        return create_chart_tool(**tool_call.arguments)
    if tool_call.name == "create_table":
        return create_table_tool(**tool_call.arguments)
    raise ValueError(f"Unknown tool: {tool_call.name}")


def classify_request(question):
    q = question.lower()
    if any(word in q for word in ["chart", "plot", "graph", "compare", "comparison"]):
        return "chart"
    if any(word in q for word in ["table", "tabulate", "grid"]):
        return "table"
    if any(word in q for word in ["summarize", "summary", "high level", "overview"]):
        return "summary"
    return "query"


def _parse_json(text):
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```json\s*", "", cleaned)
        cleaned = re.sub(r"^```\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start != -1 and end != -1:
        cleaned = cleaned[start:end + 1]
    return json.loads(cleaned)


def _run_python(code, workdir):
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, dir=workdir) as handle:
        handle.write(code)
        script_path = handle.name

    proc = subprocess.run(
        ["python", script_path],
        cwd=workdir,
        capture_output=True,
        text=True,
        timeout=60
    )

    return proc.returncode, proc.stdout, proc.stderr, script_path


def build_chart(question, evidence, citations):
    prompt = f"""
You are extracting chart data from census evidence.

Return JSON only with keys:
- title
- x_label
- y_label
- rows: list of objects with keys "label" and "value"

Rules:
- Use only the evidence.
- Keep rows small and numeric.
- If the evidence is insufficient, return {{"error": "insufficient evidence"}}.

EVIDENCE:
{evidence}

QUESTION:
{question}
"""
    raw = generate_answer(prompt)
    try:
        parsed = _parse_json(raw)
    except Exception as exc:
        return {"error": f"chart spec parse failed: {exc}", "citations": citations, "raw": raw}
    if parsed.get("error"):
        return {"error": parsed["error"], "citations": citations}

    rows = parsed.get("rows", [])
    if not rows:
        return {"error": "no rows extracted", "citations": citations}

    with tempfile.TemporaryDirectory() as workdir:
        spec_path = Path(workdir) / "chart.json"
        spec_path.write_text(json.dumps(parsed), encoding="utf-8")

        code = """
import base64
import json
from pathlib import Path
import matplotlib.pyplot as plt

spec = json.loads(Path("chart.json").read_text(encoding="utf-8"))
rows = spec["rows"]

labels = [row["label"] for row in rows]
values = [float(row["value"]) for row in rows]

plt.figure(figsize=(8, 4.5))
plt.bar(labels, values, color="#2f6fed")
plt.title(spec["title"])
plt.ylabel(spec["y_label"])
plt.xlabel(spec["x_label"])
plt.xticks(rotation=30, ha="right")
plt.tight_layout()
plt.savefig("chart.png", dpi=160)
print("chart.png")
"""
        rc, stdout, stderr, _ = _run_python(code, workdir)
        image_path = Path(workdir) / "chart.png"
        if rc != 0 or not image_path.exists():
            return {"error": stderr or stdout or "chart execution failed", "citations": citations}

        image_bytes = image_path.read_bytes()

    return {
        "title": parsed["title"],
        "image_base64": base64.b64encode(image_bytes).decode("ascii"),
        "stdout": stdout,
        "stderr": stderr,
        "citations": citations
    }


def build_table(question, evidence, citations, facts=None):
    if facts:
        columns = ["State", "Metric", "2011", "2001", "Source", "Page"]
        rows = []
        for fact in facts:
            rows.append({
                "State": fact.get("state", ""),
                "Metric": fact.get("metric", ""),
                "2011": fact.get("value_2011", ""),
                "2001": fact.get("value_2001", ""),
                "Source": fact.get("source", ""),
                "Page": fact.get("page", "")
            })

        header = "| " + " | ".join(columns) + " |"
        sep = "| " + " | ".join(["---"] * len(columns)) + " |"
        body = []
        for row in rows:
            body.append("| " + " | ".join(str(row.get(col, "")) for col in columns) + " |")

        return {
            "title": "Literacy comparison",
            "table_markdown": "\n".join([header, sep] + body),
            "citations": citations
        }

    prompt = f"""
You are extracting table data from census evidence.

Return JSON only with keys:
- title
- columns: list of column names
- rows: list of row objects

Rules:
- Use only the evidence.
- If the evidence is insufficient, return {{"error": "insufficient evidence"}}.

EVIDENCE:
{evidence}

QUESTION:
{question}
"""
    raw = generate_answer(prompt)
    try:
        parsed = _parse_json(raw)
    except Exception as exc:
        return {"error": f"table spec parse failed: {exc}", "citations": citations, "raw": raw}
    if parsed.get("error"):
        return {"error": parsed["error"], "citations": citations}

    columns = parsed.get("columns", [])
    rows = parsed.get("rows", [])
    if not columns or not rows:
        return {"error": "no table rows extracted", "citations": citations}

    header = "| " + " | ".join(columns) + " |"
    sep = "| " + " | ".join(["---"] * len(columns)) + " |"
    body = []
    for row in rows:
        body.append("| " + " | ".join(str(row.get(col, "")) for col in columns) + " |")

    table_md = "\n".join([header, sep] + body)

    return {
        "title": parsed["title"],
        "table_markdown": table_md,
        "citations": citations
    }


def create_chart_tool(question, evidence, citations):
    return build_chart(question, evidence, citations)


def create_table_tool(question, evidence, citations, facts=None):
    return build_table(question, evidence, citations, facts=facts)
