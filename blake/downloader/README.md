# Blake Downloader Module

Multi-source data acquisition for William Blake's works.

## Features

- **Multi-Source**: Blake Archive, Gutenberg, Internet Archive
- **Async Downloads**: High-performance concurrent downloads
- **Retry Logic**: Exponential backoff for failed requests
- **Verification**: Checksum validation for downloads
- **Rate Limiting**: Respectful request patterns

## Usage

```python
from blake.blake_downloader import BlakeDownloader

downloader = BlakeDownloader(data_dir="./blake_data")

# Fetch currently discoverable provider records
works = await downloader.download_all()

# Download specific source
works = await downloader.download_from_source("blake_archive")
```

## Sources

| Source | Content |
|--------|---------|
| Blake Archive | Target-ledger and Archive catalog records |
| Project Gutenberg | Plain text versions |
| Internet Archive | Historical scans |
| British Museum | Curated images |
| Tate | Collection metadata |

## Configuration

- `max_concurrent`: Concurrent download limit (default: 10)
- `retry_attempts`: Retry count (default: 3)
- `timeout`: Request timeout in seconds (default: 30)
