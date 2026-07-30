"""Project structure validation."""

from app.exceptions.custom import ValidationFailedException


def validate_job_id(job_id: str) -> None:
    """Validate job ID format."""
    if not job_id or not job_id.strip():
        raise ValidationFailedException("Job ID cannot be empty")
    if len(job_id) > 128:
        raise ValidationFailedException("Job ID exceeds maximum length of 128 characters")


def validate_service_name(service_name: str) -> None:
    """Validate service name for deployment."""
    if not service_name or not service_name.strip():
        raise ValidationFailedException("Service name cannot be empty")
    if len(service_name) > 128:
        raise ValidationFailedException("Service name exceeds maximum length")
