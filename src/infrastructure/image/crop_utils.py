from __future__ import annotations
import base64
import io

from PIL import Image


def crop_region_base64(
    png_bytes: bytes,
    x_min: int,
    y_min: int,
    x_max: int,
    y_max: int,
) -> str:
    """Recorta una region de una imagen PNG y la devuelve como base64.

    Args:
        png_bytes: Bytes de la imagen PNG completa.
        x_min, y_min: Coordenada superior izquierda del recorte (pixeles).
        x_max, y_max: Coordenada inferior derecha del recorte (pixeles).

    Returns:
        String base64 del PNG recortado, listo para enviar al text-detector.
    """
    img = Image.open(io.BytesIO(png_bytes)).convert("RGB")
    # Clamp al tamano real de la imagen para evitar errores de bounds
    w, h = img.size
    box = (
        max(0, int(x_min)),
        max(0, int(y_min)),
        min(w, int(x_max)),
        min(h, int(y_max)),
    )
    cropped = img.crop(box)
    buf = io.BytesIO()
    cropped.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()
