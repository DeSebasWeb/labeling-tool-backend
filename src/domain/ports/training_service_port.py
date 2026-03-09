from __future__ import annotations
from abc import ABC, abstractmethod


class ITrainingServicePort(ABC):
    """
    Puerto de dominio para comunicación con el servicio de entrenamiento.
    El dominio no conoce detalles HTTP ni URLs.
    """

    @abstractmethod
    async def start_training(self, workspace_id: str) -> dict:
        """Inicia un job de entrenamiento para el workspace dado."""
        ...

    @abstractmethod
    async def get_jobs(self, workspace_id: str) -> list[dict]:
        """Obtiene los jobs de entrenamiento asociados a un workspace."""
        ...
