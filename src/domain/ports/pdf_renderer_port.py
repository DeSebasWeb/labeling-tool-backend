from __future__ import annotations
from abc import ABC, abstractmethod
from ..entities.document_page import DocumentPage


class IPdfRenderer(ABC):
    """
    Convierte un PDF a imágenes PNG.
    El DPI y el directorio de salida llegan por parámetro — nada hardcodeado.
    """

    @abstractmethod
    def render(self, pdf_path: str, document_id: str, output_dir: str, dpi: int) -> list[DocumentPage]:
        """
        Renderiza todas las páginas del PDF y retorna sus metadatos.
        Cada PNG se guarda en output_dir/{document_id}/page_{n:03d}.png.
        """
        ...
