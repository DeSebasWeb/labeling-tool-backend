from __future__ import annotations
import json
from datetime import datetime
from ...domain.entities.document_kind import DocumentKind
from ...domain.entities.workspace import Workspace
from ...domain.entities.workspace_document_status import WorkspaceDocumentStatus
from ...domain.exceptions.workspace_not_found_exception import WorkspaceNotFoundException
from ...domain.ports.blob_storage_port import IBlobStoragePort
from ...domain.ports.workspace_repository_port import IWorkspaceRepository

_WORKSPACE_METADATA_BLOB = "_workspace.json"


class BlobWorkspaceRepository(IWorkspaceRepository):
    """
    Persiste cada Workspace como _workspace.json dentro de su propio container.
    El workspace_id == container_name — un container por workspace.
    """

    def __init__(self, blob_storage: IBlobStoragePort) -> None:
        self._blob = blob_storage

    def save(self, workspace: Workspace) -> None:
        data = self._serialize(workspace)
        payload = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
        self._blob.upload(workspace.container_name, _WORKSPACE_METADATA_BLOB, payload)

    def find_by_id(self, workspace_id: str) -> Workspace:
        if not self._blob.container_exists(workspace_id):
            raise WorkspaceNotFoundException(workspace_id)
        raw = self._blob.download(workspace_id, _WORKSPACE_METADATA_BLOB)
        try:
            return self._deserialize(json.loads(raw.decode("utf-8")))
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            raise WorkspaceNotFoundException(workspace_id) from e

    def find_all(self) -> list[Workspace]:
        workspaces = []
        for container_name in self._blob.list_containers():
            if not self._blob.blob_exists(container_name, _WORKSPACE_METADATA_BLOB):
                continue
            try:
                raw = self._blob.download(container_name, _WORKSPACE_METADATA_BLOB)
                workspaces.append(self._deserialize(json.loads(raw.decode("utf-8"))))
            except Exception:
                continue  # container dañado — no bloquea la lista
        return sorted(workspaces, key=lambda w: w.created_at, reverse=True)

    def exists(self, workspace_id: str) -> bool:
        return (
            self._blob.container_exists(workspace_id)
            and self._blob.blob_exists(workspace_id, _WORKSPACE_METADATA_BLOB)
        )

    def _serialize(self, workspace: Workspace) -> dict:
        return {
            "id": workspace.id,
            "name": workspace.name,
            "container_name": workspace.container_name,
            "document_kind": workspace.document_kind.value,
            "model_name": workspace.model_name,
            "labels": workspace.labels,
            "documents": {
                blob_name: status.value
                for blob_name, status in workspace.documents.items()
            },
            "created_at": workspace.created_at.isoformat(),
            "updated_at": workspace.updated_at.isoformat(),
        }

    def _deserialize(self, data: dict) -> Workspace:
        return Workspace(
            id=data["id"],
            name=data["name"],
            container_name=data["container_name"],
            document_kind=DocumentKind(data["document_kind"]),
            model_name=data["model_name"],
            documents={
                blob_name: WorkspaceDocumentStatus(status)
                for blob_name, status in data.get("documents", {}).items()
            },
            labels=data.get("labels", []),
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
        )
