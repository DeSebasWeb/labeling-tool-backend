from __future__ import annotations
from abc import ABC, abstractmethod
from ..entities.labeling_document import LabelingDocument


class IDocumentRepository(ABC):

    @abstractmethod
    def save(self, document: LabelingDocument) -> None: ...

    @abstractmethod
    def find_by_id(self, document_id: str) -> LabelingDocument: ...

    @abstractmethod
    def find_all(self) -> list[LabelingDocument]: ...

    @abstractmethod
    def delete(self, document_id: str) -> None: ...
