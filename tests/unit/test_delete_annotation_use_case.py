"""Unit tests — DeleteAnnotationUseCase."""
from __future__ import annotations
from unittest.mock import MagicMock
import pytest
from src.domain.entities.annotation import Annotation
from src.domain.entities.bounding_box import BoundingBox
from src.domain.entities.document_kind import DocumentKind
from src.domain.entities.labeling_document import LabelingDocument
from src.domain.exceptions.annotation_not_found_exception import AnnotationNotFoundException
from src.application.use_cases.delete_annotation_use_case import DeleteAnnotationUseCase


def _make_annotation() -> Annotation:
    return Annotation(
        id="ann-1",
        document_id="doc-1",
        page_number=1,
        label="TotalSufragantes",
        bbox=BoundingBox.from_rect(0, 0, 50, 25),
        value_string="200",
    )


def _make_doc_with_annotations(count: int) -> LabelingDocument:
    doc = LabelingDocument(
        id="doc-1",
        original_filename="test.pdf",
        storage_path="/tmp/test.pdf",
        document_kind=DocumentKind.E14_SENADO,
    )
    for _ in range(count):
        doc.increment_annotations()
    return doc


class TestDeleteAnnotationUseCase:
    def test_calls_delete_on_repo(self):
        ann = _make_annotation()
        doc = _make_doc_with_annotations(1)

        ann_repo = MagicMock()
        doc_repo = MagicMock()
        ann_repo.find_by_id.return_value = ann
        doc_repo.find_by_id.return_value = doc

        use_case = DeleteAnnotationUseCase(ann_repo, doc_repo)
        use_case.execute("ann-1")

        ann_repo.delete.assert_called_once_with("ann-1")

    def test_decrements_document_counter(self):
        ann = _make_annotation()
        doc = _make_doc_with_annotations(2)

        ann_repo = MagicMock()
        doc_repo = MagicMock()
        ann_repo.find_by_id.return_value = ann
        doc_repo.find_by_id.return_value = doc

        use_case = DeleteAnnotationUseCase(ann_repo, doc_repo)
        use_case.execute("ann-1")

        assert doc.total_annotations == 1
        doc_repo.save.assert_called_once_with(doc)

    def test_annotation_not_found_propagates(self):
        ann_repo = MagicMock()
        doc_repo = MagicMock()
        ann_repo.find_by_id.side_effect = AnnotationNotFoundException("ann-999")

        use_case = DeleteAnnotationUseCase(ann_repo, doc_repo)

        with pytest.raises(AnnotationNotFoundException):
            use_case.execute("ann-999")
