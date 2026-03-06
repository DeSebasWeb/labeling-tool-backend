from __future__ import annotations
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import Response
from pydantic import BaseModel, Field
from ...domain.exceptions.workspace_not_found_exception import WorkspaceNotFoundException
from ...domain.exceptions.workspace_already_exists_exception import WorkspaceAlreadyExistsException
from ...domain.exceptions.blob_storage_exception import BlobStorageException
from ...domain.exceptions.invalid_document_exception import InvalidDocumentException
from ...domain.exceptions.pdf_render_exception import PdfRenderException
from ...application.use_cases.create_workspace_use_case import CreateWorkspaceUseCase
from ...application.use_cases.list_workspaces_use_case import ListWorkspacesUseCase
from ...application.use_cases.get_workspace_use_case import GetWorkspaceUseCase
from ...application.use_cases.upload_document_to_workspace_use_case import UploadDocumentToWorkspaceUseCase
from ...application.use_cases.mark_document_done_in_workspace_use_case import MarkDocumentDoneInWorkspaceUseCase
from ..persistence.blob_document_repository import BlobDocumentRepository
from ..persistence.blob_annotation_repository import BlobAnnotationRepository
from ..dependencies import (
    get_create_workspace_use_case,
    get_list_workspaces_use_case,
    get_get_workspace_use_case,
    get_upload_document_to_workspace_use_case,
    get_mark_document_done_in_workspace_use_case,
    get_blob_document_repository,
    get_blob_annotation_repository,
    get_workspace_repository,
    get_blob_storage,
)
from .dtos.create_workspace_request import CreateWorkspaceRequest
from .dtos.workspace_response import WorkspaceDocumentEntry, WorkspaceResponse

router = APIRouter(prefix="/workspaces", tags=["workspaces"])


# ── Request/Response DTOs for annotations ────────────────────────────────────

class BboxModel(BaseModel):
    x_min: float = Field(..., ge=0)
    y_min: float = Field(..., ge=0)
    x_max: float = Field(..., ge=0)
    y_max: float = Field(..., ge=0)


class CreateAnnotationBody(BaseModel):
    page_number: int = Field(..., ge=1)
    label: str = Field(..., min_length=1)
    bbox: BboxModel
    value_string: str = ""


class UpdateAnnotationBody(BaseModel):
    label: Optional[str] = None
    bbox: Optional[BboxModel] = None
    value_string: Optional[str] = None


# ── Workspace CRUD ───────────────────────────────────────────────────────────

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


# ── Document upload ──────────────────────────────────────────────────────────

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
    except (BlobStorageException, PdfRenderException) as e:
        raise HTTPException(status_code=502, detail=str(e))
    finally:
        await file.close()


# ── Delete document (blob + workspace registry) ─────────────────────────────

@router.delete("/{workspace_id}/documents/{blob_name:path}", response_model=WorkspaceResponse)
async def delete_document(
    workspace_id: str,
    blob_name: str,
    ws_repo=Depends(get_workspace_repository),
    blob_storage=Depends(get_blob_storage),
):
    """Elimina un PDF y todos sus blobs asociados (páginas, anotaciones, metadata)."""
    import os
    try:
        workspace = ws_repo.find_by_id(workspace_id)
        container = workspace.container_name
        prefix = os.path.splitext(blob_name)[0]

        # Delete all blobs with this prefix (pages, _document.json, _annotations.json)
        related = blob_storage.list_blobs(container, prefix=f"{prefix}/")
        for b in related:
            blob_storage.delete_blob(container, b)

        # Delete the PDF itself
        blob_storage.delete_blob(container, blob_name)

        # Delete export file if exists
        export_blob = f"{blob_name}.labels.json"
        blob_storage.delete_blob(container, export_blob)

        # Remove from workspace registry
        workspace.remove_document(blob_name)
        ws_repo.save(workspace)

        return _to_response(workspace)
    except WorkspaceNotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except BlobStorageException as e:
        raise HTTPException(status_code=502, detail=str(e))


# ── Document metadata (from blob) ───────────────────────────────────────────

@router.get("/{workspace_id}/documents/{blob_name:path}/meta")
async def get_document_meta(
    workspace_id: str,
    blob_name: str,
    doc_repo: BlobDocumentRepository = Depends(get_blob_document_repository),
    ws_repo=Depends(get_workspace_repository),
):
    try:
        workspace = ws_repo.find_by_id(workspace_id)
        meta = doc_repo.get_document_meta(workspace.container_name, blob_name)
        return meta
    except WorkspaceNotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Documento no encontrado: {e}")


