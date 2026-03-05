"""Unit tests — ListAnnotationsUseCase (now validates document existence)."""
from __future__ import annotations
from unittest.mock import MagicMock
import pytest
from src.domain.entities.annotation import Annotation
from src.domain.entities.bounding_box import BoundingBox
from src.domain.entities.document_kind import DocumentKind
from src.domain.entities.labeling_document import LabelingDocument
from src.domain.exceptions.document_not_found_exception import DocumentNotFoundException
from src.application.use_cases.list_annotations_use_case import ListAnnotationsUseCase


def _ann(id_: str, page: int = 1) -> Annotation:
    return Annotation(
        id=id_,
        document_id="doc-1",
        page_number=page,
        label="TotalSufragantes",
        bbox=BoundingBox.from_rect(0, 0, 50, 25),
        value_string="0",
    )


def _make_doc() -> LabelingDocument:
    return LabelingDocument(
        id="doc-1",
        original_filename="a.pdf",
        storage_path="/tmp/a.pdf",
        document_kind=DocumentKind.E14_SENADO,
    )


class TestListAnnotationsUseCase:
    def test_returns_all_annotations_for_document(self):
        ann_repo = MagicMock()
        doc_repo = MagicMock()
        doc_repo.find_by_id.return_value = _make_doc()
        ann_repo.find_by_document.return_value = [_ann("a1"), _ann("a2")]

        use_case = ListAnnotationsUseCase(ann_repo, doc_repo)
        result = use_case.execute("doc-1")

        assert len(result) == 2

    def test_filters_by_page(self):
        ann_repo = MagicMock()
        doc_repo = MagicMock()
        doc_repo.find_by_id.return_value = _make_doc()
        ann_repo.find_by_document_and_page.return_value = [_ann("a1", page=2)]

        use_case = ListAnnotationsUseCase(ann_repo, doc_repo)
        result = use_case.execute("doc-1", page_number=2)

        ann_repo.find_by_document_and_page.assert_called_once_with("doc-1", 2)
        assert len(result) == 1

    def test_nonexistent_document_raises_exception(self):
        ann_repo = MagicMock()
        doc_repo = MagicMock()
        doc_repo.find_by_id.side_effect = DocumentNotFoundException("doc-999")

        use_case = ListAnnotationsUseCase(ann_repo, doc_repo)

        with pytest.raises(DocumentNotFoundException):
            use_case.execute("doc-999")

    def test_nonexistent_document_does_not_query_annotations(self):
        ann_repo = MagicMock()
        doc_repo = MagicMock()
        doc_repo.find_by_id.side_effect = DocumentNotFoundException("doc-999")

        use_case = ListAnnotationsUseCase(ann_repo, doc_repo)

        with pytest.raises(DocumentNotFoundException):
            use_case.execute("doc-999")

        ann_repo.find_by_document.assert_not_called()
        ann_repo.find_by_document_and_page.assert_not_called()
