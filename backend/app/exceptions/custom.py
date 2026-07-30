"""Custom domain exceptions."""


class EMIPException(Exception):
    """Base exception for EMIP application."""

    def __init__(self, message: str = "An unexpected error occurred", status_code: int = 500):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class ResourceNotFoundException(EMIPException):
    """Raised when a requested resource is not found."""

    def __init__(self, resource: str = "Resource", resource_id: str = ""):
        msg = f"{resource} '{resource_id}' not found" if resource_id else f"{resource} not found"
        super().__init__(message=msg, status_code=404)


class ValidationFailedException(EMIPException):
    """Raised when input validation fails."""

    def __init__(self, message: str = "Validation failed"):
        super().__init__(message=message, status_code=400)


class AnalysisFailedException(EMIPException):
    """Raised when analysis pipeline fails."""

    def __init__(self, message: str = "Analysis pipeline failed", job_id: str = ""):
        msg = f"Analysis failed for job {job_id}: {message}" if job_id else message
        super().__init__(message=msg, status_code=500)


class AWSServiceException(EMIPException):
    """Raised when an AWS service call fails."""

    def __init__(self, service: str = "AWS", message: str = "Service call failed"):
        super().__init__(message=f"{service} error: {message}", status_code=500)


class FileUploadException(EMIPException):
    """Raised when file upload fails."""

    def __init__(self, message: str = "File upload failed"):
        super().__init__(message=message, status_code=400)
