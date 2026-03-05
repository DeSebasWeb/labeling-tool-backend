from __future__ import annotations
from pydantic import BaseModel


class DocumentResponse(BaseModel):
    id: str
    original_filename: str
    document_kind: str
    status: str
    total_annotations: int
    page_count: int
    created_at: str
    updated_at: str
