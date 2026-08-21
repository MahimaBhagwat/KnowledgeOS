from typing import Optional
from pathlib import Path

from pydantic import DirectoryPath, Field, HttpUrl, PostgresDsn, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    database_url: PostgresDsn = Field(..., validation_alias="DATABASE_URL")

    supabase_url: HttpUrl = Field(..., validation_alias="SUPABASE_URL")
    supabase_service_role_key: SecretStr = Field(..., validation_alias="SUPABASE_SERVICE_ROLE_KEY")
    supabase_anon_key: SecretStr = Field(..., validation_alias="SUPABASE_ANON_KEY")
    supabase_jwt_secret: SecretStr = Field(..., validation_alias="SUPABASE_JWT_SECRET")
    supabase_storage_bucket: str = Field(..., validation_alias="SUPABASE_STORAGE_BUCKET")

    chroma_persist_directory: DirectoryPath = Field(..., validation_alias="CHROMA_PERSIST_DIRECTORY")

    llm_provider: str = Field(..., validation_alias="LLM_PROVIDER")
    llm_api_key: SecretStr = Field(..., validation_alias="LLM_API_KEY")
    llm_chat_model_name: str = Field(..., validation_alias="LLM_CHAT_MODEL_NAME")
    llm_embedding_model_name: str = Field(..., validation_alias="LLM_EMBEDDING_MODEL_NAME")
    llm_api_url: Optional[HttpUrl] = Field(None, validation_alias="LLM_API_URL")

    # Optional override to specify absolute uploads directory via env var
    uploads_dir: Optional[str] = Field(None, validation_alias="UPLOADS_DIR")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


settings = Settings()

# Compute a stable absolute uploads directory path relative to the backend package root
# Default: <repo-root>/uploads where repo-root is the parent of the 'app' package
# Use the configured uploads_dir env var if provided (absolute or relative path)
_default_base = Path(__file__).resolve().parent.parent.parent / "uploads"
if settings.uploads_dir:
    _uploads_path = Path(settings.uploads_dir)
    # If a relative path was provided, resolve it against the package root
    if not _uploads_path.is_absolute():
        _uploads_path = (Path(__file__).resolve().parent.parent.parent / _uploads_path).resolve()
else:
    _uploads_path = _default_base.resolve()

# Ensure the directory exists at startup
_uploads_path.mkdir(parents=True, exist_ok=True)

# Expose the absolute path as a string on settings for runtime use
settings.uploads_dir = str(_uploads_path)
