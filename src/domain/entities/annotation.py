from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, UTC
from .bounding_box import BoundingBox


@dataclass
class Annotation:
    """
    Una anotación manual: caja + etiqueta + texto visible en esa región.
    Una anotación pertenece a una página concreta de un documento.
    """
    id: str
    document_id: str
    page_number: int           # 1-based, igual que ADI
    label: str                 # nombre del campo, ej. "TotalSufragantes"
    bbox: BoundingBox
    value_string: str          # texto que el anotador ve/confirma en esa región
    confidence: float = 1.0   # manual → siempre 1.0; puede ajustarse si es asistido
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def update_value(self, new_value: str) -> None:
        self.value_string = new_value
        self.updated_at = datetime.now(UTC)

    def update_bbox(self, new_bbox: BoundingBox) -> None:
        self.bbox = new_bbox
        self.updated_at = datetime.now(UTC)

    def update_label(self, new_label: str) -> None:
        self.label = new_label
        self.updated_at = datetime.now(UTC)
