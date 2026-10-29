# Blake Architecture

Blake is organized around a canonical `BlakeCorpus` workflow. A run plans and executes discovery, acquisition, metadata ingestion, analysis, visualization, export, and reporting into reproducible artifacts under `analysis_output/`. Raw and cached content remains under `blake_data/`.

## Current interfaces

Recovery runs through `blake.recovery_commands` and the registered `blake corpus` commands. Schema conversion lives in `blake.methods.schema_conversion`. Workspace serialization uses its public implementations directly. The distinct NFKC, literal-casefold and regex retrieval profiles retain their own contracts.

## Core Architecture

### 1. Corpus Layer

**Purpose**: Owns reproducible runs and the manifest contract

**Components**:

- `BlakeCorpus` - Primary orchestrator
- `CorpusConfig` - Run configuration
- `CorpusTarget` and `CorpusTargetEntry` - Versioned canonical Blake corpus ledger
- `CorpusManifest` - Corpus inventory, provenance, and target coverage
- `CorpusRunSummary` and `PhaseResult` - Run status and artifacts
- `SourceRegistry` - Normalized source provider registry

### 2. Data Layer

**Purpose**: Manages data acquisition, storage, and retrieval

**Components**:

- `BlakeDownloader` - Source-provider download coordinator
- `SourceProvider` adapters - Normalized source discovery/fetch contract
- `DownloadManager` - Session management and coordination
- `MetadataManager` - Metadata storage and retrieval
- Source adapters (Project Gutenberg, Blake Archive, etc.)

**Key Features**:

- Multi-source data acquisition
- Robust error handling and retry logic
- Content validation and quality assurance
- Efficient storage and caching

### 3. Analysis Layer

**Purpose**: Processes and analyzes Blake works

**Components**:

- `BlakeAnalyzer` - Core analysis engine
- Text analysis modules
- Visual analysis modules
- Cross-modal analysis

**Key Features**:

- Sentiment analysis
- Thematic analysis
- Stylistic analysis
- Comparative analysis

### 4. Visualization Layer

**Purpose**: Creates visual representations of data and analysis

**Components**:

- `VisualizationEngine` - Core visualization processing
- `CorpusVisualizationBuilder` - Target coverage, provenance, text, image, network, chronology, and workbench artifacts
- `DataProcessor` - Data preparation and transformation
- Renderer modules (text, image, temporal, network, comparative)
- Dashboard system

**Key Features**:

- Multi-modal visualizations
- Interactive dashboards
- Automated report generation
- Export capabilities

### 5. Interface Layer

**Purpose**: Provides user interfaces and interaction points

**Components**:

- `BlakeGUI` - Graphical user interface
- `InteractiveOrchestrator` - Terminal interface
- `blake corpus run`
- Current commands: `blake corpus`, `blake info`, `blake search` and `blake-text`
- API endpoints

**Key Features**:

- Rich terminal interface
- Web-based dashboard
- Command-line tools
- Programmatic API

## Design Principles

### 1. Modularity

Each component is designed as a self-contained module with clear interfaces:

```
blake/
├── corpus/                 # Corpus workflow, manifests, source registry
├── models.py              # Data models
├── downloader/            # Download system
├── analysis/              # Analysis system
├── viz/                   # Visualization system
└── cli.py                 # Command-line interface
```

### 2. Extensibility

The system is designed for easy extension:

- **New Sources**: Add `SourceProvider` adapters or wrap source-specific clients through the registry
- **New Analysis**: Extend analysis modules with new algorithms
- **New Visualizations**: Add renderer modules for new visualization types
- **New Interfaces**: Add new UI components or API endpoints

### 3. Testability

Comprehensive testing at all levels:

- **Unit Tests**: Individual component testing
- **Integration Tests**: Component interaction testing
- **Performance Tests**: Load and stress testing
- **End-to-End Tests**: Complete workflow testing

### 4. Performance

Optimized for efficiency and scalability:

- **Async Processing**: Non-blocking I/O operations
- **Parallel Downloads**: Concurrent data acquisition
- **Caching**: Intelligent content caching
- **Memory Management**: Efficient resource usage

## Data Flow

### 1. Acquisition Flow

```
User Request → BlakeCorpus → SourceRegistry → SourceProvider → Content Storage
```

1. User runs `blake corpus run`
2. `BlakeCorpus` resolves run configuration
3. `SourceRegistry` normalizes and deduplicates source records
4. Source adapters acquire data when not in quick mode
5. Content is stored, verified, and represented in `corpus_manifest.json`

### 2. Analysis Flow

```
Stored Content → BlakeCorpus → BlakeAnalyzer → AnalysisResult Records → analysis_output/analysis
```

