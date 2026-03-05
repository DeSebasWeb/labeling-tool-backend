"""Integration tests — YamlLabelSchemaRepository (real YAML files via tmp_path)."""
from __future__ import annotations
import pytest
from src.domain.entities.document_kind import DocumentKind
from src.domain.exceptions.label_schema_not_found_exception import LabelSchemaNotFoundException
from src.infrastructure.persistence.yaml_label_schema_repository import YamlLabelSchemaRepository


VALID_YAML = """\
labels:
  - name: Pagina
    description: "Número de página"
    repeats_per_page: false
  - name: TotalSufragantes
    description: "Total sufragantes"
    repeats_per_page: false
  - name: TipoDeVotoPartido
    description: "Votos por partido"
    repeats_per_page: true
"""


@pytest.fixture
def schemas_dir(tmp_path):
    return tmp_path / "schemas"


@pytest.fixture
def repo_with_senado(schemas_dir):
    schemas_dir.mkdir()
    (schemas_dir / "e14_senado.yaml").write_text(VALID_YAML, encoding="utf-8")
    return YamlLabelSchemaRepository(str(schemas_dir))


class TestGetSchema:
    def test_returns_schema_for_existing_kind(self, repo_with_senado):
        schema = repo_with_senado.get_schema(DocumentKind.E14_SENADO)
        assert schema.document_kind == DocumentKind.E14_SENADO

    def test_labels_loaded_correctly(self, repo_with_senado):
        schema = repo_with_senado.get_schema(DocumentKind.E14_SENADO)
        assert "Pagina" in schema.label_names()
        assert "TotalSufragantes" in schema.label_names()
        assert len(schema.labels) == 3

    def test_repeats_per_page_flag(self, repo_with_senado):
        schema = repo_with_senado.get_schema(DocumentKind.E14_SENADO)
        partido = schema.find("TipoDeVotoPartido")
        assert partido.repeats_per_page is True

    def test_missing_schema_raises_domain_exception(self, schemas_dir):
        schemas_dir.mkdir()
        repo = YamlLabelSchemaRepository(str(schemas_dir))
        with pytest.raises(LabelSchemaNotFoundException):
            repo.get_schema(DocumentKind.E14_CAMARA)

    def test_raises_domain_exception_not_file_not_found_error(self, schemas_dir):
        schemas_dir.mkdir()
        repo = YamlLabelSchemaRepository(str(schemas_dir))
        with pytest.raises(LabelSchemaNotFoundException):
            repo.get_schema(DocumentKind.E14_CAMARA)
        # Verify it's NOT a FileNotFoundError leaking through
        try:
            repo.get_schema(DocumentKind.E14_CAMARA)
        except LabelSchemaNotFoundException:
            pass
        except FileNotFoundError:
            pytest.fail("FileNotFoundError leaked through domain boundary!")

    def test_cache_returns_same_object(self, repo_with_senado):
        schema1 = repo_with_senado.get_schema(DocumentKind.E14_SENADO)
        schema2 = repo_with_senado.get_schema(DocumentKind.E14_SENADO)
        assert schema1 is schema2


class TestListKinds:
    def test_returns_all_document_kinds(self, repo_with_senado):
        kinds = repo_with_senado.list_kinds()
        assert DocumentKind.E14_SENADO in kinds
        assert DocumentKind.E14_CAMARA in kinds
