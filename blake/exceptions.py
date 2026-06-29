"""
Custom exceptions for the Blake package.
"""


class BlakeError(Exception):
    """Base exception for all Blake-related errors."""
    pass


class DownloadError(BlakeError):
    """Raised when download operations fail."""
    pass


class AnalysisError(BlakeError):
    """Raised when analysis operations fail."""
    pass


class ExportError(BlakeError):
    """Raised when export operations fail."""
    pass


class MetadataError(BlakeError):
    """Raised when metadata operations fail."""
    pass


class ValidationError(BlakeError):
    """Raised when data validation fails."""
    pass

