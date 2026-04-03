"""xlcloak — reversible Excel text sanitization CLI for AI workflows."""

from __future__ import annotations

__version__ = "0.1.0"

from xlcloak.excel_io import WorkbookReader, WorkbookWriter
from xlcloak.manifest import Manifest
from xlcloak.models import EntityType
from xlcloak.token_engine import TokenFormatter, TokenRegistry

__all__ = [
    "__version__",
    "EntityType",
    "Manifest",
    "TokenFormatter",
    "TokenRegistry",
    "WorkbookReader",
    "WorkbookWriter",
]
