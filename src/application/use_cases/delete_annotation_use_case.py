from __future__ import annotations
from ...domain.ports.annotation_repository_port import IAnnotationRepository
from ...domain.ports.document_repository_port import IDocumentRepository


class DeleteAnnotationUseCase:
    """Elimina una anotación y actualiza el contador del documento."""

    def __init__(
        self,
        annotation_repository: IAnnotationRepository,
        document_repository: IDocumentRepository,
    ) -> None:
        self._annotation_repository = annotation_repository
        self._document_repository = document_repository

    def execute(self, annotation_id: str) -> None:
        annotation = self._annotation_repository.find_by_id(annotation_id)
        document = self._document_repository.find_by_id(annotation.document_id)

        self._annotation_repository.delete(annotation_id)
        document.decrement_annotations()
        self._document_repository.save(document)
