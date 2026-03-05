from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException
from ...domain.entities.document_kind import DocumentKind
from ...domain.exceptions.label_schema_not_found_exception import LabelSchemaNotFoundException
from ...application.use_cases.get_label_schema_use_case import GetLabelSchemaUseCase
from ..dependencies import get_label_schema_use_case
from .dtos.label_definition_response import LabelDefinitionResponse
from .dtos.label_schema_response import LabelSchemaResponse

router = APIRouter(prefix="/schemas", tags=["schemas"])


@router.get("/{document_kind}", response_model=LabelSchemaResponse)
async def get_schema(
    document_kind: DocumentKind,
    use_case: GetLabelSchemaUseCase = Depends(get_label_schema_use_case),
):
    try:
        schema = use_case.execute(document_kind)
        return LabelSchemaResponse(
            document_kind=schema.document_kind.value,
            labels=[
                LabelDefinitionResponse(
                    name=lb.name,
                    description=lb.description,
                    repeats_per_page=lb.repeats_per_page,
                )
                for lb in schema.labels
            ],
        )
    except LabelSchemaNotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{document_kind}/names", response_model=list[str])
async def get_label_names(
    document_kind: DocumentKind,
    use_case: GetLabelSchemaUseCase = Depends(get_label_schema_use_case),
):
    try:
        return use_case.execute(document_kind).label_names()
    except LabelSchemaNotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))
