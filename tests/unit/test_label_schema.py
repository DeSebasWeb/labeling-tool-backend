"""Unit tests — LabelSchema + LabelDefinition domain entities."""
from __future__ import annotations
from src.domain.entities.document_kind import DocumentKind
from src.domain.entities.label_definition import LabelDefinition
from src.domain.entities.label_schema import LabelSchema


def _schema(*names: str) -> LabelSchema:
    labels = [LabelDefinition(name=n, description="", repeats_per_page=False) for n in names]
    return LabelSchema(document_kind=DocumentKind.E14_SENADO, labels=labels)


class TestIsValidLabel:
    def test_known_label_returns_true(self):
        schema = _schema("TotalSufragantes", "VotosNulos")
        assert schema.is_valid_label("TotalSufragantes") is True

    def test_unknown_label_returns_false(self):
        schema = _schema("TotalSufragantes")
        assert schema.is_valid_label("NoExiste") is False

    def test_case_sensitive(self):
        schema = _schema("TotalSufragantes")
        assert schema.is_valid_label("totalsufragantes") is False


class TestLabelNames:
    def test_returns_all_names(self):
        schema = _schema("A", "B", "C")
        assert schema.label_names() == ["A", "B", "C"]

    def test_empty_schema(self):
        schema = _schema()
        assert schema.label_names() == []


class TestFind:
    def test_finds_existing_label(self):
        schema = _schema("Pagina", "TotalSufragantes")
        found = schema.find("Pagina")
        assert found is not None
        assert found.name == "Pagina"

    def test_returns_none_for_missing(self):
        schema = _schema("Pagina")
        assert schema.find("NoExiste") is None
