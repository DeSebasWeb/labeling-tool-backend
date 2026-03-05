from __future__ import annotations
from ...domain.entities.workspace import Workspace
from ...domain.ports.workspace_repository_port import IWorkspaceRepository


class ListWorkspacesUseCase:
    """Lista todos los workspaces disponibles en blob storage."""

    def __init__(self, workspace_repository: IWorkspaceRepository) -> None:
        self._workspace_repository = workspace_repository

    def execute(self) -> list[Workspace]:
        return self._workspace_repository.find_all()
