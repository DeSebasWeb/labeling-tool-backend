from __future__ import annotations
import re
from ...domain.entities.document_kind import DocumentKind
from ...domain.entities.workspace import Workspace
from ...domain.exceptions.workspace_already_exists_exception import WorkspaceAlreadyExistsException
from ...domain.ports.blob_storage_port import IBlobStoragePort
from ...domain.ports.workspace_repository_port import IWorkspaceRepository


def _slugify(name: str) -> str:
    """
    Convierte el nombre del workspace en un nombre de container válido para Azure Blob.
    Reglas: minúsculas, solo letras/números/guiones, 3-63 chars, no empieza/termina en guion.
    """
    slug = name.lower().strip()
    slug = re.sub(r"[^a-z0-9\-]", "-", slug)
    slug = re.sub(r"-{2,}", "-", slug)
    slug = slug.strip("-")
    slug = slug[:63].rstrip("-")  # truncar a 63 y eliminar guion final si quedó tras corte
    if len(slug) < 3:
        slug = slug.ljust(3, "0")
    return slug


class CreateWorkspaceUseCase:
    """
    Crea un workspace nuevo:
    1. Genera un container_name desde el nombre (slugificado)
    2. Crea el container en blob storage
    3. Persiste _workspace.json en el container
    """

    def __init__(
        self,
        workspace_repository: IWorkspaceRepository,
        blob_storage: IBlobStoragePort,
    ) -> None:
        self._workspace_repository = workspace_repository
        self._blob_storage = blob_storage

    def execute(
        self,
        name: str,
        document_kind: DocumentKind,
        model_name: str,
    ) -> Workspace:
        container_name = _slugify(name)

        if self._blob_storage.container_exists(container_name):
            raise WorkspaceAlreadyExistsException(container_name)

        self._blob_storage.create_container(container_name)

        workspace = Workspace(
            id=container_name,   # id == container_name — un único identificador
            name=name,
            container_name=container_name,
            document_kind=document_kind,
            model_name=model_name,
        )

        self._workspace_repository.save(workspace)
        return workspace
