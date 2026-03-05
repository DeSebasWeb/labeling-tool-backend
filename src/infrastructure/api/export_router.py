from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from ...application.use_cases.export_annotations_use_case import ExportAnnotationsUseCase
from ...domain.exceptions.document_not_found_exception import DocumentNotFoundException
from ..dependencies import get_export_use_case

router = APIRouter(prefix="/documents/{document_id}/export", tags=["export"])


@router.get("")
async def export_annotations(
    document_id: str,
    use_case: ExportAnnotationsUseCase = Depends(get_export_use_case),
):
    """
    Exporta las anotaciones de un documento en formato idéntico al JSON de ADI.
    El resultado puede consumirse directamente por VerifyID sin cambios.
    """
    try:
        result = use_case.execute(document_id)
        return JSONResponse(content=result)
    except DocumentNotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))
