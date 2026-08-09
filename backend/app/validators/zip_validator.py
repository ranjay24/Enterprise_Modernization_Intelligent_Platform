"""ZIP file validation utilities."""

import io
import os
import zipfile

from app.core.constants import ALLOWED_UPLOAD_EXTENSIONS, MAX_UPLOAD_SIZE_BYTES
from app.exceptions.custom import ValidationFailedException
from app.utils.zip_utils import ZipSafetyError, validate_zip_safety


def validate_zip_file(filename: str, content: bytes) -> None:
    """Validate uploaded ZIP file extension, size, and contents."""
    ext = os.path.splitext(filename)[1].lower()
    if ext not in ALLOWED_UPLOAD_EXTENSIONS:
        raise ValidationFailedException(
            f"Invalid file type '{ext}'. Only ZIP files are accepted."
        )
    if len(content) > MAX_UPLOAD_SIZE_BYTES:
        max_mb = MAX_UPLOAD_SIZE_BYTES // (1024 * 1024)
        raise ValidationFailedException(
            f"File exceeds {max_mb}MB limit. Received {len(content) // (1024 * 1024)}MB."
        )
    if len(content) < 22:
        raise ValidationFailedException("File is too small to be a valid ZIP archive.")
    try:
        with zipfile.ZipFile(io.BytesIO(content)) as zf:
            validate_zip_safety(zf)
            bad = zf.testzip()
            if bad:
                raise ValidationFailedException(f"ZIP archive is corrupted: {bad}")
            names = zf.namelist()
            if not names:
                raise ValidationFailedException("ZIP archive contains no files. Please upload a project with source code.")
    except ZipSafetyError as exc:
        raise ValidationFailedException(f"ZIP archive rejected for safety: {exc}")
    except zipfile.BadZipFile:
        raise ValidationFailedException("File is not a valid ZIP archive.")
    except (zipfile.LargeZipFile, EOFError):
        raise ValidationFailedException("ZIP archive is corrupted or invalid.")
