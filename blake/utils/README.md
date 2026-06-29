# Blake Utilities Module

Logging, error handling, and performance tracking utilities.

## Features

- **Unified Logging**: Consistent log formatting
- **Error Handling**: Graceful error recovery
- **Performance Tracking**: Timing and metrics

## Usage

```python
from blake.utils.unified_logger import get_logger
from blake.utils.performance_tracker import PerformanceTracker

logger = get_logger(__name__)
logger.info("Processing work")

tracker = PerformanceTracker()
with tracker.track("download"):
    await download_work()

metrics = tracker.get_metrics()
```

## Components

| File | Description |
|------|-------------|
| `logging_config.py` | Log configuration |
| `unified_logger.py` | Logger factory |
| `error_handling.py` | Error utilities |
| `performance_tracker.py` | Timing metrics |
