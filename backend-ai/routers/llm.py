"""
LLM 스트리밍 응답 라우터.
Spring Boot가 내부적으로 호출하는 AI 전용 엔드포인트.
"""
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Dict, Any
from services import llm_service

router = APIRouter(prefix="/llm", tags=["llm"])


class LlmStreamRequest(BaseModel):
    question: str
    chunks: List[Dict[str, Any]]
    query_id: str


@router.post("/stream")
def stream(req: LlmStreamRequest):
    """Ollama LLM 응답을 SSE로 스트리밍. Spring Boot가 이를 프록시해 React에 전달한다."""
    return StreamingResponse(
        llm_service.stream_response(req.question, req.chunks),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
