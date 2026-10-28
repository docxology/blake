# Quick Start Guide

Choose the methods-only install or the full corpus pipeline. The following
0.3.0 candidate installation commands await clean installed-package qualification.

## Installation

### Using UV (Recommended)

```bash
# Methods-only dependencies
uv add blake

# Acquisition, NLP, vision and corpus pipeline
uv add "blake[full]"

# Install with specific extras
uv add "blake[full,gui,api,dev]"
```

### Using Pip

```bash
# Methods-only installation
pip install blake

# With all extras
pip install "blake[full,gui,api,dev]"
```

### From Source

```bash
git clone https://github.com/docxology/blake.git
cd blake
uv sync --extra full --extra dev
# Add --extra gui or --extra api for those surfaces; retain --extra full.
```

For methods-only work in a source checkout, use `uv sync`. See
[shared methods](shared-methods.md) for explicit search profiles and a synthetic
example, and [applications](applications.md) for private portable bundles.
The corpus, analysis and interactive examples below require `full`; the web
interface additionally requires `gui`.

## Basic Usage

### 1. Run the Corpus Workflow

```python
import asyncio
from blake import BlakeCorpus, CorpusConfig
from pathlib import Path

async def main():
    corpus = BlakeCorpus(Path("./blake_data"), output_dir=Path("./analysis_output"))
    summary = await corpus.run(CorpusConfig(quick=True))
    print(summary.status)
    print(await corpus.coverage())

asyncio.run(main())
```

Quick mode is offline. When `blake_data/` is empty, it seeds a small fixture corpus so the generated analysis, visualization, export, and report artifacts are non-empty. The manifest marks this with `fixture_mode: true`; use `blake corpus status --coverage` to inspect remaining canonical target gaps.

### 2. Explore Interactively

```python
from blake import BlakeCorpus

corpus = BlakeCorpus()
corpus.explore()
```

The web interface provides:

- **Work Browser**: Browse local collection works with filtering
- **Search Interface**: Advanced search capabilities
- **Analysis Dashboard**: View analysis results and visualizations
- **Export Tools**: Download works in various formats

### 3. Search and Analyze

```python
import asyncio
from blake import BlakeCorpus

async def main():
    corpus = BlakeCorpus()
    
    # Search for works by content
    results = await corpus.search_works("innocence")
    print(f"Found {len(results)} works containing 'innocence'")
    
    # Search with filters
    poems = await corpus.search_works("tiger", {"work_type": "poem"})
    print(f"Found {len(poems)} poems containing 'tiger'")
    
    # Analyze a specific work
    if results:
        work = results[0]
        analysis = await corpus.analyze_work(work.id)
        print(f"Analysis completed for {work.metadata.title}")
        
        # Show analysis results
        if 'text_analysis' in analysis:
            print(f"Text analysis: {analysis['text_analysis']}")

asyncio.run(main())
```

### 4. Export Data

```python
import asyncio
from blake import BlakeCorpus
from blake.models import ExportConfig
from pathlib import Path

async def main():
    corpus = BlakeCorpus()
    works = await corpus.get_all_works()
    
    # Export to JSON with analysis
    config = ExportConfig(
        format="json",
        output_dir=Path("./exports"),
        include_analysis=True,
        include_images=True
    )
    
    output_path = await corpus.export_works(config)
    print(f"Exported to: {output_path}")

asyncio.run(main())
```

## End-to-End Local Example

### Quick Workflow Script

```python
import asyncio
from blake import BlakeCorpus, CorpusConfig
from pathlib import Path

async def main():
    print("=== Blake Package Quick Start ===")
    
    corpus = BlakeCorpus(Path("./blake_data"), output_dir=Path("./analysis_output"))
    print("✓ Initialized Blake workspace")

    summary = await corpus.run(CorpusConfig(quick=True))
    print(f"✓ Corpus run: {summary.status}")
    
    # Search for specific content
    print("\n🔎 Searching for 'innocence'...")
    results = await corpus.search_works("innocence")
    print(f"✓ Found {len(results)} works containing 'innocence'")
    for work in results:
        print(f"  - {work.metadata.title}")
    
    # Get collection statistics
    print("\n📊 Collection statistics:")
    stats = await corpus.get_statistics()
    for key, value in stats.items():
        print(f"  {key}: {value}")
    
    # Launch web interface
    print("\n🌐 Launching web interface...")
    print("   Open your browser to http://localhost:8501")
    corpus.explore()

if __name__ == "__main__":
    asyncio.run(main())
```

## Command Line Interface

### Corpus Workflow

