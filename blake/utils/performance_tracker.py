"""
Performance tracking and optimization utilities for Blake system.

Provides comprehensive performance monitoring, optimization suggestions,
and resource usage tracking.
"""

import asyncio
import time
import psutil
import logging
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from pathlib import Path
import json
from functools import wraps

from .logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class PerformanceMetrics:
    """Performance metrics for operations."""
    
    operation_name: str
    start_time: datetime
    end_time: Optional[datetime] = None
    duration: Optional[float] = None
    memory_usage: Optional[float] = None
    cpu_usage: Optional[float] = None
    items_processed: int = 0
    items_per_second: Optional[float] = None
    success_count: int = 0
    error_count: int = 0
    success_rate: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        if self.end_time and not self.duration:
            self.duration = (self.end_time - self.start_time).total_seconds()
        
        if self.duration and self.items_processed > 0:
            self.items_per_second = self.items_processed / self.duration
        
        if self.success_count + self.error_count > 0:
            self.success_rate = self.success_count / (self.success_count + self.error_count)


class PerformanceTracker:
    """Comprehensive performance tracking for Blake operations."""
    
    def __init__(self, log_dir: Optional[Path] = None):
        self.log_dir = log_dir or Path("./logs")
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.metrics_history: List[PerformanceMetrics] = []
        self.active_operations: Dict[str, PerformanceMetrics] = {}
        self.logger = get_logger(__name__, log_dir)
        
        # System resource monitoring
        self.process = psutil.Process()
        self.initial_memory = self.process.memory_info().rss / 1024 / 1024  # MB
    
    def start_operation(self, operation_name: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        """Start tracking an operation."""
        operation_id = f"{operation_name}_{int(time.time() * 1000)}"
        
        metrics = PerformanceMetrics(
            operation_name=operation_name,
            start_time=datetime.now(),
            metadata=metadata or {}
        )
        
        self.active_operations[operation_id] = metrics
        self.logger.logger.info(f"🚀 Started operation: {operation_name} ({operation_id})")
        
        return operation_id
    
    def end_operation(self, operation_id: str, success: bool = True, 
                     items_processed: int = 0, metadata: Optional[Dict[str, Any]] = None):
        """End tracking an operation."""
        if operation_id not in self.active_operations:
            self.logger.logger.warning(f"⚠️  Operation {operation_id} not found in active operations")
            return
        
        metrics = self.active_operations[operation_id]
        metrics.end_time = datetime.now()
        metrics.duration = (metrics.end_time - metrics.start_time).total_seconds()
        
        # Update metrics
        if success:
            metrics.success_count += 1
        else:
            metrics.error_count += 1
        
        metrics.items_processed += items_processed
        
        # Get current resource usage
        metrics.memory_usage = self.process.memory_info().rss / 1024 / 1024  # MB
        metrics.cpu_usage = self.process.cpu_percent()
        
        # Update metadata
        if metadata:
            metrics.metadata.update(metadata)
        
        # Store in history
        self.metrics_history.append(metrics)
        del self.active_operations[operation_id]
        
        # Log performance
        self.logger.log_performance_metrics(
            metrics.operation_name,
            metrics.duration,
            {
                'items_processed': metrics.items_processed,
                'items_per_second': metrics.items_per_second,
                'success_rate': metrics.success_rate,
                'memory_usage_mb': metrics.memory_usage,
                'cpu_usage_percent': metrics.cpu_usage
            }
        )
    
    def track_progress(self, operation_id: str, current: int, total: int, 
                      item_name: str = "item"):
        """Track progress of an operation."""
        if operation_id not in self.active_operations:
            return
        
        progress_pct = (current / total) * 100 if total > 0 else 0
        elapsed = (datetime.now() - self.active_operations[operation_id].start_time).total_seconds()
        
        if current > 0:
            estimated_total = elapsed * total / current
            eta = estimated_total - elapsed
            eta_str = f"ETA: {eta:.1f}s" if eta > 0 else "ETA: calculating..."
        else:
            eta_str = "ETA: calculating..."
        
        self.logger.logger.info(
            f"📊 Progress: {current}/{total} ({progress_pct:.1f}%) - {item_name} | {eta_str}"
        )
    
    def get_performance_summary(self, operation_name: Optional[str] = None) -> Dict[str, Any]:
        """Get performance summary for operations."""
        if operation_name:
            metrics = [m for m in self.metrics_history if m.operation_name == operation_name]
        else:
            metrics = self.metrics_history
        
        if not metrics:
            return {'message': 'No performance data available'}
        
        # Calculate statistics
        durations = [m.duration for m in metrics if m.duration is not None]
        items_processed = [m.items_processed for m in metrics]
        success_rates = [m.success_rate for m in metrics if m.success_rate is not None]
        memory_usage = [m.memory_usage for m in metrics if m.memory_usage is not None]
        
        summary = {
            'operation_name': operation_name or 'All Operations',
            'total_operations': len(metrics),
            'total_duration': sum(durations) if durations else 0,
            'average_duration': sum(durations) / len(durations) if durations else 0,
            'min_duration': min(durations) if durations else 0,
            'max_duration': max(durations) if durations else 0,
            'total_items_processed': sum(items_processed),
            'average_items_per_second': sum([m.items_per_second for m in metrics if m.items_per_second]) / len([m for m in metrics if m.items_per_second]) if [m for m in metrics if m.items_per_second] else 0,
            'average_success_rate': sum(success_rates) / len(success_rates) if success_rates else 0,
            'average_memory_usage_mb': sum(memory_usage) / len(memory_usage) if memory_usage else 0,
            'peak_memory_usage_mb': max(memory_usage) if memory_usage else 0
        }
        
        return summary
    
    def save_performance_report(self, file_path: Optional[Path] = None):
        """Save detailed performance report."""
        if file_path is None:
            file_path = self.log_dir / f"performance_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        report = {
            'generated_at': datetime.now().isoformat(),
            'summary': self.get_performance_summary(),
            'detailed_metrics': [
                {
                    'operation_name': m.operation_name,
                    'start_time': m.start_time.isoformat(),
                    'end_time': m.end_time.isoformat() if m.end_time else None,
                    'duration': m.duration,
                    'items_processed': m.items_processed,
                    'items_per_second': m.items_per_second,
                    'success_rate': m.success_rate,
                    'memory_usage_mb': m.memory_usage,
                    'cpu_usage_percent': m.cpu_usage,
                    'metadata': m.metadata
                }
                for m in self.metrics_history
            ]
        }
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, default=str)
        
        self.logger.logger.info(f"📄 Performance report saved: {file_path}")
        return file_path
    
    def get_optimization_suggestions(self) -> List[str]:
        """Get optimization suggestions based on performance data."""
        suggestions = []
        
        if not self.metrics_history:
            return ["No performance data available for optimization suggestions"]
        
        # Analyze recent metrics
        recent_metrics = [m for m in self.metrics_history 
                         if m.start_time > datetime.now() - timedelta(hours=1)]
        
        if not recent_metrics:
            recent_metrics = self.metrics_history[-10:]  # Last 10 operations
        
        # Check for slow operations
        slow_operations = [m for m in recent_metrics 
                          if m.duration and m.duration > 30]  # > 30 seconds
        
        if slow_operations:
            suggestions.append(
                f"Consider optimizing {len(slow_operations)} slow operations (>30s): "
                f"{', '.join(set(m.operation_name for m in slow_operations))}"
            )
        
        # Check for low success rates
        low_success_operations = [m for m in recent_metrics 
                                 if m.success_rate and m.success_rate < 0.8]
        
        if low_success_operations:
            suggestions.append(
                f"Improve error handling for {len(low_success_operations)} operations "
                f"with low success rates (<80%): "
                f"{', '.join(set(m.operation_name for m in low_success_operations))}"
            )
        
        # Check for high memory usage
        high_memory_operations = [m for m in recent_metrics 
                                 if m.memory_usage and m.memory_usage > 500]  # > 500MB
        
        if high_memory_operations:
            suggestions.append(
                f"Optimize memory usage for {len(high_memory_operations)} operations "
                f"with high memory usage (>500MB): "
                f"{', '.join(set(m.operation_name for m in high_memory_operations))}"
            )
        
        # Check for low throughput
        low_throughput_operations = [m for m in recent_metrics 
                                   if m.items_per_second and m.items_per_second < 1]
        
        if low_throughput_operations:
            suggestions.append(
                f"Consider parallelization for {len(low_throughput_operations)} operations "
                f"with low throughput (<1 item/s): "
                f"{', '.join(set(m.operation_name for m in low_throughput_operations))}"
            )
        
        if not suggestions:
            suggestions.append("Performance looks good! No optimization suggestions at this time.")
        
        return suggestions


