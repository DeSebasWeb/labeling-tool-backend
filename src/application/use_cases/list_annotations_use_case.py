from __future__ import annotations
from ...domain.entities.annotation import Annotation
from ...domain.ports.annotation_repository_port import IAnnotationRepository
from ...domain.ports.document_repository_port import IDocumentRepository


class ListAnnotationsUseCase:
    """Lista anotaciones de un documento, opcionalmente filtradas por página.
    Valida que el documento exista — evita retornar [] silencioso para IDs inexistentes.
    """

    def __init__(
        self,
        annotation_repository: IAnnotationRepository,
        document_repository: IDocumentRepository,
    ) -> None:
        self._annotation_repository = annotation_repository
        self._document_repository = document_repository

    def execute(self, document_id: str, page_number: int | None = None) -> list[Annotation]:
        self._document_repository.find_by_id(document_id)  # raises DocumentNotFoundException if missing
        if page_number is not None:
            return self._annotation_repository.find_by_document_and_page(
                document_id, page_number
            )
        return self._annotation_repository.find_by_document(document_id)
