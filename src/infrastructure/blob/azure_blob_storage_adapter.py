from __future__ import annotations
from azure.storage.blob import BlobServiceClient
from azure.core.exceptions import ResourceNotFoundError, ResourceExistsError
from ...domain.exceptions.blob_storage_exception import BlobStorageException
from ...domain.ports.blob_storage_port import IBlobStoragePort


class AzureBlobStorageAdapter(IBlobStoragePort):
    """
    Adaptador de Azure Blob Storage.
    Funciona con Azurite (desarrollo) y Azure Blob Storage real (producción)
    — solo cambia la connection string en .env.
    """

    def __init__(self, connection_string: str) -> None:
        try:
            self._client = BlobServiceClient.from_connection_string(connection_string)
        except ValueError as e:
            # from_connection_string solo parsea la string — no hace red.
            # ValueError indica que el connection string tiene formato inválido.
            raise BlobStorageException(f"Connection string de blob storage inválida: {e}") from e

    def create_container(self, container_name: str) -> None:
        try:
            self._client.create_container(container_name)
        except ResourceExistsError:
            pass  # ya existe — no es un error
        except Exception as e:
            raise BlobStorageException(f"Error creando container '{container_name}': {e}")

    def container_exists(self, container_name: str) -> bool:
        try:
            container = self._client.get_container_client(container_name)
            container.get_container_properties()
            return True
        except ResourceNotFoundError:
            return False
        except Exception as e:
            raise BlobStorageException(f"Error verificando container '{container_name}': {e}")

    def list_containers(self) -> list[str]:
        try:
            return [c["name"] for c in self._client.list_containers()]
        except Exception as e:
            raise BlobStorageException(f"Error listando containers: {e}")

    def upload(self, container_name: str, blob_name: str, data: bytes) -> None:
        try:
            container = self._client.get_container_client(container_name)
            container.upload_blob(name=blob_name, data=data, overwrite=True)
        except Exception as e:
            raise BlobStorageException(
                f"Error subiendo blob '{blob_name}' a '{container_name}': {e}"
            )

    def download(self, container_name: str, blob_name: str) -> bytes:
        try:
            container = self._client.get_container_client(container_name)
            blob = container.get_blob_client(blob_name)
            return blob.download_blob().readall()
        except ResourceNotFoundError:
            raise BlobStorageException(
                f"Blob '{blob_name}' no encontrado en container '{container_name}'"
            )
        except Exception as e:
            raise BlobStorageException(
                f"Error descargando blob '{blob_name}' de '{container_name}': {e}"
            )

    def blob_exists(self, container_name: str, blob_name: str) -> bool:
        try:
            blob = self._client.get_blob_client(container=container_name, blob=blob_name)
            blob.get_blob_properties()
            return True
        except ResourceNotFoundError:
            return False
        except Exception as e:
            raise BlobStorageException(
                f"Error verificando blob '{blob_name}' en '{container_name}': {e}"
            )

    def list_blobs(self, container_name: str, prefix: str = "") -> list[str]:
        try:
            container = self._client.get_container_client(container_name)
            return [
                b.name for b in container.list_blobs(name_starts_with=prefix or None)
            ]
        except Exception as e:
            raise BlobStorageException(
                f"Error listando blobs en '{container_name}': {e}"
            )

    def delete_blob(self, container_name: str, blob_name: str) -> None:
        try:
            blob = self._client.get_blob_client(container=container_name, blob=blob_name)
            blob.delete_blob()
        except ResourceNotFoundError:
            pass  # ya no existe — idempotente
        except Exception as e:
            raise BlobStorageException(
                f"Error eliminando blob '{blob_name}' de '{container_name}': {e}"
            )
