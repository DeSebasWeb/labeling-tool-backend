from __future__ import annotations
from fastapi import Depends
from .config import Settings, get_settings
from .persistence.blob_workspace_repository import BlobWorkspaceRepository
from .persistence.blob_document_repository import BlobDocumentRepository
from .persistence.blob_annotation_repository import BlobAnnotationRepository
from .blob.azure_blob_storage_adapter import AzureBlobStorageAdapter
from .renderer.pypdfium2_renderer import Pypdfium2Renderer
from ..application.use_cases.create_workspace_use_case import CreateWorkspaceUseCase
from ..application.use_cases.list_workspaces_use_case import ListWorkspacesUseCase
from ..application.use_cases.get_workspace_use_case import GetWorkspaceUseCase
from ..application.use_cases.upload_document_to_workspace_use_case import UploadDocumentToWorkspaceUseCase
from ..application.use_cases.mark_document_done_in_workspace_use_case import MarkDocumentDoneInWorkspaceUseCase


# ─── blob storage ────────────────────────────────────────────────────────────

def get_blob_storage(settings: Settings = Depends(get_settings)):
    return AzureBlobStorageAdapter(settings.azure_storage_connection_string)


def get_workspace_repository(blob_storage=Depends(get_blob_storage)):
    return BlobWorkspaceRepository(blob_storage)


def get_blob_document_repository(blob_storage=Depends(get_blob_storage)):
    return BlobDocumentRepository(blob_storage)


def get_blob_annotation_repository(blob_storage=Depends(get_blob_storage)):
    return BlobAnnotationRepository(blob_storage)


def get_pdf_renderer():
    return Pypdfium2Renderer()


# ─── workspace use cases ─────────────────────────────────────────────────────

def get_create_workspace_use_case(
    workspace_repository=Depends(get_workspace_repository),
    blob_storage=Depends(get_blob_storage),
):
    return CreateWorkspaceUseCase(workspace_repository, blob_storage)


def get_list_workspaces_use_case(workspace_repository=Depends(get_workspace_repository)):
    return ListWorkspacesUseCase(workspace_repository)


def get_get_workspace_use_case(workspace_repository=Depends(get_workspace_repository)):
    return GetWorkspaceUseCase(workspace_repository)


def get_upload_document_to_workspace_use_case(
    settings: Settings = Depends(get_settings),
    workspace_repository=Depends(get_workspace_repository),
    blob_storage=Depends(get_blob_storage),
    pdf_renderer=Depends(get_pdf_renderer),
):
    return UploadDocumentToWorkspaceUseCase(
        workspace_repository=workspace_repository,
        blob_storage=blob_storage,
        pdf_renderer=pdf_renderer,
        render_dpi=settings.render_dpi,
    )


def get_mark_document_done_in_workspace_use_case(
    workspace_repository=Depends(get_workspace_repository),
):
    return MarkDocumentDoneInWorkspaceUseCase(workspace_repository)
