# Blake Corpus Analysis Platform

Software candidate: **0.3.0**. See [release changes](CHANGELOG.md) and the
[versioned methods contract](docs/methods.md). The Streamlit **Local evidence**
view exposes recorded recovery status and scoped, read-only corpus search.

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![DOI](https://img.shields.io/badge/DOI-10.5281%2Fzenodo.23601681-blue.svg)](https://doi.org/10.5281/zenodo.23601681)

Blake builds a reproducible local corpus workflow for William Blake texts, images, metadata, analysis results, visual summaries, exports, and reports. The API is `BlakeCorpus`.

## Corpus, methods and application papers

This is the shared **corpus and methods repository**. It owns acquisition,
source custody, completeness accounting, passage identity, normalization and
reusable analysis. Application projects own their questions, query vocabularies,
contextual annotations, arguments and manuscripts. The corpus/methods paper here
documents this infrastructure; an application's interpretation is not a property
of the corpus.

The [application contract](docs/applications.md) provides private, hash-bound
portable snapshots and uncapped lexical studies. An application supplies explicit
search forms and receives every category/source-span match, all zero cells and
source denominators. Source roles and authorship labels survive the transfer.
Applications do not need to read an internal SQLite schema or copy search code.
The package imports this surface without loading the legacy NLP/vision stack;
the default installation contains only the methods dependencies. Install the `full`
extra for acquisition, NLP, vision and the legacy corpus pipeline. The narrower
`recovery` extra supports recovered-source export with HTML parsing and image
verification. See the
[shared methods API](docs/shared-methods.md) for explicit retrieval profiles,
counted statistics, proximity, review custody and offline workspaces.

The 0.3.0 dependency split is a candidate until clean installed-package checks
are completed; these instructions do not attest a published release.

## Primary Workflow

```bash
uv sync --extra full --extra dev
uv run blake corpus run --quick --output-dir analysis_output
uv run blake corpus run --skip-download --output-dir analysis_output --fixture-mode never --viz-profile core --format json --archive-scope archive-inventory --image-mode archive-all --image-dpi 300 --max-images-per-work none
uv run blake corpus public-release-preflight --output-dir analysis_output --data-dir blake_data
uv run blake corpus public-release-package --output-dir analysis_output --data-dir blake_data
```

A quick run is offline and uses the local `blake_data/` cache. If that cache is empty, quick mode seeds a tiny bundled fixture corpus so the pipeline proves non-empty processing, visualization, export, and reporting without network access. A full run enables live acquisition through registered source providers.

The second command refreshes the existing pipeline store. Publication analysis instead uses a fresh store so captured metadata and earlier results remain intact; see the workflow below. Do not add `--skip-analysis` when claiming newly computed results.

`archive-all` is an evidence-depth setting for local Archive image acquisition. It is not a redistribution permission. Public-release preflight and package commands stage metadata, checksums, and release-safe files locally; they do not publish, tag, deposit, or clear rights-gated source materials.

## Publication analysis and rendered paper

The [versioned working paper](https://doi.org/10.5281/zenodo.23601681) accompanies
the software assets. Its source/copy records, target-ledger entries, image
associations and distinct files are separate denominators. Exploratory NLP
retains unverified authorship labels. Recoverability of captured bytes does not
establish whole-oeuvre completeness or permission to redistribute provider files.

For a fresh reproduction checkout, preserve prior outputs and prepare a new store:

```bash
uv run python scripts/prepare_manuscript_epoch.py --destination blake_data/publication/reproduction
uv run python scripts/reproduce_manuscript_analysis.py --data-dir blake_data/publication/reproduction --seed 20261023
uv run python scripts/seal_manuscript_evidence.py --analysis-receipt analysis_output/data/analysis_epoch_receipt.json
uv run python scripts/generate_manuscript_figures.py --public-only
TEMPLATE_REPO_ROOT=../template uv run python scripts/z_generate_manuscript_variables.py
```

The seal verifies the existing recovery inventory, backup, private search and
retained corruption/repair controls; it does not run another restore drill.
These analytical commands require the private corpus and retained backup/control
files. The public reproduction archive includes hydrated manuscript sources,
aggregate figures and rendering instructions. See [the paper workflow](docs/manuscript/08_reproducibility.md).

The saved record analyses retain their actual 0.2.0rc1 producer identity.
Version 0.2.0 supplies corrected membership-bound summaries and covariance
projection, methods profile `local-source-evidence-v2`, and dashboard schema `2`.
The dashboard admits a completed saved epoch only while its bound metadata,
results and transcriptions match. It discloses stale evidence and keeps the
original recovery store separate.

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

## Recover the local corpus

```bash
uv sync --python 3.11 --extra full --extra dev --extra api --extra gui
uv run --python 3.11 python -m blake.recovery recover --full
uv run --python 3.11 python -m blake.recovery verify
uv run --python 3.11 python -m blake.recovery register
uv run --python 3.11 blake-text build-recovered
uv run --python 3.11 blake-text --recovered query eternity
uv run --python 3.11 blake-text --recovered query state --scope exploratory --plane erdman
```

Recovery saves the entire pinned `blakearchive/data` source repository, every
work-copy XML file (including ZIP-delivered variants), and the complete response
from the Archive's Erdman *Complete Poetry and Prose* reader. Files remain local
under the gitignored `blake_data/recovery/` directory. The source archive, extracted
files, per-copy reading texts, all Erdman page records, combined Erdman text,
passage JSONL, and search index have SHA-256 receipts in `manifest.json`.

The `register` command makes those source documents available to `BlakeCorpus`
and the existing pipeline through `blake_data/metadata/metadata.db`. It preserves
other works and existing recovery analyses. Source documents retain individual
copy identities; the ZIP and XML versions of the same copy remain distinct.
The equivalent commands are `blake corpus recover`, `blake corpus
verify-recovery`, and `blake corpus import-recovery`.

Reruns reuse saved sources and verify the prior manifest before updating it.
Use `recover --offline --no-images` to rebuild from those sources without network
access. Keep each Archive commit in a separate data directory; `--commit` accepts
only a full commit SHA. The compatibility script
`scripts/download_complete_archive.py` delegates to this workflow and propagates
errors to its exit status.

`--full` also retains the complete work, copy, and object API responses and a
pinned snapshot of the full Erdman source edition, including its four XML parts.
Once enabled, that profile is retained on subsequent offline rebuilds. The
Image acquisition tries canonical lowercase and original source spellings;
case exceptions retain their actual source URLs. Source identifiers retain their
original case in the manifest. `--image-workers` controls concurrency (1–8).

Source recovery, transcription extraction, image recovery, and coverage of
Blake's oeuvre are reported separately. Recovery attempts every identified object
at 300 dpi, then tries an explicitly recorded 100 dpi fallback when necessary.
Resolution counts and fallback object IDs are reported separately. Lower
resolution is never reported as meeting the requested 300 dpi target.
Recovery records each remaining failure for retry. Downloaded images must decode
before being saved. `verify` checks file hashes, snapshot membership, source
bindings, page and search membership, and the complete image outcome ledger.
Unresolved files are never counted as downloaded. Reviewed transcription rules
are bound to exact source hashes; other ambiguous readings remain explicit errors.

Create a portable local backup after recovery:

```bash
uv run --python 3.11 python -m blake.recovery backup --destination blake_data/backups/full-corpus.tar
uv run --python 3.11 python -m blake.recovery verify-backup blake_data/backups/full-corpus.tar
uv run --python 3.11 python -m blake.recovery restore-drill blake_data/backups/full-corpus.tar --destination blake_data/restore-check
```

The bundle includes every inventoried source, text, image and index, plus the
exact recovery source code and dependency lockfile. A separate checksum receipt
binds the complete bundle. `restore` works offline and quarantines conflicting
bytes before restoring them. `restore-drill` requires an empty destination,
restores every byte, deliberately corrupts a copy, proves verification rejects
the corruption, and restores the original bytes again. It preserves the damaged
control and writes a durable report. Existing backups are preserved; choose a
new destination or use the default content-named path for later snapshots.

`MetadataManager.export_metadata` also preserves the complete work model,
including all four saved analysis fields. `import_metadata` validates the full
input array before saving records and stores included text under the destination
corpus. Image paths remain references; use the recovery backup for portable
source and image bytes. Metadata import does not provide a transaction across
the SQLite database and filesystem if an I/O failure interrupts saving.

Primary occurrence search includes only Archive reading layers bound to text
works in the existing canonical ledger. Other Archive transcriptions remain
unverified. Erdman reading text retains editorial material and stays separate
from primary occurrence search. The raw JSON and XML preserve the complete
provider response and diplomatic apparatus, including material excluded from
the reading layers. An unresolved original reading is reported explicitly;
its source file is preserved. A recovered source snapshot establishes the saved
inventory, not completeness of every surviving Blake work or edition.

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

## CLI

```bash
blake corpus run --quick --output-dir analysis_output
blake corpus run --quick --viz-profile full
blake corpus status --coverage
blake corpus visualize --profile core
blake corpus run --format json --format csv --format markdown
blake corpus public-release-preflight --output-dir analysis_output --data-dir blake_data
blake corpus public-release-package --output-dir analysis_output --data-dir blake_data
blake search --query "tyger"
blake info --work-id <id>
blake explore
```

The corpus workflow lives under `blake corpus`; `search`, `info`, and `explore` are convenience commands over local corpus metadata.

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

## Search primary words, phrases and concepts

Use [`blake-text`](docs/text-search.md) for deterministic passage search with
original spellings, edition/source locators, occurrence counts and explicit
concept expansions. The included demonstration contains seven excerpts from one
1906 edition of *The Marriage of Heaven and Hell*; it is not the full corpus.
Restored restricted source caches and indexes remain private and untracked.

```sh
python -m blake.text_search --index blake_data/search/demo.sqlite build examples/primary-passages.jsonl
python -m blake.text_search --index blake_data/search/demo.sqlite query 'Eternity is in love with the productions of time' --mode phrase
python -m blake.text_search --index blake_data/search/demo.sqlite suite
```

## Development

```bash
uv sync --extra full --extra dev --extra api
uv run pytest tests/ -q
uv run pytest tests/ -q -m "not slow and not integration"
uv run blake corpus run --quick --output-dir analysis_output
uv run blake corpus run --skip-download --output-dir analysis_output --fixture-mode never --viz-profile core --format json --archive-scope archive-inventory --image-mode archive-all --image-dpi 300 --max-images-per-work none
uv run blake corpus private-release-preflight --output-dir analysis_output --data-dir blake_data
uv run blake corpus public-release-preflight --output-dir analysis_output --data-dir blake_data
uv run blake corpus public-release-package --output-dir analysis_output --data-dir blake_data
```

Plain `uv sync` installs the methods-only dependency set: packaging, Click,
Pydantic and typing extensions. Use `uv sync --extra full --extra dev` for
the full pipeline and its tests. Add `--extra gui` for Streamlit/Gradio or
`--extra api` for FastAPI; both surfaces also require `--extra full`.

## License and Data Rights

The project code and project-authored documentation are licensed under the MIT License. See [LICENSE](LICENSE).

Downloaded or cached Blake materials under `blake_data/`, generated image mosaics, source TEI, transcriptions, and provider-supplied images are not relicensed by this repository. Treat them under their source-provider terms and the manifest's recorded authority/license metadata.

The manuscript's legal distribution section and rights-matrix supplement are the release checklist for public artifacts. In short: publish code, commands, checksums, source URLs, manifests, and aggregate diagnostics; keep raw provider files and local evidence caches out of public source releases unless permission, source-compatible licensing, or a venue-specific fair-use rationale is documented.

`uv run blake corpus private-release-preflight` writes local-only preflight and rights-gate reports under `analysis_output/reports/`. It never publishes, tags, deposits, or redistributes artifacts; it records what a private GitHub-oriented review would include and which public artifact classes remain blocked.

`uv run blake corpus public-release-preflight` and `uv run blake corpus public-release-package` prepare the GitHub + Zenodo release bundle under `analysis_output/releases/public_release/`. The package includes code, safe generated outputs, `CITATION.cff`, Zenodo metadata, and SHA-256 checksums while excluding the local manuscript pipeline, raw source caches, and rights-gated assets by default.

## Citation and Archive

This project is archived on Zenodo with a DOI, cross-linked to this repository:

- **DOI:** [10.5281/zenodo.23601681](https://doi.org/10.5281/zenodo.23601681)
- **Zenodo record:** working-paper PDF, wheel, source distribution, allowlisted reproduction archive, release manifest and SHA-256 checksums. Provider image mosaics are omitted.
- **Earlier paper:** [10.5281/zenodo.21047574](https://doi.org/10.5281/zenodo.21047574), whose published record contains the earlier PDF.
- See [`CITATION.cff`](CITATION.cff) for citation metadata.

The MIT license covers project code and project-authored outputs only. Provider-supplied Blake Archive TEI, transcriptions, images, and fallback source texts are not included here and remain under their source-provider terms.
