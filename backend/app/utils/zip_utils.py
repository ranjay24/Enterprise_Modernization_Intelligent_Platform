"""ZIP file handling utilities."""

import logging
import os
import re
import tempfile
import zipfile

from app.core.constants import (
    MAX_ZIP_ENTRY_COUNT,
    MAX_ZIP_ENTRY_SIZE_BYTES,
    MAX_ZIP_TOTAL_UNCOMPRESSED_BYTES,
)

logger = logging.getLogger(__name__)


class ZipSafetyError(Exception):
    """Raised when a ZIP archive violates safety constraints."""


def _is_safe_member_name(member_name: str) -> bool:
    """Reject traversal members (``..``, absolute paths, drive letters)."""
    if not member_name:
        return False
    normalized = member_name.replace("\\", "/")
    if normalized.startswith("/") or os.path.isabs(normalized):
        return False
    parts = normalized.split("/")
    if len(parts) >= 2 and re.match(r"^[A-Za-z]:", parts[0]):
        return False
    return ".." not in parts


def _safe_member_path(dest_dir: str, member_name: str) -> str:
    """Resolve a ZIP member path, rejecting path traversal outside dest_dir."""
    if not _is_safe_member_name(member_name):
        raise ZipSafetyError(f"ZIP entry path traversal blocked: {member_name}")
    base = os.path.realpath(dest_dir)
    target = os.path.realpath(os.path.join(base, member_name))
    if not (target == base or target.startswith(base + os.sep)):
        raise ZipSafetyError(f"ZIP entry path traversal blocked: {member_name}")
    return target


def validate_zip_safety(zf: zipfile.ZipFile) -> None:
    """Validate a ZIP archive against zip-bomb and path-traversal constraints."""
    total_uncompressed = 0
    members = zf.infolist()
    if not members:
        raise ZipSafetyError("ZIP archive contains no files")
    if len(members) > MAX_ZIP_ENTRY_COUNT:
        raise ZipSafetyError(
            f"ZIP archive has too many entries ({len(members)} > {MAX_ZIP_ENTRY_COUNT})"
        )
    for member in members:
        if not _is_safe_member_name(member.filename):
            raise ZipSafetyError(f"ZIP entry path traversal blocked: {member.filename}")
        if member.file_size > MAX_ZIP_ENTRY_SIZE_BYTES:
            raise ZipSafetyError(
                f"ZIP entry too large: {member.filename} "
                f"({member.file_size // (1024 * 1024)}MB > {MAX_ZIP_ENTRY_SIZE_BYTES // (1024 * 1024)}MB)"
            )
        if member.compress_size > 0 and member.file_size / member.compress_size > 200:
            raise ZipSafetyError(
                f"ZIP entry compression ratio too high: {member.filename}"
            )
        total_uncompressed += member.file_size
        if total_uncompressed > MAX_ZIP_TOTAL_UNCOMPRESSED_BYTES:
            raise ZipSafetyError(
                f"ZIP archive expands beyond "
                f"{MAX_ZIP_TOTAL_UNCOMPRESSED_BYTES // (1024 * 1024)}MB"
            )


def extract_zip_to_temp(content: bytes) -> str | None:
    """Extract ZIP content to a temporary directory. Returns the extraction path."""
    temp_dir = None
    zip_path = None
    try:
        temp_dir = tempfile.mkdtemp(prefix="emip_")
        zip_path = os.path.join(temp_dir, "upload.zip")
        with open(zip_path, "wb") as f:
            f.write(content)
        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            validate_zip_safety(zip_ref)
            for member in zip_ref.infolist():
                _safe_member_path(temp_dir, member.filename)
                zip_ref.extract(member, temp_dir)
        os.remove(zip_path)
        logger.info("ZIP extracted", extra={"path": temp_dir})
        return temp_dir
    except (zipfile.BadZipFile, ZipSafetyError) as exc:
        logger.warning("Invalid or unsafe ZIP file uploaded", extra={"error": str(exc)})
        if temp_dir and os.path.exists(temp_dir):
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)
        return None
    except Exception as exc:
        logger.error("ZIP extraction failed", extra={"error": str(exc)})
        if temp_dir and os.path.exists(temp_dir):
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)
        return None
    finally:
        if zip_path and os.path.exists(zip_path):
            try:
                os.remove(zip_path)
            except OSError:
                pass


def cleanup_temp_dir(path: str | None) -> None:
    """Remove temporary directory."""
    if path and os.path.exists(path):
        import shutil
        shutil.rmtree(path, ignore_errors=True)
