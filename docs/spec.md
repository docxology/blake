<img src="https://r2cdn.perplexity.ai/pplx-full-logo-primary-dark%402x.png" style="height:64px;margin-right:32px"/>

# Comprehensive Specification for Project "Blake"

**Main Takeaway:**
Project "blake" will be a large, extensible repository and Python package using `uv` for management, designed to assemble, analyze, and provide interactive exploration/export capabilities for William Blake's works. Full-corpus claims are mediated by a canonical target ledger that records what is present, partial, missing, duplicate, or unverified across texts and images.

**Current evidence contract:** corpus claims are evaluated through generated artifacts rather than broad source-mirroring language. The core review surfaces are `corpus_manifest.json`, `pipeline_summary.json`, `source_discovery_health.json`, `source_audit.json`, `evidence_acquisition_review.json`, `analysis_summary.json`, `analysis_diagnostics.json`, `figure_registry.json`, and local-only private preflight/rights-gate reports. `archive-all` is an acquisition-depth mode for local validation and does not grant redistribution rights.

## 1. Repository \& Package Structure

**Core technologies:**

- **Python** (main language)
- **uv** (package and environment management)
- **Modern GUI framework** (e.g., PyQt, Tkinter, or web-based like Streamlit/Gradio/FastAPI)
- **Data management:** SQLite/Parquet for metadata storage, robust file/folder structures for raw assets

**Submodules:**

- `downloader`: scraping/downloading plaintext and images from high-quality sources
- `metadata`: parsing, cleaning, and generating metadata
- `analysis`: NLP, textual analysis, visualization, and similarity search
- `gui`: interactive exploration
- `export`: controlled methods for exporting raw and processed data/assets

## 2. Data Acquisition: William Blake’s Works

### Text \& Image Sources

Key sources to audit, acquire from when permitted, or record as corroborating leads:

- **Blake Archive** (<https://blakearchive.org>): principal source for Blake work identifiers, editorial metadata, object/copy routes, TEI-oriented records, and image/source authority; raw files and mirrors remain rights-gated
- **Project Gutenberg**: plain texts of Blake’s poetic works
- **Internet Archive**, **HathiTrust**: raw scans, facsimiles, letters, rare editions
- **British Museum**, **Tate**, **Google Arts \& Culture**: curated images, data, essays about works/artifacts
- **Wikimedia Commons**: public domain images and media

### Download Workflow

- Automated scripted pipeline, managed by package submodule.
- For images: resolve permitted URLs, download and organize local review copies, generate thumbnails, and keep redistribution status separate.
- For texts: download validated source texts where permitted, parse titles, sections, dates, and retain rejected or manual-review leads as review artifacts.
- License/data tracking metadata embedded (source, access date, terms).

### Data Organization

- `/blake_data/texts/`: all text versions
- `/blake_data/images/`: high-res, thumbnails
- `/blake_data/metadata/`: work titles, years, provenance, medium, source, licensing
- `/blake_data/raw/`: untouched raw scrapes (if possible)
- `/analysis_output/`: run summaries, manifests, analysis, exports, and reports

## 3. Metadata Generation

- Standardized metadata fields: title, type (poem, plate, letter), creation/publication date, image/text linkage, repository, person/entities, tags.
- Auto-generated structure from scraping \& manual enhancements.
- Option for collaborative/curated annotation (JSON/YAML edit support, maybe via GUI).

## 4. Textual \& Image Analysis

**Text Analysis Features:**

- Authorship clustering (Blake vs. contemporaries, variants)
- Theme/topic modeling (NLP: LDA, BERT embeddings)
- Sentiment/emotion detection per work/section
- Concordance, keyword-in-context, n-gram distribution
- Stylistic fingerprinting (metrics: rhyme, meter, complexity)
- Cross-linking illustrations and texts (linking plates and stanzas)
- Named entity recognition (places, people, mythological motifs)
- Intertextual mapping (references, inspiration networks)

**Image Analysis Features:**

- Visual tag extraction (OCR, object detection, color/hue theme mapping)
- Plate-title correlation (linking image to text artifacts)
- Style similarity, image histograms, composition analysis
- Thumbnail/mosaic creation for visual browsing

## 5. Interactive GUI Specification

**Core Features:**

- Exploration interface: browse by work, year, type, medium, theme
- Search/filter by text, metadata, image content, annotated tags
- Synchronized view: display poem alongside illustration/plate
- Timeline or map interface: situate Blake’s works in context (historical, spatial)
- Dynamic visualization: thematic maps, similarity graphs, topic clouds
- Export functions embedded: download selected or custom datasets (CSV, JSON, images, full packages)
- Annotation tools: users can add custom tags/comments directly from UI

**User Scenarios:**

- Scholar/export: batch download annotated materials for research
- Student: visually browse key works and themes
- General public: interactive exhibits, curated “stories”
- Digital humanities: API-access for programmatic querying

## 6. Export \& API Integration

**Export Formats:**

- Raw assets only when source terms, rights metadata, and release policy permit redistribution; otherwise publish manifests, checksums, aggregate reports, and acquisition instructions.
- Processed datasets (metadata-enhanced CSV, JSON, Parquet)
- Thematic reports (PDF, Markdown)
- Bundled packages for other digital humanities platforms

**API/CLI:**

- Modular Python API for all major functions (scraping, querying, analysis)
- CLI: pipeline orchestration (e.g., `blake corpus run --quick`, `blake corpus run --format json`, `blake explore`)
- Documentation auto-generation (Sphinx/README integration)

## 7. Extensibility \& Collaboration

- Clear extension points (new corpora, analysis modules, visualization plugins)
- Configurable scraping and analysis (config files, runtime flags)
- Instructions for contributing metadata, annotation, new data sources
- Option for Github Actions/CI to maintain updated datasets

## 8. Licensing, Data Ethics, Attribution

- All scraped/downloaded materials meticulously tracked for copyright, license, usage terms
- Attribution built-in; data exports include a README/license file
- Non-commercial options for large image sets as required by source (Tate, etc.)

## 9. Documentation

- Comprehensive README, user/developer guide, usage examples
- Inline docstrings for all functions/classes
- Tutorials: scraping, analysis, extending, GUI use, exporting
- Open issue tracker for bugs/feature requests

***

**Conclusion:**
Project "blake" will provide a robust, research-grade platform for source-governed exploration and analysis of William Blake’s works. It is designed for systematic growth, reproducible scholarly workflows, and broad usability while keeping target coverage, source authority, and redistribution rights explicit.
