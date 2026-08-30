# `blake/corpus/` — Agent Notes

Agent-facing map for the corpus workflow package. Human overview: see
`README.md` here; repo-wide policy: See the lane-level policy at `/Volumes/external_drive/Git/template/projects/ongoing/AGENTS.md` (local-only tree, symlinked into the template checkout; never commit).

## Layout

| File | Invariants / gotchas |
|------|----------------------|
| `pipeline.py` | Defines `BlakeCorpus`. Largest module (~70 KB). Entry for `blake corpus run`. |
| `models.py` | Pydantic models (`CorpusConfig`, `SourceRecord`, `CorpusTargetEntry`). Validation happens here — do not bypass. |
| `targets.py` + `canonical_target.json` | Completeness is measured against the versioned ledger, never assumed from local files. Editing the JSON is a content decision, not a code fix. |
| `sources.py` | `SourceProvider` Protocol; providers are async-first. |
| `source_audit.py` | Produces `source_audit.json` / `source_discovery_health.json`; reason codes are stable strings downstream `jq` filters rely on — do not rename. |
| `evidence_acquisition.py` | Consumes audit output; emits `evidence_acquisition_review.json`. |
| `release_preflight.py` / `public_release.py` | Local staging only — never publish, tag, or deposit. `archive-all` is evidence depth, NOT a redistribution permission. |
| `visualizations.py` | Coverage matrix (PNG + JSON); pure functions over tokens. |

## Verify

```bash
uv run pytest tests/ -k corpus -v
uv run blake corpus run --quick --output-dir /tmp/ao
```

Unverified claims above are from code inspection on 2026-08-29; no full run was executed in this documentation pass.
