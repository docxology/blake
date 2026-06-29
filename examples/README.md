# Blake Examples

Example scripts demonstrating Blake package usage.

## Basic Usage

```bash
uv run python examples/basic_usage.py
```

```python
from blake import BlakeCorpus

blake = BlakeCorpus()
works = await blake.download_all()
```

## Examples

| Script | Description |
|--------|-------------|
| `basic_usage.py` | Core API demonstration |
| `advanced_analysis.py` | NLP and visual analysis |
| `download_all.py` | Download all works |
| `blake_interactive.py` | Terminal interface |
| `project_b_demo.py` | Visualization demo |

## Interactive Mode

```bash
# Launch interactive terminal
uv run python examples/blake_interactive.py
```

Features:
- Work browsing
- Download management
- Analysis tools
- Search interface
- Export options
