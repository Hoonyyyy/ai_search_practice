"""
문서 임베딩 & 벡터 저장/삭제 라우터.
Spring Boot가 내부적으로 호출하는 AI 전용 엔드포인트.
"""
import json
from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from starlette.concurrency import iterate_in_threadpool
from pydantic import BaseModel
from typing import List
from repositories import vector_repository

router = APIRouter(prefix="/documents", tags=["documents"])


class EmbedAndStoreRequest(BaseModel):
    doc_id: str
    filename: str
    chunks: List[str]


@router.post("/embed-and-store")
async def embed_and_store(req: EmbedAndStoreRequest, request: Request):
    """
    Spring Boot가 전달한 청크를 임베딩 후 Qdrant에 저장.
    배치 단위로 진행률을 SSE로 스트리밍한다.

    호출한 쪽이 연결을 끊으면 즉시 멈추고, 그때까지 저장한 벡터를 직접 지운다.
    쓰기를 멈춘 시점을 확실히 아는 건 쓰는 쪽뿐이라 정리도 여기서 한다.
    (Spring 이 먼저 지우면 그 뒤에 저장된 묶음이 잔여 벡터로 남는다 — 2026-09-21 재현)
    """
    async def generate():
        completed = False
        try:
            batches = vector_repository.add_chunks_stream(req.doc_id, req.filename, req.chunks)
            async for done, total in iterate_in_threadpool(batches):
                if await request.is_disconnected():
                    return                      # 호출한 쪽이 떠났다 — 더 쓰지 않는다
                yield f"data: {json.dumps({'stage': 'embedding', 'message': f'임베딩 생성 중... ({done}/{total})', 'done': done, 'total': total})}\n\n"
            yield f"data: {json.dumps({'stage': 'stored', 'message': '벡터 저장 완료'})}\n\n"
            completed = True
        finally:
            if not completed:
                # await 를 쓰지 않는다 — 취소되는 중에도 이 정리는 끝까지 실행돼야 한다
                vector_repository.delete_document(req.doc_id)
                print(f"[embed] 중단 → 저장했던 벡터 정리 (doc_id={req.doc_id})", flush=True)

    return StreamingResponse(generate(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})



@router.get("/doc-ids")
def list_doc_ids():
    return {"doc_ids": vector_repository.list_doc_ids()}


@router.delete("/{doc_id}")
def delete_document(doc_id: str):
    vector_repository.delete_document(doc_id)
    return {"message": "삭제 완료"}
