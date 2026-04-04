"""Tests for xlcloak.bundle — Fernet-encrypted bundle writer and reader."""

from __future__ import annotations

import pytest

from xlcloak.bundle import BundleReader, BundleWriter, DEFAULT_PASSWORD


# ---------------------------------------------------------------------------
# Shared sample data
# ---------------------------------------------------------------------------

SAMPLE_FORWARD: dict[str, str] = {
    "John Smith": "PERSON_001",
    "john@acme.com": "EMAIL_002@example.com",
}
SAMPLE_REVERSE: dict[str, str] = {v: k for k, v in SAMPLE_FORWARD.items()}


def _write_bundle(path, password=DEFAULT_PASSWORD, **kwargs):
    """Helper to write a bundle with default sample data, allowing overrides."""
    defaults = dict(
        forward_map=SAMPLE_FORWARD,
        reverse_map=SAMPLE_REVERSE,
        original_filename="test.xlsx",
        sheets_processed=["Sheet1"],
        token_count=2,
    )
    defaults.update(kwargs)
    BundleWriter(password).write(path, **defaults)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_encrypt_decrypt_roundtrip(tmp_path):
    """Write a bundle and read it back; maps must match exactly."""
    bundle = tmp_path / "output.xlcloak"
    _write_bundle(bundle)
    payload = BundleReader().read(bundle)

    assert payload["forward_map"] == SAMPLE_FORWARD
    assert payload["reverse_map"] == SAMPLE_REVERSE


def test_default_password_mode_flag(tmp_path):
    """Bundle written with the default password must be flagged as 'default'."""
    bundle = tmp_path / "output.xlcloak"
    _write_bundle(bundle, password=DEFAULT_PASSWORD)
    payload = BundleReader(DEFAULT_PASSWORD).read(bundle)

    assert payload["password_mode"] == "default"


def test_custom_password_mode_flag(tmp_path):
    """Bundle written with a custom password must be flagged as 'custom'."""
    bundle = tmp_path / "output.xlcloak"
    _write_bundle(bundle, password="secret123")
    payload = BundleReader("secret123").read(bundle)

    assert payload["password_mode"] == "custom"


def test_wrong_password_raises(tmp_path):
    """Reading with the wrong password must raise ValueError."""
    bundle = tmp_path / "output.xlcloak"
    _write_bundle(bundle, password="correct")

    with pytest.raises(ValueError, match="Invalid password"):
        BundleReader("wrong").read(bundle)


def test_bundle_metadata(tmp_path):
    """Bundle payload must contain expected metadata fields with correct values."""
    bundle = tmp_path / "output.xlcloak"
    _write_bundle(bundle)
    payload = BundleReader().read(bundle)

    assert "version" in payload
    assert "original_filename" in payload
    assert "created_at" in payload
    assert "sheets_processed" in payload
    assert "token_count" in payload
    assert "password_mode" in payload

    assert payload["version"] == "0.1.0"
    assert payload["original_filename"] == "test.xlsx"
    assert payload["sheets_processed"] == ["Sheet1"]
    assert payload["token_count"] == 2


def test_bundle_salt_uniqueness(tmp_path):
    """Two bundles written with the same data and password must differ (random salt)."""
    bundle1 = tmp_path / "a.xlcloak"
    bundle2 = tmp_path / "b.xlcloak"
    _write_bundle(bundle1)
    _write_bundle(bundle2)

    assert bundle1.read_bytes() != bundle2.read_bytes()
