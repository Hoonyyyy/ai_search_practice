"""Qdrant Cloud 벡터 데이터 접근 레이어. 임베딩은 Jina AI API 사용."""
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance, VectorParams, PointStruct,
    Filter, FieldCondition, MatchValue,
)
import requests
from config import settings
from typing import List, Dict, Any, Generator, Optional
import uuid

COLLECTION = "documents"
VECTOR_SIZE = 512  # jina-embeddings-v2-small-en

_client: Optional[QdrantClient] = None


def _get_client() -> QdrantClient:
    global _client
    if _client is None:
        _client = QdrantClient(url=settings.qdrant_url, api_key=settings.qdrant_api_key)
        existing = {c.name for c in _client.get_collections().collections}
        if COLLECTION not in existing:
            _client.create_collection(
                collection_name=COLLECTION,
                vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE),
            )
        _client.create_payload_index(
            collection_name=COLLECTION,
            field_name="doc_id",
            field_schema="keyword",
        )
    return _client


def _embed(texts: List[str]) -> List[List[float]]:
    resp = requests.post(
        "https://api.jina.ai/v1/embeddings",
        headers={"Authorization": f"Bearer {settings.jina_api_key}"},
        json={"model": "jina-embeddings-v2-small-en", "input": texts},
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()["data"]
    return [item["embedding"] for item in sorted(data, key=lambda x: x["index"])]


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


def similarity_search(query: str, top_k: int = 4) -> List[Dict[str, Any]]:
    client = _get_client()
    query_vec = _embed([query])[0]
    result = client.query_points(
        collection_name=COLLECTION,
        query=query_vec,
        limit=top_k,
        with_payload=True,
    )
    return [
        {
            "content": h.payload["content"],
            "metadata": {
                "doc_id": h.payload["doc_id"],
                "filename": h.payload["filename"],
                "chunk_index": h.payload["chunk_index"],
            },
            "distance": 1.0 - h.score,
        }
        for h in result.points
    ]


def delete_document(doc_id: str) -> None:
    _get_client().delete(
        collection_name=COLLECTION,
        points_selector=Filter(
            must=[FieldCondition(key="doc_id", match=MatchValue(value=doc_id))]
        ),
    )
