from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import StrEnum


class LabelType(StrEnum):
    TEXT = "text"
    TABLE = "table"
    SIGNATURE = "signature"


class AnnotationSource(StrEnum):
    MANUAL = "manual"
    OCR = "ocr"
    AUTO_LABEL = "auto_label"
    LAYOUT_DETECTION = "layout_detection"


class BboxField(StrEnum):
    X_MIN = "x_min"
    Y_MIN = "y_min"
    X_MAX = "x_max"
    Y_MAX = "y_max"


@dataclass(frozen=True)
class PageDimensions:
    """Dimensiones en pixeles de una pagina renderizada."""
    width_px: float
    height_px: float


@dataclass(frozen=True)
class OcrLine:
    """Linea detectada por OCR con bbox en formato Surya (x1,y1,x2,y2)."""
    text: str
    x1: float
    y1: float
    x2: float
    y2: float
    confidence: float


@dataclass(frozen=True)
class TemplateAnnotation:
    """Anotacion de referencia (del documento template)."""
    label: str
    bbox_x_min: float
    bbox_y_min: float
    bbox_x_max: float
    bbox_y_max: float
    value_string: str
    label_type: str  # "text" | "table" | "signature"


@dataclass(frozen=True)
class MatchedAnnotation:
    """Resultado del matching: template + lineas OCR asignadas."""
    label: str
    bbox: dict  # {x_min, y_min, x_max, y_max}
    value_string: str
    confidence: float
    source: str  # "auto_label"
    label_type: str


class IMatchingStrategy(ABC):
    """Estrategia de matching entre anotaciones template y lineas OCR."""

    @abstractmethod
    def match(
        self,
        templates: list[TemplateAnnotation],
        ocr_lines: list[OcrLine],
        *,
        ref_page_dims: PageDimensions | None = None,
        target_page_dims: PageDimensions | None = None,
    ) -> list[MatchedAnnotation]:
        """Dado un conjunto de templates y lineas OCR, retorna las anotaciones matcheadas.

        Si se proporcionan ref_page_dims y target_page_dims, escala las coordenadas
        del template del espacio de pixeles de referencia al espacio del documento destino.
        """
        ...
