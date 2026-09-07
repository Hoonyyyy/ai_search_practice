from pydantic_settings import BaseSettings
from pathlib import Path

BASE_DIR = Path(__file__).parent


class Settings(BaseSettings):
    # ── 로컬 스택 (기본값) ─────────────────────────────────────
    # Ollama: LLM + 임베딩 모두 담당
    ollama_base_url: str = "http://localhost:11434"
    llm_model: str = "llama3.2:3b"
    embed_model: str = "nomic-embed-text"
    embed_dim: int = 768  # nomic-embed-text 출력 차원

    # Qdrant: 임베디드(로컬 파일) 모드. 경로가 비어 있으면 in-memory.
    qdrant_path: str = str(BASE_DIR / "data" / "qdrant")

    # ── 클라우드 스택 (선택) ───────────────────────────────────
    # qdrant_url 이 설정되면 임베디드 대신 원격 Qdrant 를 쓴다.
    qdrant_url: str = ""
    qdrant_api_key: str = ""

    top_k: int = 4

    class Config:
        env_file = ".env"


settings = Settings()
