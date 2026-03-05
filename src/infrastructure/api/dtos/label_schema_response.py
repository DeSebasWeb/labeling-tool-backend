from __future__ import annotations
from pydantic import BaseModel
from .label_definition_response import LabelDefinitionResponse


class LabelSchemaResponse(BaseModel):
    document_kind: str
    labels: list[LabelDefinitionResponse]
