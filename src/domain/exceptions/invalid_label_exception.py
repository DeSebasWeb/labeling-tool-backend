class InvalidLabelException(Exception):
    def __init__(self, label: str, document_kind: str):
        super().__init__(
            f"Etiqueta '{label}' no es válida para el tipo de documento '{document_kind}'"
        )
        self.label = label
        self.document_kind = document_kind
