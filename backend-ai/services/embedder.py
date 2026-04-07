from sentence_transformers import SentenceTransformer
from config import settings
from typing import List, Generator

_model = None


def get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        _model = SentenceTransformer(settings.embed_model)
    return _model


def preload() -> None:
    get_model()


def embed_texts(texts: List[str]) -> List[List[float]]:
    return get_model().encode(texts, show_progress_bar=False).tolist()


def embed_texts_batched(texts: List[str], batch_size: int = 16) -> Generator:
    """배치 단위로 임베딩하며 (done, total, embeddings_so_far) yield."""
    model = get_model()
    all_embeddings = []
    total = len(texts)
    for i in range(0, total, batch_size):
        batch = texts[i:i + batch_size]
        all_embeddings.extend(model.encode(batch, show_progress_bar=False).tolist())
        yield min(i + batch_size, total), total, all_embeddings


def embed_query(text: str) -> List[float]:
    return embed_texts([text])[0]
