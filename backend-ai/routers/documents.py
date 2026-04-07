"""
문서 임베딩 & 벡터 저장/삭제 라우터.
Spring Boot가 내부적으로 호출하는 AI 전용 엔드포인트.
"""
import json
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List
from repositories import vector_repository

router = APIRouter(prefix="/documents", tags=["documents"])


class EmbedAndStoreRequest(BaseModel):
    doc_id: str
    filename: str
    chunks: List[str]


@router.post("/embed-and-store")
def embed_and_store(req: EmbedAndStoreRequest):
    """
    Spring Boot가 전달한 청크를 임베딩 후 ChromaDB에 저장.
    배치 단위로 진행률을 SSE로 스트리밍한다.
    """
    def generate():
        for done, total in vector_repository.add_chunks_stream(req.doc_id, req.filename, req.chunks):
            yield f"data: {json.dumps({'stage': 'embedding', 'message': f'임베딩 생성 중... ({done}/{total})', 'done': done, 'total': total})}\n\n"
        yield f"data: {json.dumps({'stage': 'stored', 'message': '벡터 저장 완료'})}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@router.delete("/{doc_id}")
def delete_document(doc_id: str):
    vector_repository.delete_document(doc_id)
    return {"message": "삭제 완료"}
