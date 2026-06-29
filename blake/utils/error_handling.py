"""
Comprehensive error handling and recovery system for Blake.

Provides robust error handling, retry mechanisms, and graceful degradation
for all Blake components.
"""

import asyncio
import logging
from typing import Any, Callable, Optional, Dict, List, Union, Type
from functools import wraps
from datetime import datetime, timedelta
import traceback
import json
from pathlib import Path

from .logging_config import get_logger

logger = get_logger(__name__)


class BlakeError(Exception):
    """Base exception for Blake system errors."""
    
    def __init__(self, message: str, error_code: Optional[str] = None, 
                 context: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.error_code = error_code
        self.context = context or {}
        self.timestamp = datetime.now()


class DownloadError(BlakeError):
    """Error during download operations."""
    pass


class AnalysisError(BlakeError):
    """Error during analysis operations."""
    pass


class ValidationError(BlakeError):
    """Error during data validation."""
    pass


class APIError(BlakeError):
    """Error during API operations."""
    pass


class RetryConfig:
    """Configuration for retry mechanisms."""
    
    def __init__(self, max_attempts: int = 3, base_delay: float = 1.0, 
                 max_delay: float = 60.0, exponential_base: float = 2.0,
                 jitter: bool = True):
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter


class ErrorRecovery:
    """Error recovery and retry mechanisms."""
    
    def __init__(self, log_dir: Optional[Path] = None):
        self.log_dir = log_dir or Path("./logs")
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.error_log = self.log_dir / "error_recovery.log"
        self.logger = get_logger(__name__, log_dir)
    
    async def retry_async(self, func: Callable, *args, retry_config: RetryConfig = None,
                         exceptions: tuple = (Exception,), **kwargs) -> Any:
        """
        Retry an async function with exponential backoff.
        
        Args:
            func: Async function to retry
            *args: Function arguments
            retry_config: Retry configuration
            exceptions: Exceptions to retry on
            **kwargs: Function keyword arguments
            
        Returns:
            Function result
            
        Raises:
            Last exception if all retries fail
        """
        if retry_config is None:
            retry_config = RetryConfig()
        
        last_exception = None
        
        for attempt in range(retry_config.max_attempts):
            try:
                result = await func(*args, **kwargs)
                if attempt > 0:
                    self.logger.logger.info(f"✅ Retry successful on attempt {attempt + 1}")
                return result
                
            except exceptions as e:
                last_exception = e
                
                if attempt == retry_config.max_attempts - 1:
                    self.logger.log_error_with_context(
                        e, 
                        context={
                            'function': func.__name__,
                            'attempts': attempt + 1,
                            'max_attempts': retry_config.max_attempts
                        }
                    )
                    raise e
                
                # Calculate delay with exponential backoff
                delay = min(
                    retry_config.base_delay * (retry_config.exponential_base ** attempt),
                    retry_config.max_delay
                )
                
                # Add jitter to prevent thundering herd
                if retry_config.jitter:
                    import random
                    delay *= (0.5 + random.random() * 0.5)
                
                self.logger.logger.warning(
                    f"⚠️  Retry {attempt + 1}/{retry_config.max_attempts} failed: {str(e)}. "
                    f"Retrying in {delay:.2f}s..."
                )
                
                await asyncio.sleep(delay)
        
        raise last_exception
    
    def retry_sync(self, func: Callable, *args, retry_config: RetryConfig = None,
                   exceptions: tuple = (Exception,), **kwargs) -> Any:
        """
        Retry a sync function with exponential backoff.
        
        Args:
            func: Sync function to retry
            *args: Function arguments
            retry_config: Retry configuration
            exceptions: Exceptions to retry on
            **kwargs: Function keyword arguments
            
        Returns:
            Function result
            
        Raises:
            Last exception if all retries fail
        """
        if retry_config is None:
            retry_config = RetryConfig()
        
        last_exception = None
        
        for attempt in range(retry_config.max_attempts):
            try:
                result = func(*args, **kwargs)
                if attempt > 0:
                    self.logger.logger.info(f"✅ Retry successful on attempt {attempt + 1}")
                return result
                
            except exceptions as e:
                last_exception = e
                
                if attempt == retry_config.max_attempts - 1:
                    self.logger.log_error_with_context(
                        e, 
                        context={
                            'function': func.__name__,
                            'attempts': attempt + 1,
                            'max_attempts': retry_config.max_attempts
                        }
                    )
                    raise e
                
                # Calculate delay with exponential backoff
                delay = min(
                    retry_config.base_delay * (retry_config.exponential_base ** attempt),
                    retry_config.max_delay
                )
                
                # Add jitter to prevent thundering herd
                if retry_config.jitter:
                    import random
                    delay *= (0.5 + random.random() * 0.5)
                
                self.logger.logger.warning(
                    f"⚠️  Retry {attempt + 1}/{retry_config.max_attempts} failed: {str(e)}. "
                    f"Retrying in {delay:.2f}s..."
                )
                
                import time
                time.sleep(delay)
        
        raise last_exception
    
    def log_error_recovery(self, error: Exception, recovery_action: str, 
                          success: bool, context: Optional[Dict[str, Any]] = None):
        """Log error recovery attempt."""
        status = "✅ Recovered" if success else "❌ Failed to recover"
        
        self.logger.logger.info(
            f"{status}: {recovery_action} | Error: {str(error)}"
        )
        
        # Log to error recovery file
        with open(self.error_log, 'a', encoding='utf-8') as f:
            f.write(f"{datetime.now().isoformat()} | {status} | {recovery_action} | {str(error)}\n")
            if context:
                f.write(f"Context: {json.dumps(context, default=str)}\n")
            f.write(f"Traceback: {traceback.format_exc()}\n\n")


def retry_on_failure(retry_config: RetryConfig = None, exceptions: tuple = (Exception,)):
    """
    Decorator for retrying functions on failure.
    
    Args:
        retry_config: Retry configuration
        exceptions: Exceptions to retry on
    """
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            recovery = ErrorRecovery()
            return await recovery.retry_async(
                func, *args, retry_config=retry_config, 
                exceptions=exceptions, **kwargs
            )
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            recovery = ErrorRecovery()
            return recovery.retry_sync(
                func, *args, retry_config=retry_config, 
                exceptions=exceptions, **kwargs
            )
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


def handle_graceful_degradation(fallback_value: Any = None, 
                               log_errors: bool = True):
    """
    Decorator for graceful degradation on errors.
    
    Args:
        fallback_value: Value to return on error
        log_errors: Whether to log errors
    """
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                if log_errors:
                    logger = get_logger(func.__module__)
                    logger.log_error_with_context(
                        e, 
                        context={'function': func.__name__, 'fallback_used': True}
                    )
                return fallback_value
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if log_errors:
                    logger = get_logger(func.__module__)
                    logger.log_error_with_context(
                        e, 
                        context={'function': func.__name__, 'fallback_used': True}
                    )
                return fallback_value
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


class CircuitBreaker:
    """Circuit breaker pattern for preventing cascading failures."""
    
    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60,
                 expected_exception: Type[Exception] = Exception):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        
        self.failure_count = 0
        self.last_failure_time = None
        self.state = 'CLOSED'  # CLOSED, OPEN, HALF_OPEN
        
        self.logger = get_logger(__name__)
    
    def call(self, func: Callable, *args, **kwargs):
        """Execute function through circuit breaker."""
        if self.state == 'OPEN':
            if self._should_attempt_reset():
                self.state = 'HALF_OPEN'
                self.logger.logger.info("🔄 Circuit breaker: Attempting reset (HALF_OPEN)")
            else:
                raise BlakeError("Circuit breaker is OPEN - service unavailable")
        
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except self.expected_exception as e:
            self._on_failure()
            raise e
    
    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset."""
        if self.last_failure_time is None:
            return True
        
        return (datetime.now() - self.last_failure_time).seconds >= self.recovery_timeout
    
    def _on_success(self):
        """Handle successful call."""
        self.failure_count = 0
        if self.state == 'HALF_OPEN':
            self.state = 'CLOSED'
            self.logger.logger.info("✅ Circuit breaker: Reset successful (CLOSED)")
    
    def _on_failure(self):
        """Handle failed call."""
        self.failure_count += 1
        self.last_failure_time = datetime.now()
        
        if self.failure_count >= self.failure_threshold:
            self.state = 'OPEN'
            self.logger.logger.error(
                f"🔴 Circuit breaker: Opened after {self.failure_count} failures"
            )


def validate_input(data: Any, validation_func: Callable, error_message: str = "Validation failed"):
    """Validate input data and raise ValidationError if invalid."""
    if not validation_func(data):
        raise ValidationError(error_message, context={'data': str(data)})
    return data


def safe_json_loads(json_str: str, fallback: Any = None) -> Any:
    """Safely load JSON with fallback value."""
    try:
        return json.loads(json_str)
    except (json.JSONDecodeError, TypeError) as e:
        logger = get_logger(__name__)
        logger.logger.warning(f"⚠️  JSON decode error: {e}, using fallback")
        return fallback


def safe_file_operation(operation: Callable, file_path: Path, 
                       fallback: Any = None, **kwargs) -> Any:
    """Safely perform file operation with error handling."""
    try:
        return operation(file_path, **kwargs)
    except (IOError, OSError, PermissionError) as e:
        logger = get_logger(__name__)
        logger.log_error_with_context(
            e, 
            context={'file_path': str(file_path), 'operation': operation.__name__}
        )
        return fallback
