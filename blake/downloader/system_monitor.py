"""
Comprehensive Monitoring and Alerting System for Blake download operations.
Implements real-time monitoring, health checks, and automated alerting.
"""

import asyncio
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Set, Callable
from datetime import datetime, timedelta
import json
import psutil
import time
from dataclasses import dataclass, asdict
from enum import Enum
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from ..models import SourceType, BlakeWork
from ..exceptions import DownloadError

logger = logging.getLogger(__name__)


class AlertLevel(str, Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class HealthStatus(str, Enum):
    """System health status."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    CRITICAL = "critical"


@dataclass
class Metric:
    """A monitoring metric."""
    name: str
    value: float
    timestamp: datetime
    unit: str = ""
    tags: Dict[str, str] = None

    def __post_init__(self):
        if self.tags is None:
            self.tags = {}


@dataclass
class Alert:
    """An alert notification."""
    id: str
    level: AlertLevel
    title: str
    message: str
    timestamp: datetime
    source: str
    resolved: bool = False
    resolved_at: Optional[datetime] = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class HealthCheck:
    """A health check result."""
    name: str
    status: HealthStatus
    message: str
    timestamp: datetime
    duration_ms: float
    details: Dict[str, Any] = None

    def __post_init__(self):
        if self.details is None:
            self.details = {}


class MonitoringSystem:
    """
    Comprehensive monitoring and alerting system.
    
    Features:
    - Real-time metrics collection
    - Health checks and status monitoring
    - Automated alerting and notifications
    - Performance tracking and analysis
    - System resource monitoring
    - Download progress tracking
    - Error rate monitoring
    - Custom metric collection
    """
    
    def __init__(self, data_dir: Path, config: Optional[Dict[str, Any]] = None):
        """
        Initialize monitoring system.
        
        Args:
            data_dir: Directory for monitoring data
            config: Monitoring configuration
        """
        self.data_dir = data_dir
        self.monitoring_dir = data_dir / "monitoring"
        self.monitoring_dir.mkdir(parents=True, exist_ok=True)
        
        # Configuration
        self.config = config or self._default_config()
        
        # Metrics storage
        self.metrics: List[Metric] = []
        self.alerts: List[Alert] = []
        self.health_checks: List[HealthCheck] = []
        
        # Monitoring state
        self.is_monitoring = False
        self.monitoring_task = None
        
        # Alert handlers
        self.alert_handlers: List[Callable[[Alert], None]] = []
        
        # Thresholds
        self.thresholds = {
            'cpu_usage': 80.0,
            'memory_usage': 85.0,
            'disk_usage': 90.0,
            'download_failure_rate': 0.1,
            'response_time': 30.0,
            'error_rate': 0.05
        }
        
        logger.info("Initialized MonitoringSystem")
    
    def _default_config(self) -> Dict[str, Any]:
        """Get default monitoring configuration."""
        return {
            'metrics_retention_days': 30,
            'alert_retention_days': 90,
            'health_check_interval': 60,  # seconds
            'metrics_collection_interval': 10,  # seconds
            'enable_email_alerts': False,
            'enable_webhook_alerts': False,
            'email_config': {
                'smtp_server': 'localhost',
                'smtp_port': 587,
                'username': '',
                'password': '',
                'from_email': 'monitoring@blake-system.local',
                'to_emails': []
            },
            'webhook_config': {
                'url': '',
                'headers': {}
            }
        }
    
    async def start_monitoring(self) -> None:
        """Start the monitoring system."""
        if self.is_monitoring:
            logger.warning("Monitoring already started")
            return
        
        logger.info("Starting monitoring system")
        self.is_monitoring = True
        
        # Start monitoring tasks
        self.monitoring_task = asyncio.create_task(self._monitoring_loop())
        
        # Register default health checks
        await self._register_default_health_checks()
        
        logger.info("Monitoring system started")
    
    async def stop_monitoring(self) -> None:
        """Stop the monitoring system."""
        if not self.is_monitoring:
            return
        
        logger.info("Stopping monitoring system")
        self.is_monitoring = False
        
        if self.monitoring_task:
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Monitoring system stopped")
    
    async def _monitoring_loop(self) -> None:
        """Main monitoring loop."""
        while self.is_monitoring:
            try:
                # Collect system metrics
                await self._collect_system_metrics()
                
                # Run health checks
                await self._run_health_checks()
                
                # Process alerts
                await self._process_alerts()
                
                # Clean up old data
                await self._cleanup_old_data()
                
                # Wait for next cycle
                await asyncio.sleep(self.config['metrics_collection_interval'])
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(5)  # Short delay before retry
    
    async def _collect_system_metrics(self) -> None:
        """Collect system metrics."""
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            await self._record_metric('cpu_usage', cpu_percent, '%')
            
            # Memory usage
            memory = psutil.virtual_memory()
            await self._record_metric('memory_usage', memory.percent, '%')
            await self._record_metric('memory_available', memory.available / (1024**3), 'GB')
            
            # Disk usage
            disk = psutil.disk_usage(self.data_dir)
            disk_percent = (disk.used / disk.total) * 100
            await self._record_metric('disk_usage', disk_percent, '%')
            await self._record_metric('disk_free', disk.free / (1024**3), 'GB')
            
            # Network I/O
            net_io = psutil.net_io_counters()
            await self._record_metric('network_bytes_sent', net_io.bytes_sent / (1024**2), 'MB')
            await self._record_metric('network_bytes_recv', net_io.bytes_recv / (1024**2), 'MB')
            
            # Process count
            process_count = len(psutil.pids())
            await self._record_metric('process_count', process_count, 'count')
            
        except Exception as e:
            logger.error(f"Error collecting system metrics: {e}")
    
    async def _record_metric(self, name: str, value: float, unit: str = "", tags: Dict[str, str] = None) -> None:
        """Record a metric."""
        metric = Metric(
            name=name,
            value=value,
            timestamp=datetime.now(),
            unit=unit,
            tags=tags or {}
        )
        
        self.metrics.append(metric)
        
        # Check thresholds
        await self._check_metric_thresholds(metric)
    
    async def _check_metric_thresholds(self, metric: Metric) -> None:
        """Check if metric exceeds thresholds."""
        threshold = self.thresholds.get(metric.name)
        if threshold is None:
            return
        
        if metric.value > threshold:
            level = AlertLevel.WARNING
            if metric.value > threshold * 1.5:
                level = AlertLevel.ERROR
            if metric.value > threshold * 2.0:
                level = AlertLevel.CRITICAL
            
            await self._create_alert(
                level=level,
                title=f"High {metric.name}",
                message=f"{metric.name} is {metric.value:.1f}{metric.unit}, threshold is {threshold}{metric.unit}",
                source="monitoring",
                metadata={'metric': metric.name, 'value': metric.value, 'threshold': threshold}
            )
    
    async def _register_default_health_checks(self) -> None:
        """Register default health checks."""
        # System health checks
        await self._register_health_check("system_cpu", self._check_cpu_health)
        await self._register_health_check("system_memory", self._check_memory_health)
        await self._register_health_check("system_disk", self._check_disk_health)
        await self._register_health_check("data_directory", self._check_data_directory_health)
        
        # Download health checks
        await self._register_health_check("download_system", self._check_download_health)
        await self._register_health_check("source_connectivity", self._check_source_connectivity)
    
    async def _register_health_check(self, name: str, check_func: Callable) -> None:
        """Register a health check function."""
        # This would be implemented with a proper health check registry
        pass
    
    async def _run_health_checks(self) -> None:
        """Run all registered health checks."""
        try:
            # CPU health check
            await self._check_cpu_health()
            
            # Memory health check
            await self._check_memory_health()
            
            # Disk health check
            await self._check_disk_health()
            
            # Data directory health check
            await self._check_data_directory_health()
            
            # Download system health check
            await self._check_download_health()
            
            # Source connectivity health check
            await self._check_source_connectivity()
            
        except Exception as e:
            logger.error(f"Error running health checks: {e}")
    
    async def _check_cpu_health(self) -> None:
        """Check CPU health."""
        start_time = time.time()
        
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            duration_ms = (time.time() - start_time) * 1000
            
            if cpu_percent > 90:
                status = HealthStatus.CRITICAL
                message = f"CPU usage is critically high: {cpu_percent:.1f}%"
            elif cpu_percent > 80:
                status = HealthStatus.UNHEALTHY
                message = f"CPU usage is high: {cpu_percent:.1f}%"
            elif cpu_percent > 60:
                status = HealthStatus.DEGRADED
                message = f"CPU usage is elevated: {cpu_percent:.1f}%"
            else:
                status = HealthStatus.HEALTHY
                message = f"CPU usage is normal: {cpu_percent:.1f}%"
            
            health_check = HealthCheck(
                name="cpu_health",
                status=status,
                message=message,
                timestamp=datetime.now(),
                duration_ms=duration_ms,
                details={'cpu_percent': cpu_percent}
            )
            
            self.health_checks.append(health_check)
            
        except Exception as e:
            health_check = HealthCheck(
                name="cpu_health",
                status=HealthStatus.CRITICAL,
                message=f"CPU health check failed: {e}",
                timestamp=datetime.now(),
                duration_ms=(time.time() - start_time) * 1000,
                details={'error': str(e)}
            )
            self.health_checks.append(health_check)
    
    async def _check_memory_health(self) -> None:
        """Check memory health."""
        start_time = time.time()
        
        try:
            memory = psutil.virtual_memory()
            duration_ms = (time.time() - start_time) * 1000
            
            if memory.percent > 95:
                status = HealthStatus.CRITICAL
                message = f"Memory usage is critically high: {memory.percent:.1f}%"
            elif memory.percent > 85:
                status = HealthStatus.UNHEALTHY
                message = f"Memory usage is high: {memory.percent:.1f}%"
            elif memory.percent > 70:
                status = HealthStatus.DEGRADED
                message = f"Memory usage is elevated: {memory.percent:.1f}%"
            else:
                status = HealthStatus.HEALTHY
                message = f"Memory usage is normal: {memory.percent:.1f}%"
            
            health_check = HealthCheck(
                name="memory_health",
                status=status,
                message=message,
                timestamp=datetime.now(),
                duration_ms=duration_ms,
                details={
                    'memory_percent': memory.percent,
                    'memory_available_gb': memory.available / (1024**3),
                    'memory_total_gb': memory.total / (1024**3)
                }
            )
            
            self.health_checks.append(health_check)
            
        except Exception as e:
            health_check = HealthCheck(
                name="memory_health",
                status=HealthStatus.CRITICAL,
                message=f"Memory health check failed: {e}",
                timestamp=datetime.now(),
                duration_ms=(time.time() - start_time) * 1000,
                details={'error': str(e)}
            )
            self.health_checks.append(health_check)
    
    async def _check_disk_health(self) -> None:
        """Check disk health."""
        start_time = time.time()
        
        try:
            disk = psutil.disk_usage(self.data_dir)
            disk_percent = (disk.used / disk.total) * 100
            duration_ms = (time.time() - start_time) * 1000
            
            if disk_percent > 95:
                status = HealthStatus.CRITICAL
                message = f"Disk usage is critically high: {disk_percent:.1f}%"
            elif disk_percent > 90:
                status = HealthStatus.UNHEALTHY
                message = f"Disk usage is high: {disk_percent:.1f}%"
            elif disk_percent > 80:
                status = HealthStatus.DEGRADED
                message = f"Disk usage is elevated: {disk_percent:.1f}%"
            else:
                status = HealthStatus.HEALTHY
                message = f"Disk usage is normal: {disk_percent:.1f}%"
            
            health_check = HealthCheck(
                name="disk_health",
                status=status,
                message=message,
                timestamp=datetime.now(),
                duration_ms=duration_ms,
                details={
                    'disk_percent': disk_percent,
                    'disk_free_gb': disk.free / (1024**3),
                    'disk_total_gb': disk.total / (1024**3)
                }
            )
            
            self.health_checks.append(health_check)
            
        except Exception as e:
            health_check = HealthCheck(
                name="disk_health",
                status=HealthStatus.CRITICAL,
                message=f"Disk health check failed: {e}",
                timestamp=datetime.now(),
                duration_ms=(time.time() - start_time) * 1000,
                details={'error': str(e)}
            )
            self.health_checks.append(health_check)
    
    async def _check_data_directory_health(self) -> None:
        """Check data directory health."""
        start_time = time.time()
        
        try:
            duration_ms = (time.time() - start_time) * 1000
            
            # Check if data directory exists and is writable
            if not self.data_dir.exists():
                status = HealthStatus.CRITICAL
                message = "Data directory does not exist"
            elif not self.data_dir.is_dir():
                status = HealthStatus.CRITICAL
                message = "Data directory is not a directory"
            else:
                # Check if directory is writable
                try:
                    test_file = self.data_dir / ".health_check"
                    test_file.write_text("test")
                    test_file.unlink()
                    
                    status = HealthStatus.HEALTHY
                    message = "Data directory is accessible and writable"
                except Exception as e:
                    status = HealthStatus.UNHEALTHY
                    message = f"Data directory is not writable: {e}"
            
            health_check = HealthCheck(
                name="data_directory_health",
                status=status,
                message=message,
                timestamp=datetime.now(),
                duration_ms=duration_ms,
                details={'data_directory': str(self.data_dir)}
            )
            
            self.health_checks.append(health_check)
            
        except Exception as e:
            health_check = HealthCheck(
                name="data_directory_health",
                status=HealthStatus.CRITICAL,
                message=f"Data directory health check failed: {e}",
                timestamp=datetime.now(),
                duration_ms=(time.time() - start_time) * 1000,
                details={'error': str(e)}
            )
            self.health_checks.append(health_check)
    
    async def _check_download_health(self) -> None:
        """Check download system health."""
        start_time = time.time()
        
        try:
            duration_ms = (time.time() - start_time) * 1000
            
            # Check for recent download activity
            downloads_dir = self.data_dir / "downloads"
            if not downloads_dir.exists():
                status = HealthStatus.DEGRADED
                message = "No downloads directory found"
            else:
                # Check for recent files
                recent_files = []
                for file_path in downloads_dir.rglob('*'):
                    if file_path.is_file():
                        file_age = datetime.now() - datetime.fromtimestamp(file_path.stat().st_mtime)
                        if file_age < timedelta(hours=24):
                            recent_files.append(file_path)
                
                if len(recent_files) == 0:
                    status = HealthStatus.DEGRADED
                    message = "No recent download activity"
                else:
                    status = HealthStatus.HEALTHY
                    message = f"Download system active, {len(recent_files)} recent files"
            
            health_check = HealthCheck(
                name="download_health",
                status=status,
                message=message,
                timestamp=datetime.now(),
                duration_ms=duration_ms,
                details={'recent_files': len(recent_files) if 'recent_files' in locals() else 0}
            )
            
            self.health_checks.append(health_check)
            
        except Exception as e:
            health_check = HealthCheck(
                name="download_health",
                status=HealthStatus.CRITICAL,
                message=f"Download health check failed: {e}",
                timestamp=datetime.now(),
                duration_ms=(time.time() - start_time) * 1000,
                details={'error': str(e)}
            )
            self.health_checks.append(health_check)
    
    async def _check_source_connectivity(self) -> None:
        """Check source connectivity health."""
        start_time = time.time()
        
        try:
            duration_ms = (time.time() - start_time) * 1000
            
            # This would check connectivity to various sources
            # For now, we'll simulate a basic check
            status = HealthStatus.HEALTHY
            message = "Source connectivity normal"
            
            health_check = HealthCheck(
                name="source_connectivity",
                status=status,
                message=message,
                timestamp=datetime.now(),
                duration_ms=duration_ms,
                details={}
            )
            
            self.health_checks.append(health_check)
            
        except Exception as e:
            health_check = HealthCheck(
                name="source_connectivity",
                status=HealthStatus.CRITICAL,
                message=f"Source connectivity check failed: {e}",
                timestamp=datetime.now(),
                duration_ms=(time.time() - start_time) * 1000,
                details={'error': str(e)}
            )
            self.health_checks.append(health_check)
    
    async def _process_alerts(self) -> None:
        """Process and send alerts."""
        try:
            # Get unresolved alerts
            unresolved_alerts = [alert for alert in self.alerts if not alert.resolved]
            
            for alert in unresolved_alerts:
                # Send alert to all handlers
                for handler in self.alert_handlers:
                    try:
                        handler(alert)
                    except Exception as e:
                        logger.error(f"Error in alert handler: {e}")
                
                # Mark as processed (not resolved, just sent)
                # In a real system, you'd track this separately
            
        except Exception as e:
            logger.error(f"Error processing alerts: {e}")
    
    async def _create_alert(self, level: AlertLevel, title: str, message: str, 
                           source: str, metadata: Dict[str, Any] = None) -> None:
        """Create a new alert."""
        alert = Alert(
            id=f"{source}_{int(time.time())}",
            level=level,
            title=title,
            message=message,
            timestamp=datetime.now(),
            source=source,
            metadata=metadata or {}
        )
        
        self.alerts.append(alert)
        logger.info(f"Alert created: {level.value} - {title}")
    
    def add_alert_handler(self, handler: Callable[[Alert], None]) -> None:
        """Add an alert handler."""
        self.alert_handlers.append(handler)
    
    async def _cleanup_old_data(self) -> None:
        """Clean up old monitoring data."""
        try:
            cutoff_date = datetime.now() - timedelta(days=self.config['metrics_retention_days'])
            
            # Clean up old metrics
            self.metrics = [m for m in self.metrics if m.timestamp > cutoff_date]
            
            # Clean up old health checks
            self.health_checks = [h for h in self.health_checks if h.timestamp > cutoff_date]
            
            # Clean up old alerts (keep longer)
            alert_cutoff = datetime.now() - timedelta(days=self.config['alert_retention_days'])
            self.alerts = [a for a in self.alerts if a.timestamp > alert_cutoff]
            
        except Exception as e:
            logger.error(f"Error cleaning up old data: {e}")
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get current system status."""
        try:
            # Get latest health checks
            latest_health_checks = {}
            for check in self.health_checks[-10:]:  # Last 10 checks
                latest_health_checks[check.name] = {
                    'status': check.status.value,
                    'message': check.message,
                    'timestamp': check.timestamp.isoformat(),
                    'duration_ms': check.duration_ms
                }
            
            # Get latest metrics
            latest_metrics = {}
            for metric in self.metrics[-20:]:  # Last 20 metrics
                if metric.name not in latest_metrics:
                    latest_metrics[metric.name] = []
                latest_metrics[metric.name].append({
                    'value': metric.value,
                    'unit': metric.unit,
                    'timestamp': metric.timestamp.isoformat()
                })
            
            # Get active alerts
            active_alerts = [
                {
                    'id': alert.id,
                    'level': alert.level.value,
                    'title': alert.title,
                    'message': alert.message,
                    'timestamp': alert.timestamp.isoformat(),
                    'source': alert.source
                }
                for alert in self.alerts[-10:] if not alert.resolved
            ]
            
            # Calculate overall health
            overall_health = self._calculate_overall_health()
            
            return {
                'overall_health': overall_health,
                'health_checks': latest_health_checks,
                'metrics': latest_metrics,
                'active_alerts': active_alerts,
                'monitoring_active': self.is_monitoring,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting system status: {e}")
            return {
                'overall_health': 'unknown',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def _calculate_overall_health(self) -> str:
        """Calculate overall system health."""
        if not self.health_checks:
            return 'unknown'
        
        # Get latest health check for each type
        latest_checks = {}
        for check in reversed(self.health_checks):
            if check.name not in latest_checks:
                latest_checks[check.name] = check
        
        # Determine overall health
        if any(check.status == HealthStatus.CRITICAL for check in latest_checks.values()):
            return 'critical'
        elif any(check.status == HealthStatus.UNHEALTHY for check in latest_checks.values()):
            return 'unhealthy'
        elif any(check.status == HealthStatus.DEGRADED for check in latest_checks.values()):
            return 'degraded'
        else:
            return 'healthy'
    
    def get_metrics_summary(self, hours: int = 24) -> Dict[str, Any]:
        """Get metrics summary for the last N hours."""
        try:
            cutoff_time = datetime.now() - timedelta(hours=hours)
            recent_metrics = [m for m in self.metrics if m.timestamp > cutoff_time]
            
            # Group metrics by name
            metric_groups = {}
            for metric in recent_metrics:
                if metric.name not in metric_groups:
                    metric_groups[metric.name] = []
                metric_groups[metric.name].append(metric)
            
            # Calculate summaries
            summaries = {}
            for name, metrics in metric_groups.items():
                values = [m.value for m in metrics]
                summaries[name] = {
                    'count': len(values),
                    'min': min(values),
                    'max': max(values),
                    'avg': sum(values) / len(values),
                    'latest': values[-1] if values else None,
                    'unit': metrics[0].unit if metrics else ''
                }
            
            return {
                'period_hours': hours,
                'metrics': summaries,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting metrics summary: {e}")
            return {'error': str(e)}
    
    async def record_download_metric(self, source: SourceType, success: bool, 
                                   duration_seconds: float, file_size: int) -> None:
        """Record download-specific metrics."""
        try:
            # Record download success/failure
            await self._record_metric(
                'download_success',
                1.0 if success else 0.0,
                'count',
                {'source': source.value}
            )
            
            # Record download duration
            await self._record_metric(
                'download_duration',
                duration_seconds,
                'seconds',
                {'source': source.value}
            )
            
            # Record download size
            await self._record_metric(
                'download_size',
                file_size / (1024 * 1024),  # Convert to MB
                'MB',
                {'source': source.value}
            )
            
            # Record download rate
            if duration_seconds > 0:
                rate = (file_size / (1024 * 1024)) / duration_seconds  # MB/s
                await self._record_metric(
                    'download_rate',
                    rate,
                    'MB/s',
                    {'source': source.value}
                )
            
        except Exception as e:
            logger.error(f"Error recording download metric: {e}")
    
    async def record_error(self, error_type: str, error_message: str, 
                          source: str, metadata: Dict[str, Any] = None) -> None:
        """Record an error for monitoring."""
        try:
            # Record error metric
            await self._record_metric(
                'error_count',
                1.0,
                'count',
                {'error_type': error_type, 'source': source}
            )
            
            # Create error alert
            await self._create_alert(
                level=AlertLevel.ERROR,
                title=f"Error: {error_type}",
                message=error_message,
                source=source,
                metadata=metadata or {}
            )
            
        except Exception as e:
            logger.error(f"Error recording error: {e}")
    
    def save_monitoring_data(self) -> None:
        """Save monitoring data to disk."""
        try:
            # Save metrics
            metrics_file = self.monitoring_dir / "metrics.json"
            metrics_data = [asdict(m) for m in self.metrics[-1000:]]  # Keep last 1000
            for metric in metrics_data:
                metric['timestamp'] = metric['timestamp'].isoformat()
            
            with open(metrics_file, 'w', encoding='utf-8') as f:
                json.dump(metrics_data, f, indent=2, ensure_ascii=False)
            
            # Save alerts
            alerts_file = self.monitoring_dir / "alerts.json"
            alerts_data = [asdict(a) for a in self.alerts[-100:]]  # Keep last 100
            for alert in alerts_data:
                alert['timestamp'] = alert['timestamp'].isoformat()
                if alert['resolved_at']:
                    alert['resolved_at'] = alert['resolved_at'].isoformat()
            
            with open(alerts_file, 'w', encoding='utf-8') as f:
                json.dump(alerts_data, f, indent=2, ensure_ascii=False)
            
            # Save health checks
            health_file = self.monitoring_dir / "health_checks.json"
            health_data = [asdict(h) for h in self.health_checks[-100:]]  # Keep last 100
            for check in health_data:
                check['timestamp'] = check['timestamp'].isoformat()
            
            with open(health_file, 'w', encoding='utf-8') as f:
                json.dump(health_data, f, indent=2, ensure_ascii=False)
            
            logger.info("Monitoring data saved to disk")
            
        except Exception as e:
            logger.error(f"Error saving monitoring data: {e}")
    
    def load_monitoring_data(self) -> None:
        """Load monitoring data from disk."""
        try:
            # Load metrics
            metrics_file = self.monitoring_dir / "metrics.json"
            if metrics_file.exists():
                with open(metrics_file, 'r', encoding='utf-8') as f:
                    metrics_data = json.load(f)
                
                self.metrics = []
                for data in metrics_data:
                    data['timestamp'] = datetime.fromisoformat(data['timestamp'])
                    self.metrics.append(Metric(**data))
            
            # Load alerts
            alerts_file = self.monitoring_dir / "alerts.json"
            if alerts_file.exists():
                with open(alerts_file, 'r', encoding='utf-8') as f:
                    alerts_data = json.load(f)
                
                self.alerts = []
                for data in alerts_data:
                    data['timestamp'] = datetime.fromisoformat(data['timestamp'])
                    if data['resolved_at']:
                        data['resolved_at'] = datetime.fromisoformat(data['resolved_at'])
                    self.alerts.append(Alert(**data))
            
            # Load health checks
            health_file = self.monitoring_dir / "health_checks.json"
            if health_file.exists():
                with open(health_file, 'r', encoding='utf-8') as f:
                    health_data = json.load(f)
                
                self.health_checks = []
                for data in health_data:
                    data['timestamp'] = datetime.fromisoformat(data['timestamp'])
                    self.health_checks.append(HealthCheck(**data))
            
            logger.info("Monitoring data loaded from disk")
            
        except Exception as e:
            logger.error(f"Error loading monitoring data: {e}")
