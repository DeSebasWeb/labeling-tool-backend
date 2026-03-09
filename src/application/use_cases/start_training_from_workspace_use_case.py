from __future__ import annotations

from ...domain.ports.training_service_port import ITrainingServicePort
from ...domain.ports.workspace_repository_port import IWorkspaceRepository


class StartTrainingFromWorkspaceUseCase:
    """Valida que el workspace tenga documentos DONE e inicia un entrenamiento."""

    def __init__(
        self,
        workspace_repository: IWorkspaceRepository,
        training_service: ITrainingServicePort,
    ) -> None:
        self._workspace_repo = workspace_repository
        self._training_service = training_service

    async def execute(self, workspace_id: str) -> dict:
        workspace = self._workspace_repo.find_by_id(workspace_id)

        ready = workspace.documents_ready_for_training()
        if len(ready) < 1:
            raise WorkspaceNotReadyError(
                f"El workspace '{workspace_id}' no tiene documentos listos para entrenar"
            )

        return await self._training_service.start_training(workspace_id)


class WorkspaceNotReadyError(Exception):
    """El workspace no tiene documentos DONE suficientes para entrenar."""
    pass
