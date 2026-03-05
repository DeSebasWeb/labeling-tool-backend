from __future__ import annotations
import os
import uuid
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse
from ...domain.entities.document_kind import DocumentKind
from ...application.use_cases.upload_document_use_case import UploadDocumentUseCase
from ...application.use_cases.get_document_use_case import GetDocumentUseCase
from ...application.use_cases.list_documents_use_case import ListDocumentsUseCase
from ...application.use_cases.mark_document_done_use_case import MarkDocumentDoneUseCase
from ...domain.exceptions.document_not_found_exception import DocumentNotFoundException
from ...domain.exceptions.invalid_document_exception import InvalidDocumentException
from ...domain.exceptions.pdf_render_exception import PdfRenderException
from ..config import get_settings
from ..dependencies import get_upload_use_case, get_get_document_use_case, \
    get_list_documents_use_case, get_mark_done_use_case
from .dtos.document_response import DocumentResponse
from .dtos.page_response import PageResponse

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("", response_model=DocumentResponse, status_code=201)
async def upload_document(
    file: UploadFile = File(...),
    document_kind: DocumentKind = Form(...),
    use_case: UploadDocumentUseCase = Depends(get_upload_use_case),
    settings=Depends(get_settings),
):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Solo se aceptan archivos PDF")

    os.makedirs(settings.upload_dir, exist_ok=True)
    safe_name = f"{uuid.uuid4()}_{file.filename}"
    upload_path = os.path.join(settings.upload_dir, safe_name)

    try:
        with open(upload_path, "wb") as out:
            while chunk := await file.read(1024 * 1024):
                out.write(chunk)
    except Exception:
        if os.path.exists(upload_path):
            os.remove(upload_path)
        raise
    finally:
        await file.close()

    try:
        doc = use_case.execute(
            original_filename=file.filename,
            storage_path=upload_path,
            document_kind=document_kind,
        )
    except InvalidDocumentException as e:
        os.remove(upload_path)
        raise HTTPException(status_code=400, detail=str(e))
    except PdfRenderException as e:
        os.remove(upload_path)
        raise HTTPException(status_code=422, detail=str(e))

    return _to_response(doc)


@router.get("", response_model=list[DocumentResponse])
async def list_documents(
    use_case: ListDocumentsUseCase = Depends(get_list_documents_use_case),
):
    return [_to_response(d) for d in use_case.execute()]


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: str,
    use_case: GetDocumentUseCase = Depends(get_get_document_use_case),
):
    try:
        return _to_response(use_case.execute(document_id))
    except DocumentNotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{document_id}/pages", response_model=list[PageResponse])
async def get_pages(
    document_id: str,
    use_case: GetDocumentUseCase = Depends(get_get_document_use_case),
):
    try:
        doc = use_case.execute(document_id)
    except DocumentNotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))

    return [
        PageResponse(
            page_number=p.page_number,
            image_url=f"/documents/{document_id}/pages/{p.page_number}/image",
            width_px=p.width_px,
            height_px=p.height_px,
            width_inch=p.width_inch,
            height_inch=p.height_inch,
        )
        for p in doc.pages
    ]


@router.get("/{document_id}/pages/{page_number}/image")
async def get_page_image(
    document_id: str,
    page_number: int,
    use_case: GetDocumentUseCase = Depends(get_get_document_use_case),
):
    try:
        doc = use_case.execute(document_id)
    except DocumentNotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))

    page = next((p for p in doc.pages if p.page_number == page_number), None)
    if page is None:
        raise HTTPException(status_code=404, detail=f"Página {page_number} no encontrada")

    return FileResponse(page.image_path, media_type="image/png")


@router.patch("/{document_id}/done", response_model=DocumentResponse)
async def mark_done(
    document_id: str,
    use_case: MarkDocumentDoneUseCase = Depends(get_mark_done_use_case),
):
    try:
        return _to_response(use_case.execute(document_id))
    except DocumentNotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))


def _to_response(doc) -> DocumentResponse:
    return DocumentResponse(
        id=doc.id,
        original_filename=doc.original_filename,
        document_kind=doc.document_kind.value,
        status=doc.status.value,
        total_annotations=doc.total_annotations,
        page_count=doc.page_count,
        created_at=doc.created_at.isoformat(),
        updated_at=doc.updated_at.isoformat(),
    )
