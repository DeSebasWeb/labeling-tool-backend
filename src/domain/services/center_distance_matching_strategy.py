from __future__ import annotations
from ..ports.matching_strategy_port import (
    IMatchingStrategy, TemplateAnnotation, OcrLine, MatchedAnnotation,
    LabelType, AnnotationSource, BboxField,
)


class CenterDistanceMatchingStrategy(IMatchingStrategy):
    """Asigna lineas OCR a templates por proximidad del centro del bbox.

    Para cada template TEXT/SIGNATURE:
      1. Expande el bbox del template con un margen de tolerancia
      2. Busca lineas OCR cuyo centro caiga dentro del bbox expandido
      3. Concatena textos de las lineas matcheadas
      4. Si no hay match, crea la anotacion con value_string vacio

    Para templates TABLE:
      - Usa el bbox del template directamente (la tabla se reconstruira en frontend)
      - value_string queda vacio (el usuario la llena via assembleTable)
    """

    def __init__(self, tolerance_ratio: float = 0.15):
        """tolerance_ratio: fraccion del ancho/alto del bbox usada como margen."""
        self._tolerance_ratio = tolerance_ratio

    def match(
        self,
        templates: list[TemplateAnnotation],
        ocr_lines: list[OcrLine],
    ) -> list[MatchedAnnotation]:
        used_line_indices: set[int] = set()
        results: list[MatchedAnnotation] = []

        for tmpl in templates:
            tmpl_bbox = {
                BboxField.X_MIN: tmpl.bbox_x_min,
                BboxField.Y_MIN: tmpl.bbox_y_min,
                BboxField.X_MAX: tmpl.bbox_x_max,
                BboxField.Y_MAX: tmpl.bbox_y_max,
            }

            if tmpl.label_type == LabelType.TABLE:
                results.append(MatchedAnnotation(
                    label=tmpl.label,
                    bbox=tmpl_bbox,
                    value_string="",  # tabla vacia: el usuario la llena via assembleTable
                    confidence=1.0,
                    source=AnnotationSource.AUTO_LABEL,
                    label_type=tmpl.label_type,
                ))
                continue

            # TEXT / SIGNATURE: find OCR lines inside template bbox with tolerance
            t_width = tmpl.bbox_x_max - tmpl.bbox_x_min
            t_height = tmpl.bbox_y_max - tmpl.bbox_y_min
            margin_x = t_width * self._tolerance_ratio
            margin_y = t_height * self._tolerance_ratio

            expanded_x_min = tmpl.bbox_x_min - margin_x
            expanded_y_min = tmpl.bbox_y_min - margin_y
            expanded_x_max = tmpl.bbox_x_max + margin_x
            expanded_y_max = tmpl.bbox_y_max + margin_y

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
                bbox=tmpl_bbox,
                value_string=" ".join(matched_texts),
                confidence=round(avg_conf, 4),
                source=AnnotationSource.AUTO_LABEL,
                label_type=tmpl.label_type,
            ))

        return results
