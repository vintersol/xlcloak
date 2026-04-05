"""Bundle writer and reader for xlcloak encrypted restore bundles.

Bundles use Fernet symmetric encryption with a PBKDF2HMAC-SHA256 key
derived from a user-supplied password (or the default password).
The 16-byte random salt is prepended to the ciphertext so decryption
can reproduce the same key without storing secrets at rest.
"""

from __future__ import annotations

import base64
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

import xlcloak

DEFAULT_PASSWORD = "xlcloak"
PBKDF2_ITERATIONS = 600_000  # OWASP 2023 recommendation for PBKDF2-SHA256
SALT_LENGTH = 16


def _derive_key(password: str, salt: bytes) -> bytes:
    """Derive a Fernet-compatible key from password and salt via PBKDF2HMAC-SHA256.

    Args:
        password: User-supplied password string.
        salt: 16-byte random salt.

    Returns:
        URL-safe base64-encoded 32-byte key suitable for Fernet.
    """
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=PBKDF2_ITERATIONS,
    )
    return base64.urlsafe_b64encode(kdf.derive(password.encode()))


class BundleWriter:
    """Encrypts a token map and metadata into an xlcloak bundle file.

    The bundle format is: ``[16-byte salt][Fernet ciphertext]``
    The plaintext payload is a JSON-serialised dict containing the
    token maps, workbook metadata, and password mode flag.
    """

    def __init__(self, password: str = DEFAULT_PASSWORD) -> None:
        self._password = password
        self._password_mode = "default" if password == DEFAULT_PASSWORD else "custom"

    def write(
        self,
        path: Path,
        forward_map: dict[str, str],
        reverse_map: dict[str, str],
        original_filename: str,
        sheets_processed: list[str],
        token_count: int,
        token_occurrences: dict[str, int] | None = None,
    ) -> None:
        """Encrypt and write the bundle to *path*.

        Args:
            path: Destination file path (e.g. ``output.xlcloak``).
            forward_map: Mapping of original text -> token.
            reverse_map: Mapping of token -> original text.
            original_filename: Basename of the source .xlsx file.
            sheets_processed: List of worksheet names that were sanitized.
            token_count: Total number of unique tokens created.
        """
        payload: dict = {
            "version": xlcloak.__version__,
            "original_filename": original_filename,
            "created_at": datetime.now(tz=timezone.utc).isoformat(),
            "sheets_processed": sheets_processed,
            "token_count": token_count,
            "password_mode": self._password_mode,
            "forward_map": forward_map,
            "reverse_map": reverse_map,
            "token_occurrences": token_occurrences if token_occurrences is not None else {},
        }

        salt = os.urandom(SALT_LENGTH)
        key = _derive_key(self._password, salt)
        ciphertext = Fernet(key).encrypt(json.dumps(payload).encode())
        path.write_bytes(salt + ciphertext)


class BundleReader:
    """Decrypts an xlcloak bundle file and returns the payload dict.

    Expects the bundle to follow the ``[16-byte salt][Fernet ciphertext]``
    format produced by :class:`BundleWriter`.
    """

    def __init__(self, password: str = DEFAULT_PASSWORD) -> None:
        self._password = password

    def read(self, path: Path) -> dict:
        """Decrypt and return the bundle payload from *path*.

        Args:
            path: Path to the ``.xlcloak`` bundle file.

        Returns:
            The decrypted payload dict (version, maps, metadata, etc.).

        Raises:
            ValueError: If the password is wrong or the file is corrupted.
        """
        data = path.read_bytes()
        if len(data) < SALT_LENGTH:
            raise ValueError(
                "Bundle file is too small -- corrupted or not a valid .xlcloak file"
            )
        salt = data[:SALT_LENGTH]
        ciphertext = data[SALT_LENGTH:]
        key = _derive_key(self._password, salt)
        try:
            plaintext = Fernet(key).decrypt(ciphertext)
        except InvalidToken as exc:
            raise ValueError("Invalid password or corrupted bundle") from exc
        return json.loads(plaintext.decode())
