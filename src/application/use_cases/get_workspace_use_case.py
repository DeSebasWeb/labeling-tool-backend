from __future__ import annotations
from ...domain.entities.workspace import Workspace
from ...domain.ports.workspace_repository_port import IWorkspaceRepository


class GetWorkspaceUseCase:
    """Recupera un workspace por su ID (= container_name)."""

    def __init__(self, workspace_repository: IWorkspaceRepository) -> None:
        self._workspace_repository = workspace_repository

    def execute(self, workspace_id: str) -> Workspace:
        return self._workspace_repository.find_by_id(workspace_id)
