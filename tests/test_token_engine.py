"""Tests for xlcloak.token_engine — TokenFormatter and TokenRegistry."""

from __future__ import annotations

import re

import pytest

from xlcloak.models import EntityType


# ---------------------------------------------------------------------------
# Determinism tests (TOK-01)
# ---------------------------------------------------------------------------


def test_same_value_returns_same_token() -> None:
    """Registering the same value twice must return the identical token."""
    from xlcloak.token_engine import TokenRegistry

    registry = TokenRegistry()
    token_a = registry.get_or_create("John Smith", EntityType.PERSON)
    token_b = registry.get_or_create("John Smith", EntityType.PERSON)
    assert token_a == token_b


def test_different_values_return_different_tokens() -> None:
    """Two different values must map to distinct tokens."""
    from xlcloak.token_engine import TokenRegistry

    registry = TokenRegistry()
    token_a = registry.get_or_create("John", EntityType.PERSON)
    token_b = registry.get_or_create("Jane", EntityType.PERSON)
    assert token_a != token_b


def test_deterministic_across_registries() -> None:
    """Two fresh registries given identical inputs in identical order must produce identical tokens."""
    from xlcloak.token_engine import TokenRegistry

    values = [
        ("Alice", EntityType.PERSON),
        ("alice@example.com", EntityType.EMAIL),
        ("Acme Corp", EntityType.ORG),
    ]

    registry_a = TokenRegistry()
    registry_b = TokenRegistry()

    for value, etype in values:
        registry_a.get_or_create(value, etype)
        registry_b.get_or_create(value, etype)

    for value, etype in values:
        assert registry_a.get_or_create(value, etype) == registry_b.get_or_create(value, etype)


# ---------------------------------------------------------------------------
# Prefix / format tests (TOK-02)
# ---------------------------------------------------------------------------


def test_person_token_format() -> None:
    from xlcloak.token_engine import TokenRegistry

    registry = TokenRegistry()
    token = registry.get_or_create("Alice", EntityType.PERSON)
    assert re.match(r"^PERSON_\d{3}$", token), f"Unexpected format: {token}"


def test_org_token_format() -> None:
    from xlcloak.token_engine import TokenRegistry

    registry = TokenRegistry()
    token = registry.get_or_create("Acme Corp", EntityType.ORG)
    assert re.match(r"^ORG_\d{3}$", token), f"Unexpected format: {token}"


def test_email_token_format() -> None:
    from xlcloak.token_engine import TokenRegistry

    registry = TokenRegistry()
    token = registry.get_or_create("alice@real.com", EntityType.EMAIL)
    assert re.match(r"^EMAIL_\d{3}@example\.com$", token), f"Unexpected format: {token}"


def test_phone_token_format() -> None:
    from xlcloak.token_engine import TokenRegistry

    registry = TokenRegistry()
    token = registry.get_or_create("+46701234567", EntityType.PHONE)
    assert re.match(r"^\+10-000-000-\d{3}$", token), f"Unexpected format: {token}"


def test_url_token_format() -> None:
    from xlcloak.token_engine import TokenRegistry

    registry = TokenRegistry()
    token = registry.get_or_create("https://company.com/page", EntityType.URL)
    assert re.match(r"^https://example\.com/URL_\d{3}$", token), f"Unexpected format: {token}"


def test_ssn_se_token_format() -> None:
    from xlcloak.token_engine import TokenRegistry

    registry = TokenRegistry()
    token = registry.get_or_create("19900101-1234", EntityType.SSN_SE)
    assert re.match(r"^SSN_SE_\d{3}$", token), f"Unexpected format: {token}"


def test_orgnum_se_token_format() -> None:
    from xlcloak.token_engine import TokenRegistry

    registry = TokenRegistry()
    token = registry.get_or_create("556123-4567", EntityType.ORGNUM_SE)
    assert re.match(r"^ORGNUM_SE_\d{3}$", token), f"Unexpected format: {token}"


# ---------------------------------------------------------------------------
# Shape preservation tests (TOK-03)
# ---------------------------------------------------------------------------


def test_email_token_is_email_shaped() -> None:
    from xlcloak.token_engine import TokenRegistry

    registry = TokenRegistry()
    token = registry.get_or_create("user@domain.com", EntityType.EMAIL)
    assert "@" in token
    assert ".com" in token


def test_phone_token_starts_with_plus() -> None:
    from xlcloak.token_engine import TokenRegistry

    registry = TokenRegistry()
    token = registry.get_or_create("+46701234567", EntityType.PHONE)
    assert token.startswith("+")


def test_url_token_is_valid_url() -> None:
    from xlcloak.token_engine import TokenRegistry

    registry = TokenRegistry()
    token = registry.get_or_create("https://secret.company.com", EntityType.URL)
    assert token.startswith("https://")


# ---------------------------------------------------------------------------
# Global counter tests (D-02)
# ---------------------------------------------------------------------------


