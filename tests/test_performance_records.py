"""Verify measured operation records and reports without replacing psutil or clocks."""

import asyncio
from datetime import datetime, timedelta
import json
import time

import pytest
from tests.utility_fixtures import isolated_utility_logs as isolated_utility_logs

from blake.utils.performance_tracker import (
    PerformanceMetrics,
    PerformanceTracker,
    ResourceMonitor,
    track_performance,
)


def test_live_operation_finalizes_rates_and_report(tmp_path):
    tracker = PerformanceTracker(tmp_path)
    assert tracker.get_performance_summary() == {
        "message": "No performance data available"
    }
    assert "No performance data" in tracker.get_optimization_suggestions()[0]
    operation = tracker.start_operation("read", {"source": "fixture"})
    tracker.track_progress(operation, 0, 0)
    tracker.track_progress(operation, 1, 3)
    tracker.track_progress(operation, 3, 3)
    tracker.track_progress("absent", 1, 1)
    time.sleep(0.002)
    tracker.end_operation(operation, items_processed=3, metadata={"complete": True})
    record = tracker.metrics_history[0]
    assert record.duration > 0
    assert record.items_per_second == pytest.approx(3 / record.duration)
    assert record.success_rate == 1
    assert record.memory_usage > 0 and record.cpu_usage >= 0
    assert record.metadata == {"source": "fixture", "complete": True}
    assert not tracker.active_operations
    tracker.end_operation(operation)
    assert len(tracker.metrics_history) == 1
    summary = tracker.get_performance_summary("read")
    assert (
        summary["total_items_processed"] == 3 and summary["average_success_rate"] == 1
    )
    assert tracker.get_performance_summary("absent")["message"]
    report_path = tracker.save_performance_report()
    report = json.loads(report_path.read_text())
    assert report["detailed_metrics"][0]["success_rate"] == 1
    assert report["summary"]["total_operations"] == 1
    selected = tmp_path / "selected.json"
    assert tracker.save_performance_report(selected) == selected
    assert json.loads(selected.read_text())["summary"] == report["summary"]


def test_failed_operation_records_zero_success(tmp_path):
    tracker = PerformanceTracker(tmp_path)
    operation = tracker.start_operation("failed")
    tracker.end_operation(operation, success=False)
    record = tracker.metrics_history[0]
    assert record.error_count == 1 and record.success_count == 0
    assert record.success_rate == 0
    assert any(
        "low success rates" in item for item in tracker.get_optimization_suggestions()
    )


def test_fast_same_name_operations_have_distinct_ids(tmp_path):
    tracker = PerformanceTracker(tmp_path)
    operations = [tracker.start_operation("batch") for _ in range(100)]
    assert len(set(operations)) == 100
    assert len(tracker.active_operations) == 100


def test_historical_metrics_summary_and_suggestions(tmp_path):
    tracker = PerformanceTracker(tmp_path)
    start = datetime.now() - timedelta(days=2)
    slow = PerformanceMetrics(
        "slow",
        start,
        start + timedelta(seconds=40),
        memory_usage=600,
        items_processed=2,
        error_count=1,
    )
    assert (
        slow.duration == 40 and slow.items_per_second == 0.05 and slow.success_rate == 0
    )
    tracker.metrics_history.append(slow)
    suggestions = tracker.get_optimization_suggestions()
    for fragment in (
        "slow operations",
        "low success rates",
        "high memory usage",
        "low throughput",
    ):
        assert any(fragment in item for item in suggestions)
    summary = tracker.get_performance_summary()
    assert summary["total_duration"] == 40 and summary["average_memory_usage_mb"] == 600
    assert summary["min_duration"] == summary["max_duration"] == 40
    tracker.metrics_history[:] = [PerformanceMetrics("pending", datetime.now())]
    assert tracker.get_performance_summary()["average_duration"] == 0
    assert "looks good" in tracker.get_optimization_suggestions()[0]
    path = tracker.save_performance_report(tmp_path / "pending.json")
    assert json.loads(path.read_text())["detailed_metrics"][0]["end_time"] is None
    with pytest.raises(FileNotFoundError):
        tracker.save_performance_report(tmp_path / "missing" / "report.json")


@pytest.mark.asyncio
async def test_performance_decorators_keep_returns_and_errors(tmp_path):
    @track_performance("read-fixture", {"fixture": True})
    def read(path):
        return path.read_text()

    @track_performance("async-read-fixture")
    async def async_read(path):
        return path.read_text()

    source = tmp_path / "source"
    source.write_text("retained")
    assert read(source) == "retained" and await async_read(source) == "retained"
    assert read.__name__ == "read" and async_read.__name__ == "async_read"
    with pytest.raises(FileNotFoundError):
        read(tmp_path / "missing")
    with pytest.raises(FileNotFoundError):
        await async_read(tmp_path / "missing")
    logs = list((tmp_path / "logs").glob("blake*.log"))
    assert logs and any("read-fixture" in path.read_text() for path in logs)


@pytest.mark.asyncio
async def test_resource_monitor_owns_and_stops_its_task(tmp_path):
    monitor = ResourceMonitor(tmp_path)
    await monitor.stop_monitoring()
    await monitor.start_monitoring(interval=0.01)
    task = monitor.monitor_task
    await monitor.start_monitoring(interval=0.01)
    assert monitor.monitor_task is task
    await asyncio.sleep(0.01)
    await monitor.stop_monitoring()
    assert not monitor.monitoring and task.done()
    await monitor.stop_monitoring()
