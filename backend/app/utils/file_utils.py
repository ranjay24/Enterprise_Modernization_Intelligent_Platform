"""File utility functions."""

import os


def get_extension(filename: str) -> str:
    """Extract file extension including the dot."""
    _, ext = os.path.splitext(filename)
    return ext.lower()


def get_filename_without_ext(filename: str) -> str:
    """Extract filename without extension."""
    return os.path.splitext(filename)[0]


def safe_filename(filename: str) -> str:
    """Sanitize filename to remove path traversal and special characters."""
    basename = os.path.basename(filename)
    return "".join(c for c in basename if c.isalnum() or c in "._- ")
