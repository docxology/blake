# Source-Governed Acquisition Workflow

Use the corpus workflow for source-governed acquisition and local regeneration. Compatibility download scripts are useful for debugging provider adapters, but docs/manuscript/release validation should be driven through `blake corpus run`, source audit, evidence review, and rights-gate artifacts.

## Usage

### Basic Usage
```bash
# Offline smoke run
uv run blake corpus run --quick --output-dir analysis_output

# Main local regeneration; reuses local evidence and reruns analysis
uv run blake corpus run --skip-download --output-dir analysis_output --fixture-mode never --viz-profile core --format json --archive-scope archive-inventory --image-mode archive-all --image-dpi 300 --max-images-per-work none

# Optional live audit/review surfaces
uv run blake corpus audit-sources --output-dir analysis_output --archive-scope archive-inventory
uv run blake corpus acquire-evidence --from-audit analysis_output/data/source_audit.json --dry-run
```

## Features

### Source Discovery
- Discovers records through registered providers.
- Records provider health and stable `reason_code` values in `source_discovery_health.json`.
- Separates discovered records, accepted local evidence, rejected candidates, and manual-review leads.

### Manual Source Leads
- `docs/source-leads.json` is a manual-review lead registry, not accepted evidence.
- A lead can move toward accepted evidence only after exact title or alias match, source ownership or authority-tier review, stable source URL, attribution, license or terms note, checksum, rights disposition, and regenerated coverage are recorded.
- Search pages, app shells, bibliography-only pages, and source leads without exact title validation remain rejection or manual-review cases.

### Local Evidence Refresh
- Leverages the internal robust downloading mechanisms of the Blake package
- Automatic retry and error handling logic inherited from the core library
- Treats `archive-all` as local evidence-depth acquisition, not redistribution permission

## Output Structure

Raw data is saved to `blake_data/`; reproducible run artifacts are saved to `analysis_output/`.

```
blake_data/
├── texts/                    # Downloaded text files
├── images/                   # Downloaded images
├── metadata/                 # Work metadata
└── ...
```
