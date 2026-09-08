from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

OFFICE_DIR = Path(__file__).resolve().parent.parent  # office/


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(OFFICE_DIR / ".env"), extra="ignore"
    )

    groq_api_key: str = ""
    office_model: str = "openai/gpt-oss-120b"
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
