from pydantic_settings import BaseSettings
from pathlib import Path

BASE_DIR = Path(__file__).parent


class Settings(BaseSettings):
    chroma_path: str = str(BASE_DIR / "data" / "chroma_db")
    embed_model: str = "all-MiniLM-L6-v2"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2:3b"
    top_k: int = 4

    class Config:
        env_file = ".env"


settings = Settings()
