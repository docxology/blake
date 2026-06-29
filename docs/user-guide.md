# User Guide

## Table of Contents

1. [Getting Started](#getting-started)
2. [Basic Usage](#basic-usage)
3. [Data Management](#data-management)
4. [Analysis Features](#analysis-features)
5. [Search and Exploration](#search-and-exploration)
6. [Export and Sharing](#export-and-sharing)
7. [Advanced Configuration](#advanced-configuration)
8. [Troubleshooting](#troubleshooting)

## Getting Started

### Installation

The Blake package can be installed using UV (recommended) or pip:

```bash
# Using UV (recommended)
uv add blake

# Using pip
pip install blake
```

The core install supports the corpus workflow and local artifact generation.
Install `blake[api]` for FastAPI serving surfaces and `blake[gui]` for
Streamlit/Gradio exploration.

### First Steps

1. **Run the corpus pipeline:**
```bash
uv run blake corpus run --quick --output-dir analysis_output
```

2. **Import the package:**
```python
from blake import BlakeCorpus, CorpusConfig
import asyncio
```

3. **Initialize your workspace:**
```python
corpus = BlakeCorpus("blake_data", output_dir="analysis_output")
```

4. **Run a reproducible workflow:**
```python
async def main():
    summary = await corpus.run(CorpusConfig(quick=True))
    print(summary.status)

asyncio.run(main())
```

5. **Start exploring:**
```python
corpus.explore()
```

## Basic Usage

### Downloading Works

The recommended entry point is the corpus workflow:

```bash
blake corpus run --quick --output-dir analysis_output
blake corpus run --skip-download --output-dir analysis_output --fixture-mode never --viz-profile core --format json --archive-scope archive-inventory --image-mode archive-all --image-dpi 300 --max-images-per-work none
blake corpus run --format json --format csv --format markdown
blake corpus status --coverage
blake corpus visualize --profile core
```

Quick mode uses the local cache and does not require network access. If the cache is empty, it seeds a small fixture corpus so analysis, visualization, export, and report artifacts are non-empty. Full runs perform live acquisition through registered providers.

The canonical manuscript/regression rerun uses `--skip-download` to reuse `blake_data/` while regenerating metadata, analysis, visualizations, exports, and reports. It reports acquisition as reused local corpus and analysis as generated/completed when the local analyzer runs. `archive-all` records local image-depth evidence; it is not a permission statement for public redistribution.

Public-release preflight and package commands prepare local review artifacts,
metadata, checksums, and release-safe files. They do not publish, tag, deposit,
or make rights-gated source files redistributable.

### Understanding Corpus Coverage

`corpus_manifest.json` compares local works against the canonical Blake target ledger. Coverage is honest by default:

- `present`: the local work has the expected text/image modality
- `partial`: a local work exists but text or image evidence is missing
- `missing`: no matching local work or discovered source record exists
- `duplicate`: multiple local works match one target entry
- `unverified`: a source record was discovered but not saved locally

Fixture quick runs are labeled with `fixture_mode: true`; they prove the pipeline and visualization surfaces, not a complete Blake corpus.

#### Fetch Provider-Discovered Records
```python
works = await corpus.download_all()

works = await corpus.download_all(force=True)
```

#### Download Specific Works
```python
work = await corpus.download_work("21160")
if work:
    print(f"Downloaded: {work.metadata.title}")
```

#### Check What's Available
```python
all_works = await corpus.get_all_works()
print(f"You have {len(all_works)} works")

stats = await corpus.get_statistics()
print(f"Work types: {stats['work_types']}")
print(f"Sources: {stats['sources']}")
```

### Working with Individual Works

#### Access Work Information
```python
work = await corpus.get_work("21160")
if work:
    print(f"Title: {work.metadata.title}")
    print(f"Type: {work.metadata.work_type}")
    print(f"Source: {work.metadata.source}")
    print(f"Created: {work.metadata.creation_date}")
    print(f"Themes: {work.metadata.themes}")
```

#### Read Text Content
```python
if work.text_content:
    print(f"Text length: {len(work.text_content)} characters")
    print("First 200 characters:")
    print(work.text_content[:200])
```

#### Access Images
```python
if work.images:
    print(f"Number of images: {len(work.images)}")
    for image in work.images:
        print(f"Image {image.id}: {image.width}x{image.height}")
        print(f"File: {image.file_path}")
```

## Data Management

### Understanding the Data Structure

The Blake package organizes data in a structured directory tree:

```
analysis_output/
├── pipeline_summary.json
├── corpus_manifest.json
├── analysis/
├── visualizations/
│   ├── visualization_summary.json
│   ├── target_coverage_matrix.json
│   ├── target_coverage_matrix.png
│   └── corpus_workbench.html
├── exports/
└── reports/

blake_data/
├── texts/
├── images/
├── metadata/
└── analysis/
```

### Managing Your Collection

#### View Collection Statistics
```python
stats = await corpus.get_statistics()
print("Collection Overview:")
print(f"Total works: {stats['total_works']}")
print(f"Work types: {stats['work_types']}")
print(f"Sources: {stats['sources']}")
print(f"Date range: {stats['date_range']}")
print(f"Total images: {stats['total_images']}")
print(f"Processed works: {stats['processed_works']}")
```

#### Search Your Collection
```python
# Search by content
results = await corpus.search_works("innocence")
print(f"Found {len(results)} works containing 'innocence'")

# Search with filters
poems = await corpus.search_works("tiger", {"work_type": "poem"})
gutenberg_works = await corpus.search_works("", {"source": "project_gutenberg"})
```

#### Clear Cache
```python
# Clear the works cache (useful for memory management)
await corpus.clear_cache()
```

## Analysis Features

### Running Analysis

#### Analyze All Works
```python
# Run analysis on all locally acquired works
analysis_results = await corpus.analyze_all()
print(f"Analyzed {len(analysis_results)} works")
```

#### Analyze Specific Work
```python
# Analyze a specific work
work_analysis = await corpus.analyze_work("21160")
print("Analysis results:")
for analysis_type, results in work_analysis.items():
    print(f"{analysis_type}: {type(results).__name__}")
```

#### Analyze Specific Types
```python
# Text analysis only
text_analysis = await corpus.analyze_work("21160", ["text"])

# Visual analysis only
visual_analysis = await corpus.analyze_work("21160", ["visual"])

# Cross-analysis only
cross_analysis = await corpus.analyze_work("21160", ["cross"])
```

### Understanding Analysis Results

#### Text Analysis
```python
work = await corpus.get_work("21160")
if work.text_analysis:
    print("Text Analysis Results:")
    
    # Basic statistics
    if 'basic_stats' in work.text_analysis:
        stats = work.text_analysis['basic_stats']
        print(f"Word count: {stats.get('word_count', 'N/A')}")
        print(f"Character count: {stats.get('char_count', 'N/A')}")
        print(f"Sentence count: {stats.get('sentence_count', 'N/A')}")
    
    # Sentiment analysis
    if 'sentiment' in work.text_analysis:
        sentiment = work.text_analysis['sentiment']
        print(f"Sentiment: {sentiment.get('overall', 'N/A')}")
        print(f"Positive: {sentiment.get('positive', 0)}")
        print(f"Negative: {sentiment.get('negative', 0)}")
    
    # Topics/themes
    if 'topics' in work.text_analysis:
        topics = work.text_analysis['topics']
        print(f"Topics: {topics}")
```

#### Visual Analysis
```python
if work.visual_analysis:
    print("Visual Analysis Results:")
    for image_id, analysis in work.visual_analysis.items():
        print(f"Image {image_id}:")
        if 'colors' in analysis:
            print(f"  Dominant colors: {analysis['colors']}")
        if 'composition' in analysis:
            print(f"  Composition: {analysis['composition']}")
```

### Batch Analysis

#### Analyze Multiple Works
```python
# Get all works
works = await corpus.get_all_works()

# Analyze in batches
batch_size = 5
for i in range(0, len(works), batch_size):
    batch = works[i:i + batch_size]
    print(f"Analyzing batch {i//batch_size + 1}...")
    
    # This would be done internally by analyze_all()
    # but you can also process works individually
    for work in batch:
        if not work.fully_processed:
            await corpus.analyze_work(work.id)
```

## Search and Exploration

### Basic Search

#### Content Search
```python
# Search for specific words or phrases
results = await corpus.search_works("tiger")
results = await corpus.search_works("innocence and experience")
results = await corpus.search_works("William Blake")
```

#### Filtered Search
```python
# Search with filters
filters = {
    "work_type": "poem",
    "source": "project_gutenberg",
    "has_images": True
}
results = await corpus.search_works("", filters)
```

### Advanced Search Patterns

#### Search by Themes
```python
# Search for works with specific themes
themes = ["innocence", "experience", "nature", "religion"]
for theme in themes:
    results = await corpus.search_works(theme)
    print(f"'{theme}': {len(results)} works")
```

#### Search by Date Range
```python
# Get all works and filter by date
all_works = await corpus.get_all_works()
from datetime import datetime

# Filter works by creation date (if available)
dated_works = [w for w in all_works if w.metadata.creation_date]
print(f"Works with dates: {len(dated_works)}")
```

### Using the Web Interface

#### Launch the GUI
```python
# Start the web interface
corpus.explore()

# Or specify host and port
corpus.explore(host="0.0.0.0", port=8501)
```

The web interface provides:
- **Work Browser**: Browse works in the local collection
- **Search Interface**: Advanced search with filters
- **Analysis Dashboard**: View analysis results and visualizations
- **Export Tools**: Download works in various formats

## Export and Sharing

### Export Individual Works

#### Export to JSON
```python
from blake.models import ExportConfig
from pathlib import Path

# Export specific work
work = await corpus.get_work("21160")
config = ExportConfig(
    format="json",
    output_dir=Path("./exports"),
    include_images=True,
    include_analysis=True
)
output_path = await corpus.export_works([work], config)
print(f"Exported to: {output_path}")
```

#### Export to CSV
```python
config = ExportConfig(
    format="csv",
    output_dir=Path("./exports"),
    include_analysis=True
)
output_path = await corpus.export_works([work], config)
```

### Export Collections

#### Export All Works
```python
all_works = await corpus.get_all_works()
config = ExportConfig(
    format="json",
    output_dir=Path("./exports"),
    include_images=True,
    include_analysis=True
)
output_path = await corpus.export_works(all_works, config)
```

#### Export Filtered Works
```python
# Export only poems
poems = await corpus.search_works("", {"work_type": "poem"})
config = ExportConfig(format="json", output_dir=Path("./exports"))
output_path = await corpus.export_works(poems, config)
```

### Export Formats

#### JSON Export
- Complete work data including metadata and analysis
- Machine-readable format
- Preserves all relationships and structure

#### CSV Export
- Tabular format for spreadsheet analysis
- One row per work
- Analysis results in separate columns

#### PDF Export
- Human-readable reports
- Includes visualizations
- Suitable for sharing and presentation

## Advanced Configuration

### Custom Data Directory

```python
from pathlib import Path

# Use custom directory
corpus = BlakeCorpus(Path("/path/to/my/blake/data"))
```

### Environment Variables

Set these environment variables for global configuration:

```bash
export BLAKE_DATA_DIR="/path/to/data"
export BLAKE_MAX_CONCURRENT_DOWNLOADS=5
export BLAKE_DOWNLOAD_TIMEOUT=60
```

### Configuration File

Create `blake_config.yaml` in your data directory:

```yaml
download:
  max_concurrent: 5
  timeout: 60
  retry_attempts: 3

analysis:
  text_analysis: true
  visual_analysis: true
  cross_analysis: true

export:
  default_format: "json"
  include_images: true
```

### Custom Analysis

```python
# You can extend the analysis by accessing the analyzer directly
analyzer = corpus.analyzer

# Run custom analysis
custom_results = await analyzer.analyze_work(work, ["text"])
```

## Troubleshooting

### Common Issues

#### Download Failures
```python
# Check if works were downloaded
works = await corpus.get_all_works()
if not works:
    print("No works found. Check your internet connection and try again.")
    
# Check specific work
work = await corpus.get_work("21160")
if not work:
    print("Work not found. It may not be available from the source.")
```

#### Analysis Errors
```python
# Check if work is processed
work = await corpus.get_work("21160")
if not work.fully_processed:
    print("Work not fully processed. Check processing_errors:")
    print(work.processing_errors)
```

#### Memory Issues
```python
# Clear cache if running out of memory
await corpus.clear_cache()

# Process works in smaller batches
works = await corpus.get_all_works()
batch_size = 3
for i in range(0, len(works), batch_size):
    batch = works[i:i + batch_size]
    await corpus.analyze_all()
    await corpus.clear_cache()
```

### Getting Help

1. **Check the logs**: Look in your data directory's `logs/` folder
2. **Run diagnostics**: Use the verification script
3. **Check GitHub Issues**: Look for similar problems
4. **Ask for help**: Create a new issue with details

### Performance Tips

1. **Use async/await**: Always use async functions for I/O operations
2. **Batch operations**: Process multiple works together when possible
3. **Clear cache**: Regularly clear the works cache to free memory
4. **Monitor disk space**: Ensure you have enough space for downloads
5. **Use filters**: Use search filters to limit results when possible

### Debugging

```python
import logging

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)

# Check work details
work = await corpus.get_work("21160")
print(f"Work ID: {work.id}")
print(f"Fully processed: {work.fully_processed}")
print(f"Processing errors: {work.processing_errors}")
print(f"Text content length: {len(work.text_content) if work.text_content else 0}")
print(f"Number of images: {len(work.images)}")
```
