"""Shared fixtures for E2E tests — FastAPI TestClient with real tmp filesystem."""
from __future__ import annotations
import pytest
from fastapi.testclient import TestClient
from src.main import app
from src.infrastructure.config import get_settings, Settings


def _make_test_settings(tmp_path) -> Settings:
    return Settings(
        upload_dir=str(tmp_path / "uploads"),
        pages_dir=str(tmp_path / "pages"),
        documents_storage_dir=str(tmp_path / "documents"),
        annotations_storage_dir=str(tmp_path / "annotations"),
        schemas_dir=str(tmp_path / "schemas"),
        render_dpi=72,
        host="127.0.0.1",
        port=8000,
        cors_origins="http://localhost:5173",
    )


@pytest.fixture
def client(tmp_path):
    """TestClient with isolated tmp storage + YAML schemas."""
    settings = _make_test_settings(tmp_path)

    # Create schemas dir with real YAML files
    schemas_dir = tmp_path / "schemas"
    schemas_dir.mkdir(parents=True, exist_ok=True)
    _write_schema(schemas_dir / "e14_senado.yaml")
    _write_schema(schemas_dir / "e14_camara.yaml")

    get_settings.cache_clear()
    app.dependency_overrides[get_settings] = lambda: settings

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()
    get_settings.cache_clear()


def _write_schema(path):
    path.write_text(
        "labels:\n"
        "  - name: TotalSufragantes\n"
        "    description: Total\n"
        "    repeats_per_page: false\n"
        "  - name: TipoDeVotoPartido\n"
        "    description: Partido\n"
        "    repeats_per_page: true\n",
        encoding="utf-8",
    )
