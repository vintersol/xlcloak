"""Custom Presidio PatternRecognizer subclasses for xlcloak."""

from __future__ import annotations

import re

from presidio_analyzer import PatternRecognizer
from presidio_analyzer.pattern import Pattern


class CompanySuffixRecognizer(PatternRecognizer):
    """Detect company/legal entity names via capitalized-word + suffix pattern.

    Matches one to five capitalized words followed by a recognized legal suffix
    at a word boundary. Case-insensitive suffix match. Score 0.65 (between NER
    ORGANIZATION at 0.85+ and random pattern match at 0.5).

    Maps to EntityType.ORG (via PRESIDIO_TO_ENTITY_TYPE["COMPANY_SUFFIX"]).
    Coexists with Presidio's NER-based ORGANIZATION recognizer — TokenRegistry
    deduplicates by original string, so no token duplication occurs.
    """

    _SUFFIXES = (
        "Aktiebolag|AB|HB|KB|Ltd|Limited|Inc|Corp|Corporation|GmbH|LLC|LLP|SA|NV|BV"
    )
    # One or more capitalized words (Xxxx) followed by a suffix at word boundary.
    # The suffix alternation is case-insensitive via re.IGNORECASE in Pattern.
    _PATTERN = (
        r"(?:[A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,4}\s+)"
        r"(?:" + _SUFFIXES + r")\b"
    )

    PATTERNS = [
        Pattern("company_suffix", _PATTERN, 0.65),
    ]

    def __init__(self) -> None:
        super().__init__(
            supported_entity="COMPANY_SUFFIX",
            patterns=self.PATTERNS,
            supported_language="en",
        )

    def validate_result(self, pattern_text: str) -> bool | None:  # type: ignore[override]
        """Reject matches where the first word is not capitalized (case-sensitive check).

        Presidio compiles patterns with re.IGNORECASE, so '[A-Z][a-z]+' would
        match 'the'. This validator ensures the first character is actually
        an uppercase letter.
        """
        # Strip leading/trailing whitespace and check first character
        stripped = pattern_text.lstrip()
        if not stripped or not stripped[0].isupper():
            return False
        return True


def _luhn_personnummer(digits_10: str) -> bool:
    """Validate a 10-digit personnummer string using the Luhn variant.

    The multiplier array [2,1,2,1,2,1,2,1,2] is applied left-to-right to the
    first 9 digits. Products >= 10 have their digits summed (subtract 9).
    The 10th digit is the check digit; the sum of all 9 products mod 10
    must equal (10 - check) mod 10.
    """
    multipliers = [2, 1, 2, 1, 2, 1, 2, 1, 2]
    total = 0
    for i, m in enumerate(multipliers):
        product = int(digits_10[i]) * m
        if product >= 10:
            product -= 9
        total += product
    check = (10 - (total % 10)) % 10
    return check == int(digits_10[9])


def _luhn_orgnummer(digits_10: str) -> bool:
    """Validate a 10-digit org-nummer string using standard Luhn-10.

    Doubles every second digit from the right (positions 1,3,5,7,9 in
    0-indexed right-to-left). Total mod 10 must equal 0.
    """
    total = 0
    reverse_digits = digits_10[::-1]
    for i, ch in enumerate(reverse_digits):
        n = int(ch)
        if i % 2 == 1:
            n *= 2
            if n > 9:
                n -= 9
        total += n
    return total % 10 == 0


class SwePersonnummerRecognizer(PatternRecognizer):
    """Detect Swedish personnummer (personal identity numbers).

    Accepts both 10-digit (YYMMDD±XXXX) and 12-digit (YYYYMMDD±XXXX) forms
    with optional hyphen or plus separator. Rejects false positives via the
    Luhn variant checksum defined by Skatteverket.
    """

    PATTERNS = [
        Pattern("personnummer_10", r"\b\d{6}[-+]?\d{4}\b", 0.5),
        Pattern("personnummer_12", r"\b\d{8}[-+]?\d{4}\b", 0.5),
    ]

    def __init__(self) -> None:
        super().__init__(
            supported_entity="PERSONNUMMER_SE",
            patterns=self.PATTERNS,
            supported_language="en",
        )

    def validate_result(self, pattern_text: str) -> bool | None:  # type: ignore[override]
        """Run Luhn variant checksum. Returns False to reject invalid matches."""
        digits = re.sub(r"[^0-9]", "", pattern_text)
        if len(digits) == 12:
            digits = digits[2:]  # strip century prefix — Luhn is on 10-digit form
        if len(digits) != 10:
            return False
        if not _luhn_personnummer(digits):
            return False
        return True


class SweOrgNummerRecognizer(PatternRecognizer):
    """Detect Swedish org-nummer (corporate identity numbers).

    Requires the mandatory hyphen (NNNNNN-NNNN format) per standard notation.
    Validates via standard Luhn-10 checksum (Bolagsverket specification).
    """

    PATTERNS = [
        Pattern("orgnummer", r"\b\d{6}-\d{4}\b", 0.5),
    ]

    def __init__(self) -> None:
        super().__init__(
            supported_entity="ORGNUM_SE",
            patterns=self.PATTERNS,
            supported_language="en",
        )

    def validate_result(self, pattern_text: str) -> bool | None:  # type: ignore[override]
        """Run standard Luhn-10 checksum. Returns False to reject invalid matches."""
        digits = re.sub(r"[^0-9]", "", pattern_text)
        if len(digits) != 10:
            return False
        if not _luhn_orgnummer(digits):
            return False
        return True
