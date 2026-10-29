---
project: blake
task: Initial publication hardening for the source-audited Blake corpus manuscript
effort: E4
phase: local-publication-ready
progress: 5/5
mode: algorithm
started: 2026-06-22
updated: 2026-06-23
---

# ISA - Blake Initial Publication Hardening

## Current State

The active corpus manuscript describes a source-audited Blake corpus pass with a `{{TARGET_TOTAL}}`-entry target ledger, `{{WORKS_PRESENT}}` local works, `{{TARGETS_PRESENT}}` fully evidenced targets, `{{WORKS_PARTIAL}}` partial targets, and `{{WORKS_MISSING}}` missing targets after token injection. Text-canon targets without primary Archive work ids may be represented by explicitly recorded Wikisource fallback text.

The publication object is local source-owned readiness: regenerated corpus artifacts, manuscript variables, figures, PDF, web output, and validation reports. It does not include GitHub publication, Zenodo deposition, public promotion, or new live acquisition beyond the bounded source audit.

## Active Publication Contract

- The manuscript reports a target-aware partial corpus, not William Blake's complete works.
- Representation, full evidence, partial evidence, fallback text evidence, missing targets, and source-audit status remain separate claims.
- ArXiv scholarship may support related work and future method paths only. It must not imply current LLM OCR, NER extraction, restoration, or knowledge-graph completion.
- Generated cover art is a manuscript design asset with provenance, not corpus evidence.
- Open-source distribution applies to the project code and project-authored outputs, not automatically to provider-supplied Blake Archive images, TEI, transcriptions, or local evidence caches.
- Figures are generated from `analysis_output/` JSON and local corpus metadata, retain existing filenames and labels, and may add only additional registry metadata.
- Public UI and script copy must use target-aware language while preserving command names such as "download all" when they describe an operation.
- Reproducibility instructions must use the real sibling-template gate: `uv run python scripts/04_validate_output.py --project working/blake`.
- TODO tracking is forward-only: no completed fixture-era checklist items, no stale past gates, and every upcoming item must be scoped.

## Initial Publication Gates

1. Scholarship: selected arXiv entries are integrated only in related-work, discussion, or limitation contexts that match their actual claims.
2. Claim hygiene: release-facing complete-corpus overclaims are removed and corpus claims remain tied to the tokenized target ledger.
3. Visualization strategy: manuscript figures have mini-brief metadata and the figure registry carries story, caveat and QA fields, including supplemental image/work-profile mosaics.
4. Reproducibility: corpus outputs, bounded source audit, figures, variables, PDF, and validation output have been regenerated with the current commands.
5. Release readiness: focused manuscript tests, rendered PDF/web QA, and forward-only TODO cleanup have been completed for local initial publication readiness.

## Verification Spine

```bash
uv run pytest tests/test_manuscript_tools.py -q
uv run python scripts/acquire_missing_texts.py
uv run blake corpus run --skip-download --output-dir analysis_output --fixture-mode never --viz-profile core --format json --archive-scope archive-inventory --image-mode archive-all --image-dpi 300 --max-images-per-work none
uv run blake corpus audit-sources --limit 16 --output-dir analysis_output --archive-scope archive-inventory
uv run python scripts/generate_manuscript_figures.py
TEMPLATE_REPO_ROOT=/path/to/template uv run python scripts/z_generate_manuscript_variables.py
cd /path/to/template
uv run python scripts/03_render_pdf.py --project working/blake
uv run python scripts/04_validate_output.py --project working/blake
```

## Historical Note

The prior fixture-era ISA criteria are closed history. They described a 38-target, 3-work demonstration and should not be used as active publication criteria for the current manuscript.
