# Blake Package

Core Python package for William Blake's works analysis platform.

## Module Structure

| Module | Purpose |
|--------|---------|
| `core.py` | `BlakeWorks` orchestrator class |
| `models.py` | Pydantic data models |
| `cli.py` | Click-based CLI commands |
| `exceptions.py` | Custom exception classes |
| `interactive_orchestrator.py` | Terminal UI orchestrator |

## Submodules

| Submodule | Description |
|-----------|-------------|
| `analysis/` | Text/visual analysis with NLTK, spaCy, transformers |
| `downloader/` | Multi-source downloaders, verifier subpackage |
| `export/` | JSON, CSV, PDF, HTML, Markdown export + FastAPI |
| `gui/` | Streamlit-based exploration interface |
| `metadata/` | SQLite database and search functionality |
| `utils/` | Logging, error handling, performance tracking |
| `viz/` | Visualization system with dashboards and renderers |

## Quick Start

```python
from blake import BlakeWorks

blake = BlakeWorks()
works = await blake.download_all()
analysis = await blake.analyze_all()
```

## Entry Points

- `blake.cli:main` - CLI entrypoint
- `blake.BlakeWorks` - Programmatic API
- `blake corpus run` - Target-aware corpus pipeline orchestrator
- `run_all.py` - Compatibility wrapper for older local workflows
