from __future__ import annotations
from pydantic import BaseModel


class LabelDefinitionResponse(BaseModel):
    name: str
    description: str
    repeats_per_page: bool
