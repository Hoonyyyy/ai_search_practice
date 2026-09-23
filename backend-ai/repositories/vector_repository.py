"""벡터 데이터 접근 레이어.

기본은 Qdrant 임베디드(로컬 파일) + Ollama 임베딩.
`.env` 에 QDRANT_URL 을 넣으면 원격 Qdrant 로 자동 전환된다.
"""
from pathlib import Path
from typing import List, Dict, Any, Generator, Optional
import uuid
import time

import requests
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance, VectorParams, PointStruct,
    Filter, FieldCondition, MatchValue,
    IsEmptyCondition, PayloadField,
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

        # owner 필터 검색용. 인덱스가 없으면 Qdrant 가 필터를 무시하거나 전수 검사를 한다.
        try:
            _client.create_payload_index(
                collection_name=COLLECTION,
                field_name="owner",
                field_schema="keyword",
            )
        except (UnexpectedResponse, ValueError):
            pass
    return _client


def _embed(texts: List[str], task: str = "search_document") -> List[List[float]]:
    """provider 에 따라 임베딩 백엔드를 고른다."""
    if settings.embed_provider == "ollama":
        return _embed_ollama(texts, task)
    return _embed_cloud(texts)


def _embed_ollama(texts: List[str], task: str = "search_document") -> List[List[float]]:
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


def _embed_cloud(texts: List[str]) -> List[List[float]]:
    """OpenAI 호환 임베딩 API 로 텍스트 → 임베딩 벡터.

    Ollama 와 달리 응답이 {"data": [{"embedding": [...]}, ...]} 형태다.
    """
    if not settings.embed_api_key:
        raise RuntimeError("EMBED_API_KEY 가 없습니다. .env 를 확인하세요.")

    resp = requests.post(
        f"{settings.embed_api_url}/embeddings",
        headers={"Authorization": f"Bearer {settings.embed_api_key}"},
        json={
            "model": settings.embed_cloud_model,
            "input": texts,
        },
        timeout=120,
    )
    resp.raise_for_status()
    return [item["embedding"] for item  in resp.json()["data"]]




def add_chunks_stream(doc_id: str, filename: str, chunks: List[str], owner: str) -> Generator:
    """배치 단위로 Qdrant에 저장하며 진행률을 (done, total)로 yield."""
    client = _get_client()
    total = len(chunks)
    batch_size = 16

    t_embed_total = 0.0
    t_upsert_total = 0.0
    t_start = time.time()

    for i in range(0, total, batch_size):
        end = min(i + batch_size, total)
        batch = chunks[i:end]

        t0 = time.time()
        vectors = _embed(batch)
        t_embed_total += time.time() - t0

        points = [
            PointStruct(
                id=str(uuid.uuid4()),
                vector=vectors[j],
                payload={
                    "doc_id": doc_id,
                    "filename": filename,
                    "chunk_index": i + j,
                    "content": batch[j],
                    "owner":owner,
                },
            )
            for j in range(len(batch))
        ]

        t1 = time.time()
        client.upsert(collection_name=COLLECTION, points=points)
        t_upsert_total += time.time() - t1

        yield end, total

    print(f"[timing] embed {t_embed_total*1000:.0f}ms, "
          f"upsert {t_upsert_total*1000:.0f}ms, "
          f"total {(time.time()-t_start)*1000:.0f}ms ({total} chunks)", flush=True)


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


def _owner_filter(owner: Optional[str]) -> Filter:
    """검색 범위를 한 세션으로 좁히는 조건.

    owner가 있으면 그 세션의 청크만, 없으면 owner가 비어 있는 청크(= 예시 문서)만 본다.
    후보를 top_k로 뽑은 뒤에 걸러내면 안된다 - 남의 청크가 상위를 차지하면
    내 청크는 아예 후보에 들지 못한다. 그래서 조건을 Qdrant 에게 넘긴다
    """
    if owner:
        return Filter(must=[FieldCondition(key="owner", match=MatchValue(value=owner))])
    return Filter(must=[IsEmptyCondition(is_empty=PayloadField(key="owner"))])


def similarity_search(query: str, top_k: int = 4, owner: Optional[str] = None) -> List[Dict[str, Any]]:

    t_start = time.time()

    t0 = time.time()

    client = _get_client()

    t_client = time.time() - t0

    t0 = time.time()

    flt = _owner_filter(owner)
    total = client.count(collection_name=COLLECTION, count_filter=flt).count

    t_count = time.time() - t0

    # 청크가 얼마 없으면 검색 자체가 손해 — 전부 넣고 순서만 정렬한다.
    if 0 < total <= settings.full_context_threshold:
        pts, _ = client.scroll(collection_name=COLLECTION, scroll_filter=flt, limit=total, with_payload=True)
        pts.sort(key=lambda p: (p.payload["doc_id"], p.payload["chunk_index"]))
        return [_to_dict(p.payload, 1.0) for p in pts]

    t0 = time.time()

    query_vec = _embed([query], task="search_query")[0]

    t_embed = time.time() - t0

    t0 = time.time()

    result = client.query_points(
        collection_name=COLLECTION,
        query=query_vec,
        query_filter=flt,
        limit=top_k,
        with_payload=True,
    )

    t_query = time.time() - t0

    print(f"[search timing] client {t_client*1000:.0f}ms, "
          f"count {t_count*1000:.0f}ms, embed {t_embed*1000:.0f}ms, query {t_query*1000:.0f}ms, "
          f"total {(time.time()-t_start)*1000:.0f}ms (총 {total}개 청크)", flush=True)

    return [_to_dict(h.payload, h.score) for h in result.points]


def delete_document(doc_id: str) -> None:
    _get_client().delete(
        collection_name=COLLECTION,
        points_selector=Filter(
            must=[FieldCondition(key="doc_id", match=MatchValue(value=doc_id))]
        ),
    )


def list_doc_ids() -> List[str]:
    """Qdrant에 실제로 저장돼 있는 doc_id 목록(중복 제거)."""
    client = _get_client()
    ids = set()
    offset = None
    while True:
        points, offset = client.scroll(
            collection_name=COLLECTION,
            limit=256,
            with_payload=["doc_id"],
            with_vectors=False,
            offset=offset,
        )
        ids.update(p.payload["doc_id"] for p in points)
        if offset is None:
            break
    return sorted(ids)
