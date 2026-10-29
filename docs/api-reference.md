# API Reference

## BlakeCorpus Class

The primary orchestrator for reproducible Blake corpus workflows. `BlakeCorpus` is defined in `blake.corpus.pipeline` and re-exported as `blake.BlakeCorpus`.

## Current Evidence Contract

The corpus API is source-governed and target-aware. A run is evaluated through generated artifacts, not through an implicit claim that every Blake source has been mirrored:

- `analysis_output/corpus_manifest.json`: target-ledger coverage, fixture status, and source-backed work records.
- `analysis_output/pipeline_summary.json`: phase status, including reused local acquisition and generated analysis.
- `analysis_output/data/source_discovery_health.json`: per-provider discovery status.
- `analysis_output/data/source_audit.json`: provider health, URL checks, Archive metadata enrichment, and missing-evidence candidates.
- `analysis_output/data/evidence_acquisition_review.json`: reviewer-facing unresolved-target and manual-lead ledger.
- `analysis_output/analysis/analysis_summary.json` and `analysis_output/analysis/analysis_diagnostics.json`: current analysis ledger and corpus-level diagnostics.
- `analysis_output/reports/private_release_preflight.*` and `analysis_output/reports/rights_gate_report.*`: local-only release/readiness checks; they do not publish, tag, deposit, or grant redistribution rights.
- `analysis_output/reports/public_release_preflight.*` and `analysis_output/releases/public_release/` including `public_release_package.json`: public GitHub + Zenodo release staging outputs with bundle metadata, checksums, and citation files.

The core package supports corpus and export workflows. Install `blake[api]` for
FastAPI serving and `blake[gui]` for Streamlit/Gradio exploration; those serving
packages are intentionally not required for the default quick corpus run.

### Constructor

```python
BlakeCorpus(data_dir: Optional[Path] = None, output_dir: Optional[Path] = None)
```

**Parameters:**

- `data_dir` (Optional[Path]): Directory for raw/cache data. Defaults to `./blake_data`
- `output_dir` (Optional[Path]): Directory for pipeline artifacts. Defaults to `./analysis_output`

**Example:**

```python
from blake import BlakeCorpus, CorpusConfig
from pathlib import Path

# Initialize with default directory
corpus = BlakeCorpus()

# Initialize with custom directory
corpus = BlakeCorpus(Path("./my_blake_data"), output_dir=Path("./analysis_output"))

# Run an offline quick workflow
summary = await corpus.run(CorpusConfig(quick=True))
```

### CorpusConfig

```python
CorpusConfig(
    data_dir=Path("blake_data"),
    output_dir=Path("analysis_output"),
    quick=False,
    target_profile="canonical",
    fixture_mode="auto",
    viz_profile="core",
)
```

- `target_profile`: canonical corpus target ledger to measure coverage against
- `fixture_mode`: `auto`, `always`, or `never` for quick-mode fixture seeding
- `viz_profile`: `inventory`, `core`, or `full` visualization artifact generation

### CorpusManifest Coverage Fields

`corpus_manifest.json` includes `target_profile`, `target_version`, `target_total`, `coverage_status`, `coverage_counts`, `target_records`, `fixture_mode`, and `fixture_work_ids`. These fields are the public contract for deciding whether a run is complete, partial, empty, or fixture-backed.

### Core Methods

#### download_all()

```python
async def download_all(force: bool = False) -> List[BlakeWork]
```

Fetch currently discoverable source-provider records through the source-provider download coordinator. For docs/manuscript/release validation, prefer `blake corpus run` so target coverage, source audit, provider health, and rights-gate artifacts are regenerated together.

**Parameters:**

- `force` (bool): Force re-download even if works exist. Default: False

**Returns:**

- `List[BlakeWork]`: List of downloaded BlakeWork objects

**Example:**

```python
# Fetch provider-discovered records through the source-provider coordinator
works = await blake.download_all()

# Force re-download
works = await blake.download_all(force=True)
```

#### download_work()

```python
async def download_work(work_id: str, force: bool = False) -> Optional[BlakeWork]
```

Download a specific work by ID.

**Parameters:**

- `work_id` (str): Unique identifier for the work
- `force` (bool): Force re-download even if work exists. Default: False

**Returns:**

- `Optional[BlakeWork]`: Downloaded work or None if not found

**Example:**

