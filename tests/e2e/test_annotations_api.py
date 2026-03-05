"""E2E — Annotations CRUD + export flow (no real PDF — document is injected directly)."""
from __future__ import annotations
import pytest
from src.domain.entities.document_kind import DocumentKind
from src.domain.entities.document_page import DocumentPage
from src.domain.entities.labeling_document import LabelingDocument
from src.infrastructure.dependencies import get_document_repository


def _seed_document(client, tmp_path) -> str:
    """Inject a document directly into the repo (bypasses PDF rendering)."""
    from src.infrastructure.config import get_settings
    settings = get_settings()
    from src.infrastructure.persistence.local_document_repository import LocalDocumentRepository
    repo = LocalDocumentRepository(settings.documents_storage_dir)

    doc = LabelingDocument(
        id="test-doc-1",
        original_filename="acta.pdf",
        storage_path="/tmp/acta.pdf",
        document_kind=DocumentKind.E14_SENADO,
    )
    doc.add_page(DocumentPage(
        page_number=1,
        image_path="/tmp/page_001.png",
        width_px=1240,
        height_px=1754,
        width_inch=8.5,
        height_inch=11.0,
    ))
    repo.save(doc)
    return doc.id


BBOX = {"x0": 10, "y0": 10, "x1": 100, "y1": 10, "x2": 100, "y2": 50, "x3": 10, "y3": 50}


class TestCreateAnnotation:
    def test_create_returns_201(self, client, tmp_path):
        doc_id = _seed_document(client, tmp_path)
        payload = {
            "page_number": 1,
            "label": "TotalSufragantes",
            "bbox": BBOX,
            "value_string": "150",
        }
        resp = client.post(f"/documents/{doc_id}/annotations", json=payload)
        assert resp.status_code == 201
        body = resp.json()
        assert body["label"] == "TotalSufragantes"
        assert body["value_string"] == "150"
        assert body["document_id"] == doc_id
        assert len(body["bbox"]) == 8

    def test_create_invalid_label_returns_400(self, client, tmp_path):
        doc_id = _seed_document(client, tmp_path)
        payload = {
            "page_number": 1,
            "label": "EtiquetaFalsa",
            "bbox": BBOX,
            "value_string": "abc",
        }
        resp = client.post(f"/documents/{doc_id}/annotations", json=payload)
        assert resp.status_code == 400

    def test_create_page_zero_returns_422(self, client, tmp_path):
        doc_id = _seed_document(client, tmp_path)
        payload = {
            "page_number": 0,
            "label": "TotalSufragantes",
            "bbox": BBOX,
            "value_string": "0",
        }
        resp = client.post(f"/documents/{doc_id}/annotations", json=payload)
        assert resp.status_code == 422

    def test_create_negative_bbox_returns_422(self, client, tmp_path):
        doc_id = _seed_document(client, tmp_path)
        bad_bbox = {**BBOX, "x0": -1}
        payload = {
            "page_number": 1,
            "label": "TotalSufragantes",
            "bbox": bad_bbox,
            "value_string": "0",
        }
        resp = client.post(f"/documents/{doc_id}/annotations", json=payload)
        assert resp.status_code == 422


class TestListAnnotations:
    def test_nonexistent_document_returns_404(self, client):
        resp = client.get("/documents/no-existe/annotations")
        assert resp.status_code == 404

    def test_list_returns_created_annotations(self, client, tmp_path):
        doc_id = _seed_document(client, tmp_path)
        payload = {"page_number": 1, "label": "TotalSufragantes", "bbox": BBOX, "value_string": "10"}
        client.post(f"/documents/{doc_id}/annotations", json=payload)

        resp = client.get(f"/documents/{doc_id}/annotations")
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    def test_list_filter_by_page(self, client, tmp_path):
        doc_id = _seed_document(client, tmp_path)
        client.post(f"/documents/{doc_id}/annotations", json={"page_number": 1, "label": "TotalSufragantes", "bbox": BBOX, "value_string": "1"})
        client.post(f"/documents/{doc_id}/annotations", json={"page_number": 2, "label": "TipoDeVotoPartido", "bbox": BBOX, "value_string": "2"})

        resp = client.get(f"/documents/{doc_id}/annotations?page_number=1")
        assert resp.status_code == 200
        assert all(a["page_number"] == 1 for a in resp.json())


class TestUpdateAnnotation:
    def test_patch_value_string(self, client, tmp_path):
        doc_id = _seed_document(client, tmp_path)
        create_resp = client.post(f"/documents/{doc_id}/annotations", json={
            "page_number": 1, "label": "TotalSufragantes", "bbox": BBOX, "value_string": "old"
        })
        ann_id = create_resp.json()["id"]

        patch_resp = client.patch(
            f"/documents/{doc_id}/annotations/{ann_id}",
            json={"value_string": "new"},
        )
        assert patch_resp.status_code == 200
        assert patch_resp.json()["value_string"] == "new"

    def test_patch_nonexistent_returns_404(self, client, tmp_path):
        doc_id = _seed_document(client, tmp_path)
        resp = client.patch(
            f"/documents/{doc_id}/annotations/no-existe",
            json={"value_string": "x"},
        )
        assert resp.status_code == 404


class TestDeleteAnnotation:
    def test_delete_returns_204(self, client, tmp_path):
        doc_id = _seed_document(client, tmp_path)
        create_resp = client.post(f"/documents/{doc_id}/annotations", json={
            "page_number": 1, "label": "TotalSufragantes", "bbox": BBOX, "value_string": "10"
        })
        ann_id = create_resp.json()["id"]

        del_resp = client.delete(f"/documents/{doc_id}/annotations/{ann_id}")
        assert del_resp.status_code == 204

    def test_deleted_annotation_no_longer_listed(self, client, tmp_path):
        doc_id = _seed_document(client, tmp_path)
        create_resp = client.post(f"/documents/{doc_id}/annotations", json={
            "page_number": 1, "label": "TotalSufragantes", "bbox": BBOX, "value_string": "10"
        })
        ann_id = create_resp.json()["id"]
        client.delete(f"/documents/{doc_id}/annotations/{ann_id}")

        list_resp = client.get(f"/documents/{doc_id}/annotations")
        assert list_resp.status_code == 200
        assert list_resp.json() == []


class TestExportAnnotations:
    def test_export_returns_adi_format(self, client, tmp_path):
        doc_id = _seed_document(client, tmp_path)
        client.post(f"/documents/{doc_id}/annotations", json={
            "page_number": 1, "label": "TotalSufragantes", "bbox": BBOX, "value_string": "500"
        })

        resp = client.get(f"/documents/{doc_id}/export")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "succeeded"
        assert "analyzeResult" in body
        fields = body["analyzeResult"]["documents"][0]["fields"]
        assert "TotalSufragantes" in fields
        assert fields["TotalSufragantes"]["valueString"] == "500"

    def test_export_nonexistent_document_returns_404(self, client):
        resp = client.get("/documents/no-existe/export")
        assert resp.status_code == 404
