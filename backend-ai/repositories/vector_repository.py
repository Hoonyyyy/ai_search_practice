"""ChromaDB 벡터 데이터 접근 레이어."""
import chromadb
from chromadb.config import Settings as ChromaSettings
from chromadb.utils.embedding_functions import DefaultEmbeddingFunction
from config import settings
from typing import List, Dict, Any, Generator

_client = None
_collection = None
_ef = DefaultEmbeddingFunction()


def _get_collection():
    global _client, _collection
    if _client is None:
        _client = chromadb.PersistentClient(
            path=settings.chroma_path,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
    if _collection is None:
        _collection = _client.get_or_create_collection(
            name="documents",
            embedding_function=_ef,
            metadata={"hnsw:space": "cosine"},
        )
    return _collection


def add_chunks_stream(doc_id: str, filename: str, chunks: List[str]) -> Generator:
    """배치 단위로 ChromaDB에 저장하며 진행률을 (done, total)로 yield."""
    collection = _get_collection()
    ids = [f"{doc_id}_{i}" for i in range(len(chunks))]
    metadatas = [{"doc_id": doc_id, "filename": filename, "chunk_index": i} for i in range(len(chunks))]

    batch_size = 16
    total = len(chunks)
    for i in range(0, total, batch_size):
        end = min(i + batch_size, total)
        collection.add(
            ids=ids[i:end],
            documents=chunks[i:end],
            metadatas=metadatas[i:end],
        )
        yield end, total


def similarity_search(query: str, top_k: int = 4) -> List[Dict[str, Any]]:
    collection = _get_collection()
    if collection.count() == 0:
        return []
    results = collection.query(
        query_texts=[query],
        n_results=min(top_k, collection.count()),
        include=["documents", "metadatas", "distances"],
    )
    return [
        {"content": doc, "metadata": results["metadatas"][0][i], "distance": results["distances"][0][i]}
        for i, doc in enumerate(results["documents"][0])
    ]


def delete_document(doc_id: str) -> None:
    collection = _get_collection()
    results = collection.get(where={"doc_id": doc_id})
    if results["ids"]:
        collection.delete(ids=results["ids"])
