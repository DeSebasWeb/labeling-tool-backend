from __future__ import annotations
from pydantic import BaseModel


class AnnotationResponse(BaseModel):
    id: str
    document_id: str
    page_number: int
    label: str
    bbox: list[float]
    value_string: str
    confidence: float
    created_at: str
    updated_at: str
