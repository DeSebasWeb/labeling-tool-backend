from __future__ import annotations
import base64
import json
import os
import re
from datetime import datetime, UTC
from typing import Literal, Optional
import httpx
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
from ...application.use_cases.start_training_from_workspace_use_case import (
    StartTrainingFromWorkspaceUseCase,
    WorkspaceNotReadyError,
)
from ...application.use_cases.get_training_status_use_case import GetTrainingStatusUseCase
from ..client.http_training_service_adapter import TrainingBadRequestError
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
    get_auto_label_use_case,
    get_start_training_use_case,
    get_get_training_status_use_case,
)
from ..image.crop_utils import crop_region_base64
from ...domain.ports.matching_strategy_port import TemplateAnnotation, OcrLine, LabelType, PageDimensions
from ...application.use_cases.auto_label_use_case import AutoLabelUseCase
from ..config import Settings, get_settings
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
    confidence: Optional[float] = None
    text_type: Optional[str] = None
    source: Optional[str] = None


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
            labels=body.labels,
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


@router.delete("/{workspace_id}", status_code=204)
async def delete_workspace(
    workspace_id: str,
    ws_repo=Depends(get_workspace_repository),
    blob_storage=Depends(get_blob_storage),
):
    """Elimina el workspace y todos sus blobs (documentos, anotaciones, metadata)."""
    try:
        workspace = ws_repo.find_by_id(workspace_id)
        blob_storage.delete_container(workspace.container_name)
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


# ── Training ─────────────────────────────────────────────────────────────────

@router.post("/{workspace_id}/train")
async def start_training(
    workspace_id: str,
    use_case: StartTrainingFromWorkspaceUseCase = Depends(get_start_training_use_case),
):
    """Inicia un job de entrenamiento para el workspace."""
    try:
        result = await use_case.execute(workspace_id)
        return result
    except WorkspaceNotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))
    except WorkspaceNotReadyError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except TrainingBadRequestError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except httpx.ConnectError:
        raise HTTPException(status_code=502, detail="Training service no disponible")
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=502, detail=f"Training service error: {e.response.status_code}")


@router.get("/{workspace_id}/train/status")
async def get_training_status(
    workspace_id: str,
    use_case: GetTrainingStatusUseCase = Depends(get_get_training_status_use_case),
):
    """Obtiene el estado de los jobs de entrenamiento del workspace."""
    try:
        return await use_case.execute(workspace_id)
    except (httpx.ConnectError, httpx.HTTPStatusError):
        # Si el training-service no está disponible, retornar lista vacía
        # (es una consulta de estado, no una acción crítica)
        return []


# ── Annotations CRUD — REORDERED (annotations BEFORE documents for route priority) ───

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


class ClearAnnotationsResponse(BaseModel):
    deleted: int


@router.delete("/{workspace_id}/documents/{blob_name:path}/annotations", response_model=ClearAnnotationsResponse)
async def clear_annotations_by_source(
    workspace_id: str,
    blob_name: str,
    source: str = "auto_label",
    ann_repo: BlobAnnotationRepository = Depends(get_blob_annotation_repository),
    ws_repo=Depends(get_workspace_repository),
):
    """Elimina todas las anotaciones con el source indicado (default: auto_label)."""
    try:
        workspace = ws_repo.find_by_id(workspace_id)
    except WorkspaceNotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))
    deleted = ann_repo.delete_annotations_by_source(workspace.container_name, blob_name, source)
    return ClearAnnotationsResponse(deleted=deleted)


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
        # Try with trailing slash
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
        data = {
                "page_number": body.page_number,
                "label": body.label,
                "bbox": body.bbox.model_dump(),
                "value_string": body.value_string,
            }
        if body.confidence is not None:
            data["confidence"] = body.confidence
        if body.text_type is not None:
            data["text_type"] = body.text_type
        if body.source is not None:
            data["source"] = body.source
        annotation = ann_repo.create_annotation(
            workspace.container_name,
            blob_name,
            data,
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


# ── Labels CRUD ──────────────────────────────────────────────────────────────

class AddLabelRequest(BaseModel):
    name: str = Field(..., min_length=1)
    color: str = Field(..., pattern=r"^#[0-9a-fA-F]{6}$")
    description: str = ""
    label_type: Literal["text", "table", "signature"] = "text"


@router.post("/{workspace_id}/labels", response_model=WorkspaceResponse, status_code=201)
async def add_label(
    workspace_id: str,
    body: AddLabelRequest,
    ws_repo=Depends(get_workspace_repository),
):
    """Añade una etiqueta al workspace."""
    try:
        workspace = ws_repo.find_by_id(workspace_id)
        workspace.add_label(name=body.name, color=body.color, description=body.description, label_type=body.label_type)
        ws_repo.save(workspace)
        return _to_response(workspace)
    except WorkspaceNotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))


class UpdateLabelRequest(BaseModel):
    new_name: Optional[str] = None
    color: Optional[str] = None
    description: Optional[str] = None


