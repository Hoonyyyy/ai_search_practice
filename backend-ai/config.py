from pydantic_settings import BaseSettings
from pathlib import Path

BASE_DIR = Path(__file__).parent


class Settings(BaseSettings):
    qdrant_url: str = ""
    qdrant_api_key: str = ""
    groq_api_key: str = ""
    groq_model: str = "llama-3.1-8b-instant"
    top_k: int = 4

    class Config:
        env_file = ".env"


settings = Settings()
