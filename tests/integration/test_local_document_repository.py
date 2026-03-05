"""Integration tests — LocalDocumentRepository (real filesystem via tmp_path)."""
from __future__ import annotations
import json
import pytest
from src.domain.entities.document_kind import DocumentKind
from src.domain.entities.document_page import DocumentPage
from src.domain.entities.labeling_document import LabelingDocument
from src.domain.entities.labeling_status import LabelingStatus
from src.domain.exceptions.document_not_found_exception import DocumentNotFoundException
from src.infrastructure.persistence.local_document_repository import LocalDocumentRepository


def _make_doc(id_: str = "doc-1") -> LabelingDocument:
    return LabelingDocument(
        id=id_,
        original_filename="acta.pdf",
        storage_path=f"/tmp/{id_}.pdf",
        document_kind=DocumentKind.E14_SENADO,
    )


@pytest.fixture
def repo(tmp_path):
    return LocalDocumentRepository(str(tmp_path / "documents"))


class TestSaveAndFindById:
    def test_saved_document_can_be_retrieved(self, repo):
        doc = _make_doc()
        repo.save(doc)
        found = repo.find_by_id("doc-1")
        assert found.id == "doc-1"
        assert found.original_filename == "acta.pdf"
        assert found.document_kind == DocumentKind.E14_SENADO

    def test_status_persisted(self, repo):
        doc = _make_doc()
        doc.mark_done()
        repo.save(doc)
        found = repo.find_by_id("doc-1")
        assert found.status == LabelingStatus.DONE

    def test_pages_persisted(self, repo):
        doc = _make_doc()
        doc.add_page(DocumentPage(
            page_number=1, image_path="/tmp/p1.png",
            width_px=1240, height_px=1754,
            width_inch=8.5, height_inch=11.0,
        ))
        repo.save(doc)
        found = repo.find_by_id("doc-1")
        assert found.page_count == 1
        assert found.pages[0].page_number == 1

    def test_find_nonexistent_raises(self, repo):
        with pytest.raises(DocumentNotFoundException):
            repo.find_by_id("no-existe")

    def test_save_overwrites_previous(self, repo):
        doc = _make_doc()
        repo.save(doc)
        doc.increment_annotations()
        repo.save(doc)
        found = repo.find_by_id("doc-1")
        assert found.total_annotations == 1


class TestFindAll:
    def test_returns_all_saved_documents(self, repo):
        repo.save(_make_doc("d1"))
        repo.save(_make_doc("d2"))
        repo.save(_make_doc("d3"))
        result = repo.find_all()
        assert len(result) == 3

    def test_sorted_newest_first(self, repo):
        import time
        repo.save(_make_doc("old"))
        time.sleep(0.01)
        repo.save(_make_doc("new"))
        result = repo.find_all()
        ids = [d.id for d in result]
        assert ids.index("new") < ids.index("old")

    def test_corrupt_json_skipped(self, repo, tmp_path):
        repo.save(_make_doc("good"))
        corrupt_path = tmp_path / "documents" / "corrupt.json"
        corrupt_path.write_text("{not valid json", encoding="utf-8")
        result = repo.find_all()
        assert len(result) == 1
        assert result[0].id == "good"


class TestDelete:
    def test_delete_removes_document(self, repo):
        repo.save(_make_doc())
        repo.delete("doc-1")
        with pytest.raises(DocumentNotFoundException):
            repo.find_by_id("doc-1")

    def test_delete_nonexistent_raises(self, repo):
        with pytest.raises(DocumentNotFoundException):
            repo.delete("no-existe")
