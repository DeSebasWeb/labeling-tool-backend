"""Unit tests — SaveAnnotationUseCase (pure mocks, no I/O)."""
from __future__ import annotations
from unittest.mock import MagicMock
import pytest
from src.domain.entities.bounding_box import BoundingBox
from src.domain.entities.document_kind import DocumentKind
from src.domain.entities.label_definition import LabelDefinition
from src.domain.entities.label_schema import LabelSchema
from src.domain.entities.labeling_document import LabelingDocument
from src.domain.exceptions.document_not_found_exception import DocumentNotFoundException
from src.domain.exceptions.invalid_label_exception import InvalidLabelException
from src.application.use_cases.save_annotation_use_case import SaveAnnotationUseCase


def _bbox() -> BoundingBox:
    return BoundingBox.from_rect(0, 0, 100, 50)


def _make_schema(*names: str) -> LabelSchema:
    labels = [LabelDefinition(name=n, description="", repeats_per_page=False) for n in names]
    return LabelSchema(document_kind=DocumentKind.E14_SENADO, labels=labels)


def _make_document() -> LabelingDocument:
    return LabelingDocument(
        id="doc-1",
        original_filename="acta.pdf",
        storage_path="/tmp/acta.pdf",
        document_kind=DocumentKind.E14_SENADO,
    )


def _make_use_case(document, schema):
    ann_repo = MagicMock()
    doc_repo = MagicMock()
    schema_repo = MagicMock()

    doc_repo.find_by_id.return_value = document
    schema_repo.get_schema.return_value = schema

    return SaveAnnotationUseCase(ann_repo, doc_repo, schema_repo), ann_repo, doc_repo


class TestSaveAnnotationUseCase:
    def test_returns_annotation_with_correct_fields(self):
        doc = _make_document()
        use_case, ann_repo, doc_repo = _make_use_case(doc, _make_schema("TotalSufragantes"))

        ann = use_case.execute("doc-1", 1, "TotalSufragantes", _bbox(), "150")

        assert ann.document_id == "doc-1"
        assert ann.page_number == 1
        assert ann.label == "TotalSufragantes"
        assert ann.value_string == "150"
        assert ann.confidence == 1.0

    def test_calls_save_on_annotation_repo(self):
        doc = _make_document()
        use_case, ann_repo, doc_repo = _make_use_case(doc, _make_schema("TotalSufragantes"))

        use_case.execute("doc-1", 1, "TotalSufragantes", _bbox(), "150")

        ann_repo.save.assert_called_once()

    def test_increments_document_annotations(self):
        doc = _make_document()
        use_case, ann_repo, doc_repo = _make_use_case(doc, _make_schema("TotalSufragantes"))

        use_case.execute("doc-1", 1, "TotalSufragantes", _bbox(), "150")

        assert doc.total_annotations == 1
        doc_repo.save.assert_called_once_with(doc)

    def test_invalid_label_raises_exception(self):
        doc = _make_document()
        use_case, _, _ = _make_use_case(doc, _make_schema("TotalSufragantes"))

        with pytest.raises(InvalidLabelException):
            use_case.execute("doc-1", 1, "EtiquetaFalsa", _bbox(), "abc")

    def test_document_not_found_propagates(self):
        ann_repo = MagicMock()
        doc_repo = MagicMock()
        schema_repo = MagicMock()
        doc_repo.find_by_id.side_effect = DocumentNotFoundException("doc-999")

        use_case = SaveAnnotationUseCase(ann_repo, doc_repo, schema_repo)

        with pytest.raises(DocumentNotFoundException):
            use_case.execute("doc-999", 1, "TotalSufragantes", _bbox(), "0")
