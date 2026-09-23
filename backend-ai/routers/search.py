"""
벡터 유사도 검색 라우터.
Spring Boot가 내부적으로 호출하는 AI 전용 엔드포인트.
"""
from typing import Optional
from fastapi import APIRouter
from pydantic import BaseModel
from repositories import vector_repository

router = APIRouter(prefix="/search", tags=["search"])


class SearchRequest(BaseModel):
    query: str
    top_k: int = 4
    owner: Optional[str]    # 기본값 없음 = 반드시 보내야함. null 이면 "예시 문서"를 뜻함


@router.post("")
def search(req: SearchRequest):
    """쿼리와 유사한 청크를 Qdrant에서 검색해 반환."""
    chunks = vector_repository.similarity_search(req.query, req.top_k, req.owner)
    return {"chunks": chunks}
