from __future__ import annotations
from ...domain.entities.annotation import Annotation
from ...domain.entities.bounding_box import BoundingBox
from ...domain.exceptions.invalid_label_exception import InvalidLabelException
from ...domain.ports.annotation_repository_port import IAnnotationRepository
from ...domain.ports.document_repository_port import IDocumentRepository
from ...domain.ports.label_schema_port import ILabelSchemaRepository


class UpdateAnnotationUseCase:
    """Actualiza bbox, label o value_string de una anotación existente."""

    def __init__(
        self,
        annotation_repository: IAnnotationRepository,
        document_repository: IDocumentRepository,
        label_schema_repository: ILabelSchemaRepository,
    ) -> None:
        self._annotation_repository = annotation_repository
        self._document_repository = document_repository
        self._label_schema_repository = label_schema_repository

    def execute(
        self,
        annotation_id: str,
        document_id: str,
        label: str | None = None,
        bbox: BoundingBox | None = None,
        value_string: str | None = None,
    ) -> Annotation:
        annotation = self._annotation_repository.find_by_id(annotation_id)

        if annotation.document_id != document_id:
            raise ValueError(
                f"Anotación '{annotation_id}' no pertenece al documento '{document_id}'"
            )

        if label is not None:
            document = self._document_repository.find_by_id(annotation.document_id)
            schema = self._label_schema_repository.get_schema(document.document_kind)
            if not schema.is_valid_label(label):
                raise InvalidLabelException(label, document.document_kind.value)
            annotation.update_label(label)

        if bbox is not None:
            annotation.update_bbox(bbox)

        if value_string is not None:
            annotation.update_value(value_string)

        if label is not None or bbox is not None or value_string is not None:
            self._annotation_repository.save(annotation)

        return annotation
