"""E2E — Documents API (upload tested with a mock renderer to avoid pypdfium2 dep)."""
from __future__ import annotations
import io
import pytest
from unittest.mock import MagicMock, patch
from src.domain.entities.document_kind import DocumentKind
from src.domain.entities.document_page import DocumentPage
from src.domain.entities.labeling_document import LabelingDocument
from src.infrastructure.persistence.local_document_repository import LocalDocumentRepository


def _seed_document(client, document_kind: str = "E14_SENADO") -> dict:
    """Inject a document directly into the repo and return its JSON repr."""
    from src.infrastructure.config import get_settings
    settings = get_settings()
    repo = LocalDocumentRepository(settings.documents_storage_dir)

    doc = LabelingDocument(
        id="doc-e2e-1",
        original_filename="acta.pdf",
        storage_path="/tmp/acta.pdf",
        document_kind=DocumentKind(document_kind),
    )
    doc.add_page(DocumentPage(
        page_number=1, image_path="/tmp/page_001.png",
        width_px=1240, height_px=1754,
        width_inch=8.5, height_inch=11.0,
    ))
    repo.save(doc)
    return {"id": doc.id, "document_kind": document_kind}


class TestListDocuments:
    def test_empty_list(self, client):
        resp = client.get("/documents")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_seeded_document_appears_in_list(self, client, tmp_path):
        _seed_document(client)
        resp = client.get("/documents")
        assert resp.status_code == 200
        assert len(resp.json()) == 1
        assert resp.json()[0]["id"] == "doc-e2e-1"


class TestGetDocument:
    def test_get_existing_document(self, client, tmp_path):
        _seed_document(client)
        resp = client.get("/documents/doc-e2e-1")
        assert resp.status_code == 200
        assert resp.json()["id"] == "doc-e2e-1"

    def test_get_nonexistent_returns_404(self, client):
        resp = client.get("/documents/no-existe")
        assert resp.status_code == 404


class TestGetPages:
    def test_returns_pages_for_document(self, client, tmp_path):
        _seed_document(client)
        resp = client.get("/documents/doc-e2e-1/pages")
        assert resp.status_code == 200
        pages = resp.json()
        assert len(pages) == 1
        assert pages[0]["page_number"] == 1
        assert "image_url" in pages[0]

    def test_nonexistent_document_returns_404(self, client):
        resp = client.get("/documents/no-existe/pages")
        assert resp.status_code == 404


class TestMarkDone:
    def test_mark_done_changes_status(self, client, tmp_path):
        _seed_document(client)
        resp = client.patch("/documents/doc-e2e-1/done")
        assert resp.status_code == 200
        assert resp.json()["status"] == "DONE"

    def test_mark_done_nonexistent_returns_404(self, client):
        resp = client.patch("/documents/no-existe/done")
        assert resp.status_code == 404


class TestUploadDocument:
    def test_non_pdf_returns_400(self, client):
        data = io.BytesIO(b"not a pdf")
        resp = client.post(
            "/documents",
            files={"file": ("image.png", data, "image/png")},
            data={"document_kind": "E14_SENADO"},
        )
        assert resp.status_code == 400

    def test_valid_pdf_upload_with_mock_renderer(self, client, tmp_path):
        """Mocks pypdfium2 renderer to avoid needing a real PDF file."""
        mock_page = DocumentPage(
            page_number=1, image_path=str(tmp_path / "page_001.png"),
            width_px=1240, height_px=1754,
            width_inch=8.5, height_inch=11.0,
        )

        with patch("src.infrastructure.renderer.pypdfium2_renderer.pdfium") as mock_pdfium:
            mock_doc = MagicMock()
            mock_doc.__len__ = lambda self: 1
            mock_page_obj = MagicMock()
            mock_page_obj.get_width.return_value = 612.0
            mock_page_obj.get_height.return_value = 792.0
            mock_bitmap = MagicMock()
            mock_pil = MagicMock()
            mock_pil.width = 1240
            mock_pil.height = 1754
            mock_bitmap.to_pil.return_value = mock_pil
            mock_page_obj.render.return_value = mock_bitmap
            mock_doc.__getitem__ = lambda self, i: mock_page_obj
            mock_pdfium.PdfDocument.return_value = mock_doc

            pdf_content = b"%PDF-1.4 fake content"
            resp = client.post(
                "/documents",
                files={"file": ("acta.pdf", io.BytesIO(pdf_content), "application/pdf")},
                data={"document_kind": "E14_SENADO"},
            )

        assert resp.status_code == 201
        body = resp.json()
        assert body["original_filename"] == "acta.pdf"
        assert body["document_kind"] == "E14_SENADO"
        assert body["status"] == "PENDING"
