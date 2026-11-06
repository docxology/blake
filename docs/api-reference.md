# API reference

Use the default installation for [portable methods](shared-methods.md) and
[application custody](applications.md). The corpus, NLP/vision and export classes
below use the `full` profile. The GUI/API add their own extras; exact supported
profiles and qualifications are in [verification](verification.md).

## BlakeCorpus

`BlakeCorpus` is defined in [corpus/pipeline.py](../blake/corpus/pipeline.py)
and re-exported by [blake](../blake/__init__.py). Its constructor is:

~~~text
BlakeCorpus(data_dir=None, *, output_dir=None, config=None, source_registry=None)
~~~

This is a signature, not an initialized global object. Explicit directories
override the corresponding `CorpusConfig` fields. Constructing a corpus creates
its local directories and initializes optional components; use admitted paths
and the required environment before doing so.

| Interface | Execution and result |
|---|---|
| `plan(config=None)` | Synchronous list of planned phases |
| `run(config=None)` | Await; returns `CorpusRunSummary` for the declared pipeline |
| `status()` / `coverage()` | Await; local inventory and target coverage dictionaries |
| `initialize()` | Await; marks the orchestrator initialized |
| `clear_cache()` | Await; clears the in-memory work cache, preserving stored source files |
| `download_all(force=False)` | Await; explicit acquisition through the downloader |
| `download_work(work_id, force=False)` | Await; a work or `None` |
| `get_work(work_id)` / `get_all_works()` | Await; stored work object(s) |
| `search_works(query, filters=None)` | Await; discovery results over loaded metadata/text |
| `analyze_work(work_id, analysis_types=None)` | Await; analyzes only the named work and persists results |
| `analyze_all(analysis_types=None)` | Await; analyzes every loaded work |
| `export(formats=None)` | Await; format-to-export-path mapping |
| `export_works(...)` | Await; delegates to `BlakeExporter`, returning a path |
| `get_statistics()` | Await; local collection summary |
| `explore(host="localhost", port=8501)` | Synchronous Streamlit launcher; requires GUI dependencies |

All calls in the following example share one explicit instance. The source
already needs to be present; this example requests no new Blake-source
acquisition. Optional component initialization still uses its configured model
resources:

~~~python
import asyncio
from pathlib import Path
from blake import BlakeCorpus

async def main():
    corpus = BlakeCorpus(Path("blake_data"), output_dir=Path("analysis_output"))
    works = await corpus.search_works("innocence", {"work_type": "poem"})
    for work in works:
        print(work.id, work.metadata.title)
    await corpus.clear_cache()

asyncio.run(main())
~~~

Discovery search uses substring relevance, including text content. For exact
source-bound occurrence counts and original offsets use the declared
[retrieval profiles](shared-methods.md) or [text-search interface](text-search.md).

## Configuration and models

The authoritative corpus schema is [corpus/models.py](../blake/corpus/models.py).
[Configuration](configuration.md) describes defaults, fixtures, output paths and
the separate manuscript/environment settings. `CorpusRunSummary`,
`CorpusManifest`, `PhaseResult` and source/target records describe their own
run or capture; a completed software phase is not complete Blake coverage.

Work metadata and image schemas live in [models.py](../blake/models.py).
Construct them using their actual Pydantic fields, rather than a second schema
copied from prose:

- `BlakeMetadata` requires `id`, `title`, `work_type` and `source`.
- `BlakeWork` requires `id` and `metadata`; text and associated images are separate.
- `BlakeImage` requires `id`, `metadata_id`, `title` and `file_path`.
  `original_url` records an available source URL; paths and metadata do not prove
  that a file was downloaded, inspected or cleared for redistribution.
- `WorkType`, `SourceType` and `LicenseType` have the concrete values declared
  in that source. Use `model_json_schema()` / `model_fields` for complete current
  field/validation descriptions. A recorded rights label is an observation, not
  permission inferred by the software.

Portable bundle/projection/study schemas have their own versions and explicit
[conversion boundary](shared-methods.md). They are not interchangeable with a
corpus ORM layout or a model dump from another schema.

## Analysis and visualization

| Owner | Public interface |
|---|---|
| [BlakeAnalyzer](../blake/analysis/analyzer.py) | Async `analyze_work`, `analyze_multiple_works`, `compare_works`, `load_analysis_result`; synchronous `get_analysis_summary` |
| [TextAnalyzer](../blake/analysis/text_analysis.py) | Async `analyze_work(work)` and `compare_works(works)` |
| [VisualAnalyzer](../blake/analysis/visual_analysis.py) | Async `analyze_image(image)` and `compare_images(images)` |
| [Corpus pipeline](../blake/corpus/pipeline.py) | Async `create_visualization`, `visualize`, dashboard/report methods and available-visualization inspection |
| [Visualization package](../blake/viz/README.md) | Renderer and dashboard owners |

Sentiment, theme and image-composition helpers are implementation details of
these analyzers. Their private helper names are not separate public APIs.
Model availability, inference outputs, figure inspection and literary
interpretation have separate acceptance scopes.

## Export

[BlakeExporter](../blake/export/exporter.py) owns async
`export_works(works, config)`, `export_work(work, output_path, format="json")`
and `export_analysis_results(works, output_path, format="json")`.
`get_supported_formats()` and `get_export_info()` are synchronous.

`ExportConfig` is declared in [models.py](../blake/models.py). It selects a
format and output directory plus image/metadata/analysis/filter/compression
options. Use unused accounted destinations and inspect what will be copied;
exporting local provider images is a separate rights decision.

The format protocol is [BaseExporter](../blake/export/formats.py), with three
async export methods. `formats.EXPORTERS` maps names to implementation classes;
the dispatcher instantiates these as `BlakeExporter.exporters`. Unsupported
formats raise `ExportError`. [Extension guidance](developer-guide.md#extending-the-package).

## Corpus CLI

The actual registration is [cli.py](../blake/cli.py), with recovery commands
delegated to [recovery_commands.py](../blake/recovery_commands.py).

| Entry | Purpose |
|---|---|
| `blake corpus run` | Declared corpus pipeline |
| `blake corpus status` / `visualize` | Inventory/coverage and visualization |
| `blake corpus audit-sources` / `acquire-evidence` | Explicit source inspection/acquisition |
| `blake corpus recover` / `verify-recovery` / `import-recovery` | Captured recovery and registration |
| `blake corpus backup` / `verify-backup` / `restore` | Source snapshot custody |
| `blake corpus private-release-preflight` | Private release preflight |
| `blake corpus public-release-preflight` / `public-release-package` | Selected analytical epoch, logical bundle paths and blockers; package staging requires a fresh destination and preserves occupied outputs |
| `blake info`, `search`, `interactive`, `explore`, `scrape-archive` | Inventory, discovery and optional interfaces |

Use `uv run --locked blake --help` and the selected command's `--help` with the
correct extras. Nested command help may initialize the corpus callback; use
admitted data/output paths. `blake-text` and `blake-application` have independent
entry points for their documented source-bound contracts.

## HTTP API and errors

[BlakeAPI](../blake/export/api.py) is instantiated with a corpus instance and
exposes its FastAPI `app`. The source defines the routes and error envelopes.
It does not export a module-global initialized app or supply a built-in
authentication/deployment service. API serving needs `full` and `api`.

Project exceptions are defined in [exceptions.py](../blake/exceptions.py).
Portable evidence admission also uses named `EvidenceError`/`ResearchError`
contracts documented in [shared methods](shared-methods.md). Retain the exact
error and failed epoch; an exception is not permission to replace source data
or treat an unavailable result as zero.
