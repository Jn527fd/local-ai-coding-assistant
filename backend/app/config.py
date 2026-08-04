from functools import lru_cache
from pathlib import Path

from pydantic import Field, SecretStr, field_validator
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
    csrf_cookie_name: str = "local_ai_csrf"
    csrf_header_name: str = "x-csrf-token"
    session_ttl_hours: int = Field(default=12, ge=1, le=168)
    session_cookie_secure: bool = False
    session_signing_key: SecretStr = SecretStr("")
    login_rate_limit_attempts: int = Field(default=5, ge=1, le=100)
    login_rate_limit_window_seconds: int = Field(default=300, ge=30, le=3600)
    login_lockout_seconds: int = Field(default=300, ge=30, le=3600)
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    cors_origin_regex: str = (
        r"^https?://("
        r"localhost|127\.0\.0\.1|\[::1\]|"
        r"10\.\d{1,3}\.\d{1,3}\.\d{1,3}|"
        r"192\.168\.\d{1,3}\.\d{1,3}|"
        r"172\.(1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3}|"
        r"[\w.-]+\.local"
        r")(:\d+)?$"
    )
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
    context_compression_max_prompt_chars: int = Field(
        default=12_000,
        ge=4_000,
        le=100_000,
    )
    context_compression_recent_messages_to_keep: int = Field(
        default=10,
        ge=0,
        le=30,
    )
    context_compression_max_retrieved_context_chars: int = Field(
        default=6_000,
        ge=1_000,
        le=50_000,
    )
    context_compression_max_summary_chars: int = Field(
        default=2_000,
        ge=400,
        le=20_000,
    )
    default_model: str = Field(default="qwen3:4b", min_length=1)
    data_directory: Path = PROJECT_ROOT / "data"
    repository_allowed_roots: str = ""
    repo_chunk_size: int = Field(default=2000, ge=200, le=20_000)
    rag_top_k: int = Field(default=5, ge=1, le=20)
    rag_candidate_k: int = Field(default=20, ge=1, le=50)
    rag_max_top_k: int = Field(default=20, ge=1, le=20)
    reranker_max_candidates: int = Field(default=50, ge=1, le=50)
    document_max_upload_bytes: int = Field(
        default=25 * 1024 * 1024,
        ge=1024,
        le=200 * 1024 * 1024,
    )
    document_chunk_size: int = Field(default=2000, ge=200, le=20_000)
    document_max_chunks: int = Field(default=500, ge=1, le=10_000)
    embedding_batch_size: int = Field(default=16, ge=1, le=128)
    vector_store_backend: str = Field(default="qdrant", min_length=1, max_length=40)
    qdrant_url: str = Field(default="", max_length=500)
    qdrant_api_key: SecretStr = SecretStr("")
    memory_collection_name: str = Field(
        default="local_ai_conversation_memory_v1",
        min_length=1,
        max_length=120,
    )
    memory_top_k: int = Field(default=5, ge=1, le=20)
    memory_min_importance: float = Field(default=0.35, ge=0.0, le=1.0)
    memory_auto_store_enabled: bool = True
    conversation_max_count: int = Field(default=50, ge=1, le=500)
    metadata_database_file: Path | None = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @field_validator("metadata_database_file", mode="before")
    @classmethod
    def empty_metadata_database_file_uses_default(cls, value: object) -> object:
        """Treat an empty env override as the default metadata DB path."""

        if value == "":
            return None
        return value

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
    def repository_allowed_root_paths(self) -> list[Path]:
        """Return local roots from which repositories may be indexed."""

        configured_roots = [
            value.strip()
            for value in self.repository_allowed_roots.split(",")
            if value.strip()
        ]
        roots = [Path(value).expanduser().resolve() for value in configured_roots]
        if not roots:
            roots = [
                PROJECT_ROOT.resolve(),
                self.data_directory.expanduser().resolve(),
                Path("/repositories").resolve(),
            ]
        return roots

    @property
    def upload_directory(self) -> Path:
        """Return the directory used for uploaded document artifacts."""

        return self.data_directory.expanduser().resolve() / "uploads"

    @property
    def vector_index_directory(self) -> Path:
        """Return the directory used for local vector indexes."""

        return self.data_directory.expanduser().resolve() / "vector_indexes"

    @property
    def conversation_directory(self) -> Path:
        """Return the directory used for optional persisted conversations."""

        return self.data_directory.expanduser().resolve() / "conversations"

    @property
    def resolved_metadata_database_file(self) -> Path:
        """Return the local SQLite metadata database path."""

        if self.metadata_database_file is not None:
            return self.metadata_database_file.expanduser().resolve()
        return self.data_directory.expanduser().resolve() / "metadata" / "app.sqlite3"

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
