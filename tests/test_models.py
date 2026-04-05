"""Tests for xlcloak.models — EntityType, CellRef, ScanResult, SurfaceWarning."""

from __future__ import annotations


def test_entity_type_importable() -> None:
    from xlcloak.models import EntityType

    assert EntityType is not None


def test_entity_type_has_eight_members() -> None:
    from xlcloak.models import EntityType

    assert len(EntityType) == 8


def test_entity_type_member_names() -> None:
    from xlcloak.models import EntityType

    names = {m.name for m in EntityType}
    assert names == {"PERSON", "ORG", "EMAIL", "PHONE", "URL", "SSN_SE", "ORGNUM_SE", "GENERIC"}


def test_entity_type_values() -> None:
    from xlcloak.models import EntityType

    assert {e.value for e in EntityType} == {
        "PERSON", "ORG", "EMAIL", "PHONE", "URL", "SSN_SE", "ORGNUM_SE", "GENERIC"
    }


def test_entity_type_values_match_names() -> None:
    from xlcloak.models import EntityType

    for member in EntityType:
        assert member.value == member.name


def test_cellref_importable() -> None:
    from xlcloak.models import CellRef

    assert CellRef is not None


def test_cellref_defaults() -> None:
    from xlcloak.models import CellRef

    ref = CellRef(sheet_name="Sheet1", row=1, col=1)
    assert ref.value is None


def test_cellref_is_dataclass() -> None:
    import dataclasses

    from xlcloak.models import CellRef

    assert dataclasses.is_dataclass(CellRef)


def test_scanresult_importable() -> None:
    from xlcloak.models import ScanResult

    assert ScanResult is not None


def test_scanresult_is_dataclass() -> None:
    import dataclasses

    from xlcloak.models import ScanResult

    assert dataclasses.is_dataclass(ScanResult)


def test_surfacewarning_importable() -> None:
    from xlcloak.models import SurfaceWarning

    assert SurfaceWarning is not None


def test_surfacewarning_is_dataclass() -> None:
    import dataclasses

    from xlcloak.models import SurfaceWarning

    assert dataclasses.is_dataclass(SurfaceWarning)


def test_surfacewarning_default_level() -> None:
    from xlcloak.models import CellRef, SurfaceWarning

    ref = CellRef(sheet_name="Sheet1", row=1, col=1)
    w = SurfaceWarning(cell=ref, surface_type="formula", detail="=SUM(A1)")
    assert w.level == "WARNING"
