"""
LLM 스트리밍 응답 라우터.
Spring Boot가 내부적으로 호출하는 AI 전용 엔드포인트.
"""
from fastapi import APIRouter, Request
from starlette.concurrency import iterate_in_threadpool
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Dict, Any
from services import llm_service
import time


router = APIRouter(prefix="/llm", tags=["llm"])


class LlmStreamRequest(BaseModel):
    question: str
    chunks: List[Dict[str, Any]]
    query_id: str


@router.post("/stream")
async def stream(req: LlmStreamRequest, request: Request):
    """LLM 응답을 SSE로 스트리밍. Spring Boot가 이를 프록시해 React에 전달한다.

    호출한 쪽이 연결을 끊으면 멈추고, LLM 생성기를 즉시 닫아 Groq 연결을 놓는다.
    닫지 않으면 끊긴 요청마다 생성기가 yield 에서 매달린 채 남는다
    (실측: 서버를 끌 때까지 181초 — 2026-09-21).
    """
    async def generate():
        started = time.time()
        sent = 0
        finished = False
        events = llm_service.stream_response(req.question, req.chunks)
        try:
            async for event in iterate_in_threadpool(events):
                if await request.is_disconnected():
                    return                      # 호출한 쪽이 떠났다
                sent += 1
                yield event
            finished = True
        finally:
            events.close()                      # 청소를 기다리지 않고 직접 닫는다
            state = "완료" if finished else "중단"
            print(f"[llm] {state} - {sent}개 전송, {(time.time() - started) * 1000:.0f}ms", flush=True)

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )

