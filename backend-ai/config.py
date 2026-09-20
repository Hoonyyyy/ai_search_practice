from pydantic_settings import BaseSettings
from pathlib import Path

BASE_DIR = Path(__file__).parent


class Settings(BaseSettings):
    # ── 임베딩 (provider 선택) ────────────────────────────────
    # "ollama" = 완전 로컬(느림, CPU). 그 외 = 클라우드 API(EMBED_API_KEY 필요).
    ollama_base_url: str = "http://127.0.0.1:11434"
    embed_model: str = "bge-m3"            # 다국어 임베딩. nomic-embed-text 는 한국어에서 사실상 무작위
    embed_dim: int = 1024                  # bge-m3 출력 차원
    ollama_keep_alive: str = "10m"         # 세션 중 모델 재로딩(cold start) 방지. RAM 빠듯하면 "5m"

    # 모델을 바꿔 embed_dim 이 달라지면 기존 벡터는 전부 무효다.
    # Qdrant 컬렉션은 생성 시 차원이 고정되므로 컬렉션 삭제 + 재적재가 필요하다.
    #   → evals/reload_corpus.py
    embed_provider: str = "ollama"
    embed_api_key: str = ""
    embed_api_url: str = ""
    embed_cloud_model: str = ""


    # ── LLM (provider 선택) ───────────────────────────────────
    # "ollama" = 완전 로컬(느림, CPU). "groq" = 클라우드(빠름, GROQ_API_KEY 필요).
    llm_provider: str = "ollama"
    llm_model: str = "qwen2.5:3b"          # ollama 용. 한국어 품질이 llama3.2:3b 보다 좋음
    groq_api_key: str = ""
    groq_model: str = "openai/gpt-oss-120b"

    # ── 벡터 DB ───────────────────────────────────────────────
    # 기본: Qdrant 임베디드(로컬 파일). qdrant_url 설정 시 원격 전환.
    qdrant_path: str = str(BASE_DIR / "data" / "qdrant")
    qdrant_url: str = ""
    qdrant_api_key: str = ""

    top_k: int = 4
    # 컬렉션 전체 청크 수가 이 값 이하면 검색을 건너뛰고 전부 컨텍스트로 넣는다.
    # (한두 개 문서만 올리는 데모에서 검색 누락을 없앤다)
    full_context_threshold: int = 12

    class Config:
        env_file = ".env"


settings = Settings()
