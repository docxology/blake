# export Module

Export functionality and REST API for Blake data.

## Components

| File | Class | Purpose |
|------|-------|---------|
| `exporter.py` | `BlakeExporter` | Main export orchestrator |
| `formats.py` | Format handlers | JSON, CSV, PDF, HTML, Markdown support |
| `api.py` | FastAPI app | REST API endpoints |

## Export Formats

| Format | Extension | Description |
|--------|-----------|-------------|
| JSON | `.json` | Full structured export with metadata and analysis |
| CSV | `.csv` | Tabular metadata export for spreadsheets |
| PDF | `.pdf` | Formatted document with ReportLab |
| HTML | `.html` | Styled web reports with CSS |
| Markdown | `.md` | Documentation-friendly output |

## Usage

```python
from blake.export import get_exporter

exporter = get_exporter('html')
await exporter.export_works(works, output_dir, config)
```

## API Endpoints

- `GET /works` - List all works
- `GET /works/{id}` - Get specific work
- `GET /search` - Search works
- `GET /export` - Export data