@router.patch("/{workspace_id}/labels/{label_name}", response_model=WorkspaceResponse)
async def update_label(
    workspace_id: str,
    label_name: str,
    body: UpdateLabelRequest,
    ws_repo=Depends(get_workspace_repository),
    ann_repo: BlobAnnotationRepository = Depends(get_blob_annotation_repository),
):
    """Actualiza una etiqueta (renombrar, cambiar color, etc). Actualiza anotaciones existentes."""
    try:
        workspace = ws_repo.find_by_id(workspace_id)
        workspace.update_label(
            name=label_name,
            new_name=body.new_name,
            color=body.color,
            description=body.description,
        )
        ws_repo.save(workspace)

        # Si se renombró, actualizar todas las anotaciones que usen el nombre viejo
        if body.new_name and body.new_name != label_name:
            container = workspace.container_name
            for blob_name_entry in workspace.documents:
                anns = ann_repo.list_annotations(container, blob_name_entry)
                changed = False
                for ann in anns:
                    if ann.get("label") == label_name:
                        ann["label"] = body.new_name
                        changed = True
                if changed:
                    ann_repo._save(container, blob_name_entry, anns)

        return _to_response(workspace)
    except WorkspaceNotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.delete("/{workspace_id}/labels/{label_name}", response_model=WorkspaceResponse)
async def remove_label(
    workspace_id: str,
    label_name: str,
    ws_repo=Depends(get_workspace_repository),
):
    """Elimina una etiqueta del workspace."""
    try:
        workspace = ws_repo.find_by_id(workspace_id)
        workspace.remove_label(label_name)
        ws_repo.save(workspace)
        return _to_response(workspace)
    except WorkspaceNotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))


# ── Export (blob-based, no local document_id needed) ─────────────────────────

@router.post("/{workspace_id}/documents/{blob_name:path}/export", status_code=200)
async def export_labels(
    workspace_id: str,
    blob_name: str,
    ann_repo: BlobAnnotationRepository = Depends(get_blob_annotation_repository),
    doc_repo: BlobDocumentRepository = Depends(get_blob_document_repository),
    ws_repo=Depends(get_workspace_repository),
    blob_storage=Depends(get_blob_storage),
):
    """Exporta anotaciones como .pdf.labels.json al blob y marca DONE.

    El JSON de salida incluye una seccion 'training_data' compatible con:
    - TrOCR fine-tuning: crop_bbox + ground_truth + text_type por region
    - Layout detection (DocLayout-YOLO): bboxes agrupados por pagina
    """
    try:
        workspace = ws_repo.find_by_id(workspace_id)
        container = workspace.container_name
        annotations = ann_repo.list_annotations(container, blob_name)

        # Metadata del documento para page_count
        try:
            meta = doc_repo.get_document_meta(container, blob_name)
            page_count = meta.get("page_count", 0)
        except Exception:
            page_count = 0

        # training_data.trocr: solo anotaciones con texto extraido
        trocr_entries = [
            {
                "annotation_id": a["id"],
                "page_number": a["page_number"],
                "crop_bbox": a["bbox"],
                "ground_truth": a["value_string"],
                "text_type": a.get("text_type", "unknown"),
            }
            for a in annotations
            if a.get("value_string", "").strip()
        ]

        # training_data.layout: todas las anotaciones agrupadas por pagina
        pages_map: dict[int, list[dict]] = {}
        for a in annotations:
            pg = a["page_number"]
            pages_map.setdefault(pg, []).append({
                "bbox": a["bbox"],
                "region_type": a["label"],
                "label": a["label"],
            })
        layout_entries = [
            {"page_number": pg, "regions": regions}
            for pg, regions in sorted(pages_map.items())
        ]

        export_payload = {
            "document_id": blob_name,
            "workspace_id": workspace_id,
            "document_kind": workspace.document_kind.value,
            "model_name": workspace.model_name,
            "page_count": page_count,
            "exported_at": datetime.now(UTC).isoformat(),
            "annotations": annotations,
            "training_data": {
                "trocr": trocr_entries,
                "layout": layout_entries,
            },
        }

        labels_blob_name = f"{blob_name}.labels.json"
        blob_storage.upload(
            container, labels_blob_name,
            json.dumps(export_payload, ensure_ascii=False, indent=2).encode("utf-8"),
        )
        workspace.mark_document_done(blob_name)
        ws_repo.save(workspace)
        return {"labels_blob": labels_blob_name, "workspace_id": workspace_id}
    except WorkspaceNotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except BlobStorageException as e:
        raise HTTPException(status_code=502, detail=str(e))


# ── Layout Detection Proxy ───────────────────────────────────────────────────

class DetectLayoutBody(BaseModel):
    page_number: int = Field(..., ge=1)


