from __future__ import annotations
from pydantic import BaseModel, Field
from ....domain.entities.document_kind import DocumentKind


class CreateWorkspaceRequest(BaseModel):
    name: str = Field(..., min_length=3, max_length=63)
    document_kind: DocumentKind
    model_name: str = Field(..., min_length=1)
