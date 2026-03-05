class AnnotationNotFoundException(Exception):
    def __init__(self, annotation_id: str):
        super().__init__(f"Anotación no encontrada: {annotation_id}")
        self.annotation_id = annotation_id