1. Stored content is retrieved
2. `BlakeAnalyzer` coordinates analysis
3. Analysis modules process the content
4. Results are stored for visualization

### 3. Visualization Flow

```
Manifest + Analysis Results → CorpusVisualizationBuilder + VisualizationEngine → analysis_output/visualizations
```

1. The manifest and local works are loaded
2. Corpus datasets are generated for target coverage, chronology, provenance, text, image, network, linkage, gallery, and pipeline architecture views
3. Static and HTML artifacts are written for deterministic quick runs
4. Existing renderers remain available for opt-in and full-profile visualization work

## Component Interactions

### Core Orchestrator

`BlakeCorpus` serves as the central orchestrator:

```python
class BlakeCorpus:
    def __init__(self, data_dir, output_dir):
        self.downloader = BlakeDownloader(data_dir)
        self.analyzer = BlakeAnalyzer(data_dir)
        self.exporter = BlakeExporter(data_dir)
        self.metadata_manager = MetadataManager(data_dir)
        self.source_registry = SourceRegistry()
```

`BlakeCorpus` is defined in `blake/corpus/pipeline.py` and re-exported from `blake`; there is one corpus orchestrator.

### Corpus Target Coverage

The manifest is measured against the canonical target ledger rather than inferred from whatever happens to be present locally. Each target entry receives one of these statuses:

- `present`: local work has the expected text/image modality
- `partial`: local work exists but required text or image evidence is missing
- `missing`: no local work or discovered source record matches the target
- `duplicate`: multiple local works match one target entry
- `unverified`: discovery found a source record, but no local work was saved

Quick mode may seed a fixture corpus when `blake_data/` is empty. Fixture records are labeled in `corpus_manifest.json`; they prove the pipeline surface but do not make the corpus complete.

### Data Models

Pydantic models ensure data integrity:

```python
class BlakeWork(BaseModel):
    id: str
    metadata: BlakeMetadata
    text_content: Optional[str]
    images: List[BlakeImage]
    fully_processed: bool
```

The visualization system uses one Pydantic `VisualizationConfig` model from `blake.viz.models`; root imports alias that model.

### Source Adapters

Consistent interface for all data sources:

```python
class SourceProvider:
    async def discover(self) -> List[SourceRecord]
    async def fetch(self, record: SourceRecord, *, force: bool = False) -> Optional[BlakeWork]
```

## Error Handling Strategy

### 1. Graceful Degradation

- System continues operating when individual components fail
- Fallback mechanisms for critical operations
- Clear error reporting and logging

### 2. Retry Logic

- Automatic retry for transient failures
- Exponential backoff for rate limiting
- Circuit breaker pattern for failing services

### 3. Validation

- Input validation at all entry points
- Data integrity checks throughout the pipeline
- Comprehensive error logging and reporting

## Security Considerations

### 1. Data Protection

- Secure storage of sensitive data
- Input sanitization and validation
- Access control and authentication

### 2. Network Security

- HTTPS for all external communications
- Rate limiting and abuse prevention
- Secure credential management

## Performance Optimization

### 1. Caching Strategy

- Multi-level caching (memory, disk, network)
- Intelligent cache invalidation
- Cache warming for critical data

### 2. Resource Management

- Connection pooling for network operations
- Memory usage monitoring and limits
- Garbage collection optimization

### 3. Scalability

- Horizontal scaling through stateless design
- Load balancing for high availability
- Database optimization for large datasets

## Monitoring and Observability

### 1. Logging

- Structured logging with correlation IDs
- Multiple log levels (DEBUG, INFO, WARNING, ERROR)
- Centralized log aggregation

### 2. Metrics

- Performance metrics (latency, throughput)
- Business metrics (download success rates)
- System metrics (CPU, memory, disk usage)

### 3. Health Checks

- Component health monitoring
- Dependency health verification
- Automated alerting for failures

## Deployment Architecture

### 1. Development Environment

- Local development with Docker
- Hot reloading for rapid iteration
- Comprehensive testing suite

### 2. Production Environment

- Containerized deployment
- Load balancing and auto-scaling
- Monitoring and alerting

### 3. CI/CD Pipeline

- Automated testing and validation
- Continuous integration and deployment
- Rollback capabilities

## Future Extensibility

### 1. New Data Sources

- Plugin architecture for source adapters
- Configuration-driven source management
- Dynamic source discovery

### 2. Advanced Analytics

- Machine learning integration
- Natural language processing
- Computer vision capabilities

### 3. Enhanced Visualization

- 3D visualizations
- Interactive web components
- Real-time collaboration features
