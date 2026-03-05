from __future__ import annotations
from typing import Optional
from pydantic import BaseModel
from .bbox_request import BboxRequest


class UpdateAnnotationRequest(BaseModel):
    label: Optional[str] = None
    bbox: Optional[BboxRequest] = None
    value_string: Optional[str] = None
