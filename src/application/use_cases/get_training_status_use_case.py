from __future__ import annotations

from ...domain.ports.training_service_port import ITrainingServicePort


class GetTrainingStatusUseCase:
    """Obtiene el estado de los jobs de entrenamiento de un workspace."""

    def __init__(self, training_service: ITrainingServicePort) -> None:
        self._training_service = training_service

    async def execute(self, workspace_id: str) -> list[dict]:
        return await self._training_service.get_jobs(workspace_id)
