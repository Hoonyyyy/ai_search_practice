from pydantic_settings import BaseSettings
from pathlib import Path

BASE_DIR = Path(__file__).parent


class Settings(BaseSettings):
    # ── 로컬 스택 (기본값) ─────────────────────────────────────
    # Ollama: LLM + 임베딩 모두 담당
    ollama_base_url: str = "http://localhost:11434"
    llm_model: str = "qwen2.5:3b"          # 한국어 품질이 llama3.2:3b 보다 크게 좋음
    embed_model: str = "bge-m3"            # 다국어 임베딩. nomic-embed-text 는 한국어에서 사실상 무작위
    embed_dim: int = 1024                  # bge-m3 출력 차원

    # Qdrant: 임베디드(로컬 파일) 모드. 경로가 비어 있으면 in-memory.
    qdrant_path: str = str(BASE_DIR / "data" / "qdrant")

    # ── 클라우드 스택 (선택) ───────────────────────────────────
    # qdrant_url 이 설정되면 임베디드 대신 원격 Qdrant 를 쓴다.
    qdrant_url: str = ""
    qdrant_api_key: str = ""

    top_k: int = 4
    # 모델을 메모리에 유지하는 시간. 세션 중 재로딩(cold start)을 막는다.
    # RAM 여유가 많으면 "-1"(계속 유지), 빠듯하면 "5m" 로.
    ollama_keep_alive: str = "10m"

    class Config:
        env_file = ".env"


settings = Settings()
