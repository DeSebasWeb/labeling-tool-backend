from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, UTC
from .document_kind import DocumentKind
from .document_page import DocumentPage
from .labeling_status import LabelingStatus


@dataclass
class LabelingDocument:
    """Agregado raíz: un PDF con sus páginas renderizadas y su estado de etiquetado."""
    id: str
    original_filename: str
    storage_path: str
    document_kind: DocumentKind
    pages: list[DocumentPage] = field(default_factory=list)
    status: LabelingStatus = LabelingStatus.PENDING
    total_annotations: int = 0
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def add_page(self, page: DocumentPage) -> None:
        self.pages.append(page)
        self.updated_at = datetime.now(UTC)

    def increment_annotations(self) -> None:
        self.total_annotations += 1
        if self.status == LabelingStatus.PENDING:
            self.status = LabelingStatus.IN_PROGRESS
        self.updated_at = datetime.now(UTC)

    def decrement_annotations(self) -> None:
        self.total_annotations = max(0, self.total_annotations - 1)
        if self.total_annotations == 0:
            self.status = LabelingStatus.PENDING
        self.updated_at = datetime.now(UTC)

    def mark_done(self) -> None:
        self.status = LabelingStatus.DONE
        self.updated_at = datetime.now(UTC)

    def mark_exported(self) -> None:
        self.status = LabelingStatus.EXPORTED
        self.updated_at = datetime.now(UTC)

    @property
    def page_count(self) -> int:
        return len(self.pages)
