# `scripts/` — Agent Notes (blake repo)

Thin-orchestrator rule applies: no analytical logic here — import from
`blake/` or `manuscript_tools/`. Human overview: `README.md` here.
Repo-wide policy: See the lane-level policy at `/Volumes/external_drive/Git/template/projects/ongoing/AGENTS.md` (local-only tree, symlinked into the template checkout; never commit).

- `z_generate_manuscript_variables.py` is the template-pipeline hook; it reads
  `analysis_output/` artifacts, so it fails (or drafts) if the corpus run
  hasn't happened. Run acquisition/analysis first.
- Network-touching scripts (`download_*`, `acquire_*`, `redownload_*`) hit
  external archives — run deliberately, not in doc/CI passes.
- Verify locally: `uv run python scripts/fix_text_files.py --help` style
  checks; full behaviour requires data (unverified in this pass).
