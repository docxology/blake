# utils Module

Logging, error handling, and performance tracking utilities.

## Components

| File | Purpose |
|------|---------|
| `logging_config.py` | Logging configuration |
| `unified_logger.py` | Unified logging interface |
| `error_handling.py` | Exception handling utilities |
| `improved_error_handling.py` | Enhanced error recovery |
| `performance_tracker.py` | Performance monitoring |

## Usage

```python
from blake.utils.unified_logger import get_logger
from blake.utils.performance_tracker import PerformanceTracker

logger = get_logger(__name__)
tracker = PerformanceTracker()
```
