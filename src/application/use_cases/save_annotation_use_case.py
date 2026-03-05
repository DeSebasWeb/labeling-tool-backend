from __future__ import annotations
import uuid
from ...domain.entities.annotation import Annotation
from ...domain.entities.bounding_box import BoundingBox
from ...domain.exceptions.document_not_found_exception import DocumentNotFoundException
from ...domain.exceptions.invalid_label_exception import InvalidLabelException
from ...domain.ports.annotation_repository_port import IAnnotationRepository
from ...domain.ports.document_repository_port import IDocumentRepository
from ...domain.ports.label_schema_port import ILabelSchemaRepository


class SaveAnnotationUseCase:
    """
    Crea una anotación nueva sobre una página de un documento.
    Valida que la etiqueta pertenezca al esquema del tipo de documento.
    """

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
        document_id: str,
        page_number: int,
        label: str,
        bbox: BoundingBox,
        value_string: str,
    ) -> Annotation:
        document = self._document_repository.find_by_id(document_id)

        schema = self._label_schema_repository.get_schema(document.document_kind)
        if not schema.is_valid_label(label):
            raise InvalidLabelException(label, document.document_kind.value)

        annotation = Annotation(
            id=str(uuid.uuid4()),
            document_id=document_id,
            page_number=page_number,
            label=label,
            bbox=bbox,
            value_string=value_string,
        )

        self._annotation_repository.save(annotation)
        document.increment_annotations()
        self._document_repository.save(document)

        return annotation
