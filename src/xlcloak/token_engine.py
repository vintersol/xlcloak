"""Token engine for xlcloak — deterministic, shape-preserving token generation."""

from __future__ import annotations

from xlcloak.models import EntityType

_MAX_COUNTER = 999


class TokenFormatter:
    """Produces shaped token strings given an entity type and counter."""

    def format(self, entity_type: EntityType, counter: int) -> str:
        """Format a token for the given entity type and counter value.

        Args:
            entity_type: The type of entity being tokenized.
            counter: The global counter value (1-based, max 999).

        Returns:
            A human-readable, shape-preserving token string.

        Raises:
            ValueError: If counter exceeds 999.
        """
        if counter > _MAX_COUNTER:
            raise ValueError(
                f"Counter overflow: counter={counter} exceeds maximum of {_MAX_COUNTER}. "
                f"xlcloak supports at most {_MAX_COUNTER} unique entities per workbook."
            )

        match entity_type:
            case EntityType.EMAIL:
                return f"EMAIL_{counter:03d}@example.com"
            case EntityType.PHONE:
                return f"+10-000-000-{counter:03d}"
            case EntityType.URL:
                return f"https://example.com/URL_{counter:03d}"
            case EntityType.PERSON:
                return f"PERSON_{counter:03d}"
            case EntityType.ORG:
                return f"ORG_{counter:03d}"
            case EntityType.SSN_SE:
                return f"1000000-{counter:04d}"
            case EntityType.ORGNUM_SE:
                return f"000000-{counter:04d}"
            case EntityType.GENERIC:
                return f"CELL_{counter:04d}"


class TokenRegistry:
    """Bidirectional registry mapping original values to stable tokens.

    Each unique original value gets a token on first registration.
    Subsequent registrations of the same value return the existing token.
    A global counter (starting at 1) increments across all entity types.
    """

    def __init__(self) -> None:
        self._forward: dict[str, str] = {}
        self._reverse: dict[str, str] = {}
        self._counter: int = 0
        self._formatter = TokenFormatter()

    def get_or_create(self, value: str, entity_type: EntityType) -> str:
        """Return existing token for value, or create and register a new one.

        Args:
            value: The original sensitive text to tokenize.
            entity_type: The type of entity (determines token shape).

        Returns:
            The stable token for this value.

        Raises:
            ValueError: If counter would exceed 999 (too many unique entities).
        """
        if value in self._forward:
            return self._forward[value]

        self._counter += 1
        token = self._formatter.format(entity_type, self._counter)
        self._forward[value] = token
        self._reverse[token] = value
        return token

    def reverse_lookup(self, token: str) -> str | None:
        """Return the original value for a token, or None if not found."""
        return self._reverse.get(token)

    def __len__(self) -> int:
        """Return the number of unique values registered."""
        return len(self._forward)

    @property
    def forward_map(self) -> dict[str, str]:
        """Return a copy of the forward mapping (original -> token)."""
        return dict(self._forward)

    @property
    def reverse_map(self) -> dict[str, str]:
        """Return a copy of the reverse mapping (token -> original)."""
        return dict(self._reverse)
