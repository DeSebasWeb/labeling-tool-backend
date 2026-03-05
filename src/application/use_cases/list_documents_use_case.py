from __future__ import annotations
from ...domain.entities.labeling_document import LabelingDocument
from ...domain.ports.document_repository_port import IDocumentRepository


class ListDocumentsUseCase:
    """Lista todos los documentos registrados."""

    def __init__(self, document_repository: IDocumentRepository) -> None:
        self._document_repository = document_repository

    def execute(self) -> list[LabelingDocument]:
        return self._document_repository.find_all()
