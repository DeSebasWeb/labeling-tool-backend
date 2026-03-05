from __future__ import annotations
from enum import Enum


class WorkspaceDocumentStatus(str, Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    DONE = "DONE"
