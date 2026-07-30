"""ZIP file handling utilities."""

import logging
import os
import tempfile
import zipfile

logger = logging.getLogger(__name__)


def extract_zip_to_temp(content: bytes) -> str | None:
    """Extract ZIP content to a temporary directory. Returns the extraction path."""
    try:
        temp_dir = tempfile.mkdtemp(prefix="emip_")
        zip_path = os.path.join(temp_dir, "upload.zip")
        with open(zip_path, "wb") as f:
            f.write(content)
        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            zip_ref.extractall(temp_dir)
        os.remove(zip_path)
        logger.info("ZIP extracted", extra={"path": temp_dir})
        return temp_dir
    except zipfile.BadZipFile:
        logger.warning("Invalid ZIP file uploaded")
        return None
    except Exception as exc:
        logger.error("ZIP extraction failed", extra={"error": str(exc)})
        return None


def cleanup_temp_dir(path: str | None) -> None:
    """Remove temporary directory."""
    if path and os.path.exists(path):
        import shutil
        shutil.rmtree(path, ignore_errors=True)
