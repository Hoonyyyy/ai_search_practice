"""Qdrant Cloud 벡터 데이터 접근 레이어."""
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance, VectorParams, PointStruct,
    Filter, FieldCondition, MatchValue,
)
from fastembed import TextEmbedding
from config import settings
from typing import List, Dict, Any, Generator
import uuid

COLLECTION = "documents"
VECTOR_SIZE = 384  # BAAI/bge-small-en-v1.5

_client: QdrantClient | None = None
_embed_model: TextEmbedding | None = None


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
    return _client


def _get_model() -> TextEmbedding:
    global _embed_model
    if _embed_model is None:
        _embed_model = TextEmbedding("BAAI/bge-small-en-v1.5")
    return _embed_model


def _embed(texts: List[str]) -> List[List[float]]:
    return [v.tolist() for v in _get_model().embed(texts)]


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
    hits = client.search(
        collection_name=COLLECTION,
        query_vector=query_vec,
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
        for h in hits
    ]


def delete_document(doc_id: str) -> None:
    _get_client().delete(
        collection_name=COLLECTION,
        points_selector=Filter(
            must=[FieldCondition(key="doc_id", match=MatchValue(value=doc_id))]
        ),
    )
