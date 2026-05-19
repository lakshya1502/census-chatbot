from fastapi import APIRouter
from pydantic import BaseModel

# from services.rag_service import ask_question
from app.services.rag_service import ask_question
from app.models import ChatResponse
router = APIRouter()


class ChatRequest(BaseModel):
    question: str
    session_id: str | None = None


@router.get("/health")
def health():
    return {"status": "healthy"}


@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):

    response = ask_question(request.question, request.session_id or "default")

    return response
