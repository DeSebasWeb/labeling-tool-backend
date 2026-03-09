from __future__ import annotations
from ...domain.ports.matching_strategy_port import (
    IMatchingStrategy, TemplateAnnotation, OcrLine, MatchedAnnotation,
    PageDimensions,
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
        *,
        ref_dims_by_page: dict[int, PageDimensions] | None = None,
        target_dims_by_page: dict[int, PageDimensions] | None = None,
    ) -> dict[int, list[MatchedAnnotation]]:
        """Para cada pagina, ejecuta el matching y retorna anotaciones por pagina."""
        results: dict[int, list[MatchedAnnotation]] = {}

        for page_num, templates in templates_by_page.items():
            ocr_lines = ocr_by_page.get(page_num, [])
            ref_dims = ref_dims_by_page.get(page_num) if ref_dims_by_page else None
            target_dims = target_dims_by_page.get(page_num) if target_dims_by_page else None
            matched = self._strategy.match(
                templates, ocr_lines,
                ref_page_dims=ref_dims,
                target_page_dims=target_dims,
            )
            results[page_num] = matched

        return results
