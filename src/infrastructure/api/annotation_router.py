from __future__ import annotations
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from ...domain.entities.bounding_box import BoundingBox
from ...application.use_cases.save_annotation_use_case import SaveAnnotationUseCase
from ...application.use_cases.update_annotation_use_case import UpdateAnnotationUseCase
from ...application.use_cases.delete_annotation_use_case import DeleteAnnotationUseCase
from ...application.use_cases.list_annotations_use_case import ListAnnotationsUseCase
from ...domain.exceptions.annotation_not_found_exception import AnnotationNotFoundException
from ...domain.exceptions.document_not_found_exception import DocumentNotFoundException
from ...domain.exceptions.invalid_label_exception import InvalidLabelException
from ..dependencies import (
    get_save_annotation_use_case,
    get_update_annotation_use_case,
    get_delete_annotation_use_case,
    get_list_annotations_use_case,
)
from .dtos.bbox_request import BboxRequest
from .dtos.create_annotation_request import CreateAnnotationRequest
from .dtos.update_annotation_request import UpdateAnnotationRequest
from .dtos.annotation_response import AnnotationResponse

router = APIRouter(prefix="/documents/{document_id}/annotations", tags=["annotations"])


@router.post("", response_model=AnnotationResponse, status_code=201)
async def create_annotation(
    document_id: str,
    body: CreateAnnotationRequest,
    use_case: SaveAnnotationUseCase = Depends(get_save_annotation_use_case),
):
    try:
        bbox = BoundingBox(
            x0=body.bbox.x0, y0=body.bbox.y0,
            x1=body.bbox.x1, y1=body.bbox.y1,
            x2=body.bbox.x2, y2=body.bbox.y2,
            x3=body.bbox.x3, y3=body.bbox.y3,
        )
        annotation = use_case.execute(
            document_id=document_id,
            page_number=body.page_number,
            label=body.label,
            bbox=bbox,
            value_string=body.value_string,
        )
        return _to_response(annotation)
    except DocumentNotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))
    except InvalidLabelException as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("", response_model=list[AnnotationResponse])
async def list_annotations(
    document_id: str,
    page_number: Optional[int] = None,
    use_case: ListAnnotationsUseCase = Depends(get_list_annotations_use_case),
):
    try:
        return [_to_response(a) for a in use_case.execute(document_id, page_number)]
    except DocumentNotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.patch("/{annotation_id}", response_model=AnnotationResponse)
async def update_annotation(
    document_id: str,
    annotation_id: str,
    body: UpdateAnnotationRequest,
    use_case: UpdateAnnotationUseCase = Depends(get_update_annotation_use_case),
):
    try:
        bbox = None
        if body.bbox is not None:
            bbox = BoundingBox(
                x0=body.bbox.x0, y0=body.bbox.y0,
                x1=body.bbox.x1, y1=body.bbox.y1,
                x2=body.bbox.x2, y2=body.bbox.y2,
                x3=body.bbox.x3, y3=body.bbox.y3,
            )
        annotation = use_case.execute(
            annotation_id=annotation_id,
            document_id=document_id,
            label=body.label,
            bbox=bbox,
            value_string=body.value_string,
        )
        return _to_response(annotation)
    except AnnotationNotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))
    except InvalidLabelException as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/{annotation_id}", status_code=204)
async def delete_annotation(
    document_id: str,
    annotation_id: str,
    use_case: DeleteAnnotationUseCase = Depends(get_delete_annotation_use_case),
):
    try:
        use_case.execute(annotation_id)
    except AnnotationNotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))


def _to_response(ann) -> AnnotationResponse:
    return AnnotationResponse(
        id=ann.id,
        document_id=ann.document_id,
        page_number=ann.page_number,
        label=ann.label,
        bbox=ann.bbox.to_polygon(),
        value_string=ann.value_string,
        confidence=ann.confidence,
        created_at=ann.created_at.isoformat(),
        updated_at=ann.updated_at.isoformat(),
    )