@router.post("/{workspace_id}/documents/{blob_name:path}/detect-layout")
async def detect_layout(
    workspace_id: str,
    blob_name: str,
    body: DetectLayoutBody,
    doc_repo: BlobDocumentRepository = Depends(get_blob_document_repository),
    ws_repo=Depends(get_workspace_repository),
    settings: Settings = Depends(get_settings),
):
    """Proxy hacia el layout-detector: obtiene la imagen del blob y llama al servicio GPU.

    El servidor GPU permanece en red interna — el browser nunca lo contacta directamente.
    """
    try:
        workspace = ws_repo.find_by_id(workspace_id)
        png_bytes = doc_repo.get_page_image(
            workspace.container_name, blob_name, body.page_number
        )
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Página no encontrada: {e}")

    # Obtener dimensiones de la página desde la metadata
    try:
        meta = doc_repo.get_document_meta(workspace.container_name, blob_name)
        page_meta = next(
            (p for p in meta.get("pages", []) if p["page_number"] == body.page_number),
            None,
        )
        width = page_meta["width_px"] if page_meta else 1024
        height = page_meta["height_px"] if page_meta else 1024
    except Exception:
        width, height = 1024, 1024

    image_base64 = base64.b64encode(png_bytes).decode()
    payload = {
        "document_id": blob_name,
        "pages": [
            {
                "page_number": body.page_number,
                "image_base64": image_base64,
                "width": width,
                "height": height,
            }
        ],
    }

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{settings.layout_detector_url}/api/v1/layout/detect",
                json=payload,
            )
            response.raise_for_status()
            return response.json()
    except httpx.ConnectError:
        raise HTTPException(
            status_code=503,
            detail="El servicio de detección de layout no está disponible",
        )
    except httpx.TimeoutException:
        raise HTTPException(
            status_code=504,
            detail="El servicio de detección de layout tardó demasiado",
        )
    except httpx.HTTPStatusError as e:
        raise HTTPException(
            status_code=502,
            detail=f"Error del servicio de layout: {e.response.text}",
        )


# ── Text Detection (OCR) Proxy ───────────────────────────────────────────────

class ExtractTextBody(BaseModel):
    page_number: int = Field(..., ge=1)


@router.post("/{workspace_id}/documents/{blob_name:path}/extract-text")
async def extract_text(
    workspace_id: str,
    blob_name: str,
    body: ExtractTextBody,
    doc_repo: BlobDocumentRepository = Depends(get_blob_document_repository),
    ann_repo: BlobAnnotationRepository = Depends(get_blob_annotation_repository),
    ws_repo=Depends(get_workspace_repository),
    blob_storage=Depends(get_blob_storage),
    settings: Settings = Depends(get_settings),
):
    """Proxy hacia el text-detector (Surya OCR).

    El backend:
    1. Recupera la imagen de la pagina del blob.
    2. Envia la pagina completa al text-detector (Surya procesa todo).
    3. Surya devuelve todas las lineas detectadas con bbox + texto + confianza.
    4. Guarda la respuesta cruda como _ocr.json en el blob.
    5. Recupera las anotaciones existentes y hace matching espacial:
       para cada anotacion, busca las lineas de Surya cuyo bbox cae dentro
       del bbox de la anotacion y concatena sus textos.
    6. Actualiza cada anotacion con el texto extraido.
    """
    try:
        workspace = ws_repo.find_by_id(workspace_id)
    except WorkspaceNotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))

    container = workspace.container_name

    # Cargar imagen de la pagina
    try:
        png_bytes = doc_repo.get_page_image(container, blob_name, body.page_number)
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Pagina no encontrada: {e}")

    # Enviar pagina completa al text-detector (Surya)
    image_b64 = base64.b64encode(png_bytes).decode("utf-8")
    payload = {
        "document_id": blob_name,
        "pages": [{"page_number": body.page_number, "image_base64": image_b64}],
    }

    try:
        async with httpx.AsyncClient(timeout=600.0) as client:
            response = await client.post(
                f"{settings.text_detector_url}/ocr/extract",
                json=payload,
            )
            response.raise_for_status()
            ocr_result = response.json()
    except httpx.ConnectError:
        raise HTTPException(
            status_code=503,
            detail="El servicio de extraccion de texto no esta disponible",
        )
    except httpx.TimeoutException:
        raise HTTPException(
            status_code=504,
            detail="El servicio de extraccion de texto tardo demasiado",
        )
    except httpx.HTTPStatusError as e:
        raise HTTPException(
            status_code=502,
            detail=f"Error del servicio de OCR: {e.response.text}",
        )

    # Guardar respuesta cruda como _ocr.json
    prefix = os.path.splitext(blob_name)[0]
    ocr_blob = f"{prefix}/_ocr.json"
    blob_storage.upload(
        container, ocr_blob,
        json.dumps(ocr_result, ensure_ascii=False, indent=2).encode("utf-8"),
    )

    # Recoger todas las lineas detectadas por Surya
    surya_lines: list[dict] = []
    for page_result in ocr_result.get("results", []):
        for extraction in page_result.get("extractions", []):
            surya_lines.append(extraction)

    # Matching espacial: asignar lineas de Surya a anotaciones existentes
    annotations = ann_repo.list_annotations(container, blob_name, body.page_number)
    if annotations:
        for ann in annotations:
            bbox = ann["bbox"]
            matched_texts = []
            matched_confidences = []
            for line in surya_lines:
                lb = line.get("bounding_box", {})
                if _bbox_contains(bbox, lb):
                    text = line.get("text", "").strip()
                    if text:
                        matched_texts.append(text)
                        matched_confidences.append(line.get("confidence", 0.0))

            if matched_texts:
                combined_text = " ".join(matched_texts)
                avg_confidence = sum(matched_confidences) / len(matched_confidences)
                ann_repo.update_annotation(
                    container, blob_name, ann["id"],
                    {
                        "value_string": combined_text,
                        "confidence": round(avg_confidence, 4),
                        "text_type": "unknown",
                        "source": "ocr",
                    },
                )

    return ocr_result


