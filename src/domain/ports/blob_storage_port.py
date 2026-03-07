from __future__ import annotations
from abc import ABC, abstractmethod


class IBlobStoragePort(ABC):
    """
    Port para almacenamiento de blobs (Azure Blob Storage / Azurite).
    El dominio no sabe nada de SDK ni connection strings.
    """

    @abstractmethod
    def create_container(self, container_name: str) -> None:
        """Crea el container si no existe."""
        ...

    @abstractmethod
    def container_exists(self, container_name: str) -> bool:
        ...

    @abstractmethod
    def list_containers(self) -> list[str]:
        """Retorna los nombres de todos los containers."""
        ...

    @abstractmethod
    def upload(self, container_name: str, blob_name: str, data: bytes) -> None:
        """Sube o sobreescribe un blob."""
        ...

    @abstractmethod
    def download(self, container_name: str, blob_name: str) -> bytes:
        """Descarga el contenido de un blob."""
        ...

    @abstractmethod
    def blob_exists(self, container_name: str, blob_name: str) -> bool:
        ...

    @abstractmethod
    def list_blobs(self, container_name: str, prefix: str = "") -> list[str]:
        """Lista nombres de blobs, opcionalmente filtrados por prefijo."""
        ...

    @abstractmethod
    def delete_blob(self, container_name: str, blob_name: str) -> None:
        ...

    @abstractmethod
    def delete_container(self, container_name: str) -> None:
        """Elimina el container y todos sus blobs."""
        ...
