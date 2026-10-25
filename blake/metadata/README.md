# Blake Metadata Module

Metadata management with SQLite storage and search functionality.

## Features

- **SQLite Storage**: Persistent metadata database
- **Full-Text Search**: Search titles, descriptions, content
- **Filtering**: Work type, source, date, tags
- **Relationships**: Track work-image associations

## Usage

```python
from blake.metadata import MetadataManager

manager = MetadataManager(data_dir="./blake_data")

# Save work
manager.save_work(work)

# Load work
work = manager.load_work("work_id")

# Search
results = manager.search_works(
    query="innocence",
    work_type="poem",
    limit=10
)
```

## Classes

| Class | Description |
|-------|-------------|
| `MetadataManager` | Main orchestrator |
| `BlakeDatabase` | SQLite operations |
| `MetadataProcessor` | Extraction logic |
| `SearchEngine` | Query processing |
