from __future__ import annotations
from ...domain.entities.workspace import Workspace
from ...domain.ports.workspace_repository_port import IWorkspaceRepository


class MarkDocumentDoneInWorkspaceUseCase:
    """Marca un documento del workspace como DONE (listo para entrenar)."""

    def __init__(self, workspace_repository: IWorkspaceRepository) -> None:
        self._workspace_repository = workspace_repository

    def execute(self, workspace_id: str, blob_name: str) -> Workspace:
        workspace = self._workspace_repository.find_by_id(workspace_id)
        workspace.mark_document_done(blob_name)
        self._workspace_repository.save(workspace)
        return workspace
