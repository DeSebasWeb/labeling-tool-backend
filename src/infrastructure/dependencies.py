from __future__ import annotations
from fastapi import Depends
from .config import Settings, get_settings
from .persistence.local_document_repository import LocalDocumentRepository
from .persistence.local_annotation_repository import LocalAnnotationRepository
from .persistence.yaml_label_schema_repository import YamlLabelSchemaRepository
from .persistence.blob_workspace_repository import BlobWorkspaceRepository
from .blob.azure_blob_storage_adapter import AzureBlobStorageAdapter
from .renderer.pypdfium2_renderer import Pypdfium2Renderer
from ..application.use_cases.upload_document_use_case import UploadDocumentUseCase
from ..application.use_cases.get_document_use_case import GetDocumentUseCase
from ..application.use_cases.list_documents_use_case import ListDocumentsUseCase
from ..application.use_cases.save_annotation_use_case import SaveAnnotationUseCase
from ..application.use_cases.update_annotation_use_case import UpdateAnnotationUseCase
from ..application.use_cases.delete_annotation_use_case import DeleteAnnotationUseCase
from ..application.use_cases.list_annotations_use_case import ListAnnotationsUseCase
from ..application.use_cases.export_annotations_use_case import ExportAnnotationsUseCase
from ..application.use_cases.get_label_schema_use_case import GetLabelSchemaUseCase
from ..application.use_cases.mark_document_done_use_case import MarkDocumentDoneUseCase
from ..application.use_cases.create_workspace_use_case import CreateWorkspaceUseCase
from ..application.use_cases.list_workspaces_use_case import ListWorkspacesUseCase
from ..application.use_cases.get_workspace_use_case import GetWorkspaceUseCase
from ..application.use_cases.upload_document_to_workspace_use_case import UploadDocumentToWorkspaceUseCase
from ..application.use_cases.mark_document_done_in_workspace_use_case import MarkDocumentDoneInWorkspaceUseCase
from ..application.use_cases.export_labels_to_blob_use_case import ExportLabelsToBlobUseCase


# ─── repositorios (singleton por settings) ──────────────────────────────────

def get_document_repository(settings: Settings = Depends(get_settings)):
    return LocalDocumentRepository(settings.documents_storage_dir)


def get_annotation_repository(settings: Settings = Depends(get_settings)):
    return LocalAnnotationRepository(settings.annotations_storage_dir)


def get_label_schema_repository(settings: Settings = Depends(get_settings)):
    return YamlLabelSchemaRepository(settings.schemas_dir)


def get_pdf_renderer():
    return Pypdfium2Renderer()


# ─── use cases ───────────────────────────────────────────────────────────────

def get_upload_use_case(
    settings: Settings = Depends(get_settings),
    document_repository=Depends(get_document_repository),
    pdf_renderer=Depends(get_pdf_renderer),
):
    return UploadDocumentUseCase(
        document_repository=document_repository,
        pdf_renderer=pdf_renderer,
        pages_dir=settings.pages_dir,
        render_dpi=settings.render_dpi,
    )


def get_get_document_use_case(document_repository=Depends(get_document_repository)):
    return GetDocumentUseCase(document_repository)


def get_list_documents_use_case(document_repository=Depends(get_document_repository)):
    return ListDocumentsUseCase(document_repository)


def get_save_annotation_use_case(
    annotation_repository=Depends(get_annotation_repository),
    document_repository=Depends(get_document_repository),
    label_schema_repository=Depends(get_label_schema_repository),
):
    return SaveAnnotationUseCase(
        annotation_repository=annotation_repository,
        document_repository=document_repository,
        label_schema_repository=label_schema_repository,
    )


def get_update_annotation_use_case(
    annotation_repository=Depends(get_annotation_repository),
    document_repository=Depends(get_document_repository),
    label_schema_repository=Depends(get_label_schema_repository),
):
    return UpdateAnnotationUseCase(
        annotation_repository=annotation_repository,
        document_repository=document_repository,
        label_schema_repository=label_schema_repository,
    )


def get_delete_annotation_use_case(
    annotation_repository=Depends(get_annotation_repository),
    document_repository=Depends(get_document_repository),
):
    return DeleteAnnotationUseCase(
        annotation_repository=annotation_repository,
        document_repository=document_repository,
    )


def get_list_annotations_use_case(
    annotation_repository=Depends(get_annotation_repository),
    document_repository=Depends(get_document_repository),
):
    return ListAnnotationsUseCase(annotation_repository, document_repository)


def get_export_use_case(
    document_repository=Depends(get_document_repository),
    annotation_repository=Depends(get_annotation_repository),
):
    return ExportAnnotationsUseCase(
        document_repository=document_repository,
        annotation_repository=annotation_repository,
    )


def get_label_schema_use_case(label_schema_repository=Depends(get_label_schema_repository)):
    return GetLabelSchemaUseCase(label_schema_repository)


def get_mark_done_use_case(document_repository=Depends(get_document_repository)):
    return MarkDocumentDoneUseCase(document_repository)


# ─── blob storage ────────────────────────────────────────────────────────────

def get_blob_storage(settings: Settings = Depends(get_settings)):
    return AzureBlobStorageAdapter(settings.azure_storage_connection_string)


def get_workspace_repository(blob_storage=Depends(get_blob_storage)):
    return BlobWorkspaceRepository(blob_storage)


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
    document_repository=Depends(get_document_repository),
    pdf_renderer=Depends(get_pdf_renderer),
):
    return UploadDocumentToWorkspaceUseCase(
        workspace_repository=workspace_repository,
        blob_storage=blob_storage,
        document_repository=document_repository,
        pdf_renderer=pdf_renderer,
        upload_dir=settings.upload_dir,
        pages_dir=settings.pages_dir,
        render_dpi=settings.render_dpi,
    )


def get_mark_document_done_in_workspace_use_case(
    workspace_repository=Depends(get_workspace_repository),
):
    return MarkDocumentDoneInWorkspaceUseCase(workspace_repository)


def get_export_labels_to_blob_use_case(
    workspace_repository=Depends(get_workspace_repository),
    annotation_repository=Depends(get_annotation_repository),
    blob_storage=Depends(get_blob_storage),
):
    return ExportLabelsToBlobUseCase(workspace_repository, annotation_repository, blob_storage)
