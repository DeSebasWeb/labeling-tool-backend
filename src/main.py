from __future__ import annotations
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .infrastructure.config import get_settings
from .infrastructure.api.health_router import router as health_router
from .infrastructure.api.workspace_router import router as workspace_router

settings = get_settings()

app = FastAPI(
    title="Labeling Tool API",
    description="Herramienta de etiquetado de actas E14 — genera datos de entrenamiento en formato ADI",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(workspace_router)


if __name__ == "__main__":
    uvicorn.run(
        "src.main:app",
        host=settings.host,
        port=settings.port,
        reload=True,
    )