```python
# Download specific work
work = await blake.download_work("21160")
if work:
    print(f"Downloaded: {work.metadata.title}")
```

#### analyze_work()

```python
async def analyze_work(work_id: str, analysis_types: Optional[List[str]] = None) -> Dict[str, Any]
```

Analyze a specific work.

**Parameters:**

- `work_id` (str): Unique identifier for the work
- `analysis_types` (Optional[List[str]]): Types of analysis to perform. Options: ['text', 'visual', 'cross']. Default: None (all types)

**Returns:**

- `Dict[str, Any]`: Analysis results dictionary

**Example:**

```python
# Analyze all types
results = await blake.analyze_work("21160")

# Analyze only text
text_results = await blake.analyze_work("21160", ["text"])
```

#### analyze_all()

```python
async def analyze_all(analysis_types: Optional[List[str]] = None) -> Dict[str, Dict[str, Any]]
```

Analyze every work currently saved in the local corpus cache.

**Parameters:**

- `analysis_types` (Optional[List[str]]): Types of analysis to perform. Default: None (all types)

**Returns:**

- `Dict[str, Dict[str, Any]]`: Dictionary mapping work IDs to analysis results

**Example:**

```python
# Analyze all local works
all_analysis = await blake.analyze_all()

# Analyze only visual content
visual_analysis = await blake.analyze_all(["visual"])
```

#### get_work()

```python
async def get_work(work_id: str) -> Optional[BlakeWork]
```

Retrieve a work by ID from the database.

**Parameters:**

- `work_id` (str): Unique identifier for the work

**Returns:**

- `Optional[BlakeWork]`: Work object or None if not found

**Example:**

```python
work = await blake.get_work("21160")
if work:
    print(f"Title: {work.metadata.title}")
    print(f"Source: {work.metadata.source}")
```

#### get_all_works()

```python
async def get_all_works() -> List[BlakeWork]
```

Retrieve every work currently saved in the local database.

**Returns:**

- `List[BlakeWork]`: List of all BlakeWork objects

**Example:**

```python
works = await blake.get_all_works()
print(f"Total works: {len(works)}")
```

#### search_works()

```python
async def search_works(query: str, filters: Optional[Dict[str, Any]] = None) -> List[BlakeWork]
```

Search works by content and metadata.

**Parameters:**

- `query` (str): Search query string
- `filters` (Optional[Dict[str, Any]]): Additional filters. Options: work_type, source, has_images, has_text

**Returns:**

- `List[BlakeWork]`: List of matching BlakeWork objects

**Example:**

```python
# Basic search
results = await blake.search_works("innocence")

# Search with filters
poems = await blake.search_works("tiger", {"work_type": "poem"})
```

#### get_statistics()

```python
async def get_statistics() -> Dict[str, Any]
```

Get collection statistics.

**Returns:**

- `Dict[str, Any]`: Statistics dictionary with counts and metadata

**Example:**

```python
stats = await blake.get_statistics()
print(f"Total works: {stats['total_works']}")
print(f"Work types: {stats['work_types']}")
```

#### export_works()

```python
async def export_works(config: ExportConfig) -> Path
```

Export works in specified format.

**Parameters:**

- `config` (ExportConfig): Export configuration object

**Returns:**

- `Path`: Path to exported file

**Example:**

```python
from blake.models import ExportConfig

config = ExportConfig(
    format="json",
    output_dir=Path("./exports"),
    include_images=True
)
output_path = await blake.export_works(config)
```

#### explore()

```python
def explore(host: str = "localhost", port: int = 8501) -> None
```

Launch interactive web interface.

**Parameters:**

- `host` (str): Host address. Default: "localhost"
- `port` (int): Port number. Default: 8501

**Example:**

```python
# Launch GUI
blake.explore()

# Launch on specific port
blake.explore(port=8502)
```

#### clear_cache()

```python
async def clear_cache() -> None
```

Clear the works cache.

**Example:**

```python
await blake.clear_cache()
```

#### download_all_comprehensive()

```python
async def download_all_comprehensive() -> Dict[str, Any]
```

Source-provider discovery helper for provider discovery. Its report is useful for debugging older source adapters, but the target-ledger corpus contract is `BlakeCorpus.run(...)` plus `corpus_manifest.json`, source audit, evidence review, analysis diagnostics, and rights-gate reports.

**Returns:**

- `Dict[str, Any]`: Provider-discovery download report with statistics

