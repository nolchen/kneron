"""
Symmetric encryption for secrets at rest — specifically the Microsoft refresh
tokens, which grant ongoing access to a person's mailbox/calendar and must not
sit in the database as plaintext.

Tokens are Fernet-encrypted (AES-128-CBC + HMAC) with a key derived from
TOKEN_ENCRYPTION_KEY (preferred) or SESSION_SECRET. Encrypted values carry an
'enc:v1:' prefix so we can tell them from legacy plaintext and migrate
transparently: old rows decrypt as-is, and any write re-stores them encrypted.

NOTE: rotating the key makes existing ciphertext undecryptable (users just
re-authenticate). Set a stable TOKEN_ENCRYPTION_KEY in production.
"""

import base64
import hashlib
import os

from cryptography.fernet import Fernet, InvalidToken

_PREFIX = "enc:v1:"


def _fernet() -> Fernet:
    secret = (
        os.environ.get("TOKEN_ENCRYPTION_KEY")
        or os.environ.get("SESSION_SECRET")
        or "dev-insecure-change-me"
    )
    # Derive a stable 32-byte urlsafe-base64 key Fernet accepts.
    key = base64.urlsafe_b64encode(hashlib.sha256(secret.encode()).digest())
    return Fernet(key)


def encrypt(value: str) -> str:
    """Encrypt a secret for storage. Empty stays empty."""
    if not value:
        return value
    return _PREFIX + _fernet().encrypt(value.encode()).decode()


def decrypt(value: str) -> str:
    """Decrypt a stored secret. Legacy plaintext (no prefix) is returned as-is,
    so existing rows keep working until they're next written. A value encrypted
    under a different/rotated key returns '' (treated as 'no token' → re-auth)."""
    if not value or not value.startswith(_PREFIX):
        return value
    try:
        return _fernet().decrypt(value[len(_PREFIX):].encode()).decode()
    except InvalidToken:
        return ""
