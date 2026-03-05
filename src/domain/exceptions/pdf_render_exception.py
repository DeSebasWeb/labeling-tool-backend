class PdfRenderException(Exception):
    def __init__(self, document_id: str, reason: str):
        super().__init__(f"Error renderizando PDF '{document_id}': {reason}")
        self.document_id = document_id
        self.reason = reason