def track_performance(operation_name: str, metadata: Optional[Dict[str, Any]] = None):
    """Decorator for tracking function performance."""
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            tracker = PerformanceTracker()
            operation_id = tracker.start_operation(operation_name, metadata)
            
            try:
                result = await func(*args, **kwargs)
                tracker.end_operation(operation_id, success=True)
                return result
            except Exception as e:
                tracker.end_operation(operation_id, success=False)
                raise e
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            tracker = PerformanceTracker()
            operation_id = tracker.start_operation(operation_name, metadata)
            
            try:
                result = func(*args, **kwargs)
                tracker.end_operation(operation_id, success=True)
                return result
            except Exception as e:
                tracker.end_operation(operation_id, success=False)
                raise e
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


class ResourceMonitor:
    """Monitor system resources during operations."""
    
    def __init__(self, log_dir: Optional[Path] = None):
        self.log_dir = log_dir or Path("./logs")
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.logger = get_logger(__name__, log_dir)
        self.monitoring = False
        self.monitor_task = None
    
    async def start_monitoring(self, interval: float = 5.0):
        """Start resource monitoring."""
        if self.monitoring:
            return
        
        self.monitoring = True
        self.monitor_task = asyncio.create_task(self._monitor_loop(interval))
        self.logger.logger.info("🔍 Started resource monitoring")
    
    async def stop_monitoring(self):
        """Stop resource monitoring."""
        if not self.monitoring:
            return
        
        self.monitoring = False
        if self.monitor_task:
            self.monitor_task.cancel()
            try:
                await self.monitor_task
            except asyncio.CancelledError:
                pass
        
        self.logger.logger.info("⏹️  Stopped resource monitoring")
    
    async def _monitor_loop(self, interval: float):
        """Resource monitoring loop."""
        process = psutil.Process()
        
        while self.monitoring:
            try:
                # Get system metrics
                cpu_percent = psutil.cpu_percent(interval=1)
                memory = psutil.virtual_memory()
                disk = psutil.disk_usage('/')
                
                # Get process metrics
                process_memory = process.memory_info().rss / 1024 / 1024  # MB
                process_cpu = process.cpu_percent()
                
                # Log if resources are high
                if cpu_percent > 80:
                    self.logger.logger.warning(f"⚠️  High CPU usage: {cpu_percent:.1f}%")
                
                if memory.percent > 80:
                    self.logger.logger.warning(f"⚠️  High memory usage: {memory.percent:.1f}%")
                
                if disk.percent > 90:
                    self.logger.logger.warning(f"⚠️  High disk usage: {disk.percent:.1f}%")
                
                await asyncio.sleep(interval)
                
            except Exception as e:
                self.logger.logger.error(f"❌ Error in resource monitoring: {e}")
                await asyncio.sleep(interval)
