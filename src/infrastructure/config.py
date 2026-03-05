from __future__ import annotations
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Directorios de almacenamiento local — usados por repositorios locales y renderer
    upload_dir: str
    pages_dir: str
    documents_storage_dir: str
    annotations_storage_dir: str
    schemas_dir: str

    # Azure Blob Storage / Azurite
    azure_storage_connection_string: str

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
