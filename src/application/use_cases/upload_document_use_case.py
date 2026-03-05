from __future__ import annotations
import uuid
from ...domain.entities.document_kind import DocumentKind
from ...domain.entities.labeling_document import LabelingDocument
from ...domain.exceptions.invalid_document_exception import InvalidDocumentException
from ...domain.exceptions.pdf_render_exception import PdfRenderException
from ...domain.ports.document_repository_port import IDocumentRepository
from ...domain.ports.pdf_renderer_port import IPdfRenderer


class UploadDocumentUseCase:
    """
    Registra un PDF nuevo: lo persiste y renderiza todas sus páginas a PNG.
    Devuelve el LabelingDocument creado.
    """

    def __init__(
        self,
        document_repository: IDocumentRepository,
        pdf_renderer: IPdfRenderer,
        pages_dir: str,
        render_dpi: int,
    ) -> None:
        self._document_repository = document_repository
        self._pdf_renderer = pdf_renderer
        self._pages_dir = pages_dir
        self._render_dpi = render_dpi

    def execute(
        self,
        original_filename: str,
        storage_path: str,
        document_kind: DocumentKind,
    ) -> LabelingDocument:
        if not original_filename.lower().endswith(".pdf"):
            raise InvalidDocumentException("Solo se aceptan archivos PDF")

        document_id = str(uuid.uuid4())

        document = LabelingDocument(
            id=document_id,
            original_filename=original_filename,
            storage_path=storage_path,
            document_kind=document_kind,
        )

        try:
            pages = self._pdf_renderer.render(
                pdf_path=storage_path,
                document_id=document_id,
                output_dir=self._pages_dir,
                dpi=self._render_dpi,
            )
        except Exception as e:
            raise PdfRenderException(document_id, str(e))

        for page in pages:
            document.add_page(page)

        self._document_repository.save(document)
        return document
