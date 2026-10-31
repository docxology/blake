# Developer guide

Read the repository [agent contract](../AGENTS.md), [architecture](ARCHITECTURE.md),
[style guide](style-guide.md) and the contract for the surface you are changing.
Use [verification](verification.md) as the authoritative environment/check guide.

## Development setup

Work from the mounted canonical checkout or a supported external worktree.
Preserve peers, historical outputs and failed runs. Bind both Python prefixes,
TMP and caches to external storage; use the supported repository/common-store
lease for source integration and publication.

~~~sh
# Full corpus stack and complete test collection
uv sync --locked --python 3.11 --extra full --extra dev --extra gui --extra api

# Read the actual interpreter identity
uv run --locked python -c 'import sys; print(sys.prefix); print(sys.base_prefix)'
~~~

Dependency-light methods use a separate Python 3.9 qualification; do not import
acquisition/NLP/GUI modules into those interfaces. Plain `uv sync --locked`
installs the methods profile, not the full pipeline or complete test collection.

## Project structure

| Source owner | Responsibility |
|---|---|
| [corpus](../blake/corpus/README.md) | `BlakeCorpus`, run/target models, source registry and pipeline artifacts |
| [applications.py](../blake/applications.py) | Portable captured-bundle custody |
| [studies.py](../blake/studies.py) | Application-supplied study forms and source-bound hits |
| [methods](../blake/methods/) | Shared matching, schemas, statistics, annotations, hierarchy and review batches |
| [text_search](../blake/text_search/cli.py) | NFKC search projection and local browser workspace |
| [downloader](../blake/downloader/README.md) | Source clients and explicit acquisition |
| [metadata](../blake/metadata/README.md) | Stored work/image metadata and discovery search |
| [analysis](../blake/analysis/README.md) | Optional NLP, visual and cross-modal analysis |
| [viz](../blake/viz/README.md) | Renderers, dashboards and reporting |
| [export](../blake/export/README.md) | Format protocol, exporter and optional HTTP API |
| [manuscript tools](../manuscript_tools/README.md) | Project-specific manuscript projection and figures |

The [API reference](api-reference.md) links actual public interfaces. Applications
keep their vocabularies, source eligibility, judgments and manuscripts; shared
algorithms belong upstream with exact producer/source binding.

## Code standards

Use the declared Black/isort/flake8 and mypy configuration from
[pyproject.toml](../pyproject.toml). New public boundaries need precise types,
explicit schemas and meaningful failures. Prefer small modules, typed immutable
requests and real file/HTTP/CLI controls. Preserve named evidence errors and
source offsets rather than silently coercing another profile or swallowing an
unavailable result.

Corpus APIs are asynchronous where documented. Use an explicit corpus instance
and await its I/O methods. A local list slice does not constrain `analyze_all()`;
call `analyze_work(work.id)` for each selected work. Generic methods must remain
usable on Python 3.9 without optional model imports.

## Testing

Choose the affected gate from [verification](verification.md). The full stack,
installed dependency-light SDK, optional model availability, actual browser,
native output and scientific interpretation are distinct checks.

~~~sh
# Example full collection in its correctly provisioned environment
uv run --locked pytest tests/ -q

# Formatting/lint checks for a deliberately selected changed Python file
: "${OWNED_FILE:?Select the changed Python file}"
uv run --locked black --check "$OWNED_FILE"
uv run --locked isort --check-only "$OWNED_FILE"
uv run --locked flake8 "$OWNED_FILE"
~~~

Whole-package typing has documented legacy holds; a focused passing type gate
does not remove them. Use the exact current typing scope in the verification
guide. Formatting/check commands are not a claim that every historical source
file has just been reformatted or newly qualified.

For a changed custody or matching boundary, retain both a real positive case and
a refusing input: wrong caller pin, altered membership/span, occupied output or
unsupported option. Use real temporary files and local HTTP/subprocesses where
appropriate. Preserve every failed attempt and complete coverage denominator.
Documentation-only changes need link/command/claim checks, not unrelated model
campaigns or prose-pinning tests.

## Extending the package

| Extension | Owning protocol and acceptance |
|---|---|
| Source | Implement the actual [SourceProvider / SourceRegistry](../blake/corpus/sources.py) contract; keep direct text, catalog context, exclusions and provider terms distinct. Test against real local fixtures/HTTP. |
| Analysis | Extend [BlakeAnalyzer](../blake/analysis/analyzer.py) and its actual async entry points. Retain model/version/missingness and component errors separately from pipeline completion. |
| Export | Implement [BaseExporter](../blake/export/formats.py): async `export_works(works, output_dir, config)`, `export_work(work, output_path)` and `export_analysis_results(works, output_path)`. Register the class in `formats.EXPORTERS`, which the dispatcher copies into `self.exporters`. Test actual files and unsupported-format refusal. |
| Visualization | Extend the [visualization owners](../blake/viz/README.md); bind inputs, denominator, scope and output. Inspect affected rendered output. |
| Portable method | Keep domain-neutral mathematics/custody in [methods](shared-methods.md); retain distinct matching oracles and caller-held source identities. Qualify the exact SDK consumed by applications. |
| Manuscript | Follow [reproducibility](manuscript/08_reproducibility.md) and [authoring](manuscript/AGENTS.md). A changed paper needs its own native/output qualification. |

Source links define the complete protocols; this guide does not provide a
pass-only subclass or a parallel schema/registry implementation.

## Contributing and delivery

Read status, origin, current branch, staged scope and remote state before an
authorized commit. Preserve unrelated work; stage only owned paths and use an
ordinary non-force push through the repository's required route. Verify the
remote commit and retained artifact identities afterward. Hosted CI, package
publication, a manuscript build and a Zenodo deposit require their own evidence;
local test success supplies none of those claims automatically.
