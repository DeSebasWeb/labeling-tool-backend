from __future__ import annotations
import os
import pypdfium2 as pdfium
from ...domain.entities.document_page import DocumentPage
from ...domain.ports.pdf_renderer_port import IPdfRenderer


class Pypdfium2Renderer(IPdfRenderer):
    """
    Renderiza cada página de un PDF a PNG usando pypdfium2.
    DPI y directorio de salida llegan por parámetro — nada hardcodeado.
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
