from __future__ import annotations
import io
import os
from dataclasses import dataclass
import pypdfium2 as pdfium
from ...domain.entities.document_page import DocumentPage
from ...domain.ports.pdf_renderer_port import IPdfRenderer


@dataclass(frozen=True)
class RenderedPage:
    page_number: int
    png_bytes: bytes
    width_px: int
    height_px: int
    width_inch: float
    height_inch: float


class Pypdfium2Renderer(IPdfRenderer):
    """
    Renderiza cada página de un PDF a PNG usando pypdfium2.
    """

    def render(self, pdf_path: str, document_id: str, output_dir: str, dpi: int) -> list[DocumentPage]:
        pages_dir = os.path.join(output_dir, document_id)
        os.makedirs(pages_dir, exist_ok=True)

        pdf = pdfium.PdfDocument(pdf_path)
        pages: list[DocumentPage] = []
        scale = dpi / 72.0

        try:
            for index in range(len(pdf)):
                raw_page = pdf[index]
                try:
                    width_inch = raw_page.get_width() / 72.0
                    height_inch = raw_page.get_height() / 72.0

                    bitmap = raw_page.render(scale=scale, rotation=0)
                    pil_image = bitmap.to_pil()

                    page_number = index + 1
                    image_path = os.path.join(pages_dir, f"page_{page_number:03d}.png")
                    pil_image.save(image_path, format="PNG")

                    pages.append(DocumentPage(
                        page_number=page_number,
                        image_path=image_path,
                        width_px=pil_image.width,
                        height_px=pil_image.height,
                        width_inch=width_inch,
                        height_inch=height_inch,
                    ))
                finally:
                    raw_page.close()
        finally:
            pdf.close()

        return pages

    def render_to_bytes(self, pdf_bytes: bytes, dpi: int) -> list[RenderedPage]:
        """Renderiza un PDF en memoria y retorna PNG bytes por página."""
        pdf = pdfium.PdfDocument(pdf_bytes)
        results: list[RenderedPage] = []
        scale = dpi / 72.0

        try:
            for index in range(len(pdf)):
                raw_page = pdf[index]
                try:
                    width_inch = raw_page.get_width() / 72.0
                    height_inch = raw_page.get_height() / 72.0

                    bitmap = raw_page.render(scale=scale, rotation=0)
                    pil_image = bitmap.to_pil()

                    buf = io.BytesIO()
                    pil_image.save(buf, format="PNG")
                    png_bytes = buf.getvalue()

                    results.append(RenderedPage(
                        page_number=index + 1,
                        png_bytes=png_bytes,
                        width_px=pil_image.width,
                        height_px=pil_image.height,
                        width_inch=width_inch,
                        height_inch=height_inch,
                    ))
                finally:
                    raw_page.close()
        finally:
            pdf.close()

        return results
