# metadata Module

Metadata management with SQLite storage and search.

## Components

| File | Class | Purpose |
|------|-------|---------|
| `manager.py` | `MetadataManager` | Main orchestrator |
| `database.py` | `BlakeDatabase` | SQLite operations |
| `processor.py` | `MetadataProcessor` | Metadata extraction |
| `search.py` | `SearchEngine` | Query processing |

## Database Schema

- `works` - Work metadata
- `images` - Image references
- `analysis_results` - Cached analysis

## Search Features

- Full-text search on titles, descriptions
- Filter by work type, source, date range
- Tag and theme filtering
