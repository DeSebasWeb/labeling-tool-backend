from __future__ import annotations
import yaml
import os
from ...domain.entities.document_kind import DocumentKind
from ...domain.entities.label_definition import LabelDefinition
from ...domain.entities.label_schema import LabelSchema
from ...domain.exceptions.label_schema_not_found_exception import LabelSchemaNotFoundException
from ...domain.ports.label_schema_port import ILabelSchemaRepository


class YamlLabelSchemaRepository(ILabelSchemaRepository):
    """
    Carga los esquemas de etiquetas desde un directorio de archivos YAML.
    Un archivo por tipo de documento: e14_senado.yaml, e14_camara.yaml, etc.
    Nunca hardcodea etiquetas — todo viene de configuración.
    """

    def __init__(self, schemas_dir: str) -> None:
        self._schemas_dir = schemas_dir
        self._cache: dict[DocumentKind, LabelSchema] = {}

    def get_schema(self, document_kind: DocumentKind) -> LabelSchema:
        if document_kind not in self._cache:
            self._cache[document_kind] = self._load(document_kind)
        return self._cache[document_kind]

    def list_kinds(self) -> list[DocumentKind]:
        return list(DocumentKind)

    def _load(self, document_kind: DocumentKind) -> LabelSchema:
        filename = f"{document_kind.value.lower()}.yaml"
        path = os.path.join(self._schemas_dir, filename)
        if not os.path.exists(path):
            raise LabelSchemaNotFoundException(document_kind.value)
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        labels = [
            LabelDefinition(
                name=item["name"],
                description=item.get("description", ""),
                repeats_per_page=item.get("repeats_per_page", False),
            )
            for item in data.get("labels", [])
        ]
        return LabelSchema(document_kind=document_kind, labels=labels)
