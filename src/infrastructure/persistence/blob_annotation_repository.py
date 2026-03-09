from __future__ import annotations
import json
import os
import uuid
from datetime import datetime, UTC
from ...domain.ports.blob_storage_port import IBlobStoragePort


class BlobAnnotationRepository:
    """
    Persiste anotaciones como _annotations.json dentro del prefix de cada PDF en blob.
    Cada anotación tiene: id, page_number, label, bbox (x_min/y_min/x_max/y_max), value_string, confidence.
    """

    def __init__(self, blob_storage: IBlobStoragePort) -> None:
        self._blob = blob_storage

    def _annotations_blob(self, blob_name: str) -> str:
        prefix = os.path.splitext(blob_name)[0]
        return f"{prefix}/_annotations.json"

    def _load(self, container: str, blob_name: str) -> list[dict]:
        ann_blob = self._annotations_blob(blob_name)
        if not self._blob.blob_exists(container, ann_blob):
            return []
        raw = self._blob.download(container, ann_blob)
        return json.loads(raw.decode("utf-8"))

    def _save(self, container: str, blob_name: str, annotations: list[dict]) -> None:
        ann_blob = self._annotations_blob(blob_name)
        payload = json.dumps(annotations, ensure_ascii=False, indent=2).encode("utf-8")
        self._blob.upload(container, ann_blob, payload)

    def list_annotations(self, container: str, blob_name: str, page_number: int | None = None) -> list[dict]:
        annotations = self._load(container, blob_name)
        if page_number is not None:
            annotations = [a for a in annotations if a["page_number"] == page_number]
        return annotations

    def create_annotation(self, container: str, blob_name: str, data: dict) -> dict:
        annotations = self._load(container, blob_name)
        now = datetime.now(UTC).isoformat()
        annotation = {
            "id": str(uuid.uuid4()),
            "page_number": data["page_number"],
            "label": data["label"],
            "bbox": data["bbox"],
            "value_string": data.get("value_string", ""),
            "confidence": data.get("confidence", 1.0),
            "text_type": data.get("text_type", "unknown"),
            "source": data.get("source", "manual"),
            "created_at": now,
            "updated_at": now,
        }
        annotations.append(annotation)
        self._save(container, blob_name, annotations)
        return annotation

    def update_annotation(self, container: str, blob_name: str, annotation_id: str, updates: dict) -> dict:
        annotations = self._load(container, blob_name)
        for ann in annotations:
            if ann["id"] == annotation_id:
                for key in ("label", "bbox", "value_string", "confidence", "text_type", "source"):
                    if key in updates and updates[key] is not None:
                        ann[key] = updates[key]
                ann["updated_at"] = datetime.now(UTC).isoformat()
                self._save(container, blob_name, annotations)
                return ann
        raise ValueError(f"Anotación '{annotation_id}' no encontrada")

    def delete_annotation(self, container: str, blob_name: str, annotation_id: str) -> None:
        annotations = self._load(container, blob_name)
        filtered = [a for a in annotations if a["id"] != annotation_id]
        if len(filtered) == len(annotations):
            raise ValueError(f"Anotación '{annotation_id}' no encontrada")
        self._save(container, blob_name, filtered)

    def delete_annotations_by_source(self, container: str, blob_name: str, source: str) -> int:
        """Elimina todas las anotaciones con el source indicado. Retorna la cantidad eliminada."""
        annotations = self._load(container, blob_name)
        filtered = [a for a in annotations if a.get("source") != source]
        removed = len(annotations) - len(filtered)
        if removed > 0:
            self._save(container, blob_name, filtered)
        return removed