# ── Page image from blob ────────────────────────────────────────────────────

@router.get("/{workspace_id}/documents/{blob_name:path}/pages/{page_number}/image")
async def get_page_image(
    workspace_id: str,
    blob_name: str,
    page_number: int,
    doc_repo: BlobDocumentRepository = Depends(get_blob_document_repository),
    ws_repo=Depends(get_workspace_repository),
):
    try:
        workspace = ws_repo.find_by_id(workspace_id)
        png_bytes = doc_repo.get_page_image(workspace.container_name, blob_name, page_number)
        return Response(content=png_bytes, media_type="image/png")
    except WorkspaceNotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Página no encontrada: {e}")


# ── Annotations CRUD (workspace-scoped, blob-backed) ────────────────────────

@router.get("/{workspace_id}/documents/{blob_name:path}/annotations")
async def list_annotations(
    workspace_id: str,
    blob_name: str,
    page_number: Optional[int] = None,
    ann_repo: BlobAnnotationRepository = Depends(get_blob_annotation_repository),
    ws_repo=Depends(get_workspace_repository),
):
    try:
        workspace = ws_repo.find_by_id(workspace_id)
        return ann_repo.list_annotations(workspace.container_name, blob_name, page_number)
    except WorkspaceNotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{workspace_id}/documents/{blob_name:path}/annotations", status_code=201)
async def create_annotation(
    workspace_id: str,
    blob_name: str,
    body: CreateAnnotationBody,
    ann_repo: BlobAnnotationRepository = Depends(get_blob_annotation_repository),
    ws_repo=Depends(get_workspace_repository),
):
    try:
        workspace = ws_repo.find_by_id(workspace_id)
        annotation = ann_repo.create_annotation(
            workspace.container_name,
            blob_name,
            {
                "page_number": body.page_number,
                "label": body.label,
                "bbox": body.bbox.model_dump(),
                "value_string": body.value_string,
            },
        )
        return annotation
    except WorkspaceNotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.patch("/{workspace_id}/documents/{blob_name:path}/annotations/{annotation_id}")
async def update_annotation(
    workspace_id: str,
    blob_name: str,
    annotation_id: str,
    body: UpdateAnnotationBody,
    ann_repo: BlobAnnotationRepository = Depends(get_blob_annotation_repository),
    ws_repo=Depends(get_workspace_repository),
):
    try:
        workspace = ws_repo.find_by_id(workspace_id)
        updates = {}
        if body.label is not None:
            updates["label"] = body.label
        if body.bbox is not None:
            updates["bbox"] = body.bbox.model_dump()
        if body.value_string is not None:
            updates["value_string"] = body.value_string
        return ann_repo.update_annotation(workspace.container_name, blob_name, annotation_id, updates)
    except WorkspaceNotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/{workspace_id}/documents/{blob_name:path}/annotations/{annotation_id}", status_code=204)
async def delete_annotation(
    workspace_id: str,
    blob_name: str,
    annotation_id: str,
    ann_repo: BlobAnnotationRepository = Depends(get_blob_annotation_repository),
    ws_repo=Depends(get_workspace_repository),
):
    try:
        workspace = ws_repo.find_by_id(workspace_id)
        ann_repo.delete_annotation(workspace.container_name, blob_name, annotation_id)
    except WorkspaceNotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ── Mark done ────────────────────────────────────────────────────────────────

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


# ── Export (blob-based, no local document_id needed) ─────────────────────────

@router.post("/{workspace_id}/documents/{blob_name:path}/export", status_code=200)
async def export_labels(
    workspace_id: str,
    blob_name: str,
    ann_repo: BlobAnnotationRepository = Depends(get_blob_annotation_repository),
    ws_repo=Depends(get_workspace_repository),
    blob_storage=Depends(get_blob_storage),
):
    """Exporta anotaciones como .pdf.labels.json al blob y marca DONE."""
    try:
        import json
        workspace = ws_repo.find_by_id(workspace_id)
        annotations = ann_repo.list_annotations(workspace.container_name, blob_name)
        labels_blob_name = f"{blob_name}.labels.json"
        payload = json.dumps(annotations, ensure_ascii=False, indent=2).encode("utf-8")
        blob_storage.upload(workspace.container_name, labels_blob_name, payload)
        workspace.mark_document_done(blob_name)
        ws_repo.save(workspace)
        return {"labels_blob": labels_blob_name, "workspace_id": workspace_id}
    except WorkspaceNotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except BlobStorageException as e:
        raise HTTPException(status_code=502, detail=str(e))


# ── Helpers ──────────────────────────────────────────────────────────────────

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