#### create_visualization()

```python
async def create_visualization(viz_type: str, data_type: str = "all", config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]
```

Create a visualization.

**Parameters:**

- `viz_type` (str): Type of visualization to create
- `data_type` (str): Type of data to visualize (text, image, temporal, network, all). Default: "all"
- `config` (Optional[Dict[str, Any]]): Visualization configuration

**Returns:**

- `Dict[str, Any]`: Visualization data

## Corpus CLI

Use these commands for reproducible corpus work:

```bash
blake corpus run --quick --output-dir analysis_output
blake corpus run --skip-download --output-dir analysis_output --fixture-mode never --viz-profile core --format json --archive-scope archive-inventory --image-mode archive-all --image-dpi 300 --max-images-per-work none
blake corpus status --coverage
blake corpus visualize --profile core
blake corpus audit-sources --output-dir analysis_output --archive-scope archive-inventory
blake corpus acquire-evidence --from-audit analysis_output/data/source_audit.json --dry-run
blake corpus private-release-preflight --output-dir analysis_output --data-dir blake_data
blake corpus public-release-preflight --output-dir analysis_output --data-dir blake_data
blake corpus public-release-package --output-dir analysis_output --data-dir blake_data
```

- `run --quick`: offline smoke workflow; may seed fixture records if the local cache is empty.
- `run --skip-download`: main local regeneration path; reuses `blake_data/` and regenerates analysis, visualizations, exports, and reports.
- `status --coverage`: prints target-ledger coverage from local metadata.
- `visualize`: regenerates visualization datasets and the workbench from local artifacts.
- `audit-sources`: writes source discovery, provider health, source audit, and missing-evidence review data.
- `acquire-evidence`: validates fallback evidence candidates; `--dry-run` writes review output without saving works.
- `private-release-preflight`: writes local-only private preflight and rights-gate reports with `publish_action: none`.
- `public-release-preflight`: writes a non-publishing GitHub + Zenodo release preflight report and corroboration ledger.
- `public-release-package`: locally stages the release bundle, checksums, citation file, GitHub notes, and Zenodo metadata under `analysis_output/releases/public_release/`; it does not publish or deposit.

## Data Models

### BlakeWork

Main data model representing a Blake work.

```python
class BlakeWork:
    id: str
    metadata: BlakeMetadata
    text_content: Optional[str]
    text_versions: List[str]
    images: List[BlakeImage]
    primary_image: Optional[BlakeImage]
    text_analysis: Dict[str, Any]
    visual_analysis: Dict[str, Any]
    cross_analysis: Dict[str, Any]
    fully_processed: bool
    processing_errors: List[str]
```

### BlakeMetadata

Metadata for a Blake work.

```python
class BlakeMetadata:
    id: str
    title: str
    work_type: WorkType
    creation_date: Optional[datetime]
    publication_date: Optional[datetime]
    period: Optional[str]
    description: Optional[str]
    medium: Optional[str]
    dimensions: Optional[str]
    location: Optional[str]
    source: SourceType
    source_url: Optional[str]
    source_id: Optional[str]
    license_type: LicenseType
    attribution: Optional[str]
    usage_terms: Optional[str]
    related_works: List[str]
    parent_work: Optional[str]
    series: Optional[str]
    tags: List[str]
    themes: List[str]
    subjects: List[str]
    file_path: Optional[Path]
    file_size: Optional[int]
    mime_type: Optional[str]
    checksum: Optional[str]
    created_at: datetime
    updated_at: datetime
    processed: bool
    analysis_results: Dict[str, Any]
```

### BlakeImage

Image data model.

```python
class BlakeImage:
    id: str
    url: str
    file_path: Path
    width: int
    height: int
    format: str
    file_size: int
    thumbnail_path: Optional[Path]
    analysis_results: Dict[str, Any]
    metadata: Dict[str, Any]
```

### Enums

#### WorkType

```python
class WorkType(Enum):
    POEM = "poem"
    PAINTING = "painting"
    DRAWING = "drawing"
    PRINT = "print"
    MANUSCRIPT = "manuscript"
    LETTER = "letter"
    PROSE = "prose"
    UNKNOWN = "unknown"
```

#### SourceType

