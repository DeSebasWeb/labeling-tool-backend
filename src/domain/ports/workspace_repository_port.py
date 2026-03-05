from __future__ import annotations
from abc import ABC, abstractmethod
from ..entities.workspace import Workspace


class IWorkspaceRepository(ABC):
    """
    Port para persistir y recuperar workspaces.
    La implementación concreta guarda _workspace.json en blob storage.
    """

    @abstractmethod
    def save(self, workspace: Workspace) -> None:
        """Crea o actualiza el workspace (sobreescribe _workspace.json en el container)."""
        ...

    @abstractmethod
    def find_by_id(self, workspace_id: str) -> Workspace:
        """Lanza WorkspaceNotFoundException si no existe."""
        ...

    @abstractmethod
    def find_all(self) -> list[Workspace]:
        """Lista todos los workspaces (itera containers y lee sus _workspace.json)."""
        ...

    @abstractmethod
    def exists(self, workspace_id: str) -> bool:
        ...
