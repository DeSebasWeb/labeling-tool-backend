from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, UTC
from .document_kind import DocumentKind
from .workspace_document_status import WorkspaceDocumentStatus

@dataclass
class Workspace:
    """
    Agrupa un conjunto de PDFs en un container de blob storage.
    Cada PDF tiene un estado de etiquetado.
    El modelo a entrenar se registra en model-registry cuando el pipeline termina.
    """
    id: str
    name: str
    container_name: str            # nombre del container en Azure Blob / Azurite
    document_kind: DocumentKind
    model_name: str                # nombre que tendrá el modelo al entrenar
    documents: dict[str, WorkspaceDocumentStatus] = field(default_factory=dict)
    labels: list[dict] = field(default_factory=list)  # [{name, color, description}, ...]
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def add_document(self, blob_name: str) -> None:
        """Registra un PDF como PENDING solo si aún no existe en el workspace."""
        if blob_name not in self.documents:
            self.documents[blob_name] = WorkspaceDocumentStatus.PENDING
            self.updated_at = datetime.now(UTC)

    def register_document(self, blob_name: str) -> None:
        """Registra o re-registra un PDF como PENDING (idempotente para re-subidas)."""
        self.documents[blob_name] = WorkspaceDocumentStatus.PENDING
        self.updated_at = datetime.now(UTC)

    def start_document(self, blob_name: str) -> None:
        """Marca un documento como IN_PROGRESS al abrirlo en el editor."""
        self._require_exists(blob_name)
        self.documents[blob_name] = WorkspaceDocumentStatus.IN_PROGRESS
        self.updated_at = datetime.now(UTC)

    def mark_document_done(self, blob_name: str) -> None:
        """Marca un documento como completamente etiquetado."""
        self._require_exists(blob_name)
        self.documents[blob_name] = WorkspaceDocumentStatus.DONE
        self.updated_at = datetime.now(UTC)

    def remove_document(self, blob_name: str) -> None:
        """Elimina un documento del registro del workspace."""
        self._require_exists(blob_name)
        del self.documents[blob_name]
        self.updated_at = datetime.now(UTC)

    def documents_ready_for_training(self) -> list[str]:
        """Retorna los blob_names de PDFs en estado DONE."""
        return [
            name for name, status in self.documents.items()
            if status == WorkspaceDocumentStatus.DONE
        ]

    def total_documents(self) -> int:
        return len(self.documents)

    def total_done(self) -> int:
        return len(self.documents_ready_for_training())

    def add_label(self, name: str, color: str, description: str = "", label_type: str = "text") -> None:
        """Añade una etiqueta al workspace si no existe ya."""
        if not any(lbl["name"] == name for lbl in self.labels):
            self.labels.append({"name": name, "color": color, "description": description, "label_type": label_type})
            self.updated_at = datetime.now(UTC)

    def remove_label(self, name: str) -> None:
        """Elimina una etiqueta del workspace."""
        self.labels = [lbl for lbl in self.labels if lbl["name"] != name]
        self.updated_at = datetime.now(UTC)

    def update_label(self, name: str, new_name: str = None, color: str = None, description: str = None) -> None:
        """Actualiza una etiqueta existente (incluyendo renombrar)."""
        if new_name and new_name != name and any(lbl["name"] == new_name for lbl in self.labels):
            raise ValueError(f"Ya existe una etiqueta con el nombre '{new_name}'")
        for lbl in self.labels:
            if lbl["name"] == name:
                if new_name is not None:
                    lbl["name"] = new_name
                if color is not None:
                    lbl["color"] = color
                if description is not None:
                    lbl["description"] = description
                self.updated_at = datetime.now(UTC)
                return

    def _require_exists(self, blob_name: str) -> None:
        if blob_name not in self.documents:
            raise ValueError(f"Documento '{blob_name}' no registrado en el workspace")