def test_global_counter_increments_across_types() -> None:
    """Counter is global across entity types, not per-type."""
    from xlcloak.token_engine import TokenRegistry

    registry = TokenRegistry()
    t_person = registry.get_or_create("Alice", EntityType.PERSON)
    t_email = registry.get_or_create("alice@company.com", EntityType.EMAIL)
    t_org = registry.get_or_create("Acme Corp", EntityType.ORG)

    # Counters must be 001, 002, 003 — not all 001
    assert "001" in t_person
    assert "002" in t_email
    assert "003" in t_org


def test_counter_starts_at_001() -> None:
    from xlcloak.token_engine import TokenRegistry

    registry = TokenRegistry()
    token = registry.get_or_create("first", EntityType.PERSON)
    assert "001" in token


# ---------------------------------------------------------------------------
# Registry tests
# ---------------------------------------------------------------------------


def test_reverse_lookup() -> None:
    from xlcloak.token_engine import TokenRegistry

    registry = TokenRegistry()
    original = "John Doe"
    token = registry.get_or_create(original, EntityType.PERSON)
    assert registry.reverse_lookup(token) == original


def test_reverse_lookup_missing() -> None:
    from xlcloak.token_engine import TokenRegistry

    registry = TokenRegistry()
    assert registry.reverse_lookup("PERSON_999") is None


def test_registry_len() -> None:
    from xlcloak.token_engine import TokenRegistry

    registry = TokenRegistry()
    registry.get_or_create("Alice", EntityType.PERSON)
    registry.get_or_create("Bob", EntityType.PERSON)
    registry.get_or_create("Alice", EntityType.PERSON)  # duplicate — not counted again
    assert len(registry) == 2


def test_forward_map_property() -> None:
    from xlcloak.token_engine import TokenRegistry

    registry = TokenRegistry()
    token = registry.get_or_create("Alice", EntityType.PERSON)
    fmap = registry.forward_map
    assert "Alice" in fmap
    assert fmap["Alice"] == token


def test_reverse_map_property() -> None:
    from xlcloak.token_engine import TokenRegistry

    registry = TokenRegistry()
    token = registry.get_or_create("Alice", EntityType.PERSON)
    rmap = registry.reverse_map
    assert token in rmap
    assert rmap[token] == "Alice"


def test_counter_overflow_raises() -> None:
    """Registering more than 999 unique values must raise ValueError."""
    from xlcloak.token_engine import TokenRegistry

    registry = TokenRegistry()
    # Register 999 unique values
    for i in range(999):
        registry.get_or_create(f"value_{i:04d}", EntityType.PERSON)
    # 1000th must raise
    with pytest.raises(ValueError):
        registry.get_or_create("value_overflow", EntityType.PERSON)


# ---------------------------------------------------------------------------
# TokenFormatter direct tests
# ---------------------------------------------------------------------------


def test_formatter_email() -> None:
    from xlcloak.token_engine import TokenFormatter

    fmt = TokenFormatter()
    assert fmt.format(EntityType.EMAIL, 1) == "EMAIL_001@example.com"


def test_formatter_phone() -> None:
    from xlcloak.token_engine import TokenFormatter

    fmt = TokenFormatter()
    assert fmt.format(EntityType.PHONE, 5) == "+10-000-000-005"


def test_formatter_url() -> None:
    from xlcloak.token_engine import TokenFormatter

    fmt = TokenFormatter()
    assert fmt.format(EntityType.URL, 42) == "https://example.com/URL_042"


def test_formatter_person() -> None:
    from xlcloak.token_engine import TokenFormatter

    fmt = TokenFormatter()
    assert fmt.format(EntityType.PERSON, 7) == "PERSON_007"


def test_formatter_org() -> None:
    from xlcloak.token_engine import TokenFormatter

    fmt = TokenFormatter()
    assert fmt.format(EntityType.ORG, 3) == "ORG_003"


def test_formatter_ssn_se() -> None:
    from xlcloak.token_engine import TokenFormatter

    fmt = TokenFormatter()
    result = fmt.format(EntityType.SSN_SE, 1)
    assert re.match(r"^SSN_SE_\d{3}$", result)


def test_formatter_orgnum_se() -> None:
    from xlcloak.token_engine import TokenFormatter

    fmt = TokenFormatter()
    result = fmt.format(EntityType.ORGNUM_SE, 1)
    assert re.match(r"^ORGNUM_SE_\d{3}$", result)


def test_formatter_overflow_raises() -> None:
    from xlcloak.token_engine import TokenFormatter

    fmt = TokenFormatter()
    with pytest.raises(ValueError):
        fmt.format(EntityType.PERSON, 1000)


def test_generic_token_format() -> None:
    from xlcloak.token_engine import TokenFormatter

    formatter = TokenFormatter()
    assert formatter.format(EntityType.GENERIC, 1) == "CELL_0001"
    assert formatter.format(EntityType.GENERIC, 42) == "CELL_0042"
    assert formatter.format(EntityType.GENERIC, 999) == "CELL_0999"
