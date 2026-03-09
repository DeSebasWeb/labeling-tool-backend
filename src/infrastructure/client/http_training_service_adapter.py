from __future__ import annotations

import httpx

from ...domain.ports.training_service_port import ITrainingServicePort


class HttpTrainingServiceAdapter(ITrainingServicePort):
    """Adaptador HTTP que conecta con el training-service vía REST."""

    def __init__(self, base_url: str, timeout: float = 30.0) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout

    async def start_training(self, workspace_id: str) -> dict:
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.post(
                f"{self._base_url}/training/jobs",
                json={"workspace_id": workspace_id},
            )
            if response.status_code == 400:
                detail = response.json().get("detail", "Workspace no tiene documentos listos")
                raise TrainingBadRequestError(detail)
            response.raise_for_status()
            return response.json()

    async def get_jobs(self, workspace_id: str) -> list[dict]:
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.get(
                f"{self._base_url}/training/jobs",
                params={"workspace_id": workspace_id},
            )
            response.raise_for_status()
            return response.json()


class TrainingBadRequestError(Exception):
    """El training-service rechazó la solicitud (400)."""
    pass


class TrainingUnavailableError(Exception):
    """El training-service no está disponible."""
    pass
