from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class BoundingBox:
    """
    Polígono de 4 puntos en el espacio de la imagen (píxeles o pulgadas).
    Representación: [x0,y0, x1,y1, x2,y2, x3,y3] en sentido horario
    desde la esquina superior izquierda — mismo formato que ADI.
    """
    x0: float
    y0: float
    x1: float
    y1: float
    x2: float
    y2: float
    x3: float
    y3: float

    def __post_init__(self) -> None:
        coords = [self.x0, self.y0, self.x1, self.y1,
                  self.x2, self.y2, self.x3, self.y3]
        if any(c < 0 for c in coords):
            raise ValueError(f"BoundingBox no puede tener coordenadas negativas: {coords}")

    @classmethod
    def from_polygon(cls, polygon: list[float]) -> "BoundingBox":
        """Crea desde lista plana de 8 floats [x0,y0,x1,y1,x2,y2,x3,y3]."""
        if len(polygon) != 8:
            raise ValueError(f"Se esperan 8 valores para el polígono, se recibieron {len(polygon)}")
        return cls(*polygon)

    @classmethod
    def from_rect(cls, x: float, y: float, width: float, height: float) -> "BoundingBox":
        """Crea desde rectángulo alineado con los ejes (canvas del frontend)."""
        if width <= 0 or height <= 0:
            raise ValueError(f"Ancho y alto deben ser positivos: width={width}, height={height}")
        return cls(
            x0=x,        y0=y,
            x1=x+width,  y1=y,
            x2=x+width,  y2=y+height,
            x3=x,        y3=y+height,
        )

    def to_polygon(self) -> list[float]:
        """Exporta como lista plana — formato ADI polygon."""
        return [self.x0, self.y0, self.x1, self.y1,
                self.x2, self.y2, self.x3, self.y3]

    @property
    def x_min(self) -> float:
        return min(self.x0, self.x1, self.x2, self.x3)

    @property
    def y_min(self) -> float:
        return min(self.y0, self.y1, self.y2, self.y3)

    @property
    def x_max(self) -> float:
        return max(self.x0, self.x1, self.x2, self.x3)

    @property
    def y_max(self) -> float:
        return max(self.y0, self.y1, self.y2, self.y3)
