from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

OFFICE_DIR = Path(__file__).resolve().parent.parent  # office/


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(OFFICE_DIR / ".env"), extra="ignore"
    )

    # 동료들의 두뇌 — "groq"(빠름, 일일 토큰 한도) | "ollama"(로컬, 무료·무제한, 느림)
    office_provider: str = "groq"
    groq_api_key: str = ""
    office_model: str = "openai/gpt-oss-20b"
    ollama_base_url: str = "http://localhost:11434"
    office_ollama_model: str = "qwen2.5:3b"
    office_port: int = 8899
    repo_root: str = ""

    @property
    def repo_root_path(self) -> Path:
        return Path(self.repo_root) if self.repo_root else OFFICE_DIR.parent

    @property
    def data_dir(self) -> Path:
        d = OFFICE_DIR / "data"
        d.mkdir(exist_ok=True)
        return d


settings = Settings()
