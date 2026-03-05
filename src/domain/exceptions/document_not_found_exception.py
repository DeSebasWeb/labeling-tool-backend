class DocumentNotFoundException(Exception):
    def __init__(self, document_id: str):
        super().__init__(f"Documento no encontrado: {document_id}")
        self.document_id = document_id
