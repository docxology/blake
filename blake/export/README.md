# Blake Export Module

Export and API functionality for William Blake's works data.

## Features

- **Multiple Formats**: JSON, CSV, Parquet, PDF
- **REST API**: FastAPI-based programmatic access
- **Filtering**: Export specific works or collections
- **Compression**: Optional gzip compression

## Usage

```python
from blake.blake_export import BlakeExporter
from blake.models import ExportConfig

exporter = BlakeExporter()

config = ExportConfig(
    format="json",
    output_dir=Path("./export"),
    include_images=True,
    include_analysis=True
)

path = exporter.export_works(works, config)
```

## API Server

```bash
# Start API server
uvicorn blake.blake_export.api:app --reload

# Endpoints
GET /works           # List works
GET /works/{id}      # Get work
GET /search?q=query  # Search
POST /export         # Export data
```

## Export Options

| Option | Description |
|--------|-------------|
| `include_images` | Include image paths |
| `include_analysis` | Include analysis results |
| `compress` | Enable gzip compression |
| `filter_works` | Export specific work IDs |
