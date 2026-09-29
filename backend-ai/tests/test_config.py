"""1단계: config.py 기본값 회귀 테스트.

목적: RAG 품질 디버깅 때 바꾼 핵심 설정값(embed_model, embed_dim,
full_context_threshold)이 나중에 실수로 되돌아가지 않았는지 감시한다.

주의: 전역 settings 를 그대로 쓰면 .env 를 읽는다. 클라우드 임베딩으로 전환한
개발자의 .env 에는 EMBED_DIM=3072 가 들어 있어, 코드가 멀쩡한데도 이 테스트가
깨졌다(2026-09-28). "코드 기본값"을 재려면 .env 를 빼고 만들어야 한다.
그래서 여기서는 Settings 를 직접 만든다 — 이래야 누구 PC 에서나 같은 결과가 나온다.
"""
from config import Settings


def defaults() -> Settings:
    """.env 를 읽지 않는 설정 객체. 코드에 박힌 기본값만 남는다."""
    return Settings(_env_file=None)


def test_default_embed_model_is_bge_m3():
    # nomic-embed-text는 한국어에서 사실상 무작위였다 (2026-09-07 디버깅) — bge-m3여야 함
    assert defaults().embed_model == "bge-m3"


def test_default_embed_dim_matches_bge_m3_output():
    # 차원이 모델과 어긋나면 업로드가 통째로 실패한다. 기본값은 bge-m3 의 1024.
    assert defaults().embed_dim == 1024


def test_default_full_context_threshold():
    assert defaults().full_context_threshold == 12
