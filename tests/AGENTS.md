# tests/ Directory

Test suite for the Blake package.

## Structure

```
tests/
├── conftest.py                    # Pytest fixtures
├── test_core.py                   # Core functionality
├── test_models.py                 # Data models
├── test_analysis.py               # Analysis module
├── test_downloader.py             # Downloader module
├── test_download_manager.py       # Download management
├── test_visualization.py          # Visualization tests
├── test_comprehensive_acquisition.py  # Integration tests
├── run_all_tests.py               # Test runner
├── unit/                          # Unit tests
├── integration/                   # Integration tests
└── performance/                   # Performance tests
```

## Running Tests

```bash
# All tests
uv run pytest tests/ -v

# Fast tests only
uv run pytest tests/ -v -m "not slow"

# With coverage
uv run pytest tests/ --cov=blake

# Specific module
uv run pytest tests/test_core.py -v
```

## Markers

- `@pytest.mark.slow` - Long-running tests
- `@pytest.mark.integration` - Integration tests
- `@pytest.mark.unit` - Unit tests
- `@pytest.mark.download` - Download tests
