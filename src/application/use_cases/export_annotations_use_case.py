from __future__ import annotations
from datetime import datetime, UTC
from ...domain.entities.annotation import Annotation
from ...domain.entities.labeling_document import LabelingDocument
from ...domain.ports.annotation_repository_port import IAnnotationRepository
from ...domain.ports.document_repository_port import IDocumentRepository


class ExportAnnotationsUseCase:
    """
    Genera el JSON de exportación en formato idéntico al contrato de ADI:
    analyzeResult.documents[0].fields

    Cada campo queda como:
    {
        "type": "string",
        "valueString": "<texto>",
        "content": "<texto>",
        "boundingRegions": [{"pageNumber": N, "polygon": [...8 floats...]}],
        "confidence": 1.0
    }
    """

    def __init__(
        self,
        document_repository: IDocumentRepository,
        annotation_repository: IAnnotationRepository,
    ) -> None:
        self._document_repository = document_repository
        self._annotation_repository = annotation_repository

    def execute(self, document_id: str) -> dict:
        document = self._document_repository.find_by_id(document_id)
        annotations = self._annotation_repository.find_by_document(document_id)

        fields = self._build_fields(annotations)
        result = self._build_adi_envelope(document, fields)

        document.mark_exported()
        self._document_repository.save(document)

        return result

    def _build_fields(self, annotations: list[Annotation]) -> dict:
        """
        Labels únicos → objeto field estándar.
        Labels repetidos por página (ej. DivipolPag, TipoDeVotoPartido) →
        se agrupan bajo el mismo key acumulando boundingRegions de cada página.
        """
        fields: dict = {}
        for ann in annotations:
            if ann.label not in fields:
                fields[ann.label] = {
                    "type": "string",
                    "valueString": ann.value_string,
                    "content": ann.value_string,
                    "boundingRegions": [
                        {
                            "pageNumber": ann.page_number,
                            "polygon": ann.bbox.to_polygon(),
                        }
                    ],
                    "confidence": ann.confidence,
                }
            else:
                fields[ann.label]["boundingRegions"].append(
                    {
                        "pageNumber": ann.page_number,
                        "polygon": ann.bbox.to_polygon(),
                    }
                )
                fields[ann.label]["valueString"] += f"\n{ann.value_string}"
                fields[ann.label]["content"] += f"\n{ann.value_string}"
        return fields

    def _build_adi_envelope(self, document: LabelingDocument, fields: dict) -> dict:
        now = datetime.now(UTC).isoformat()
        return {
            "status": "succeeded",
            "createdDateTime": now,
            "lastUpdatedDateTime": now,
            "analyzeResult": {
                "apiVersion": "2024-11-30",
                "modelId": document.document_kind.value.lower().replace("_", "-"),
                "stringIndexType": "utf16CodeUnit",
                "content": "",
                "pages": [],
                "documents": [
                    {
                        "docType": document.document_kind.value.lower().replace("_", "-"),
                        "boundingRegions": [],
                        "fields": fields,
                        "confidence": 1.0,
                    }
                ],
            },
        }
