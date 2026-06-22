from functools import lru_cache
from pathlib import Path

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    app_name: str = "Local AI Coding Assistant"
    app_version: str = "0.1.0"
    app_environment: str = "development"
    app_debug: bool = False
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    api_key: SecretStr = SecretStr("")
    credentials_file: Path = PROJECT_ROOT / "data" / "config" / "credentials.json"
    local_settings_file: Path = (
        PROJECT_ROOT / "data" / "config" / "app-settings.json"
    )
    session_cookie_name: str = "local_ai_session"
    session_ttl_hours: int = Field(default=12, ge=1, le=168)
    session_cookie_secure: bool = False
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    ollama_base_url: str = "http://localhost:11434"
    ollama_timeout_seconds: float = 120.0
    ollama_num_predict: int = Field(default=768, ge=64, le=4096)
    ollama_think: bool = False
    ollama_keep_alive: str = Field(default="10m", min_length=1, max_length=20)
    chat_context_max_chars: int = Field(
        default=12_000,
        ge=12_000,
        le=100_000,
    )
    default_model: str = Field(default="qwen3:4b", min_length=1)
    max_model_parameters_billion: float = Field(default=7.0, gt=0, le=7.0)
    data_directory: Path = PROJECT_ROOT / "data"
    repo_chunk_size: int = Field(default=2000, ge=200, le=20_000)
    rag_top_k: int = Field(default=5, ge=1, le=20)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @property
    def cors_origin_list(self) -> list[str]:
        """Return configured CORS origins as a clean list."""

        return [
            origin.strip()
            for origin in self.cors_origins.split(",")
            if origin.strip()
        ]

    @property
    def index_directory(self) -> Path:
        """Return the directory used for generated repository indexes."""

        return self.data_directory.expanduser().resolve() / "indexes"

    @property
    def resolved_credentials_file(self) -> Path:
        """Return the absolute local credentials file path."""

        return self.credentials_file.expanduser().resolve()

    @property
    def resolved_local_settings_file(self) -> Path:
        """Return the absolute persisted application settings path."""

        return self.local_settings_file.expanduser().resolve()


@lru_cache
def get_settings() -> Settings:
    """Return a cached settings instance for the running process."""

    return Settings()
