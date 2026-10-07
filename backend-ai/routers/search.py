"""
벡터 유사도 검색 라우터.
Spring Boot가 내부적으로 호출하는 AI 전용 엔드포인트.
"""
from typing import Optional
from fastapi import APIRouter
from pydantic import BaseModel
from config import settings
from repositories import vector_repository
from services import reranker

router = APIRouter(prefix="/search", tags=["search"])


class SearchRequest(BaseModel):
    query: str
    top_k: int = 4
    owner: Optional[str]    # 기본값 없음 = 반드시 보내야함. null 이면 "예시 문서"를 뜻함


@router.post("")
def search(req: SearchRequest):
    """쿼리와 유사한 청크를 Qdrant에서 검색해 반환. 리랭커가 켜져 있으면 후보를 넉넉히 받아 다시 고른다."""
    if not reranker.enabled():
        return {"chunks": vector_repository.similarity_search(req.query, req.top_k, req.owner)}

    candidates = vector_repository.similarity_search(req.query, settings.rerank_candidates, req.owner)
    # 청크가 full_context_threshold 이하인 문서는 검색 없이 전부 돌려준다(similarity_search).
    # 그 경우는 이미 "전부 넣기"라서 다시 고를 이유가 없고, 잘라내면 오히려 정보를 잃는다.
    if len(candidates) <= settings.full_context_threshold:
        return {"chunks": candidates}

    ranked = reranker.rerank(req.query, candidates, req.top_k)
    return {"chunks": ranked if ranked is not None else candidates[: req.top_k]}
