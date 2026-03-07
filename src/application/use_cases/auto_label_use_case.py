from __future__ import annotations
from ...domain.ports.matching_strategy_port import (
    IMatchingStrategy, TemplateAnnotation, OcrLine, MatchedAnnotation,
)


class AutoLabelUseCase:
    """Orquesta el auto-labeling: recibe datos ya cargados, delega matching al dominio.

    Este use case es puro: recibe datos, retorna datos.
    La persistencia (crear anotaciones en blob) es responsabilidad del caller
    (el adapter/router).
    """

    def __init__(self, matching_strategy: IMatchingStrategy):
        self._strategy = matching_strategy

    def execute(
        self,
        templates_by_page: dict[int, list[TemplateAnnotation]],
        ocr_by_page: dict[int, list[OcrLine]],
    ) -> dict[int, list[MatchedAnnotation]]:
        """Para cada pagina, ejecuta el matching y retorna anotaciones por pagina."""
        results: dict[int, list[MatchedAnnotation]] = {}

        for page_num, templates in templates_by_page.items():
            ocr_lines = ocr_by_page.get(page_num, [])
            matched = self._strategy.match(templates, ocr_lines)
            results[page_num] = matched

        return results
