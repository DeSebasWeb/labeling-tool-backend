from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class DocumentPage:
    """
    Metadatos de una página renderizada de un PDF.
    image_path apunta al PNG generado por el renderer.
    Dimensiones en píxeles al DPI de renderizado.
    """
    page_number: int       # 1-based
    image_path: str        # ruta absoluta al PNG en disco
    width_px: int
    height_px: int
    width_inch: float      # dimensión real del PDF para escalar coordenadas
    height_inch: float