def _bbox_contains(annotation_bbox: dict, surya_bbox: dict, threshold: float = 0.5) -> bool:
    """Verifica si el centro del bbox de Surya cae dentro del bbox de la anotacion.

    Usa el centro del bbox de Surya para determinar contencion.
    Si threshold > 0, permite un margen de tolerancia basado en IoU.
    """
    # Centro del bbox de Surya
    sx1 = surya_bbox.get("x1", 0)
    sy1 = surya_bbox.get("y1", 0)
    sx2 = surya_bbox.get("x2", 0)
    sy2 = surya_bbox.get("y2", 0)
    cx = (sx1 + sx2) / 2
    cy = (sy1 + sy2) / 2

    # Bbox de la anotacion
    ax_min = annotation_bbox.get("x_min", 0)
    ay_min = annotation_bbox.get("y_min", 0)
    ax_max = annotation_bbox.get("x_max", 0)
    ay_max = annotation_bbox.get("y_max", 0)

    return ax_min <= cx <= ax_max and ay_min <= cy <= ay_max


# ── Scan (unified OCR) ──────────────────────────────────────────────────────

class ScanBody(BaseModel):
    page_number: int = Field(..., ge=1)


class ScanLineDtoResponse(BaseModel):
    text: str
    bounding_box: dict
    confidence: float


class ScanPageResultResponse(BaseModel):
    page_number: int
    lines: list[ScanLineDtoResponse]


class ScanResponse(BaseModel):
    total_lines: int
    results: list[ScanPageResultResponse]


@router.post("/{workspace_id}/documents/{blob_name:path}/scan")
async def scan_page(
    workspace_id: str,
    blob_name: str,
    body: ScanBody,
    doc_repo: BlobDocumentRepository = Depends(get_blob_document_repository),
    ws_repo=Depends(get_workspace_repository),
    blob_storage=Depends(get_blob_storage),
    settings: Settings = Depends(get_settings),
):
    """Escanea una pagina completa con Surya OCR.

    Envia la pagina al text-detector (Surya) que detecta y reconoce todo
    el texto en una sola pasada. Retorna las lineas detectadas para que
    el frontend las muestre en un modal de revision.
    """
    try:
        workspace = ws_repo.find_by_id(workspace_id)
    except WorkspaceNotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))

    container = workspace.container_name

    try:
        png_bytes = doc_repo.get_page_image(container, blob_name, body.page_number)
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Pagina no encontrada: {e}")

    image_b64 = base64.b64encode(png_bytes).decode("utf-8")
    payload = {
        "document_id": blob_name,
        "pages": [{"page_number": body.page_number, "image_base64": image_b64}],
    }

    try:
        async with httpx.AsyncClient(timeout=600.0) as client:
            response = await client.post(
                f"{settings.text_detector_url}/ocr/extract",
                json=payload,
            )
            response.raise_for_status()
            ocr_result = response.json()
    except httpx.ConnectError:
        raise HTTPException(
            status_code=503,
            detail="El servicio OCR no esta disponible. Verifica que Surya este corriendo.",
        )
    except httpx.TimeoutException:
        raise HTTPException(
            status_code=504,
            detail="El servicio OCR tardo demasiado",
        )
    except httpx.HTTPStatusError as e:
        raise HTTPException(
            status_code=502,
            detail=f"Error del servicio OCR: {e.response.text}",
        )

    # Guardar respuesta cruda por pagina
    prefix = os.path.splitext(blob_name)[0]
    ocr_blob = f"{prefix}/_ocr_page_{body.page_number}.json"
    blob_storage.upload(
        container, ocr_blob,
        json.dumps(ocr_result, ensure_ascii=False, indent=2).encode("utf-8"),
    )

    # Transformar a formato simplificado para el frontend
    page_results = []
    for page_result in ocr_result.get("results", []):
        lines = []
        for ext in page_result.get("extractions", []):
            text = ext.get("text", "").strip()
            if not text:
                continue
            lines.append(ScanLineDtoResponse(
                text=text,
                bounding_box=ext.get("bounding_box", {}),
                confidence=ext.get("confidence", 0.0),
            ))
        # Ordenar por posicion vertical (y1)
        lines.sort(key=lambda l: l.bounding_box.get("y1", 0))
        page_results.append(ScanPageResultResponse(
            page_number=page_result.get("page_number", body.page_number),
            lines=lines,
        ))

    total_lines = sum(len(p.lines) for p in page_results)
    return ScanResponse(total_lines=total_lines, results=page_results)


# ── Scan ALL pages in batches ─────────────────────────────────────────────────

_SURYA_BATCH_SIZE = 30


class ScanAllResponse(BaseModel):
    total_lines: int
    total_pages_scanned: int
    results: list[ScanPageResultResponse]


