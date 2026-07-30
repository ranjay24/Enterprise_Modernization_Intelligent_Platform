"""Hashing and checksum utilities."""

import hashlib


def sha256_hash(data: bytes) -> str:
    """Compute SHA-256 hash of bytes data."""
    return hashlib.sha256(data).hexdigest()


def md5_hash(data: bytes) -> str:
    """Compute MD5 hash of bytes data."""
    return hashlib.md5(data).hexdigest()
