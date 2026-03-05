from __future__ import annotations
from dataclasses import dataclass, field
from .document_kind import DocumentKind
from .label_definition import LabelDefinition


@dataclass(frozen=True)
class LabelSchema:
    """
    Esquema de etiquetas para un tipo de documento.
    Cargado desde configuración — nunca hardcodeado en el dominio.
    """
    document_kind: DocumentKind
    labels: list[LabelDefinition] = field(default_factory=list)

    def label_names(self) -> list[str]:
        return [lb.name for lb in self.labels]

    def find(self, name: str) -> LabelDefinition | None:
        return next((lb for lb in self.labels if lb.name == name), None)

    def is_valid_label(self, name: str) -> bool:
        return self.find(name) is not None
