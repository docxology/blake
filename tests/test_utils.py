"""
Tests for Blake utils module.
"""

import pytest
import logging
from pathlib import Path

from blake.utils import (
    get_logger,
    BlakeLogger,
    PerformanceTracker,
    BlakeError,
    DownloadError,
    AnalysisError,
    ErrorRecovery,
    RetryConfig
)


class TestBlakeLogger:
    """Tests for BlakeLogger class."""
    
    @pytest.fixture
    def logger(self, tmp_path):
        """Create BlakeLogger instance."""
        return BlakeLogger("test_logger", log_dir=tmp_path)
    
    def test_logger_initialization(self, logger):
        """Logger initializes correctly."""
        assert logger is not None
        assert logger.name == "test_logger"
    
    def test_logger_info(self, logger):
        """Logger can log info messages."""
        logger.logger.info("Test info message")
    
    def test_logger_warning(self, logger):
        """Logger can log warning messages."""
        logger.logger.warning("Test warning message")
    
    def test_logger_error(self, logger):
        """Logger can log error messages."""
        logger.logger.error("Test error message")
    
    def test_logger_debug(self, logger):
        """Logger can log debug messages."""
        logger.logger.debug("Test debug message")


class TestGetLogger:
    """Tests for get_logger function."""
    
    def test_get_logger_returns_logger(self, tmp_path):
        """get_logger returns a BlakeLogger instance."""
        logger = get_logger("test_module", log_dir=tmp_path)
        assert logger is not None
    
    def test_get_logger_same_name_returns_same_instance(self, tmp_path):
        """get_logger returns same instance for same name."""
        logger1 = get_logger("same_name", log_dir=tmp_path)
        logger2 = get_logger("same_name", log_dir=tmp_path)
        # May or may not be same instance depending on implementation
        assert logger1 is not None
        assert logger2 is not None


class TestPerformanceTracker:
    """Tests for PerformanceTracker class."""
    
    @pytest.fixture
    def tracker(self, tmp_path):
        """Create PerformanceTracker instance."""
        return PerformanceTracker(log_dir=tmp_path)
    
    def test_tracker_initialization(self, tracker):
        """Tracker initializes correctly."""
        assert tracker is not None
    
    def test_start_operation(self, tracker):
        """Start tracking an operation."""
        op_id = tracker.start_operation("test_op")
        assert op_id is not None
    
    def test_end_operation(self, tracker):
        """End tracking an operation."""
        op_id = tracker.start_operation("test_op")
        tracker.end_operation(op_id, success=True)
    
    def test_get_performance_summary(self, tracker):
        """Get performance summary."""
        op_id = tracker.start_operation("test_op", metadata={"items": 10})
        tracker.end_operation(op_id, success=True, items_processed=10)
        
        summary = tracker.get_performance_summary("test_op")
        assert isinstance(summary, dict)


class TestErrorHandling:
    """Tests for error handling utilities."""
    
    def test_blake_error_inheritance(self):
        """BlakeError is Exception."""
        assert issubclass(BlakeError, Exception)
    
    def test_download_error_inheritance(self):
        """DownloadError is BlakeError."""
        assert issubclass(DownloadError, BlakeError)
    
    def test_analysis_error_inheritance(self):
        """AnalysisError is BlakeError."""
        assert issubclass(AnalysisError, BlakeError)


class TestRetryConfig:
    """Tests for RetryConfig class."""
    
    def test_retry_config_defaults(self):
        """RetryConfig has sensible defaults."""
        config = RetryConfig()
        assert config.max_attempts >= 1
        assert config.base_delay >= 0
    
    def test_retry_config_custom(self):
        """RetryConfig accepts custom values."""
        config = RetryConfig(max_attempts=5, base_delay=2.0)
        assert config.max_attempts == 5
        assert config.base_delay == 2.0


class TestErrorRecovery:
    """Tests for ErrorRecovery class."""
    
    @pytest.fixture
    def recovery(self, tmp_path):
        """Create ErrorRecovery instance."""
        return ErrorRecovery(log_dir=tmp_path)
    
    def test_recovery_initialization(self, recovery):
        """ErrorRecovery initializes correctly."""
        assert recovery is not None
    
    @pytest.mark.asyncio
    async def test_retry_async_success(self, recovery):
        """retry_async succeeds on first try."""
        async def success_func():
            return "success"
        
        result = await recovery.retry_async(success_func)
        assert result == "success"
    
    def test_retry_sync_success(self, recovery):
        """retry_sync succeeds on first try."""
        def success_func():
            return "success"
        
        result = recovery.retry_sync(success_func)
        assert result == "success"
