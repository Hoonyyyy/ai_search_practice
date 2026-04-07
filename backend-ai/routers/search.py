"""
벡터 유사도 검색 라우터.
Spring Boot가 내부적으로 호출하는 AI 전용 엔드포인트.
"""
from fastapi import APIRouter
from pydantic import BaseModel
from repositories import vector_repository

router = APIRouter(prefix="/search", tags=["search"])


class SearchRequest(BaseModel):
    query: str
    top_k: int = 4


@router.post("")
def search(req: SearchRequest):
    """쿼리와 유사한 청크를 ChromaDB에서 검색해 반환."""
    chunks = vector_repository.similarity_search(req.query, req.top_k)
    return {"chunks": chunks}
