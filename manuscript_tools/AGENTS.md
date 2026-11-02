# `manuscript_tools/` — Agent Notes

Read the [repository contract](../AGENTS.md), [style guide](../docs/style-guide.md),
[manuscript authoring contract](../docs/manuscript/AGENTS.md) and
[reproduction workflow](../docs/manuscript/08_reproducibility.md). The human overview
is [README.md](README.md). Native template source/runtime and its ignored lifecycle
binding are qualified separately; no historical machine path selects them.

## Invariants / gotchas

- **No hard-coded metrics.** Per repo config contract, numbers in the paper
  come from the explicitly selected evidence root via `variables.py` token injection; never
  paste literal counts into prose or config titles/subtitles.
- Keep new mechanisms in focused modules. `figure_dispatch.py` orchestrates the
  registry; `figures.py` retains the large existing builder inventory. Add small
  dispatch registrations while preserving saved input/profile contracts.
- These modules are imported by repo-root scripts, not by the `blake` package;
  they are a parallel Layer-2 support package for the paper.
- `paths.py` separates authoring/output from evidence reads. Use `--evidence-root`
  or `BLAKE_MANUSCRIPT_EVIDENCE_ROOT`; explicit invalid roots fail without fallback.
- Source-derived profile and interval figures bind current code independently of
  the saved analytical producer. Didactic interval coordinates are mathematical
  examples, not corpus measurements.
- Figure/hydration commands and the separate pinned template API belong to the
  reproduction workflow. Strict hydration rejects unknown or empty used tokens.
  Use mounted GitVault, external runtime prefixes/TMP/caches and a fresh accounted
  output epoch; retain previous outputs and failures.
