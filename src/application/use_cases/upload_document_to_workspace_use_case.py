from __future__ import annotations
import os
import uuid
import tempfile
from ...domain.entities.workspace import Workspace
from ...domain.entities.labeling_document import LabelingDocument
from ...domain.exceptions.workspace_not_found_exception import WorkspaceNotFoundException
from ...domain.exceptions.blob_storage_exception import BlobStorageException
from ...domain.exceptions.invalid_document_exception import InvalidDocumentException
from ...domain.exceptions.pdf_render_exception import PdfRenderException
from ...domain.ports.blob_storage_port import IBlobStoragePort
from ...domain.ports.workspace_repository_port import IWorkspaceRepository
from ...domain.ports.document_repository_port import IDocumentRepository
from ...domain.ports.pdf_renderer_port import IPdfRenderer


class UploadDocumentToWorkspaceUseCase:
    """
    Sube un PDF al container del workspace en blob storage, lo registra como PENDING,
    y crea el documento local con las páginas renderizadas a PNG para el editor.
    """

    def __init__(
        self,
        workspace_repository: IWorkspaceRepository,
        blob_storage: IBlobStoragePort,
        document_repository: IDocumentRepository,
        pdf_renderer: IPdfRenderer,
        upload_dir: str,
        pages_dir: str,
        render_dpi: int,
    ) -> None:
        self._workspace_repository = workspace_repository
        self._blob_storage = blob_storage
        self._document_repository = document_repository
        self._pdf_renderer = pdf_renderer
        self._upload_dir = upload_dir
        self._pages_dir = pages_dir
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

        # 1. Subir al blob
        self._blob_storage.upload(
            container_name=workspace.container_name,
            blob_name=original_filename,
            data=file_data,
        )

        # 2. Guardar PDF en disco local para renderizado
        os.makedirs(self._upload_dir, exist_ok=True)
        safe_name = f"{uuid.uuid4()}_{original_filename}"
        local_path = os.path.join(self._upload_dir, safe_name)
        with open(local_path, "wb") as f:
            f.write(file_data)

        # 3. Crear documento local y renderizar páginas
        document_id = str(uuid.uuid4())
        document = LabelingDocument(
            id=document_id,
            original_filename=original_filename,
            storage_path=local_path,
            document_kind=workspace.document_kind,
        )

        try:
            pages = self._pdf_renderer.render(
                pdf_path=local_path,
                document_id=document_id,
                output_dir=self._pages_dir,
                dpi=self._render_dpi,
            )
        except Exception as e:
            raise PdfRenderException(document_id, str(e))

        for page in pages:
            document.add_page(page)

        self._document_repository.save(document)

        # 4. Registrar en workspace
        workspace.register_document(original_filename)
        self._workspace_repository.save(workspace)

        return workspace
