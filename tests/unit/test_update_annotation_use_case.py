"""Unit tests — UpdateAnnotationUseCase."""
from __future__ import annotations
from unittest.mock import MagicMock
import pytest
from src.domain.entities.annotation import Annotation
from src.domain.entities.bounding_box import BoundingBox
from src.domain.entities.document_kind import DocumentKind
from src.domain.entities.label_definition import LabelDefinition
from src.domain.entities.label_schema import LabelSchema
from src.domain.entities.labeling_document import LabelingDocument
from src.domain.exceptions.annotation_not_found_exception import AnnotationNotFoundException
from src.domain.exceptions.invalid_label_exception import InvalidLabelException
from src.application.use_cases.update_annotation_use_case import UpdateAnnotationUseCase


def _ann(doc_id: str = "doc-1") -> Annotation:
    return Annotation(
        id="ann-1",
        document_id=doc_id,
        page_number=1,
        label="TotalSufragantes",
        bbox=BoundingBox.from_rect(0, 0, 100, 50),
        value_string="old",
    )


def _make_schema(*names: str) -> LabelSchema:
    labels = [LabelDefinition(name=n, description="", repeats_per_page=False) for n in names]
    return LabelSchema(document_kind=DocumentKind.E14_SENADO, labels=labels)


def _make_doc() -> LabelingDocument:
    return LabelingDocument(
        id="doc-1",
        original_filename="a.pdf",
        storage_path="/tmp/a.pdf",
        document_kind=DocumentKind.E14_SENADO,
    )


def _use_case(ann, schema=None, doc=None):
    ann_repo = MagicMock()
    doc_repo = MagicMock()
    schema_repo = MagicMock()
    ann_repo.find_by_id.return_value = ann
    if doc:
        doc_repo.find_by_id.return_value = doc
    if schema:
        schema_repo.get_schema.return_value = schema
    return UpdateAnnotationUseCase(ann_repo, doc_repo, schema_repo), ann_repo


class TestUpdateAnnotationUseCase:
    def test_updates_value_string(self):
        ann = _ann()
        use_case, ann_repo = _use_case(ann)
        result = use_case.execute("ann-1", "doc-1", value_string="new")
        assert result.value_string == "new"
        ann_repo.save.assert_called_once()

    def test_updates_bbox(self):
        ann = _ann()
        use_case, ann_repo = _use_case(ann)
        new_bbox = BoundingBox.from_rect(5, 5, 50, 30)
        result = use_case.execute("ann-1", "doc-1", bbox=new_bbox)
        assert result.bbox == new_bbox
        ann_repo.save.assert_called_once()

    def test_updates_label_when_valid(self):
        ann = _ann()
        doc = _make_doc()
        schema = _make_schema("TotalSufragantes", "VotosNulos")
        use_case, ann_repo = _use_case(ann, schema=schema, doc=doc)
        result = use_case.execute("ann-1", "doc-1", label="VotosNulos")
        assert result.label == "VotosNulos"

    def test_invalid_label_raises_exception(self):
        ann = _ann()
        doc = _make_doc()
        schema = _make_schema("TotalSufragantes")
        use_case, _ = _use_case(ann, schema=schema, doc=doc)
        with pytest.raises(InvalidLabelException):
            use_case.execute("ann-1", "doc-1", label="EtiquetaFalsa")

    def test_wrong_document_id_raises_value_error(self):
        ann = _ann(doc_id="doc-1")
        use_case, ann_repo = _use_case(ann)
        with pytest.raises(ValueError, match="no pertenece"):
            use_case.execute("ann-1", "doc-OTRO", value_string="x")

    def test_wrong_document_id_does_not_save(self):
        ann = _ann(doc_id="doc-1")
        use_case, ann_repo = _use_case(ann)
        with pytest.raises(ValueError):
            use_case.execute("ann-1", "doc-OTRO", value_string="x")
        ann_repo.save.assert_not_called()

    def test_no_changes_does_not_call_save(self):
        ann = _ann()
        use_case, ann_repo = _use_case(ann)
        use_case.execute("ann-1", "doc-1")  # all None
        ann_repo.save.assert_not_called()
