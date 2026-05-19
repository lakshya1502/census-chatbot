from typing import Any, Optional

from pydantic import BaseModel


class Citation(BaseModel):
    id: int
    source: str
    page: Optional[int] = None
    snippet: str


class ToolCallModel(BaseModel):
    name: str
    arguments: dict[str, Any]


class TraceModel(BaseModel):
    request_type: str
    retrieved_chunks: list[dict[str, Any]]
    citations: list[Citation]
    tool_call: Optional[dict[str, Any]] = None
    tool_result: Optional[dict[str, Any]] = None


class ArtifactModel(BaseModel):
    title: Optional[str] = None
    image_base64: Optional[str] = None
    table_markdown: Optional[str] = None
    stdout: Optional[str] = None
    stderr: Optional[str] = None
    error: Optional[str] = None
    citations: list[Citation] = []


class ChatResponse(BaseModel):
    answer: str
    sources: list[str]
    citations: list[Citation]
    request_type: str
    artifact: Optional[ArtifactModel] = None
    tool_call: Optional[dict[str, Any]] = None
    trace: Optional[TraceModel] = None

