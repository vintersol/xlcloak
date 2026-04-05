"""Shared pytest fixtures for xlcloak tests."""

from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture
def tmp_workbook_path(tmp_path: Path) -> Path:
    """Return a temporary path for test xlsx files."""
    return tmp_path / "test.xlsx"


@pytest.fixture
def simple_fixture() -> Path:
    """Return the path to the simple test fixture xlsx file."""
    return Path(__file__).parent / "fixtures" / "simple.xlsx"
