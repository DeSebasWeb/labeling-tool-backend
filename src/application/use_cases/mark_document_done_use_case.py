from __future__ import annotations
from ...domain.entities.labeling_document import LabelingDocument
from ...domain.ports.document_repository_port import IDocumentRepository


class MarkDocumentDoneUseCase:
    """Marca un documento como completamente etiquetado."""

    def __init__(self, document_repository: IDocumentRepository) -> None:
        self._document_repository = document_repository

    def execute(self, document_id: str) -> LabelingDocument:
        document = self._document_repository.find_by_id(document_id)
        document.mark_done()
        self._document_repository.save(document)
        return document