@router.post("/{workspace_id}/documents/{blob_name:path}/scan-all")
async def scan_all_pages(
    workspace_id: str,
    blob_name: str,
    doc_repo: BlobDocumentRepository = Depends(get_blob_document_repository),
    ws_repo=Depends(get_workspace_repository),
    blob_storage=Depends(get_blob_storage),
    settings: Settings = Depends(get_settings),
):
    """Escanea TODAS las paginas del documento en batches de hasta 30,
    enviando multiples imagenes a Surya en un solo request por batch."""
    try:
        workspace = ws_repo.find_by_id(workspace_id)
    except WorkspaceNotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))

    container = workspace.container_name

    # Obtener page_count del metadata
    try:
        meta = doc_repo.get_document_meta(container, blob_name)
        page_count = meta.get("page_count", 0)
    except Exception:
        raise HTTPException(status_code=404, detail="No se pudo obtener metadata del documento")

    if page_count == 0:
        return ScanAllResponse(total_lines=0, total_pages_scanned=0, results=[])

    prefix = os.path.splitext(blob_name)[0]
    all_page_results: list[ScanPageResultResponse] = []

    # Procesar en batches de _SURYA_BATCH_SIZE
    for batch_start in range(1, page_count + 1, _SURYA_BATCH_SIZE):
        batch_end = min(batch_start + _SURYA_BATCH_SIZE, page_count + 1)
        pages_payload = []

        for page_num in range(batch_start, batch_end):
            try:
                png_bytes = doc_repo.get_page_image(container, blob_name, page_num)
                image_b64 = base64.b64encode(png_bytes).decode("utf-8")
                pages_payload.append({
                    "page_number": page_num,
                    "image_base64": image_b64,
                })
            except Exception:
                continue  # skip pages that can't be read

        if not pages_payload:
            continue

        payload = {
            "document_id": blob_name,
            "pages": pages_payload,
        }

        try:
            async with httpx.AsyncClient(timeout=1200.0) as client:
                response = await client.post(
                    f"{settings.text_detector_url}/ocr/extract",
                    json=payload,
                )
                response.raise_for_status()
                ocr_result = response.json()
        except (httpx.ConnectError, httpx.TimeoutException, httpx.HTTPStatusError) as e:
            raise HTTPException(
                status_code=503,
                detail=f"Error del servicio OCR en batch {batch_start}-{batch_end - 1}: {str(e)}",
            )

        # Guardar cada pagina por separado y construir resultado
        for page_result in ocr_result.get("results", []):
            pn = page_result.get("page_number", batch_start)

            # Guardar respuesta cruda de esta pagina
            page_ocr_data = {"results": [page_result]}
            ocr_blob = f"{prefix}/_ocr_page_{pn}.json"
            blob_storage.upload(
                container, ocr_blob,
                json.dumps(page_ocr_data, ensure_ascii=False, indent=2).encode("utf-8"),
            )

            # Transformar a formato simplificado
            lines = []
            for ext in page_result.get("extractions", []):
                text = ext.get("text", "").strip()
                if not text:
                    continue
                lines.append(ScanLineDtoResponse(
                    text=text,
                    bounding_box=ext.get("bounding_box", {}),
                    confidence=ext.get("confidence", 0.0),
                ))
            lines.sort(key=lambda l: l.bounding_box.get("y1", 0))
            all_page_results.append(ScanPageResultResponse(
                page_number=pn,
                lines=lines,
            ))

    total_lines = sum(len(p.lines) for p in all_page_results)
    return ScanAllResponse(
        total_lines=total_lines,
        total_pages_scanned=len(all_page_results),
        results=all_page_results,
    )


# ── GET OCR results (saved from previous scan) ──────────────────────────────

@router.get("/{workspace_id}/documents/{blob_name:path}/ocr/{page_number}")
async def get_ocr_results(
    workspace_id: str,
    blob_name: str,
    page_number: int,
    ws_repo=Depends(get_workspace_repository),
    blob_storage=Depends(get_blob_storage),
):
    workspace = ws_repo.find_by_id(workspace_id)
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace no encontrado")

    container = workspace.container_name
    prefix = os.path.splitext(blob_name)[0]
    ocr_blob = f"{prefix}/_ocr_page_{page_number}.json"

    try:
        raw = blob_storage.download(container, ocr_blob)
        ocr_result = json.loads(raw)
    except Exception:
        return ScanResponse(total_lines=0, results=[])

    page_results = []
    for page_result in ocr_result.get("results", []):
        lines = []
        for ext in page_result.get("extractions", []):
            text = ext.get("text", "").strip()
            if not text:
                continue
            lines.append(ScanLineDtoResponse(
                text=text,
                bounding_box=ext.get("bounding_box", {}),
                confidence=ext.get("confidence", 0.0),
            ))
        lines.sort(key=lambda l: l.bounding_box.get("y1", 0))
        page_results.append(ScanPageResultResponse(
            page_number=page_result.get("page_number", page_number),
            lines=lines,
        ))

    total_lines = sum(len(p.lines) for p in page_results)
    return ScanResponse(total_lines=total_lines, results=page_results)


