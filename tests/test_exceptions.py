"""
Tests for Blake exceptions module.
"""

import pytest
from blake.exceptions import (
    BlakeError,
    DownloadError,
    AnalysisError,
    ExportError,
    MetadataError,
    ValidationError
)


class TestBlakeExceptions:
    """Tests for Blake custom exceptions."""
    
    def test_blake_error_is_exception(self):
        """BlakeError should be an Exception."""
        assert issubclass(BlakeError, Exception)
    
    def test_blake_error_can_be_raised(self):
        """BlakeError can be raised and caught."""
        with pytest.raises(BlakeError):
            raise BlakeError("test error")
    
    def test_blake_error_message(self):
        """BlakeError stores message correctly."""
        error = BlakeError("test message")
        assert str(error) == "test message"


class TestDownloadError:
    """Tests for DownloadError exception."""
    
    def test_download_error_is_blake_error(self):
        """DownloadError should inherit from BlakeError."""
        assert issubclass(DownloadError, BlakeError)
    
    def test_download_error_can_be_raised(self):
        """DownloadError can be raised and caught."""
        with pytest.raises(DownloadError):
            raise DownloadError("download failed")
    
    def test_download_error_caught_as_blake_error(self):
        """DownloadError can be caught as BlakeError."""
        with pytest.raises(BlakeError):
            raise DownloadError("download failed")


class TestAnalysisError:
    """Tests for AnalysisError exception."""
    
    def test_analysis_error_is_blake_error(self):
        """AnalysisError should inherit from BlakeError."""
        assert issubclass(AnalysisError, BlakeError)
    
    def test_analysis_error_can_be_raised(self):
        """AnalysisError can be raised and caught."""
        with pytest.raises(AnalysisError):
            raise AnalysisError("analysis failed")


class TestExportError:
    """Tests for ExportError exception."""
    
    def test_export_error_is_blake_error(self):
        """ExportError should inherit from BlakeError."""
        assert issubclass(ExportError, BlakeError)
    
    def test_export_error_can_be_raised(self):
        """ExportError can be raised and caught."""
        with pytest.raises(ExportError):
            raise ExportError("export failed")


class TestMetadataError:
    """Tests for MetadataError exception."""
    
    def test_metadata_error_is_blake_error(self):
        """MetadataError should inherit from BlakeError."""
        assert issubclass(MetadataError, BlakeError)
    
    def test_metadata_error_can_be_raised(self):
        """MetadataError can be raised and caught."""
        with pytest.raises(MetadataError):
            raise MetadataError("metadata failed")


class TestValidationError:
    """Tests for ValidationError exception."""
    
    def test_validation_error_is_blake_error(self):
        """ValidationError should inherit from BlakeError."""
        assert issubclass(ValidationError, BlakeError)
    
    def test_validation_error_can_be_raised(self):
        """ValidationError can be raised and caught."""
        with pytest.raises(ValidationError):
            raise ValidationError("validation failed")
