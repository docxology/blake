"""
Comprehensive logging configuration for the Blake system.

Provides structured logging with different levels, formatters, and handlers
for different components and use cases.
"""

import logging
import logging.handlers
import sys
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime
import json
import traceback


class BlakeLogger:
    """Enhanced logger for Blake system with structured logging."""
    
    def __init__(self, name: str, log_dir: Optional[Path] = None, level: str = "INFO"):
        """
        Initialize Blake logger.
        
        Args:
            name: Logger name (usually __name__)
            log_dir: Directory for log files
            level: Logging level
        """
        self.name = name
        self.log_dir = log_dir or Path("./logs")
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Create logger
        self.logger = logging.getLogger(name)
        self.logger.setLevel(getattr(logging, level.upper()))
        
        # Clear existing handlers
        self.logger.handlers.clear()
        
        # Add handlers
        self._setup_console_handler()
        self._setup_file_handler()
        self._setup_error_handler()
        self._setup_debug_handler()
        
        # Prevent propagation to root logger
        self.logger.propagate = False
    
    def _setup_console_handler(self):
        """Setup console handler with colored output."""
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        
        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s',
            datefmt='%H:%M:%S'
        )
        console_handler.setFormatter(formatter)
        
        self.logger.addHandler(console_handler)
    
    def _setup_file_handler(self):
        """Setup file handler for general logs."""
        log_file = self.log_dir / f"blake_{datetime.now().strftime('%Y%m%d')}.log"
        file_handler = logging.handlers.RotatingFileHandler(
            log_file, maxBytes=10*1024*1024, backupCount=5
        )
        file_handler.setLevel(logging.DEBUG)
        
        # Detailed formatter for file
        formatter = logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(name)-20s | %(funcName)-15s:%(lineno)-4d | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(formatter)
        
        self.logger.addHandler(file_handler)
    
    def _setup_error_handler(self):
        """Setup error handler for error logs."""
        error_file = self.log_dir / f"blake_errors_{datetime.now().strftime('%Y%m%d')}.log"
        error_handler = logging.handlers.RotatingFileHandler(
            error_file, maxBytes=5*1024*1024, backupCount=3
        )
        error_handler.setLevel(logging.ERROR)
        
        # Error formatter with traceback
        formatter = logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(name)-20s | %(funcName)-15s:%(lineno)-4d | %(message)s\n%(pathname)s:%(lineno)d',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        error_handler.setFormatter(formatter)
        
        self.logger.addHandler(error_handler)
    
    def _setup_debug_handler(self):
        """Setup debug handler for detailed debugging."""
        debug_file = self.log_dir / f"blake_debug_{datetime.now().strftime('%Y%m%d')}.log"
        debug_handler = logging.handlers.RotatingFileHandler(
            debug_file, maxBytes=20*1024*1024, backupCount=2
        )
        debug_handler.setLevel(logging.DEBUG)
        
        # Debug formatter with full context
        formatter = logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(name)-20s | %(funcName)-15s:%(lineno)-4d | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        debug_handler.setFormatter(formatter)
        
        self.logger.addHandler(debug_handler)
    
    def log_download_progress(self, current: int, total: int, work_title: str, status: str = "downloading"):
        """Log download progress with structured information."""
        progress_pct = (current / total) * 100 if total > 0 else 0
        self.logger.info(
            f"📥 {status.capitalize()} {current}/{total} ({progress_pct:.1f}%): {work_title}"
        )
    
    def log_download_result(self, work_id: str, work_title: str, success: bool, 
                          details: Optional[Dict[str, Any]] = None):
        """Log download result with structured information."""
        status_icon = "✅" if success else "❌"
        status_text = "Success" if success else "Failed"
        
        message = f"{status_icon} {status_text}: {work_title} ({work_id})"
        
        if details:
            if success:
                message += f" - {details.get('characters', 0):,} characters"
                if details.get('images', 0) > 0:
                    message += f", {details.get('images', 0)} images"
            else:
                message += f" - {details.get('error', 'Unknown error')}"
        
        if success:
            self.logger.info(message)
        else:
            self.logger.error(message)
    
    def log_api_request(self, api_name: str, endpoint: str, status_code: int, 
                       response_time: float, details: Optional[Dict[str, Any]] = None):
        """Log API request with performance metrics."""
        status_icon = "✅" if 200 <= status_code < 300 else "❌"
        
        message = f"{status_icon} API {api_name}: {endpoint} - {status_code} ({response_time:.2f}s)"
        
        if details:
            if 'works_found' in details:
                message += f" - {details['works_found']} works found"
            if 'error' in details:
                message += f" - {details['error']}"
        
        if 200 <= status_code < 300:
            self.logger.info(message)
        else:
            self.logger.warning(message)
    
    def log_performance_metrics(self, operation: str, duration: float, 
                               metrics: Optional[Dict[str, Any]] = None):
        """Log performance metrics for operations."""
        message = f"⏱️  {operation}: {duration:.2f}s"
        
        if metrics:
            for key, value in metrics.items():
                if isinstance(value, (int, float)):
                    if key.endswith('_count') or key.endswith('_size'):
                        message += f", {key}: {value:,}"
                    else:
                        message += f", {key}: {value}"
                else:
                    message += f", {key}: {value}"
        
        self.logger.info(message)
    
    def log_error_with_context(self, error: Exception, context: Optional[Dict[str, Any]] = None):
        """Log error with full context and traceback."""
        error_msg = f"❌ Error: {str(error)}"
        
        if context:
            error_msg += f" | Context: {json.dumps(context, default=str)}"
        
        self.logger.error(error_msg, exc_info=True)
    
    def log_system_status(self, component: str, status: str, details: Optional[Dict[str, Any]] = None):
        """Log system component status."""
        status_icon = {
            'initialized': '🚀',
            'running': '✅',
            'error': '❌',
            'warning': '⚠️',
            'stopped': '⏹️'
        }.get(status.lower(), '📊')
        
        message = f"{status_icon} {component}: {status}"
        
        if details:
            message += f" | {json.dumps(details, default=str)}"
        
        self.logger.info(message)


def setup_blake_logging(log_dir: Optional[Path] = None, level: str = "INFO") -> Dict[str, BlakeLogger]:
    """
    Setup logging for all Blake components.
    
    Args:
        log_dir: Directory for log files
        level: Logging level
        
    Returns:
        Dictionary of component loggers
    """
    loggers = {}
    
    # Core components
    components = [
        'blake.core',
        'blake.downloader',
        'blake.analyzer',
        'blake.visualization',
        'blake.gui',
        'blake.api_sources',
        'blake.comprehensive_manager'
    ]
    
    for component in components:
        loggers[component] = BlakeLogger(component, log_dir, level)
    
    return loggers


def get_logger(name: str, log_dir: Optional[Path] = None, level: str = "INFO") -> BlakeLogger:
    """
    Get a logger for a specific component.
    
    Args:
        name: Logger name
        log_dir: Directory for log files
        level: Logging level
        
    Returns:
        BlakeLogger instance
    """
    return BlakeLogger(name, log_dir, level)
