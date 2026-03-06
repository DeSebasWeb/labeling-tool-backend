from __future__ import annotations
import json
from ...domain.ports.blob_storage_port import IBlobStoragePort


class BlobDocumentRepository:
    """
    Accede a _document.json almacenado en blob storage por cada PDF.
    El prefix es el nombre del PDF sin extensión.
    """

    def __init__(self, blob_storage: IBlobStoragePort) -> None:
        self._blob = blob_storage

    def get_document_meta(self, container_name: str, blob_name: str) -> dict:
        """Descarga y parsea _document.json para un PDF dado."""
        import os
        prefix = os.path.splitext(blob_name)[0]
        doc_blob = f"{prefix}/_document.json"
        raw = self._blob.download(container_name, doc_blob)
        return json.loads(raw.decode("utf-8"))

    def get_page_image(self, container_name: str, blob_name: str, page_number: int) -> bytes:
        """Descarga el PNG de una página específica."""
        import os
        prefix = os.path.splitext(blob_name)[0]
        page_blob = f"{prefix}/page_{page_number:03d}.png"
        return self._blob.download(container_name, page_blob)