# ── Assemble table from OCR lines within a user-drawn bbox ────────────────────

class AssembleTableBody(BaseModel):
    page_number: int
    bbox: dict  # {x_min, y_min, x_max, y_max}


E14_DEFAULT_COLUMNS = [
    "IDCandidato1", "Casilla1", "Casilla2", "Casilla3",
    "IDCandidato2", "Casilla4", "Casilla5", "Casilla6",
    "IDCandidato3", "Casilla7", "Casilla8", "Casilla9",
]


def _default_column_name(index: int) -> str:
    if index < len(E14_DEFAULT_COLUMNS):
        return E14_DEFAULT_COLUMNS[index]
    return f"Col {index + 1}"


class CellData(BaseModel):
    text: str
    bbox: dict | None = None  # {x_min, y_min, x_max, y_max} — null if manually added

class AssembleTableResponse(BaseModel):
    columns: list[str]
    rows: list[list[CellData]]


_ID_CANDIDATO_RE = re.compile(r"^\d{2,3}$")


def _fix_e14_id_columns(rows: list[list["CellData"]]) -> None:
    """Corrige la ubicación de IDCandidato2 (col 4) e IDCandidato3 (col 8).

    Regla de negocio E14:
      - IDCandidato2 e IDCandidato3 son siempre 2 o 3 dígitos (nunca 0 ni 1 dígito).
      - Si la columna esperada no cumple, busca en columnas adyacentes (±1)
        y hace swap.
    """
    for row in rows:
        for id_col in (4, 8):
            id_text = row[id_col].text.strip()
            if _ID_CANDIDATO_RE.match(id_text):
                continue

            left = id_col - 1
            if left >= 0 and _ID_CANDIDATO_RE.match(row[left].text.strip()):
                row[left], row[id_col] = row[id_col], row[left]
                continue

            right = id_col + 1
            if right < len(row) and _ID_CANDIDATO_RE.match(row[right].text.strip()):
                row[id_col], row[right] = row[right], row[id_col]
                continue


def _assemble_table_from_ocr(
    all_lines: list[dict],
    bbox: dict,
    tolerance_ratio: float = 0.15,
    expected_cols: int | None = None,
) -> AssembleTableResponse | None:
    """Organiza lineas OCR dentro de un bbox como tabla (filas x columnas).

    tolerance_ratio expande el bbox para capturar lineas ligeramente fuera.
    Solo expande horizontalmente y hacia abajo — nunca hacia arriba,
    para evitar capturar encabezados de partidos u otros textos superiores.
    Retorna None si no hay lineas dentro del bbox expandido.
    """
    bx_min = bbox.get("x_min", 0)
    by_min = bbox.get("y_min", 0)
    bx_max = bbox.get("x_max", 0)
    by_max = bbox.get("y_max", 0)

    margin_x = (bx_max - bx_min) * tolerance_ratio
    bx_min -= margin_x
    bx_max += margin_x
    # No expandir verticalmente para no capturar encabezados ni totales

    inside = []
    for ln in all_lines:
        cx = (ln["x1"] + ln["x2"]) / 2
        cy = (ln["y1"] + ln["y2"]) / 2
        if bx_min <= cx <= bx_max and by_min <= cy <= by_max:
            inside.append(ln)

    if not inside:
        return None

    # Ordenar por Y, luego agrupar en filas por proximidad vertical
    inside.sort(key=lambda l: l["y1"])

    heights = [l["y2"] - l["y1"] for l in inside]
    avg_height = sum(heights) / len(heights) if heights else 10
    y_threshold = avg_height * 0.6

    rows_grouped: list[list[dict]] = []
    current_row = [inside[0]]
    for ln in inside[1:]:
        if abs(ln["y1"] - current_row[0]["y1"]) <= y_threshold:
            current_row.append(ln)
        else:
            rows_grouped.append(current_row)
            current_row = [ln]
    rows_grouped.append(current_row)

    for row in rows_grouped:
        row.sort(key=lambda l: l["x1"])

    # Detectar columnas por clustering de centros X
    all_cx = sorted([(ln["x1"] + ln["x2"]) / 2 for ln in inside])

    if expected_cols and expected_cols > 0:
        # Dividir el rango X en N columnas equidistantes
        x_min_all = min(ln["x1"] for ln in inside)
        x_max_all = max(ln["x2"] for ln in inside)
        col_width = (x_max_all - x_min_all) / expected_cols
        col_centers = [x_min_all + col_width * (i + 0.5) for i in range(expected_cols)]
        num_cols = expected_cols
    else:
        widths = [ln["x2"] - ln["x1"] for ln in inside]
        avg_width = sum(widths) / len(widths) if widths else 20
        x_threshold = avg_width * 0.8

        col_centers: list[float] = [all_cx[0]]
        for cx in all_cx[1:]:
            if cx - col_centers[-1] > x_threshold:
                col_centers.append(cx)
            else:
                col_centers[-1] = (col_centers[-1] + cx) / 2

        col_centers.sort()
        num_cols = len(col_centers)

    columns = [_default_column_name(i) for i in range(num_cols)]

    def nearest_col(ln: dict) -> int:
        cx = (ln["x1"] + ln["x2"]) / 2
        best = 0
        best_dist = abs(cx - col_centers[0])
        for i, cc in enumerate(col_centers[1:], 1):
            d = abs(cx - cc)
            if d < best_dist:
                best_dist = d
                best = i
        return best

    rows = []
    for row_group in rows_grouped:
        cells: list[CellData] = [CellData(text="") for _ in range(num_cols)]
        for ln in row_group:
            ci = nearest_col(ln)
            ln_bbox = {"x_min": ln["x1"], "y_min": ln["y1"], "x_max": ln["x2"], "y_max": ln["y2"]}
            if cells[ci].text:
                prev = cells[ci]
                merged_bbox = None
                if prev.bbox:
                    merged_bbox = {
                        "x_min": min(prev.bbox["x_min"], ln_bbox["x_min"]),
                        "y_min": min(prev.bbox["y_min"], ln_bbox["y_min"]),
                        "x_max": max(prev.bbox["x_max"], ln_bbox["x_max"]),
                        "y_max": max(prev.bbox["y_max"], ln_bbox["y_max"]),
                    }
                else:
                    merged_bbox = ln_bbox
                cells[ci] = CellData(text=prev.text + " " + ln["text"], bbox=merged_bbox)
            else:
                cells[ci] = CellData(text=ln["text"], bbox=ln_bbox)
        rows.append(cells)

    # ── Post-proceso E14: corregir IDCandidato2 (col 4) e IDCandidato3 (col 8) ──
    # Regla de negocio: IDCandidato2 e IDCandidato3 son siempre exactamente 2 dígitos.
    # Si nearest_col los puso en una columna vecina, los reubicamos.
    if num_cols == 12:
        _fix_e14_id_columns(rows)

    return AssembleTableResponse(columns=columns, rows=rows)


