# downloader Module

Multi-source data acquisition for Blake's works.

## Components

| File | Purpose |
|------|---------|
| `downloader.py` | `BlakeDownloader` - Main download orchestrator |
| `sources.py` | Source implementations (Blake Archive, Gutenberg, etc.) |
| `scraper.py` | Web scraping utilities |
| `manager.py` | Download queue management |
| `api_sources.py` | API-based downloaders |
| `museum_adapters.py` | Museum collection adapters |
| `system_monitor.py` | Download health monitoring |

## Submodules

### verifier/

Modular quality assurance system:

- `models.py` - VerificationResult, QualityLevel, QualityReport
- `integrity.py` - File checksum and existence checks
- `content.py` - Text and image quality assessment
- `metadata.py` - Metadata completeness and accuracy
- `quality_assurance.py` - Orchestrating QualityAssurance class

## Source Adapters

- `BlakeArchiveSource` - Blake Archive (blakearchive.org)
- `ProjectGutenbergSource` - Project Gutenberg texts
- `InternetArchiveSource` - Internet Archive scans
- `BritishMuseumAdapter` - British Museum API
- `TateAdapter` - Tate collection

## Key Patterns

- Async downloads with retry logic
- Rate limiting per source
- Checksum verification
- Incremental sync (skip existing)
