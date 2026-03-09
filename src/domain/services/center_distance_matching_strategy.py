from __future__ import annotations
from ..ports.matching_strategy_port import (
    IMatchingStrategy, TemplateAnnotation, OcrLine, MatchedAnnotation,
    LabelType, AnnotationSource, BboxField, PageDimensions,
)


class CenterDistanceMatchingStrategy(IMatchingStrategy):
    """Asigna lineas OCR a templates por proximidad del centro del bbox.

    Para cada template TEXT/SIGNATURE:
      1. Escala el bbox del template al espacio de pixeles del documento destino
      2. Expande el bbox escalado con un margen de tolerancia
      3. Busca lineas OCR cuyo centro caiga dentro del bbox expandido
      4. Concatena textos de las lineas matcheadas
      5. Si no hay match, crea la anotacion con value_string vacio

    Para templates TABLE:
      - Escala el bbox y lo usa directamente (la tabla se reconstruira en frontend)
      - value_string queda vacio (el usuario la llena via assembleTable)
    """

    def __init__(self, tolerance_ratio: float = 0.30):
        """tolerance_ratio: fraccion del ancho/alto del bbox usada como margen."""
        self._tolerance_ratio = tolerance_ratio

    @staticmethod
    def _compute_scale(
        ref_page_dims: PageDimensions | None,
        target_page_dims: PageDimensions | None,
    ) -> tuple[float, float]:
        """Calcula factores de escala (scale_x, scale_y) entre referencia y destino."""
        if ref_page_dims is None or target_page_dims is None:
            return 1.0, 1.0
        if ref_page_dims.width_px == 0 or ref_page_dims.height_px == 0:
            return 1.0, 1.0
        return (
            target_page_dims.width_px / ref_page_dims.width_px,
            target_page_dims.height_px / ref_page_dims.height_px,
        )

    def match(
        self,
        templates: list[TemplateAnnotation],
        ocr_lines: list[OcrLine],
        *,
        ref_page_dims: PageDimensions | None = None,
        target_page_dims: PageDimensions | None = None,
    ) -> list[MatchedAnnotation]:
        scale_x, scale_y = self._compute_scale(ref_page_dims, target_page_dims)
        used_line_indices: set[int] = set()
        results: list[MatchedAnnotation] = []

        for tmpl in templates:
            # Escalar bbox del template al espacio de pixeles del destino
            scaled_x_min = tmpl.bbox_x_min * scale_x
            scaled_y_min = tmpl.bbox_y_min * scale_y
            scaled_x_max = tmpl.bbox_x_max * scale_x
            scaled_y_max = tmpl.bbox_y_max * scale_y

            scaled_bbox = {
                BboxField.X_MIN: scaled_x_min,
                BboxField.Y_MIN: scaled_y_min,
                BboxField.X_MAX: scaled_x_max,
                BboxField.Y_MAX: scaled_y_max,
            }

            if tmpl.label_type == LabelType.TABLE:
                results.append(MatchedAnnotation(
                    label=tmpl.label,
                    bbox=scaled_bbox,
                    value_string="",  # tabla vacia: el usuario la llena via assembleTable
                    confidence=1.0,
                    source=AnnotationSource.AUTO_LABEL,
                    label_type=tmpl.label_type,
                ))
                continue

            # TEXT / SIGNATURE: find OCR lines inside scaled bbox with tolerance
            t_width = scaled_x_max - scaled_x_min
            t_height = scaled_y_max - scaled_y_min
            margin_x = t_width * self._tolerance_ratio
            margin_y = t_height * self._tolerance_ratio

            expanded_x_min = scaled_x_min - margin_x
            expanded_y_min = scaled_y_min - margin_y
            expanded_x_max = scaled_x_max + margin_x
            expanded_y_max = scaled_y_max + margin_y

            matched_texts: list[str] = []
            matched_confidences: list[float] = []

            for i, line in enumerate(ocr_lines):
                if i in used_line_indices:
                    continue
                cx = (line.x1 + line.x2) / 2
                cy = (line.y1 + line.y2) / 2
                if expanded_x_min <= cx <= expanded_x_max and expanded_y_min <= cy <= expanded_y_max:
                    matched_texts.append(line.text)
                    matched_confidences.append(line.confidence)
                    used_line_indices.add(i)

            avg_conf = (
                sum(matched_confidences) / len(matched_confidences)
                if matched_confidences else 0.0
            )

            results.append(MatchedAnnotation(
                label=tmpl.label,
                bbox=scaled_bbox,
                value_string=" ".join(matched_texts),
                confidence=round(avg_conf, 4),
                source=AnnotationSource.AUTO_LABEL,
                label_type=tmpl.label_type,
            ))

        return results
