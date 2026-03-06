from __future__ import annotations
import json
import os
from ...domain.entities.workspace import Workspace
from ...domain.exceptions.invalid_document_exception import InvalidDocumentException
from ...domain.exceptions.pdf_render_exception import PdfRenderException
from ...domain.ports.blob_storage_port import IBlobStoragePort
from ...domain.ports.workspace_repository_port import IWorkspaceRepository
from ...infrastructure.renderer.pypdfium2_renderer import Pypdfium2Renderer


class UploadDocumentToWorkspaceUseCase:
    """
    Sube un PDF al container del workspace en blob storage,
    renderiza páginas en memoria, sube PNGs al blob,
    y crea _document.json con metadata. No usa disco local.
    """

    def __init__(
        self,
        workspace_repository: IWorkspaceRepository,
        blob_storage: IBlobStoragePort,
        pdf_renderer: Pypdfium2Renderer,
        render_dpi: int,
    ) -> None:
        self._workspace_repository = workspace_repository
        self._blob_storage = blob_storage
        self._pdf_renderer = pdf_renderer
        self._render_dpi = render_dpi

    def execute(
        self,
        workspace_id: str,
        original_filename: str,
        file_data: bytes,
    ) -> Workspace:
        if not original_filename.lower().endswith(".pdf"):
            raise InvalidDocumentException("Solo se aceptan archivos PDF")

        workspace = self._workspace_repository.find_by_id(workspace_id)
        container = workspace.container_name
        prefix = os.path.splitext(original_filename)[0]

        # 1. Subir PDF original al blob
        self._blob_storage.upload(container, original_filename, file_data)

        # 2. Renderizar páginas en memoria
        try:
            rendered_pages = self._pdf_renderer.render_to_bytes(file_data, self._render_dpi)
        except Exception as e:
            raise PdfRenderException(original_filename, str(e))

        # 3. Subir cada PNG al blob
        pages_meta = []
        for rp in rendered_pages:
            blob_name = f"{prefix}/page_{rp.page_number:03d}.png"
            self._blob_storage.upload(container, blob_name, rp.png_bytes)
            pages_meta.append({
                "page_number": rp.page_number,
                "width_px": rp.width_px,
                "height_px": rp.height_px,
                "width_inch": rp.width_inch,
                "height_inch": rp.height_inch,
            })

        # 4. Crear _document.json en el blob
        doc_meta = {
            "original_filename": original_filename,
            "document_kind": workspace.document_kind.value,
            "page_count": len(rendered_pages),
            "pages": pages_meta,
            "status": "PENDING",
            "total_annotations": 0,
        }
        doc_blob = f"{prefix}/_document.json"
        self._blob_storage.upload(
            container, doc_blob,
            json.dumps(doc_meta, ensure_ascii=False, indent=2).encode("utf-8"),
        )

        # 5. Registrar en workspace
        workspace.register_document(original_filename)
        self._workspace_repository.save(workspace)

        return workspace
