from __future__ import annotations
from abc import ABC, abstractmethod
from ..entities.label_schema import LabelSchema, DocumentKind


class ILabelSchemaRepository(ABC):
    """
    Provee el esquema de etiquetas para cada tipo de documento.
    La implementación carga desde YAML/JSON de configuración — nunca hardcodeado.
    """

    @abstractmethod
    def get_schema(self, document_kind: DocumentKind) -> LabelSchema: ...

    @abstractmethod
    def list_kinds(self) -> list[DocumentKind]: ...
