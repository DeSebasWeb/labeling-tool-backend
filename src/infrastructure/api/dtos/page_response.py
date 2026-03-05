from __future__ import annotations
from pydantic import BaseModel


class PageResponse(BaseModel):
    page_number: int
    image_url: str
    width_px: int
    height_px: int
    width_inch: float
    height_inch: float
