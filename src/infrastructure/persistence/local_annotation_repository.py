from __future__ import annotations
import json
import os
from datetime import datetime, UTC
from ...domain.entities.annotation import Annotation
from ...domain.entities.bounding_box import BoundingBox
from ...domain.exceptions.annotation_not_found_exception import AnnotationNotFoundException
from ...domain.ports.annotation_repository_port import IAnnotationRepository


class LocalAnnotationRepository(IAnnotationRepository):

    def __init__(self, storage_dir: str) -> None:
        self._storage_dir = storage_dir
        os.makedirs(storage_dir, exist_ok=True)

    def save(self, annotation: Annotation) -> None:
        data = {
            "id": annotation.id,
            "document_id": annotation.document_id,
            "page_number": annotation.page_number,
            "label": annotation.label,
            "bbox": annotation.bbox.to_polygon(),
            "value_string": annotation.value_string,
            "confidence": annotation.confidence,
            "created_at": annotation.created_at.isoformat(),
            "updated_at": annotation.updated_at.isoformat(),
        }
        tmp = self._path_for(annotation.id) + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp, self._path_for(annotation.id))

    def find_by_id(self, annotation_id: str) -> Annotation:
        path = self._path_for(annotation_id)
        if not os.path.exists(path):
            raise AnnotationNotFoundException(annotation_id)
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return self._deserialize(data)

    def find_by_document(self, document_id: str) -> list[Annotation]:
        result = []
        for filename in os.listdir(self._storage_dir):
            if not filename.endswith(".json"):
                continue
            try:
                data = self._load(filename)
                if data.get("document_id") == document_id:
                    result.append(self._deserialize(data))
            except Exception:
                continue
        return result

    def find_by_document_and_page(self, document_id: str, page_number: int) -> list[Annotation]:
        return [
            a for a in self.find_by_document(document_id)
            if a.page_number == page_number
        ]

    def delete(self, annotation_id: str) -> None:
        path = self._path_for(annotation_id)
        if not os.path.exists(path):
            raise AnnotationNotFoundException(annotation_id)
        os.remove(path)

    def delete_by_document(self, document_id: str) -> None:
        for ann in self.find_by_document(document_id):
            self.delete(ann.id)

    def _path_for(self, annotation_id: str) -> str:
        return os.path.join(self._storage_dir, f"{annotation_id}.json")

    def _load(self, filename: str) -> dict:
        with open(os.path.join(self._storage_dir, filename), "r", encoding="utf-8") as f:
            return json.load(f)

    def _deserialize(self, data: dict) -> Annotation:
        return Annotation(
            id=data["id"],
            document_id=data["document_id"],
            page_number=data["page_number"],
            label=data["label"],
            bbox=BoundingBox.from_polygon(data["bbox"]),
            value_string=data["value_string"],
            confidence=data["confidence"],
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
        )