def _load_ocr_lines(blob_storage, container: str, prefix: str, page_number: int) -> list[dict]:
    """Carga las lineas OCR de una pagina desde blob storage."""
    ocr_blob = f"{prefix}/_ocr_page_{page_number}.json"
    try:
        raw = blob_storage.download(container, ocr_blob)
        ocr_result = json.loads(raw)
    except Exception:
        return []

    all_lines = []
    for page_result in ocr_result.get("results", []):
        for ext in page_result.get("extractions", []):
            text = ext.get("text", "").strip()
            if not text:
                continue
            bb = ext.get("bounding_box", {})
            all_lines.append({
                "text": text,
                "x1": bb.get("x1", 0),
                "y1": bb.get("y1", 0),
                "x2": bb.get("x2", 0),
                "y2": bb.get("y2", 0),
            })
    return all_lines


@router.post("/{workspace_id}/documents/{blob_name:path}/assemble-table")
async def assemble_table(
    workspace_id: str,
    blob_name: str,
    body: AssembleTableBody,
    ws_repo=Depends(get_workspace_repository),
    blob_storage=Depends(get_blob_storage),
):
    """Dado un bbox dibujado por el usuario, busca las lineas OCR guardadas
    que caen dentro de esa region y las organiza como tabla (filas x columnas)
    usando proximidad espacial."""
    workspace = ws_repo.find_by_id(workspace_id)
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace no encontrado")

    container = workspace.container_name
    prefix = os.path.splitext(blob_name)[0]
    all_lines = _load_ocr_lines(blob_storage, container, prefix, body.page_number)

    if not all_lines:
        return AssembleTableResponse(columns=["Col 1"], rows=[[CellData(text="")]])

    result = _assemble_table_from_ocr(all_lines, body.bbox)
    if result is None:
        return AssembleTableResponse(columns=["Col 1"], rows=[[CellData(text="")]])

    return result


# ── Auto-label from reference document ──────────────────────────────────

class AutoLabelBody(BaseModel):
    reference_blob_name: str


class AutoLabelPageResultDto(BaseModel):
    page_number: int
    annotations_created: int


class AutoLabelResponse(BaseModel):
    total_annotations: int
    pages: list[AutoLabelPageResultDto]


