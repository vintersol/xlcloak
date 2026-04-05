"""Shared data models for xlcloak."""

from __future__ import annotations

import enum
from dataclasses import dataclass


class EntityType(enum.Enum):
    """Recognized PII/sensitive entity types."""

    PERSON = "PERSON"
    ORG = "ORG"
    EMAIL = "EMAIL"
    PHONE = "PHONE"
    URL = "URL"
    SSN_SE = "SSN_SE"
    ORGNUM_SE = "ORGNUM_SE"
    GENERIC = "GENERIC"


@dataclass
class CellRef:
    """Reference to a specific cell in a workbook."""

    sheet_name: str
    row: int
    col: int
    value: str | None = None


@dataclass
class ScanResult:
    """Result of scanning a cell for PII."""

    cell: CellRef
    entity_type: EntityType
    original: str
    token: str
    score: float | None = None
    detection_method: str | None = None


@dataclass
class SurfaceWarning:
    """Warning about an unsupported surface (formula, chart, comment, etc.)."""

    cell: CellRef
    surface_type: str
    detail: str
    level: str = "WARNING"
