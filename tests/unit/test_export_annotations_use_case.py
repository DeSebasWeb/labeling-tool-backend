"""Unit tests — ExportAnnotationsUseCase (ADI format contract)."""
from __future__ import annotations
from unittest.mock import MagicMock
from src.domain.entities.annotation import Annotation
from src.domain.entities.bounding_box import BoundingBox
from src.domain.entities.document_kind import DocumentKind
from src.domain.entities.labeling_document import LabelingDocument
from src.application.use_cases.export_annotations_use_case import ExportAnnotationsUseCase


def _make_doc() -> LabelingDocument:
    return LabelingDocument(
        id="doc-1",
        original_filename="acta.pdf",
        storage_path="/tmp/acta.pdf",
        document_kind=DocumentKind.E14_SENADO,
    )


def _make_annotation(id_: str, label: str, value: str, page: int = 1) -> Annotation:
    return Annotation(
        id=id_,
        document_id="doc-1",
        page_number=page,
        label=label,
        bbox=BoundingBox.from_rect(0, 0, 100, 50),
        value_string=value,
    )


def _make_use_case(doc, annotations):
    doc_repo = MagicMock()
    ann_repo = MagicMock()
    doc_repo.find_by_id.return_value = doc
    ann_repo.find_by_document.return_value = annotations
    return ExportAnnotationsUseCase(doc_repo, ann_repo), doc_repo


class TestExportAnnotationsUseCase:
    def test_result_has_adi_envelope_structure(self):
        use_case, _ = _make_use_case(_make_doc(), [])
        result = use_case.execute("doc-1")

        assert result["status"] == "succeeded"
        assert "analyzeResult" in result
        assert "documents" in result["analyzeResult"]

    def test_single_label_creates_field(self):
        ann = _make_annotation("a1", "TotalSufragantes", "150")
        use_case, _ = _make_use_case(_make_doc(), [ann])
        result = use_case.execute("doc-1")

        fields = result["analyzeResult"]["documents"][0]["fields"]
        assert "TotalSufragantes" in fields
        assert fields["TotalSufragantes"]["valueString"] == "150"
        assert fields["TotalSufragantes"]["type"] == "string"
        assert fields["TotalSufragantes"]["confidence"] == 1.0

    def test_duplicate_label_accumulates_bounding_regions(self):
        a1 = _make_annotation("a1", "TipoDeVotoPartido", "PARTIDO_A", page=1)
        a2 = _make_annotation("a2", "TipoDeVotoPartido", "PARTIDO_B", page=2)
        use_case, _ = _make_use_case(_make_doc(), [a1, a2])
        result = use_case.execute("doc-1")

        field = result["analyzeResult"]["documents"][0]["fields"]["TipoDeVotoPartido"]
        assert len(field["boundingRegions"]) == 2
        assert "PARTIDO_A" in field["valueString"]
        assert "PARTIDO_B" in field["valueString"]

    def test_bounding_region_has_page_number_and_polygon(self):
        ann = _make_annotation("a1", "Pagina", "1", page=1)
        use_case, _ = _make_use_case(_make_doc(), [ann])
        result = use_case.execute("doc-1")

        region = result["analyzeResult"]["documents"][0]["fields"]["Pagina"]["boundingRegions"][0]
        assert region["pageNumber"] == 1
        assert len(region["polygon"]) == 8

    def test_marks_document_as_exported(self):
        doc = _make_doc()
        use_case, doc_repo = _make_use_case(doc, [])
        use_case.execute("doc-1")

        from src.domain.entities.labeling_status import LabelingStatus
        assert doc.status == LabelingStatus.EXPORTED
        doc_repo.save.assert_called_once_with(doc)

    def test_model_id_matches_document_kind(self):
        use_case, _ = _make_use_case(_make_doc(), [])
        result = use_case.execute("doc-1")

        assert result["analyzeResult"]["modelId"] == "e14_senado"
