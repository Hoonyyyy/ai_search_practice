"""1단계: config.py 기본값 회귀 테스트.

목적: RAG 품질 디버깅 때 바꾼 핵심 설정값(embed_model, embed_dim,
full_context_threshold)이 나중에 실수로 되돌아가지 않았는지 감시한다.
의존성 없음(Ollama/Qdrant 안 켜져 있어도 통과) — pytest에서 가장 쉬운 형태.
"""
from config import settings


def test_default_embed_model_is_bge_m3():
    # nomic-embed-text는 한국어에서 사실상 무작위였다 (2026-09-07 디버깅) — bge-m3여야 함
    assert settings.embed_model == "bge-m3"


def test_default_embed_dim_matches_bge_m3_output():
    assert settings.embed_dim == 1024


def test_default_full_context_threshold():
    assert settings.full_context_threshold == 12
