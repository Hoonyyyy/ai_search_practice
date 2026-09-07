"""벡터 데이터 접근 레이어.

기본은 Qdrant 임베디드(로컬 파일) + Ollama 임베딩.
`.env` 에 QDRANT_URL 을 넣으면 원격 Qdrant 로 자동 전환된다.
"""
from pathlib import Path
from typing import List, Dict, Any, Generator, Optional
import uuid

import requests
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance, VectorParams, PointStruct,
    Filter, FieldCondition, MatchValue,
)
from qdrant_client.http.exceptions import UnexpectedResponse

from config import settings

COLLECTION = "documents"
VECTOR_SIZE = settings.embed_dim

_client: Optional[QdrantClient] = None


def _get_client() -> QdrantClient:
    global _client
    if _client is not None:
        return _client

    if settings.qdrant_url:
        _client = QdrantClient(url=settings.qdrant_url, api_key=settings.qdrant_api_key or None)
    else:
        Path(settings.qdrant_path).mkdir(parents=True, exist_ok=True)
        _client = QdrantClient(path=settings.qdrant_path)

    existing = {c.name for c in _client.get_collections().collections}
    if COLLECTION not in existing:
        _client.create_collection(
            collection_name=COLLECTION,
            vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE),
        )

    # doc_id 필터 검색/삭제용 인덱스. 임베디드 모드에선 인덱스가 무의미하므로
    # 원격 Qdrant 일 때만 생성한다. 이미 있으면 조용히 넘어간다.
    if settings.qdrant_url:
        try:
            _client.create_payload_index(
                collection_name=COLLECTION,
                field_name="doc_id",
                field_schema="keyword",
            )
        except (UnexpectedResponse, ValueError):
            pass

    return _client


def _embed(texts: List[str], task: str = "search_document") -> List[List[float]]:
    """Ollama 로 텍스트 → 임베딩 벡터. 한 번에 배치 처리.

    nomic-embed-text 는 task 접두사(`search_document:` / `search_query:`)를
    붙여야 검색 품질이 크게 오른다. 다른 모델이면 접두사가 무해하게 무시된다.
    """
    prefix = f"{task}: " if settings.embed_model.startswith("nomic-embed") else ""
    resp = requests.post(
        f"{settings.ollama_base_url}/api/embed",
        json={
            "model": settings.embed_model,
            "input": [prefix + t for t in texts],
            "keep_alive": settings.ollama_keep_alive,
        },
        timeout=120,
    )
    resp.raise_for_status()
    return resp.json()["embeddings"]


def add_chunks_stream(doc_id: str, filename: str, chunks: List[str]) -> Generator:
    """배치 단위로 Qdrant에 저장하며 진행률을 (done, total)로 yield."""
    client = _get_client()
    total = len(chunks)
    batch_size = 16

    for i in range(0, total, batch_size):
        end = min(i + batch_size, total)
        batch = chunks[i:end]
        vectors = _embed(batch)
        points = [
            PointStruct(
                id=str(uuid.uuid4()),
                vector=vectors[j],
                payload={
                    "doc_id": doc_id,
                    "filename": filename,
                    "chunk_index": i + j,
                    "content": batch[j],
                },
            )
            for j in range(len(batch))
        ]
        client.upsert(collection_name=COLLECTION, points=points)
        yield end, total


def _to_dict(payload: Dict[str, Any], score: float) -> Dict[str, Any]:
    return {
        "content": payload["content"],
        "metadata": {
            "doc_id": payload["doc_id"],
            "filename": payload["filename"],
            "chunk_index": payload["chunk_index"],
        },
        "distance": 1.0 - score,
    }


def similarity_search(query: str, top_k: int = 4) -> List[Dict[str, Any]]:
    client = _get_client()
    total = client.count(collection_name=COLLECTION).count

    # 청크가 얼마 없으면 검색 자체가 손해 — 전부 넣고 순서만 정렬한다.
    if 0 < total <= settings.full_context_threshold:
        pts, _ = client.scroll(collection_name=COLLECTION, limit=total, with_payload=True)
        pts.sort(key=lambda p: (p.payload["doc_id"], p.payload["chunk_index"]))
        return [_to_dict(p.payload, 1.0) for p in pts]

    query_vec = _embed([query], task="search_query")[0]
    result = client.query_points(
        collection_name=COLLECTION,
        query=query_vec,
        limit=top_k,
        with_payload=True,
    )
    return [_to_dict(h.payload, h.score) for h in result.points]


def delete_document(doc_id: str) -> None:
    _get_client().delete(
        collection_name=COLLECTION,
        points_selector=Filter(
            must=[FieldCondition(key="doc_id", match=MatchValue(value=doc_id))]
        ),
    )
