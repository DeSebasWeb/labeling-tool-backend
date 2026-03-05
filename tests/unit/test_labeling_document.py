"""Unit tests — LabelingDocument aggregate."""
from __future__ import annotations
import pytest
from src.domain.entities.document_kind import DocumentKind
from src.domain.entities.document_page import DocumentPage
from src.domain.entities.labeling_document import LabelingDocument
from src.domain.entities.labeling_status import LabelingStatus


def _make_doc(**kwargs) -> LabelingDocument:
    defaults = dict(
        id="doc-1",
        original_filename="test.pdf",
        storage_path="/tmp/test.pdf",
        document_kind=DocumentKind.E14_SENADO,
    )
    defaults.update(kwargs)
    return LabelingDocument(**defaults)


def _make_page(n: int) -> DocumentPage:
    return DocumentPage(
        page_number=n,
        image_path=f"/tmp/page_{n}.png",
        width_px=1240,
        height_px=1754,
        width_inch=8.5,
        height_inch=11.0,
    )


class TestAddPage:
    def test_page_count_increments(self):
        doc = _make_doc()
        doc.add_page(_make_page(1))
        doc.add_page(_make_page(2))
        assert doc.page_count == 2

    def test_updated_at_changes(self):
        doc = _make_doc()
        before = doc.updated_at
        doc.add_page(_make_page(1))
        assert doc.updated_at >= before


class TestIncrementAnnotations:
    def test_status_changes_to_in_progress_on_first(self):
        doc = _make_doc()
        assert doc.status == LabelingStatus.PENDING
        doc.increment_annotations()
        assert doc.status == LabelingStatus.IN_PROGRESS

    def test_counter_increments(self):
        doc = _make_doc()
        doc.increment_annotations()
        doc.increment_annotations()
        assert doc.total_annotations == 2


class TestDecrementAnnotations:
    def test_counter_decrements(self):
        doc = _make_doc()
        doc.increment_annotations()
        doc.increment_annotations()
        doc.decrement_annotations()
        assert doc.total_annotations == 1

    def test_never_goes_below_zero(self):
        doc = _make_doc()
        doc.decrement_annotations()
        assert doc.total_annotations == 0

    def test_status_returns_to_pending_at_zero(self):
        doc = _make_doc()
        doc.increment_annotations()
        doc.decrement_annotations()
        assert doc.status == LabelingStatus.PENDING


class TestMarkDoneAndExported:
    def test_mark_done_sets_status(self):
        doc = _make_doc()
        doc.mark_done()
        assert doc.status == LabelingStatus.DONE

    def test_mark_exported_sets_status(self):
        doc = _make_doc()
        doc.mark_exported()
        assert doc.status == LabelingStatus.EXPORTED
