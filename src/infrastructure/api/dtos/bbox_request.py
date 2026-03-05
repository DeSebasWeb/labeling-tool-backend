from __future__ import annotations
from pydantic import BaseModel, Field


class BboxRequest(BaseModel):
    x0: float = Field(..., ge=0)
    y0: float = Field(..., ge=0)
    x1: float = Field(..., ge=0)
    y1: float = Field(..., ge=0)
    x2: float = Field(..., ge=0)
    y2: float = Field(..., ge=0)
    x3: float = Field(..., ge=0)
    y3: float = Field(..., ge=0)
