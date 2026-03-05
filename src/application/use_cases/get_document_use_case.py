from __future__ import annotations
from ...domain.entities.labeling_document import LabelingDocument
from ...domain.ports.document_repository_port import IDocumentRepository


class GetDocumentUseCase:
    """Recupera un documento por su ID."""

    def __init__(self, document_repository: IDocumentRepository) -> None:
        self._document_repository = document_repository

    def execute(self, document_id: str) -> LabelingDocument:
        return self._document_repository.find_by_id(document_id)
