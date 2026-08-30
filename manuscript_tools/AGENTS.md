# `manuscript_tools/` — Agent Notes

Human overview: `README.md` here. Repo-wide policy: See the lane-level policy at `/Volumes/external_drive/Git/template/projects/ongoing/AGENTS.md` (local-only tree, symlinked into the template checkout; never commit).

## Invariants / gotchas

- **No hard-coded metrics.** Per repo config contract, numbers in the paper
  come from `analysis_output/` via `variables.py` token injection; never
  paste literal counts into prose or config titles/subtitles.
- `figures.py` is very large (~107 KB) — prefer extending `variables.py` or a
  new module over growing it further.
- These modules are imported by repo-root scripts, not by the `blake` package;
  they are a parallel Layer-2 support package for the paper.
- Verify: `uv run python scripts/z_generate_manuscript_variables.py` (unverified
  in this doc pass; it may require `analysis_output/` artifacts to exist).
