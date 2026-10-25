# `blake/corpus/` — Corpus Workflow Package

The heart of the Blake platform: the target-aware corpus pipeline, canonical
target ledger, source providers/audit, evidence acquisition, visualization
generation, and public-release packaging. Exposed to users through
`uv run blake corpus ...` (see `../cli.py`) and the `BlakeCorpus` orchestrator
defined in `pipeline.py` and re-exported from the `blake` package.

## Canonical regeneration (from repo root)

```bash
uv run blake corpus run --quick --output-dir analysis_output
uv run blake corpus run --skip-download --output-dir analysis_output --fixture-mode never --viz-profile core --format json --archive-scope archive-inventory --image-mode archive-all --image-dpi 300 --max-images-per-work none
uv run blake corpus public-release-preflight --output-dir analysis_output --data-dir blake_data
uv run blake corpus public-release-package --output-dir analysis_output --data-dir blake_data
```

## Modules

| File | Role |
|------|------|
| `pipeline.py` | `BlakeCorpus` orchestrator — coordinates the whole workflow |
| `models.py` | Pydantic models: `CorpusConfig`, `SourceRecord`, `CorpusTargetEntry` |
| `targets.py` | Canonical target ledger (`canonical_target.json` + parsing) |
| `canonical_target.json` | Versioned ledger of works the corpus aims to hold |
| `sources.py` | `SourceProvider` protocol + providers (Blake Archive, Gutenberg, Internet Archive) |
| `source_audit.py` | Provider/source health classification, missing-evidence candidates |
| `evidence_acquisition.py` | Pulls evidence flagged by the audit; builds acquisition review |
| `release_preflight.py` | Private-release preflight + rights-gate reports |
| `public_release.py` | Public-release staging: assets, exclusions, corroboration records |
| `visualizations.py` | Lexical/bigram analysis + coverage-matrix visuals |

Artifacts land under `analysis_output/` (see repo README for layout).
