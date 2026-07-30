"""General input validation utilities."""

from app.exceptions.custom import ValidationFailedException


def validate_progress(progress: int) -> None:
    """Validate progress value is within range."""
    if not 0 <= progress <= 100:
        raise ValidationFailedException(f"Progress must be between 0 and 100, got {progress}")


def validate_phase(phase: str, valid_phases: list[str]) -> None:
    """Validate analysis phase against allowed values."""
    if phase not in valid_phases:
        raise ValidationFailedException(
            f"Invalid phase '{phase}'. Valid phases: {', '.join(valid_phases)}"
        )
