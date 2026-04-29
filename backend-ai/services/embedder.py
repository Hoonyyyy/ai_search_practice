"""임베딩 모델 사전 로드 — ChromaDB 내장 ONNX 모델 사용."""
from chromadb.utils.embedding_functions import DefaultEmbeddingFunction


def preload() -> None:
    """앱 시작 시 ONNX 임베딩 모델을 미리 로드해 첫 요청 지연을 줄인다."""
    DefaultEmbeddingFunction()
