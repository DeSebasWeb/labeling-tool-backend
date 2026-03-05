class InvalidDocumentException(Exception):
    def __init__(self, reason: str):
        super().__init__(f"Documento inválido: {reason}")
        self.reason = reason
