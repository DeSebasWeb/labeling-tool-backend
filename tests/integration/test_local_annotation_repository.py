"""Integration tests — LocalAnnotationRepository (real filesystem via tmp_path)."""
from __future__ import annotations
import pytest
from src.domain.entities.annotation import Annotation
from src.domain.entities.bounding_box import BoundingBox
from src.domain.exceptions.annotation_not_found_exception import AnnotationNotFoundException
from src.infrastructure.persistence.local_annotation_repository import LocalAnnotationRepository


def _ann(id_: str, doc_id: str = "doc-1", page: int = 1, label: str = "TotalSufragantes") -> Annotation:
    return Annotation(
        id=id_,
        document_id=doc_id,
        page_number=page,
        label=label,
        bbox=BoundingBox.from_rect(0, 0, 100, 50),
        value_string="test",
    )


@pytest.fixture
def repo(tmp_path):
    return LocalAnnotationRepository(str(tmp_path / "annotations"))


class TestSaveAndFindById:
    def test_saved_annotation_can_be_retrieved(self, repo):
        ann = _ann("a1")
        repo.save(ann)
        found = repo.find_by_id("a1")
        assert found.id == "a1"
        assert found.label == "TotalSufragantes"

    def test_bbox_roundtrip(self, repo):
        ann = _ann("a1")
        repo.save(ann)
        found = repo.find_by_id("a1")
        assert found.bbox.to_polygon() == ann.bbox.to_polygon()

    def test_find_nonexistent_raises(self, repo):
        with pytest.raises(AnnotationNotFoundException):
            repo.find_by_id("no-existe")

    def test_save_is_atomic_tmp_replaced(self, repo, tmp_path):
        ann = _ann("a1")
        repo.save(ann)
        tmp_file = tmp_path / "annotations" / "a1.json.tmp"
        assert not tmp_file.exists()


class TestFindByDocument:
    def test_returns_only_matching_document(self, repo):
        repo.save(_ann("a1", doc_id="doc-1"))
        repo.save(_ann("a2", doc_id="doc-2"))
        repo.save(_ann("a3", doc_id="doc-1"))

        result = repo.find_by_document("doc-1")
        ids = {a.id for a in result}
        assert ids == {"a1", "a3"}

    def test_empty_when_no_annotations(self, repo):
        assert repo.find_by_document("doc-999") == []


class TestFindByDocumentAndPage:
    def test_filters_by_page(self, repo):
        repo.save(_ann("a1", page=1))
        repo.save(_ann("a2", page=2))
        repo.save(_ann("a3", page=1))

        result = repo.find_by_document_and_page("doc-1", 1)
        ids = {a.id for a in result}
        assert ids == {"a1", "a3"}


class TestDelete:
    def test_delete_removes_annotation(self, repo):
        repo.save(_ann("a1"))
        repo.delete("a1")
        with pytest.raises(AnnotationNotFoundException):
            repo.find_by_id("a1")

    def test_delete_nonexistent_raises(self, repo):
        with pytest.raises(AnnotationNotFoundException):
            repo.delete("no-existe")


class TestDeleteByDocument:
    def test_removes_all_annotations_for_document(self, repo):
        repo.save(_ann("a1", doc_id="doc-1"))
        repo.save(_ann("a2", doc_id="doc-1"))
        repo.save(_ann("a3", doc_id="doc-2"))

        repo.delete_by_document("doc-1")

        assert repo.find_by_document("doc-1") == []
        assert len(repo.find_by_document("doc-2")) == 1
