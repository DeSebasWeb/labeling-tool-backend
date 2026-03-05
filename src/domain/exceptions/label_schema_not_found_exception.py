class LabelSchemaNotFoundException(Exception):
    def __init__(self, document_kind: str):
        super().__init__(f"Esquema de etiquetas no encontrado para tipo: '{document_kind}'")
        self.document_kind = document_kind
