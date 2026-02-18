"""
Core error hierarchy for the App Management RAG Assistant.
Follows ACE Framework architecture standards for error categorization.
"""

class BaseAppError(Exception):
    """Base class for all application errors."""
    def __init__(self, message: str, details: dict = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}

class DomainError(BaseAppError):
    """
    Business rule violations or invalid domain states.
    Maps to 400 or 422 HTTP status codes.
    """
    pass

class ApplicationError(BaseAppError):
    """
    Use case failures or authentication/authorization issues.
    Maps to 401, 403, or 404 HTTP status codes.
    """
    pass

class InfrastructureError(BaseAppError):
    """
    External system failures (Database, LLM, Filesystem).
    Maps to 500 or 503 HTTP status codes.
    """
    pass

# Specific Domain Errors
class IncompleteMetadataError(DomainError):
    """Raised when document metadata is missing required fields."""
    pass

class InvalidDocumentFormatError(DomainError):
    """Raised when an uploaded file is not a supported format."""
    pass

# Specific Infrastructure Errors
class VectorDatabaseError(InfrastructureError):
    """Raised when LanceDB operations fail."""
    pass

class LLMServiceError(InfrastructureError):
    """Raised when Ollama or embedding service fails."""
    pass

class DocumentIngestionError(InfrastructureError):
    """Raised when a batch ingestion process fails due to system issues."""
    pass
