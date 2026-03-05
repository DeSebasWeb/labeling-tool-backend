from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from ...domain.exceptions.workspace_not_found_exception import WorkspaceNotFoundException
from ...domain.exceptions.workspace_already_exists_exception import WorkspaceAlreadyExistsException
from ...domain.exceptions.blob_storage_exception import BlobStorageException
from ...domain.exceptions.invalid_document_exception import InvalidDocumentException
from ...application.use_cases.create_workspace_use_case import CreateWorkspaceUseCase
from ...application.use_cases.list_workspaces_use_case import ListWorkspacesUseCase
from ...application.use_cases.get_workspace_use_case import GetWorkspaceUseCase
from ...application.use_cases.upload_document_to_workspace_use_case import UploadDocumentToWorkspaceUseCase
from ...application.use_cases.mark_document_done_in_workspace_use_case import MarkDocumentDoneInWorkspaceUseCase
from ...application.use_cases.export_labels_to_blob_use_case import ExportLabelsToBlobUseCase
from ..dependencies import (
    get_create_workspace_use_case,
    get_list_workspaces_use_case,
    get_get_workspace_use_case,
    get_upload_document_to_workspace_use_case,
    get_mark_document_done_in_workspace_use_case,
    get_export_labels_to_blob_use_case,
)
from .dtos.create_workspace_request import CreateWorkspaceRequest
from .dtos.workspace_response import WorkspaceDocumentEntry, WorkspaceResponse

router = APIRouter(prefix="/workspaces", tags=["workspaces"])


@router.post("", response_model=WorkspaceResponse, status_code=201)
async def create_workspace(
    body: CreateWorkspaceRequest,
    use_case: CreateWorkspaceUseCase = Depends(get_create_workspace_use_case),
):
    try:
        workspace = use_case.execute(
            name=body.name,
            document_kind=body.document_kind,
            model_name=body.model_name,
        )
        return _to_response(workspace)
    except WorkspaceAlreadyExistsException as e:
        raise HTTPException(status_code=409, detail=str(e))
    except BlobStorageException as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.get("", response_model=list[WorkspaceResponse])
async def list_workspaces(
    use_case: ListWorkspacesUseCase = Depends(get_list_workspaces_use_case),
):
    try:
        return [_to_response(w) for w in use_case.execute()]
    except BlobStorageException as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.get("/{workspace_id}", response_model=WorkspaceResponse)
async def get_workspace(
    workspace_id: str,
    use_case: GetWorkspaceUseCase = Depends(get_get_workspace_use_case),
):
    try:
        return _to_response(use_case.execute(workspace_id))
    except WorkspaceNotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))
    except BlobStorageException as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.post("/{workspace_id}/documents", response_model=WorkspaceResponse, status_code=201)
async def upload_document(
    workspace_id: str,
    file: UploadFile = File(...),
    use_case: UploadDocumentToWorkspaceUseCase = Depends(get_upload_document_to_workspace_use_case),
):
    try:
        if not file.filename:
            raise HTTPException(status_code=400, detail="El archivo debe tener un nombre")
        data = await file.read()
        workspace = use_case.execute(
            workspace_id=workspace_id,
            original_filename=file.filename,
            file_data=data,
        )
        return _to_response(workspace)
    except WorkspaceNotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))
    except InvalidDocumentException as e:
        raise HTTPException(status_code=400, detail=str(e))
    except BlobStorageException as e:
        raise HTTPException(status_code=502, detail=str(e))
    finally:
        await file.close()


@router.patch("/{workspace_id}/documents/{blob_name:path}/done", response_model=WorkspaceResponse)
async def mark_document_done(
    workspace_id: str,
    blob_name: str,
    use_case: MarkDocumentDoneInWorkspaceUseCase = Depends(get_mark_document_done_in_workspace_use_case),
):
    try:
        workspace = use_case.execute(workspace_id, blob_name)
        return _to_response(workspace)
    except WorkspaceNotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except BlobStorageException as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.post("/{workspace_id}/documents/{blob_name:path}/export", status_code=200)
async def export_labels(
    workspace_id: str,
    blob_name: str,
    document_id: str = Query(..., description="ID del documento en el repositorio local de anotaciones"),
    use_case: ExportLabelsToBlobUseCase = Depends(get_export_labels_to_blob_use_case),
):
    """
    Exporta las anotaciones como .pdf.labels.json en el blob del workspace
    y marca el documento como DONE.
    document_id: ID del documento en el repositorio local de anotaciones.
    """
    try:
        labels_blob = use_case.execute(workspace_id, blob_name, document_id)
        return {"labels_blob": labels_blob, "workspace_id": workspace_id}
    except WorkspaceNotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except BlobStorageException as e:
        raise HTTPException(status_code=502, detail=str(e))


def _to_response(workspace) -> WorkspaceResponse:
    return WorkspaceResponse(
        id=workspace.id,
        name=workspace.name,
        container_name=workspace.container_name,
        document_kind=workspace.document_kind.value,
        model_name=workspace.model_name,
        total_documents=workspace.total_documents(),
        total_done=workspace.total_done(),
        documents=[
            WorkspaceDocumentEntry(blob_name=name, status=status.value)
            for name, status in workspace.documents.items()
        ],
        created_at=workspace.created_at.isoformat(),
        updated_at=workspace.updated_at.isoformat(),
    )
