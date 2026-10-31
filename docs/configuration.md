# Configuration Guide

## Overview

Corpus runtime settings are passed explicitly through `CorpusConfig`, the `BlakeCorpus` constructor or `blake corpus` options. This surface does not automatically load a global config file or arbitrary environment overrides. Manuscript authoring and workspace storage have separate explicit inputs, described below.

## Configuration Methods

### 1. Programmatic Configuration

```python
from pathlib import Path

from blake import BlakeCorpus, CorpusConfig

config = CorpusConfig(
    data_dir=Path("./blake_data"),
    output_dir=Path("./analysis_output"),
    quick=True,
    fixture_mode="auto",
    viz_profile="core",
    archive_scope="archive-inventory",
    image_mode="archive-all",
    image_dpi=300,
    export_formats=["json"],
    max_workers=4,
)

corpus = BlakeCorpus(config=config)
```

`BlakeCorpus(data_dir, *, output_dir=..., config=...)` also accepts the data and
output directories directly; either overrides the matching config field.

### 2. `CorpusConfig` Fields

| Field | Default | Meaning |
|-------|---------|---------|
| `data_dir` | `blake_data` | Local corpus, metadata, and cache root |
| `output_dir` | `analysis_output` | Root for pipeline artifacts |
| `quick` | `False` | Offline run; seeds a fixture corpus when the cache is empty |
| `force` | `False` | Re-fetch records instead of reusing local copies |
| `skip_download` | `False` | Reuse captured sources; analysis still runs |
| `skip_analysis` | `False` | Skip the analysis phases |
| `skip_visualizations` | `False` | Skip visualization generation |
| `skip_export` | `False` | Skip export generation |
| `skip_reports` | `False` | Skip report generation |
| `analysis_types` | `None` (all) | Subset of analysis components to run |
| `export_formats` | `["json"]` | Export formats written by the run |
| `target_profile` | `canonical` | Target-ledger profile used for coverage |
| `fixture_mode` | `auto` | `auto` / `always` / `never` fixture corpus use |
| `viz_profile` | `core` | `inventory` / `core` / `full` visualization depth |
| `archive_scope` | `archive-inventory` | `target-ledger` / `archive-inventory` discovery scope |
| `image_mode` | `archive-all` | `representative` / `archive-all` image metadata depth |
| `image_dpi` | `300` | Requested image resolution |
| `max_images_per_work` | `None` (all) | Image cap per work |
| `max_workers` | `4` | Declared run setting; actual concurrency is determined by the selected component |

### 3. Command Line Configuration

```bash
# Global options
blake --data-dir /path/to/data --output-dir /path/to/output --verbose corpus run --quick

# Run profiles
blake corpus run --quick --fixture-mode auto --viz-profile core
blake corpus run --skip-download --output-dir analysis_output --fixture-mode never \
  --viz-profile core --format json --archive-scope archive-inventory \
  --image-mode archive-all --image-dpi 300 --max-images-per-work none

# Coverage and visualization inspection
blake corpus status --coverage
blake corpus visualize --profile core

# Interactive surfaces
blake explore --host localhost --port 8501

# Image recovery concurrency (1-8)
blake corpus recover --image-workers 4
```

## Manuscript and workspace settings

The paper's YAML is [docs/manuscript/config.yaml](manuscript/config.yaml),
interpreted by its separately pinned native framework. It is not a corpus-run
configuration file. Project preparation tools accept
`BLAKE_MANUSCRIPT_EVIDENCE_ROOT` for an explicit evidence epoch and
`TEMPLATE_REPO_ROOT` for the selected template checkout. See the
[style contract](style-guide.md) and [reproduction workflow](manuscript/08_reproducibility.md).
Explicit evidence selection is recorded; it does not rename a historical producer.

`TMPDIR`, outer-shell `TMPPREFIX`, `UV_CACHE_DIR`, `UV_PROJECT_ENVIRONMENT`,
`UV_PYTHON` and `UV_LINK_MODE=copy` are storage/toolchain bindings. In managed
GitVault work they must select the mounted external workspace and appropriate
project interpreter. Verify both Python prefixes before source work. These
bindings are not undocumented `CorpusConfig` fields.

## Notes

- Synthetic fixture records are labeled in `corpus_manifest.json`; a quick run
  proves the workflow surface and never implies whole-oeuvre completeness.
- Release-readiness settings are command options, not config keys: see
  `blake corpus private-release-preflight`, `blake corpus public-release-preflight`,
  and `blake corpus public-release-package` in the [CLI reference](api-reference.md#corpus-cli).
- Recovery, backup, search, and manuscript tooling keep their own arguments; see
  [text-search.md](text-search.md) and the recovery commands in
  `blake corpus --help`.
