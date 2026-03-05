from __future__ import annotations
from abc import ABC, abstractmethod
from ..entities.annotation import Annotation


class IAnnotationRepository(ABC):

    @abstractmethod
    def save(self, annotation: Annotation) -> None: ...

    @abstractmethod
    def find_by_id(self, annotation_id: str) -> Annotation: ...

    @abstractmethod
    def find_by_document(self, document_id: str) -> list[Annotation]: ...

    @abstractmethod
    def find_by_document_and_page(self, document_id: str, page_number: int) -> list[Annotation]: ...

    @abstractmethod
    def delete(self, annotation_id: str) -> None: ...

    @abstractmethod
    def delete_by_document(self, document_id: str) -> None: ...
