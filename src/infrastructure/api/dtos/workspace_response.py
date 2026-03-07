from __future__ import annotations
from pydantic import BaseModel


class WorkspaceDocumentEntry(BaseModel):
    blob_name: str
    status: str


class WorkspaceResponse(BaseModel):
    id: str
    name: str
    container_name: str
    document_kind: str
    model_name: str
    labels: list[dict] = []
    total_documents: int
    total_done: int
    documents: list[WorkspaceDocumentEntry]
    created_at: str
    updated_at: str
