from __future__ import annotations
import json
import os
from datetime import datetime, UTC
from ...domain.entities.document_kind import DocumentKind
from ...domain.entities.document_page import DocumentPage
from ...domain.entities.labeling_document import LabelingDocument
from ...domain.entities.labeling_status import LabelingStatus
from ...domain.exceptions.document_not_found_exception import DocumentNotFoundException
from ...domain.ports.document_repository_port import IDocumentRepository


class LocalDocumentRepository(IDocumentRepository):

    def __init__(self, storage_dir: str) -> None:
        self._storage_dir = storage_dir
        os.makedirs(storage_dir, exist_ok=True)

    def save(self, document: LabelingDocument) -> None:
        data = {
            "id": document.id,
            "original_filename": document.original_filename,
            "storage_path": document.storage_path,
            "document_kind": document.document_kind.value,
            "status": document.status.value,
            "total_annotations": document.total_annotations,
            "created_at": document.created_at.isoformat(),
            "updated_at": document.updated_at.isoformat(),
            "pages": [
                {
                    "page_number": p.page_number,
                    "image_path": p.image_path,
                    "width_px": p.width_px,
                    "height_px": p.height_px,
                    "width_inch": p.width_inch,
                    "height_inch": p.height_inch,
                }
                for p in document.pages
            ],
        }
        tmp = self._path_for(document.id) + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp, self._path_for(document.id))

    def find_by_id(self, document_id: str) -> LabelingDocument:
        path = self._path_for(document_id)
        if not os.path.exists(path):
            raise DocumentNotFoundException(document_id)
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return self._deserialize(data)

    def find_all(self) -> list[LabelingDocument]:
        result = []
        for filename in os.listdir(self._storage_dir):
            if not filename.endswith(".json"):
                continue
            try:
                with open(os.path.join(self._storage_dir, filename), "r", encoding="utf-8") as f:
                    data = json.load(f)
                result.append(self._deserialize(data))
            except Exception:
                continue
        return sorted(result, key=lambda d: d.created_at, reverse=True)

    def delete(self, document_id: str) -> None:
        path = self._path_for(document_id)
        if not os.path.exists(path):
            raise DocumentNotFoundException(document_id)
        os.remove(path)

    def _path_for(self, document_id: str) -> str:
        return os.path.join(self._storage_dir, f"{document_id}.json")

    def _deserialize(self, data: dict) -> LabelingDocument:
        doc = LabelingDocument(
            id=data["id"],
            original_filename=data["original_filename"],
            storage_path=data["storage_path"],
            document_kind=DocumentKind(data["document_kind"]),
            status=LabelingStatus(data["status"]),
            total_annotations=data["total_annotations"],
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
        )
        for p in data["pages"]:
            doc.add_page(DocumentPage(
                page_number=p["page_number"],
                image_path=p["image_path"],
                width_px=p["width_px"],
                height_px=p["height_px"],
                width_inch=p["width_inch"],
                height_inch=p["height_inch"],
            ))
        return doc
