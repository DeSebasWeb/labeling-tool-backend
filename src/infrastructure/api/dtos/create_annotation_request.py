from __future__ import annotations
from pydantic import BaseModel, Field
from .bbox_request import BboxRequest


class CreateAnnotationRequest(BaseModel):
    page_number: int = Field(..., ge=1)
    label: str = Field(..., min_length=1)
    bbox: BboxRequest
    value_string: str