```python
class SourceType(Enum):
    BLAKE_ARCHIVE = "blake_archive"
    PROJECT_GUTENBERG = "project_gutenberg"
    INTERNET_ARCHIVE = "internet_archive"
    BRITISH_MUSEUM = "british_museum"
    TATE = "tate"
    WIKIMEDIA = "wikimedia"
    UNKNOWN = "unknown"
```

#### LicenseType

```python
class LicenseType(Enum):
    PUBLIC_DOMAIN = "public_domain"
    CREATIVE_COMMONS = "creative_commons"
    COPYRIGHT = "copyright"
    UNKNOWN = "unknown"
```

## Analysis Classes

### BlakeAnalyzer

Main analysis orchestrator.

```python
class BlakeAnalyzer:
    def __init__(self, data_dir: Path)
    
    async def analyze_work(self, work: BlakeWork, analysis_types: Optional[List[str]] = None) -> Dict[str, Any]
    async def analyze_multiple_works(self, works: List[BlakeWork], analysis_types: Optional[List[str]] = None) -> Dict[str, Dict[str, Any]]
    async def compare_works(self, works: List[BlakeWork]) -> Dict[str, Any]
    def get_analysis_summary(self, works: List[BlakeWork]) -> Dict[str, Any]
```

### TextAnalyzer

Text analysis functionality.

```python
class TextAnalyzer:
    def __init__(self)
    
    async def analyze_work(self, work: BlakeWork) -> Dict[str, Any]
    async def compare_works(self, works: List[BlakeWork]) -> Dict[str, Any]
    async def extract_themes(self, text: str) -> List[str]
    async def analyze_sentiment(self, text: str) -> Dict[str, Any]
    async def extract_entities(self, text: str) -> List[Dict[str, Any]]
```

### VisualAnalyzer

Visual analysis functionality.

```python
class VisualAnalyzer:
    def __init__(self)
    
    async def analyze_image(self, image: BlakeImage) -> Dict[str, Any]
    async def compare_images(self, images: List[BlakeImage]) -> Dict[str, Any]
    async def extract_colors(self, image_path: Path) -> List[str]
    async def analyze_composition(self, image_path: Path) -> Dict[str, Any]
```

## Export Classes

### BlakeExporter

Export functionality.

```python
class BlakeExporter:
    def __init__(self, data_dir: Path)
    
    async def export_works(self, works: List[BlakeWork], config: ExportConfig) -> Path
    async def export_to_json(self, works: List[BlakeWork], output_path: Path) -> Path
    async def export_to_csv(self, works: List[BlakeWork], output_path: Path) -> Path
    async def export_to_pdf(self, works: List[BlakeWork], output_path: Path) -> Path
```

### ExportConfig

Export configuration.

```python
class ExportConfig:
    format: str  # "json", "csv", "pdf", "parquet"
    output_dir: Path
    include_images: bool
    include_analysis: bool
    include_metadata: bool
    custom_fields: Optional[List[str]]
```

## GUI Classes

### BlakeGUI

Streamlit-based GUI.

```python
class BlakeGUI:
    def __init__(self, data_dir: Path)
    
    def run(self, host: str = "localhost", port: int = 8501) -> None
    def create_work_explorer(self) -> None
    def create_analysis_dashboard(self) -> None
    def create_search_interface(self) -> None
```

## API Classes

### BlakeAPI

REST API server.

```python
class BlakeAPI:
    def __init__(self, blake_instance: BlakeCorpus)
    
    def run(self, host: str = "0.0.0.0", port: int = 8000) -> None
```

**Endpoints:**

- `GET /` - Root endpoint
- `GET /works` - List works with pagination
- `GET /works/{work_id}` - Get specific work
- `GET /works/{work_id}/analysis` - Get work analysis
- `POST /works/{work_id}/analyze` - Analyze work
- `GET /search` - Search works
- `GET /statistics` - Get collection statistics
- `GET /export/{work_id}` - Export work
- `GET /health` - Health check

## Exceptions

### BlakeError

Base exception for all Blake package errors.

### DownloadError

Raised when download operations fail.

### AnalysisError

Raised when analysis operations fail.

### MetadataError

Raised when metadata operations fail.

### ExportError

Raised when export operations fail.

## Configuration

### Configuration Surfaces

The package reads no `BLAKE_*` environment variables and no configuration file.
Configuration is passed programmatically through `CorpusConfig`, through the
`BlakeCorpus` constructor, or through the CLI options described under
[Corpus CLI](#corpus-cli).
