from __future__ import annotations
from ...domain.entities.document_kind import DocumentKind
from ...domain.entities.label_schema import LabelSchema
from ...domain.ports.label_schema_port import ILabelSchemaRepository


class GetLabelSchemaUseCase:
    """Devuelve el esquema de etiquetas válidas para un tipo de documento."""

    def __init__(self, label_schema_repository: ILabelSchemaRepository) -> None:
        self._label_schema_repository = label_schema_repository

    def execute(self, document_kind: DocumentKind) -> LabelSchema:
        return self._label_schema_repository.get_schema(document_kind)
