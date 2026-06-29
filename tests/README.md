# Blake Test Suite

Test suite for the Blake package.

## Quick Start

```bash
# Run offline fast tests
uv run pytest tests/ -q -m "not slow and not integration"

# Run source-governed corpus/release contract tests
uv run pytest tests/test_cli.py tests/test_corpus.py tests/test_public_release.py tests/test_export.py tests/test_manuscript_tools.py -q

# Run all local tests with coverage
uv run pytest tests/ --cov=blake --cov-report=term-missing
```

Integration and live-source checks are opt-in. They may touch remote provider
endpoints and should not be used as the default proof for quick local corpus
regeneration.

## Test Structure

| Directory | Description |
|-----------|-------------|
| `unit/` | Isolated unit tests |
| `integration/` | End-to-end flows |
| `performance/` | Performance benchmarks |

## Test Files

| File | Coverage |
|------|----------|
| `test_core.py` | `BlakeWorks` class |
| `test_models.py` | Data models |
| `test_analysis.py` | Analysis module |
| `test_downloader.py` | Download module |
| `test_visualization.py` | Visualization |

## Fixtures

See `conftest.py` for shared fixtures:
- `sample_work` - Sample BlakeWork
- `sample_metadata` - Sample metadata
- `temp_dir` - Temporary directory
- `mock_*` - Mock components

## Writing Tests

```python
import pytest
from blake import BlakeWorks

class TestFeature:
    @pytest.fixture
    def fixture(self, tmp_path):
        return BlakeWorks(tmp_path)
    
    def test_feature(self, fixture):
        result = fixture.some_method()
        assert result is not None
```
