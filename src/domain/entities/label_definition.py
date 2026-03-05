from dataclasses import dataclass


@dataclass(frozen=True)
class LabelDefinition:
    """Define un campo etiquetable: nombre técnico, descripción y si se repite por página."""
    name: str
    description: str
    repeats_per_page: bool = False
