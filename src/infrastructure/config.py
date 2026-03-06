from __future__ import annotations
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Azure Blob Storage / Azurite (primary storage)
    azure_storage_connection_string: str

    # Legacy local dirs — no longer used, kept optional for backwards compat
    upload_dir: str = "./data/uploads"
    pages_dir: str = "./data/pages"
    documents_storage_dir: str = "./data/documents"
    annotations_storage_dir: str = "./data/annotations"
    schemas_dir: str = "./config/schemas"

    # Renderizado PDF
    render_dpi: int = 150

    # Servidor
    host: str = "0.0.0.0"
    port: int = 8000
    cors_origins: str = "http://localhost:5173"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",")]


@lru_cache
def get_settings() -> Settings:
    return Settings()