@router.post("/{workspace_id}/documents/{blob_name:path}/auto-label")
async def auto_label(
    workspace_id: str,
    blob_name: str,
    body: AutoLabelBody,
    ann_repo: BlobAnnotationRepository = Depends(get_blob_annotation_repository),
    doc_repo: BlobDocumentRepository = Depends(get_blob_document_repository),
    ws_repo=Depends(get_workspace_repository),
    blob_storage=Depends(get_blob_storage),
    use_case: AutoLabelUseCase = Depends(get_auto_label_use_case),
):
    """Auto-etiqueta un documento usando las anotaciones de un documento de referencia.

    1. Carga las anotaciones del documento de referencia (template)
    2. Para cada pagina del documento destino, carga el OCR guardado
    3. Usa el AutoLabelUseCase (Strategy Pattern) para hacer matching
    4. Crea las anotaciones resultantes en el documento destino
    """
    try:
        workspace = ws_repo.find_by_id(workspace_id)
    except WorkspaceNotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))

    container = workspace.container_name

    # 1. Load reference annotations
    ref_annotations = ann_repo.list_annotations(container, body.reference_blob_name)
    if not ref_annotations:
        raise HTTPException(status_code=400, detail="El documento de referencia no tiene anotaciones")

    # 2. Get workspace labels to determine label_type
    label_types: dict[str, str] = {}
    for lbl in workspace.labels:
        label_types[lbl["name"]] = lbl.get("label_type", "text")

    # 3. Group reference annotations by page → TemplateAnnotation
    templates_by_page: dict[int, list[TemplateAnnotation]] = {}
    for ann in ref_annotations:
        pg = ann["page_number"]
        bbox = ann["bbox"]
        tmpl = TemplateAnnotation(
            label=ann["label"],
            bbox_x_min=bbox["x_min"],
            bbox_y_min=bbox["y_min"],
            bbox_x_max=bbox["x_max"],
            bbox_y_max=bbox["y_max"],
            value_string=ann.get("value_string", ""),
            label_type=label_types.get(ann["label"], LabelType.TEXT),
        )
        templates_by_page.setdefault(pg, []).append(tmpl)

    # 4. Load page dimensions for scaling between reference and target
    def _load_page_dims(blob: str) -> dict[int, PageDimensions]:
        try:
            meta = doc_repo.get_document_meta(container, blob)
        except Exception:
            return {}
        return {
            p["page_number"]: PageDimensions(
                width_px=p["width_px"], height_px=p["height_px"],
            )
            for p in meta.get("pages", [])
        }

    ref_dims_by_page = _load_page_dims(body.reference_blob_name)
    target_dims_by_page = _load_page_dims(blob_name)

    # 5. For each page, load saved OCR → OcrLine
    prefix = os.path.splitext(blob_name)[0]
    ocr_by_page: dict[int, list[OcrLine]] = {}

    for page_num in templates_by_page:
        ocr_blob = f"{prefix}/_ocr_page_{page_num}.json"
        try:
            raw = blob_storage.download(container, ocr_blob)
            ocr_result = json.loads(raw)
        except Exception:
            continue  # page not scanned yet, skip

        lines: list[OcrLine] = []
        for page_result in ocr_result.get("results", []):
            for ext in page_result.get("extractions", []):
                text = ext.get("text", "").strip()
                if not text:
                    continue
                bb = ext.get("bounding_box", {})
                lines.append(OcrLine(
                    text=text,
                    x1=bb.get("x1", 0),
                    y1=bb.get("y1", 0),
                    x2=bb.get("x2", 0),
                    y2=bb.get("y2", 0),
                    confidence=ext.get("confidence", 0.0),
                ))
        ocr_by_page[page_num] = lines

    # 6. Execute matching via use case (pure domain logic)
    matched_by_page = use_case.execute(
        templates_by_page,
        ocr_by_page,
        ref_dims_by_page=ref_dims_by_page,
        target_dims_by_page=target_dims_by_page,
    )

    # 7. Persist matched annotations (auto-assemble tables from OCR)
    page_results: list[AutoLabelPageResultDto] = []
    total = 0
    ocr_lines_cache: dict[int, list[dict]] = {}

    for page_num, matched_list in sorted(matched_by_page.items()):
        count = 0
        for m in matched_list:
            value_string = m.value_string

            # Para tablas, auto-ensamblar celdas desde OCR
            if m.label_type == LabelType.TABLE:
                if page_num not in ocr_lines_cache:
                    ocr_lines_cache[page_num] = _load_ocr_lines(
                        blob_storage, container, prefix, page_num,
                    )
                # Tablas de candidatos → 12 columnas E14; consolidados → detección automática
                is_candidato_table = not m.label.startswith("ConsolidadoVotos")
                assembled = _assemble_table_from_ocr(
                    ocr_lines_cache[page_num], m.bbox,
                    expected_cols=len(E14_DEFAULT_COLUMNS) if is_candidato_table else None,
                )
                if assembled is not None:
                    value_string = json.dumps({
                        "columns": assembled.columns,
                        "rows": [[c.model_dump() for c in row] for row in assembled.rows],
                    }, ensure_ascii=False)

            ann_repo.create_annotation(container, blob_name, {
                "page_number": page_num,
                "label": m.label,
                "bbox": m.bbox,
                "value_string": value_string,
                "confidence": m.confidence,
                "source": m.source,
            })
            count += 1
        page_results.append(AutoLabelPageResultDto(
            page_number=page_num,
            annotations_created=count,
        ))
        total += count

    return AutoLabelResponse(total_annotations=total, pages=page_results)


# ── Helpers ──────────────────────────────────────────────────────────────────

def _to_response(workspace) -> WorkspaceResponse:
    return WorkspaceResponse(
        id=workspace.id,
        name=workspace.name,
        container_name=workspace.container_name,
        document_kind=workspace.document_kind.value,
        model_name=workspace.model_name,
        labels=workspace.labels,
        total_documents=workspace.total_documents(),
        total_done=workspace.total_done(),
        documents=[
            WorkspaceDocumentEntry(blob_name=name, status=status.value)
            for name, status in workspace.documents.items()
        ],
        created_at=workspace.created_at.isoformat(),
        updated_at=workspace.updated_at.isoformat(),
    )
