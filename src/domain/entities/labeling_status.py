from enum import Enum


class LabelingStatus(str, Enum):
    PENDING     = "pending"       # subido, sin anotaciones
    IN_PROGRESS = "in_progress"   # tiene al menos una anotación
    DONE        = "done"          # marcado como completo por el usuario
    EXPORTED    = "exported"      # JSON de entrenamiento ya generado
