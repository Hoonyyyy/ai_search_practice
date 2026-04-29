"""임베딩 모델 사전 로드 — fastembed BAAI/bge-small-en-v1.5 사용."""
from fastembed import TextEmbedding


def preload() -> None:
    """앱 시작 시 임베딩 모델을 미리 로드해 첫 요청 지연을 줄인다."""
    TextEmbedding("BAAI/bge-small-en-v1.5")
