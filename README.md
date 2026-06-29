# Blake Corpus Analysis Platform

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![DOI](https://img.shields.io/badge/DOI-10.5281%2Fzenodo.21047574-blue.svg)](https://doi.org/10.5281/zenodo.21047574)

Blake builds a reproducible local corpus workflow for William Blake texts, images, metadata, analysis results, visual summaries, exports, and reports. The primary API is `BlakeCorpus`; `BlakeWorks` remains as a compatibility shim for older code.

## Primary Workflow

```bash
uv sync
uv run blake corpus run --quick --output-dir analysis_output
uv run blake corpus run --skip-download --output-dir analysis_output --fixture-mode never --viz-profile core --format json --archive-scope archive-inventory --image-mode archive-all --image-dpi 300 --max-images-per-work none
uv run blake corpus public-release-preflight --output-dir analysis_output --data-dir blake_data
uv run blake corpus public-release-package --output-dir analysis_output --data-dir blake_data
```

A quick run is offline and uses the local `blake_data/` cache. If that cache is empty, quick mode seeds a tiny bundled fixture corpus so the pipeline proves non-empty processing, visualization, export, and reporting without network access. A full run enables live acquisition through registered source providers.

For manuscript/regression work, the canonical local regeneration command is the second command above: it reuses the existing local corpus with `--skip-download`, then regenerates metadata, analysis, visualizations, exports, and reports. Do not add `--skip-analysis` unless you are explicitly testing a stale-analysis scenario.

`archive-all` is an evidence-depth setting for local Archive image acquisition. It is not a redistribution permission. Public-release preflight and package commands stage metadata, checksums, and release-safe files locally; they do not publish, tag, deposit, or clear rights-gated source materials.

## Output Layout

All corpus artifacts are written under `analysis_output/` by default:

```
analysis_output/
├── pipeline_summary.json
├── corpus_manifest.json
├── data/
│   ├── source_discovery.json
│   ├── source_discovery_health.json
│   ├── source_audit.json
│   └── evidence_acquisition_review.json
├── analysis/
│   ├── analysis_summary.json
│   ├── analysis_diagnostics.json
│   └── analysis_results.json
├── visualizations/
│   ├── visualization_summary.json
│   ├── target_coverage_matrix.json
│   ├── target_coverage_matrix.png
│   └── corpus_workbench.html
├── exports/
│   └── export_summary.json
├── reports/
    ├── completeness_report.json
    ├── source_coverage.json
    ├── provenance_manifest.json
    ├── chronology.json
    ├── theme_entity_network.json
    ├── text_image_linkage.json
    ├── statistics.json
    ├── private_release_preflight.json
    ├── private_release_preflight.md
    ├── public_release_preflight.json
    ├── public_release_preflight.md
    ├── rights_gate_report.json
    ├── rights_gate_report.md
    └── corpus_report.md
└── releases/
    └── public_release/
        ├── public_release_manifest.json
        ├── public_release_bundle.zip
        ├── CITATION.cff
        └── zenodo_metadata.json
```

Raw downloads, SQLite metadata, cached texts, and images live under `blake_data/`.

## Python API

```python
import asyncio
from pathlib import Path

from blake import BlakeCorpus, CorpusConfig

async def main():
    corpus = BlakeCorpus(Path("blake_data"), output_dir=Path("analysis_output"))
    summary = await corpus.run(CorpusConfig(quick=True))
    print(summary.status)

asyncio.run(main())
```

Legacy code can still import `BlakeWorks`; it subclasses `BlakeCorpus`.

## CLI

```bash
blake corpus run --quick --output-dir analysis_output
blake corpus run --quick --viz-profile full
blake corpus status --coverage
blake corpus visualize --profile core
blake corpus run --format json --format csv --format markdown
blake corpus public-release-preflight --output-dir analysis_output --data-dir blake_data
blake corpus public-release-package --output-dir analysis_output --data-dir blake_data
blake download --all
blake analyze --all --text
blake export --format parquet
blake stats
blake explore
```

`download`, `analyze`, `export`, and `stats` are compatibility shortcuts over the corpus services.

## Current Evidence Contract

- `analysis_output/corpus_manifest.json` is the target-ledger coverage contract.
- `analysis_output/data/source_audit.json` records source discovery, provider health, URL checks, Archive metadata enrichment, and missing-evidence candidates.
- `analysis_output/data/evidence_acquisition_review.json` is the strict review ledger for unresolved targets and manual source leads.
- `analysis_output/analysis/analysis_summary.json` and `analysis_output/analysis/analysis_diagnostics.json` record current analysis status, eligibility, completion, diagnostics, and errors.
- `output/figures/figure_registry.json` records every manuscript figure, its brief, accessibility notes, statistical question, and generated statistics.
- `analysis_output/reports/private_release_preflight.*` and `analysis_output/reports/rights_gate_report.*` are local-only release/readiness checks. `analysis_output/reports/public_release_preflight.*` and `analysis_output/releases/public_release/` are the public GitHub + Zenodo release staging surfaces; they generate bundle metadata, checksums, and citation files without altering the repository itself.

## Corpus Components

- `blake.corpus` owns `CorpusConfig`, `CorpusManifest`, `CorpusRunSummary`, `PhaseResult`, source registry, and `BlakeCorpus`.
- The corpus manifest compares local works against a versioned canonical target ledger and reports `present`, `partial`, `missing`, `duplicate`, and `unverified` coverage.
- `blake.downloader` keeps legacy adapters while corpus acquisition normalizes source records through `SourceProvider` wrappers.
- `blake.metadata` stores and searches local work metadata.
- `blake.analysis` writes typed analysis records through the corpus pipeline.
- `blake.viz` exposes one Pydantic visualization configuration model.
- `blake.export` supports JSON, CSV, Markdown, HTML, PDF, and Parquet where dependencies permit.

## Data Sources

Default source adapters cover Blake Archive, Project Gutenberg, and Internet Archive. Additional museum and discovery adapters exist for British Museum, Tate, Wikimedia, HathiTrust, and related sources. Live-source integration is optional; the default test and quick-run surfaces do not require network access. A run is only reported as complete when the canonical target ledger is fully covered; otherwise reports explain the remaining gaps.

## Development

```bash
uv sync
uv sync --extra dev --extra api
uv run pytest tests/ -q
uv run pytest tests/ -q -m "not slow and not integration"
uv run blake corpus run --quick --output-dir analysis_output
uv run blake corpus run --skip-download --output-dir analysis_output --fixture-mode never --viz-profile core --format json --archive-scope archive-inventory --image-mode archive-all --image-dpi 300 --max-images-per-work none
uv run blake corpus private-release-preflight --output-dir analysis_output --data-dir blake_data
uv run blake corpus public-release-preflight --output-dir analysis_output --data-dir blake_data
uv run blake corpus public-release-package --output-dir analysis_output --data-dir blake_data
```

The default install keeps GUI/API serving packages out of the core dependency set. Use `--extra gui` for Streamlit/Gradio surfaces and `--extra api` for FastAPI serving.

## License and Data Rights

The project code and project-authored documentation are licensed under the MIT License. See [LICENSE](LICENSE).

Downloaded or cached Blake materials under `blake_data/`, generated image mosaics, source TEI, transcriptions, and provider-supplied images are not relicensed by this repository. Treat them under their source-provider terms and the manifest's recorded authority/license metadata.

The manuscript's legal distribution section and rights-matrix supplement are the release checklist for public artifacts. In short: publish code, commands, checksums, source URLs, manifests, and aggregate diagnostics; keep raw provider files and local evidence caches out of public source releases unless permission, source-compatible licensing, or a venue-specific fair-use rationale is documented.

`uv run blake corpus private-release-preflight` writes local-only preflight and rights-gate reports under `analysis_output/reports/`. It never publishes, tags, deposits, or redistributes artifacts; it records what a private GitHub-oriented review would include and which public artifact classes remain blocked.

`uv run blake corpus public-release-preflight` and `uv run blake corpus public-release-package` prepare the GitHub + Zenodo release bundle under `analysis_output/releases/public_release/`. The package includes code, safe generated outputs, `CITATION.cff`, Zenodo metadata, and SHA-256 checksums while excluding the local manuscript pipeline, raw source caches, and rights-gated assets by default.

## Citation and Archive

This project is archived on Zenodo with a DOI, cross-linked to this repository:

- **DOI:** [10.5281/zenodo.21047574](https://doi.org/10.5281/zenodo.21047574)
- **Zenodo record:** the working-paper PDF (rights-safe; Blake Archive image mosaics omitted) plus the open-source software release bundle.
- See [`CITATION.cff`](CITATION.cff) for citation metadata.

The MIT license covers project code and project-authored outputs only. Provider-supplied Blake Archive TEI, transcriptions, images, and fallback source texts are not included here and remain under their source-provider terms.
