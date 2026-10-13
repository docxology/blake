# Developer Guide

## Table of Contents

1. [Development Setup](#development-setup)
2. [Project Structure](#project-structure)
3. [Code Standards](#code-standards)
4. [Testing](#testing)
5. [Contributing](#contributing)
6. [Architecture Overview](#architecture-overview)
7. [Extending the Package](#extending-the-package)
8. [Performance Optimization](#performance-optimization)

## Development Setup

### Prerequisites

- Python 3.9 or higher
- UV package manager (recommended) or pip
- Git
- Code editor with Python support

### Clone and Setup

```bash
# Clone the repository
git clone https://github.com/docxology/blake.git
cd blake

# Install with UV (recommended)
uv sync --all-extras
uv sync --extra dev --extra api

# Or with pip
pip install -e ".[dev,gui,api]"
```

### Development Environment

```bash
# Install pre-commit hooks
pre-commit install

# Run tests
uv run pytest tests/ -q
uv run pytest tests/ -q -m "not slow and not integration"
uv run pytest tests/test_cli.py tests/test_corpus.py tests/test_public_release.py tests/test_export.py tests/test_manuscript_tools.py -q

# Run linting
uv run black blake tests
uv run isort blake tests
uv run flake8 blake tests

# Run type checking
uv run mypy blake
```

Default `uv sync` is enough for the offline quick corpus workflow. API and GUI serving dependencies are optional extras; use `--extra api` for FastAPI routes and `--extra gui` for Streamlit/Gradio. Live acquisition and integration tests remain opt-in because endpoint status and source terms can drift. Manuscript projection tests build a deterministic temporary fixture corpus and mark its manifest as fixture evidence; they do not verify a published acquisition run. Authored manuscript sources and legal claims are under `docs/manuscript/`, while `output/manuscript/` is generated render output.

## Project Structure

```
blake/
├── blake/                    # Main package
│   ├── __init__.py          # Package initialization
│   ├── corpus/              # BlakeCorpus pipeline, manifests, source registry
│   ├── core.py              # BlakeCorpus compatibility shim
│   ├── models.py            # Data models and schemas
│   ├── exceptions.py        # Custom exceptions
│   ├── cli.py              # Command-line interface
│   ├── downloader/         # Download management
│   │   ├── __init__.py
│   │   ├── downloader.py   # Main downloader
│   │   ├── scraper.py      # Web scraping utilities
│   │   ├── sources.py      # Source-specific implementations
│   │   └── manager.py      # Download orchestration
│   ├── metadata/           # Metadata management
│   │   ├── __init__.py
│   │   ├── database.py     # Database operations
│   │   ├── processor.py    # Metadata processing
│   │   ├── search.py       # Search functionality
│   │   └── manager.py      # Metadata orchestration
│   ├── analysis/           # Analysis pipeline
│   │   ├── __init__.py
│   │   ├── analyzer.py     # Main analyzer
│   │   ├── text_analysis.py # Text analysis
│   │   ├── visual_analysis.py # Visual analysis
│   │   └── cross_analysis.py # Cross-analysis
│   ├── gui/                # User interface
│   │   ├── __init__.py
│   │   ├── gui.py          # Streamlit GUI
│   │   └── components.py   # Reusable components
│   └── export/             # Export functionality
│       ├── __init__.py
│       ├── exporter.py     # Export logic
│       ├── formats.py      # Format implementations
│       └── api.py          # REST API
├── tests/                   # Test suite
│   ├── __init__.py
│   ├── conftest.py         # Test configuration
│   ├── test_models.py      # Model tests
│   ├── test_corpus.py      # Corpus workflow tests
│   ├── test_core.py        # BlakeCorpus compatibility tests
│   ├── test_downloader.py  # Downloader tests
│   ├── test_analysis.py    # Analysis tests
│   └── test_download_manager.py # Download manager tests
├── examples/               # Example scripts
├── docs/                   # Documentation
├── pyproject.toml         # Project configuration
├── pytest.ini            # Test configuration
└── README.md              # Project overview
```

## Code Standards

### Python Style

We follow PEP 8 with some modifications:

- **Line length**: 88 characters (Black default)
- **Import sorting**: isort with Black profile
- **Type hints**: Required for all public functions
- **Docstrings**: Google style for all public functions

### Code Formatting

```bash
# Format code
uv run black blake tests

# Sort imports
uv run isort blake tests

# Check formatting
uv run black --check blake tests
uv run isort --check-only blake tests
```

### Type Hints

All public functions must have type hints:

```python
from typing import List, Optional, Dict, Any
from pathlib import Path

async def download_work(
    self, 
    work_id: str, 
    force: bool = False
) -> Optional[BlakeWork]:
    """
    Download a specific work by ID.
    
    Args:
        work_id: Unique identifier for the work
        force: Force re-download even if work exists
        
    Returns:
        Downloaded work or None if not found
    """
    # Implementation here
```

### Docstrings

Use Google-style docstrings:

```python
def analyze_work(
    self, 
    work: BlakeWork, 
    analysis_types: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Perform comprehensive analysis on a work.
    
    Args:
        work: BlakeWork to analyze
        analysis_types: Types of analysis to perform. 
                       If None, performs all analyses
                       
    Returns:
        Dictionary of analysis results
        
    Raises:
        AnalysisError: If analysis fails
        
    Example:
        >>> analyzer = BlakeAnalyzer(Path("./data"))
        >>> results = await analyzer.analyze_work(work)
        >>> print(results['text_analysis'])
    """
```

### Error Handling

Use custom exceptions and proper error handling:

```python
from blake.exceptions import BlakeError, DownloadError

async def download_file(self, url: str, file_path: Path) -> bool:
    try:
        # Download logic here
        return True
    except aiohttp.ClientError as e:
        raise DownloadError(f"Network error downloading {url}: {e}")
    except Exception as e:
        raise BlakeError(f"Unexpected error: {e}")
```

## Testing

### Running Tests

```bash
# Run all tests
uv run pytest tests/ -q

# Run with coverage
uv run pytest tests/ --cov=blake --cov-report=html

# Run specific test file
uv run pytest tests/test_models.py

# Run specific test
uv run pytest tests/test_models.py::TestBlakeMetadata::test_metadata_creation

# Run with verbose output
uv run pytest tests/ -v
```

### Corpus Verification Gates

```bash
uv run pytest tests/ -q
uv run pytest tests/ -q -m "not slow and not integration"
uv run blake corpus run --quick --output-dir analysis_output
uv run blake corpus run --skip-download --output-dir analysis_output --fixture-mode never --viz-profile core --format json --archive-scope archive-inventory --image-mode archive-all --image-dpi 300 --max-images-per-work none
```

Default tests and quick corpus runs must not require live external network access.

### Test Structure

Tests are organized by module:

- `test_models.py` - Data model tests
- `test_corpus.py` - Corpus pipeline, manifest, source registry, and quick-run tests
- `test_core.py` - BlakeCorpus compatibility tests
- `test_downloader.py` - Download system tests
- `test_analysis.py` - Analysis pipeline tests
- `test_download_manager.py` - Download orchestration tests

### Writing Tests

```python
import pytest
from unittest.mock import Mock, AsyncMock, patch
from blake.models import BlakeWork, BlakeMetadata, WorkType, SourceType

class TestBlakeAnalyzer:
    """Test cases for BlakeAnalyzer."""
    
    @pytest.fixture
    def analyzer(self, tmp_path):
        """Create analyzer instance for testing."""
        return BlakeAnalyzer(tmp_path)
    
    @pytest.fixture
    def sample_work(self):
        """Create sample work for testing."""
        metadata = BlakeMetadata(
            id="test_work",
            title="Test Work",
            work_type=WorkType.POEM,
            source=SourceType.PROJECT_GUTENBERG
        )
        return BlakeWork(
            id="test_work",
            metadata=metadata,
            text_content="Test content"
        )
    
    @pytest.mark.asyncio
    async def test_analyze_work_text_only(self, analyzer, sample_work):
        """Test analyzing a work with only text."""
        with patch.object(analyzer.text_analyzer, 'analyze_work', 
                         return_value={'sentiment': 'positive'}):
            results = await analyzer.analyze_work(sample_work)
            
            assert 'text_analysis' in results
            assert results['text_analysis']['sentiment'] == 'positive'
    
    def test_get_analysis_summary(self, analyzer):
        """Test getting analysis summary."""
        works = [self.sample_work()]
        summary = analyzer.get_analysis_summary(works)
        
        assert summary['total_works'] == 1
        assert summary['analyzed_works'] == 0  # Not processed yet
```

### Test Fixtures

Use `conftest.py` for shared fixtures:

```python
import pytest
from pathlib import Path
from blake import BlakeCorpus

@pytest.fixture
def data_dir(tmp_path):
    """Create temporary data directory."""
    return tmp_path / "blake_data"

@pytest.fixture
def corpus(data_dir):
    """Create BlakeCorpus instance."""
    return BlakeCorpus(data_dir)

@pytest.fixture
def sample_metadata():
    """Create sample metadata."""
    return BlakeMetadata(
        id="test_work",
        title="Test Work",
        work_type=WorkType.POEM,
        source=SourceType.PROJECT_GUTENBERG
    )
```

### Mocking

Use mocks for external dependencies:

```python
from unittest.mock import Mock, AsyncMock, patch

# Mock async functions
mock_download = AsyncMock(return_value=BlakeWork(...))

# Mock external services
with patch('aiohttp.ClientSession') as mock_session:
    mock_response = AsyncMock()
    mock_response.text = AsyncMock(return_value="<html>...</html>")
    mock_session.return_value.__aenter__.return_value.get.return_value = mock_response
```

## Contributing

### Workflow

1. **Fork the repository**
2. **Create a feature branch**: `git checkout -b feature/your-feature-name`
3. **Make your changes**
4. **Add tests** for new functionality
5. **Run tests**: `uv run python -m pytest`
6. **Format code**: `uv run black blake tests && uv run isort blake tests`
7. **Commit changes**: `git commit -m "Add feature: description"`
8. **Push to fork**: `git push origin feature/your-feature-name`
9. **Create pull request**

### Pull Request Guidelines

- **Clear title**: Describe what the PR does
- **Detailed description**: Explain changes and motivation
- **Tests**: Include tests for new functionality
- **Documentation**: Update docs if needed
- **Breaking changes**: Clearly mark any breaking changes

### Code Review Process

1. **Automated checks**: CI runs tests, linting, and type checking
2. **Manual review**: At least one maintainer reviews the code
3. **Feedback**: Address any requested changes
4. **Merge**: Once approved, maintainer merges the PR

## Architecture Overview

### Core Components

#### BlakeCorpus (corpus/)

- Primary corpus orchestrator
- Coordinates discovery, acquisition, metadata, analysis, export, and reports
- Writes reproducible manifests and run summaries

#### BlakeCorpus (core.py)

- Deprecated compatibility shim over `BlakeCorpus`
- Keeps old imports working for one release

#### Download System (downloader/)

- Asynchronous download management
- Source-specific implementations
- Retry logic and error handling

#### Metadata System (metadata/)

- Database operations
- Search and filtering
- Metadata processing

#### Analysis System (analysis/)

- Text, visual, and cross-analysis
- Batch processing
- Result caching

#### GUI System (gui/)

- Streamlit-based interface
- Interactive exploration
- Visualization components

#### Export System (export/)

- Multiple format support
- REST API
- Programmatic access

### Data Flow

```
User Request → BlakeCorpus → SourceRegistry → SourceProvider
                    ↓
              Metadata Manager → CorpusManifest
                    ↓
              Analyzer → AnalysisResult Records
                    ↓
              Export/Reports → analysis_output/
```

### Async Architecture

The package uses asyncio for I/O operations:

```python
# All I/O operations are async
async def download_all(self) -> List[BlakeWork]:
    tasks = []
    for source in self.sources:
        task = asyncio.create_task(source.download_works())
        tasks.append(task)
    
    results = await asyncio.gather(*tasks)
    return [work for result in results for work in result]
```

## Extending the Package

### Adding New Sources

1. **Create source class**:

```python
from blake.downloader.sources import BaseSource
from blake.models import SourceType

class NewSource(BaseSource):
    def __init__(self, data_dir: Path):
        super().__init__(data_dir, SourceType.NEW_SOURCE)
    
    async def get_work_list(self) -> List[Dict[str, Any]]:
        # Implement work discovery
        pass
    
    async def download_work(self, work_info: Dict[str, Any]) -> Optional[BlakeWork]:
        # Implement work download
        pass
```

1. **Register source**:

```python
# In downloader.py
self.sources[SourceType.NEW_SOURCE] = NewSource(self.data_dir)
```

### Adding New Analysis Types

1. **Create analyzer class**:

```python
from blake.analysis.analyzer import BlakeAnalyzer

class CustomAnalyzer:
    async def analyze_work(self, work: BlakeWork) -> Dict[str, Any]:
        # Implement custom analysis
        return {"custom_metric": value}
```

1. **Integrate with main analyzer**:

```python
# In analyzer.py
class BlakeAnalyzer:
    def __init__(self, data_dir: Path):
        # ... existing code ...
        self.custom_analyzer = CustomAnalyzer()
    
    async def analyze_work(self, work: BlakeWork, analysis_types: Optional[List[str]] = None):
        # ... existing code ...
        if 'custom' in analysis_types:
            custom_results = await self.custom_analyzer.analyze_work(work)
            results['custom_analysis'] = custom_results
```

### Adding New Export Formats

1. **Create format handler**:

```python
from blake.export.formats import BaseFormat

class CustomFormat(BaseFormat):
    def export(self, works: List[BlakeWork], output_path: Path) -> Path:
        # Implement custom export logic
        pass
```

1. **Register format**:

```python
# In exporter.py
self.formats['custom'] = CustomFormat()
```

## Performance Optimization

### Async Best Practices

```python
# Use asyncio.gather for parallel operations
async def download_multiple_works(self, work_ids: List[str]) -> List[BlakeWork]:
    tasks = [self.download_work(work_id) for work_id in work_ids]
    return await asyncio.gather(*tasks)

# Use semaphores to limit concurrency
async def process_works(self, works: List[BlakeWork]):
    semaphore = asyncio.Semaphore(5)  # Max 5 concurrent
    
    async def process_work(work):
        async with semaphore:
            return await self.analyze_work(work)
    
    tasks = [process_work(work) for work in works]
    return await asyncio.gather(*tasks)
```

### Memory Management

```python
# Clear caches regularly
def clear_cache(self):
    self._works_cache.clear()
    gc.collect()

# Use generators for large datasets
def iterate_works(self):
    for work_id in self.get_all_work_ids():
        yield self.get_work(work_id)
```

### Database Optimization

```python
# Use batch operations
async def save_multiple_works(self, works: List[BlakeWork]):
    async with self.db.transaction():
        for work in works:
            await self.save_work(work)

# Use indexes for common queries
CREATE INDEX idx_work_type ON works(work_type);
CREATE INDEX idx_source ON works(source);
CREATE INDEX idx_creation_date ON works(creation_date);
```

### Caching

```python
from functools import lru_cache
import asyncio

class CachedAnalyzer:
    @lru_cache(maxsize=100)
    def _cached_analysis(self, work_id: str, analysis_type: str):
        # Cache expensive operations
        pass
    
    async def analyze_work(self, work: BlakeWork):
        # Use cache when possible
        cache_key = f"{work.id}_text"
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        result = await self._perform_analysis(work)
        self._cache[cache_key] = result
        return result
```

## Debugging

### Logging

```python
import logging

logger = logging.getLogger(__name__)

async def download_work(self, work_id: str):
    logger.info(f"Starting download for work: {work_id}")
    try:
        # Download logic
        logger.info(f"Successfully downloaded work: {work_id}")
    except Exception as e:
        logger.error(f"Failed to download work {work_id}: {e}")
        raise
```

### Debug Mode

```python
# Enable debug logging
import logging
logging.basicConfig(level=logging.DEBUG)

# Use debug mode in tests
@pytest.mark.asyncio
async def test_download_debug():
    with patch('logging.getLogger') as mock_logger:
        # Test with debug logging
        pass
```

### Profiling

```python
import cProfile
import pstats

# Profile specific functions
profiler = cProfile.Profile()
profiler.enable()

# Run your code
await blake.download_all()

profiler.disable()
stats = pstats.Stats(profiler)
stats.sort_stats('cumulative').print_stats(10)
```
