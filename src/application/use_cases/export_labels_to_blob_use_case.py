from __future__ import annotations
import json
from datetime import datetime, UTC
from ...domain.entities.annotation import Annotation
from ...domain.ports.annotation_repository_port import IAnnotationRepository
from ...domain.ports.blob_storage_port import IBlobStoragePort
from ...domain.ports.workspace_repository_port import IWorkspaceRepository


class ExportLabelsToBlobUseCase:
    """
    Exporta las anotaciones de un documento como .pdf.labels.json en blob storage.
    El formato es idéntico al contrato ADI — VerifyID lo consume sin cambios.
    El documento se marca automáticamente como DONE en el workspace.
    """

    def __init__(
        self,
        workspace_repository: IWorkspaceRepository,
        annotation_repository: IAnnotationRepository,
        blob_storage: IBlobStoragePort,
    ) -> None:
        self._workspace_repository = workspace_repository
        self._annotation_repository = annotation_repository
        self._blob_storage = blob_storage

    def execute(self, workspace_id: str, blob_name: str, document_id: str) -> str:
        """
        Returns the blob name of the saved labels file.
        document_id: ID del LabelingDocument en el repositorio local de anotaciones.
        blob_name: nombre del PDF en el container (ej: 'acta_001.pdf').
        """
        workspace = self._workspace_repository.find_by_id(workspace_id)

        # Validar antes de subir — evita labels.json huérfano si blob_name no está registrado
        if blob_name not in workspace.documents:
            raise ValueError(f"Documento '{blob_name}' no registrado en el workspace '{workspace_id}'")

        annotations = self._annotation_repository.find_by_document(document_id)

        fields = self._build_fields(annotations)
        payload = self._build_adi_envelope(workspace, blob_name, fields)

        labels_blob_name = f"{blob_name}.labels.json"
        data = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")

        self._blob_storage.upload(
            container_name=workspace.container_name,
            blob_name=labels_blob_name,
            data=data,
        )

        workspace.mark_document_done(blob_name)
        self._workspace_repository.save(workspace)

        return labels_blob_name

    def _build_fields(self, annotations: list[Annotation]) -> dict:
        fields: dict = {}
        for ann in annotations:
            if ann.label not in fields:
                fields[ann.label] = {
                    "type": "string",
                    "valueString": ann.value_string,
                    "content": ann.value_string,
                    "boundingRegions": [
                        {"pageNumber": ann.page_number, "polygon": ann.bbox.to_polygon()}
                    ],
                    "confidence": ann.confidence,
                }
            else:
                fields[ann.label]["boundingRegions"].append(
                    {"pageNumber": ann.page_number, "polygon": ann.bbox.to_polygon()}
                )
                fields[ann.label]["valueString"] += f"\n{ann.value_string}"
                fields[ann.label]["content"] += f"\n{ann.value_string}"
        return fields

    def _build_adi_envelope(self, workspace, blob_name: str, fields: dict) -> dict:
        now = datetime.now(UTC).isoformat()
        doc_type = workspace.document_kind.value.lower().replace("_", "-")
        return {
            "status": "succeeded",
            "createdDateTime": now,
            "lastUpdatedDateTime": now,
            "sourceBlob": blob_name,
            "workspaceId": workspace.id,
            "analyzeResult": {
                "apiVersion": "2024-11-30",
                "modelId": doc_type,
                "stringIndexType": "utf16CodeUnit",
                "content": "",
                "pages": [],
                "documents": [
                    {
                        "docType": doc_type,
                        "boundingRegions": [],
                        "fields": fields,
                        "confidence": 1.0,
                    }
                ],
            },
        }
