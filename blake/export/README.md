# Blake Export Module

Export and API functionality for William Blake's works data.

## Features

- **Multiple Formats**: JSON, CSV, Parquet, PDF
- **REST API**: FastAPI-based programmatic access
- **Filtering**: Export specific works or collections
- **Compression**: Optional gzip compression

## Usage

```python
from blake.export import BlakeExporter
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

`BlakeAPI` builds a FastAPI app over a `BlakeCorpus` instance; serve that app
with any ASGI server:

```python
import uvicorn

from blake import BlakeCorpus
from blake.export.api import BlakeAPI

api = BlakeAPI(BlakeCorpus())
uvicorn.run(api.app, host="127.0.0.1", port=8000)
```

Endpoints:

```
GET  /                                  # Service banner and package version
GET  /works                             # List works
GET  /works/{work_id}                   # Get one work
GET  /works/{work_id}/analysis          # Saved analysis for one work
POST /works/{work_id}/analyze           # Analyze one work
GET  /search?q=query                    # Search works
GET  /statistics                        # Local collection statistics
GET  /export/{work_id}                  # Export one work
GET  /health                            # Health probe
```

## Export Options

| Option | Description |
|--------|-------------|
| `include_images` | Include image paths |
| `include_analysis` | Include analysis results |
| `compress` | Enable gzip compression |
| `filter_works` | Export specific work IDs |