```bash
# Offline smoke run; seeds fixtures only if the local cache is empty
blake corpus run --quick --output-dir analysis_output

# Main local regeneration; reuses blake_data/ and reruns analysis
blake corpus run --skip-download --output-dir analysis_output --fixture-mode never --viz-profile core --format json --archive-scope archive-inventory --image-mode archive-all --image-dpi 300 --max-images-per-work none

# Inspect coverage and generated artifact surfaces
blake corpus status --coverage
blake corpus visualize --profile core
blake corpus audit-sources --output-dir analysis_output --archive-scope archive-inventory
blake corpus acquire-evidence --from-audit analysis_output/data/source_audit.json --dry-run
blake corpus private-release-preflight --output-dir analysis_output --data-dir blake_data
blake corpus public-release-preflight --output-dir analysis_output --data-dir blake_data
blake corpus public-release-package --output-dir analysis_output --data-dir blake_data
```

`--skip-download` means acquisition is reused from the existing local corpus; it does not skip analysis. `--image-mode archive-all` is a local evidence-depth setting, not a redistribution permission.

### Acquire and Analyze Works

```bash
# Reuse the local corpus and regenerate analysis
blake corpus run --skip-download --output-dir analysis_output

# Inspect one work's local metadata
blake info --work-id "21160"

# Write JSON exports during the run
blake corpus run --format json
```

### Explore and Search

```bash
# Start the Streamlit interface
blake explore

# Search local metadata
blake search --query "innocence" --work-type poem
```

## Advanced Examples

### Working with Specific Works

```python
async def work_with_specific_works():
    corpus = BlakeCorpus()
    
    # Get a specific work
    work = await corpus.get_work("21160")
    if work:
        print(f"Title: {work.metadata.title}")
        print(f"Text length: {len(work.text_content) if work.text_content else 0} characters")
        print(f"Images: {len(work.images)}")
        print(f"Fully processed: {work.fully_processed}")
        
        # Read text content
        if work.text_content:
            print(f"First 200 characters: {work.text_content[:200]}...")
        
        # Access images
        for image in work.images:
            print(f"Image: {image.id} ({image.width}x{image.height})")

asyncio.run(work_with_specific_works())
```

### Custom Analysis

```python
async def custom_analysis():
    corpus = BlakeCorpus()
    works = await corpus.get_all_works()
    
    # Analyze works with custom settings
    for work in works:
        if work.text_content:
            # Text analysis only
            text_results = await corpus.analyze_work(work.id, ["text"])
            print(f"Text analysis for {work.metadata.title}: {text_results}")
        
        if work.images:
            # Visual analysis only
            visual_results = await corpus.analyze_work(work.id, ["visual"])
            print(f"Visual analysis for {work.metadata.title}: {visual_results}")

asyncio.run(custom_analysis())
```

## Configuration

### Command Line

```bash
blake --data-dir /path/to/your/data --output-dir /path/to/output corpus run --quick
```

### Python

```python
from pathlib import Path

from blake import BlakeCorpus, CorpusConfig

corpus = BlakeCorpus(Path("/path/to/your/data"), output_dir=Path("/path/to/output"))
summary = await corpus.run(CorpusConfig(quick=True))
```

Run settings live in `CorpusConfig` (fixture mode, visualization profile, export
formats, archive scope, image depth) or in the corresponding `blake corpus run`
options. No separate configuration file or environment override is read.

## Troubleshooting

### Common Issues

- **Installation Problems**: Make sure you have Python 3.9+ and try using UV
- **Download Failures**: Check your internet connection and try reducing concurrent downloads
- **Analysis Errors**: Ensure spaCy model is installed: `python -m spacy download en_core_web_sm`
- **GUI Issues**: Try using a different port: `blake.explore(port=8502)`
- **Memory Issues**: Clear cache regularly: `blake.clear_cache()`

### Debug Mode

```python
import logging

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)

# Run with debug information
works = await blake.download_all()
```

### Check System Status

```python
# Check if everything is working
works = await blake.get_all_works()
print(f"Works in collection: {len(works)}")

stats = await blake.get_statistics()
print(f"Collection stats: {stats}")

# Check specific work
work = await blake.get_work("21160")
if work:
    print(f"Work found: {work.metadata.title}")
    print(f"Processing status: {work.fully_processed}")
else:
    print("Work not found")
```

## Web Interface

Start the interactive web interface:

```bash
blake explore
```

Then open your browser to `http://localhost:8501` to:

- **Browse local Blake work records** with advanced filtering
- **Search and filter** by various criteria (content, type, source, date)
- **View analysis results** and interactive visualizations
- **Export data** in multiple formats (JSON, CSV, PDF)
- **Compare works** side-by-side
- **Explore themes** and relationships

## Next Steps

- 📖 [User Guide](user-guide.md) - Comprehensive usage instructions
- 🔧 [API Reference](api-reference.md) - Detailed API documentation
- ⚙️ [Configuration Guide](configuration.md) - Advanced configuration options
- 🛠️ [Troubleshooting Guide](troubleshooting.md) - Common issues and solutions
- 👨‍💻 [Developer Guide](developer-guide.md) - Contributing and extending
