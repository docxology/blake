# AGENTS: `scripts/` — Thin Orchestrator Scripts

Technical specification for the blake repo's maintenance scripts.

## Thin-Orchestrator Contract

- Scripts are orchestration only: path bootstrap (shared helper
  `bootstrap.project_root()`), argparse, logging, and a single delegated call
  into a `blake/` or `manuscript_tools/` entrypoint.
- No analytical, plotting, download, or repair logic here — import from
  `blake/` or `manuscript_tools/`. Data-as-code tables (work registries,
  ID lists) live in `blake/` next to the code that uses them.
- Scripts route paths from `Path(__file__)` (via `bootstrap.project_root()`),
  never from the caller's cwd.
- Reusable script behavior is covered by tests in `tests/` (moved logic:
  `tests/test_text_repair.py`, `tests/test_gutenberg_redownload.py`,
  `tests/test_target_corpus.py`, `tests/test_viz_generate_visualizations.py`).
- Human overview: `README.md` here. Repo-wide policy: see the lane-level
  policy at `/Volumes/external_drive/Git/template/projects/ongoing/AGENTS.md`
  (local-only tree, symlinked into the template checkout; never commit).

## Script Inventory

| Script | Pattern | Delegates to |
|--------|---------|--------------|
| `run_pipeline.sh` | Shell wrapper | `run_all.py` |
| `download_complete_corpus.py` | Thin orchestrator (network) | `blake.downloader.target_corpus.download_target_corpus` |
| `download_complete_archive.py` | Thin orchestrator (network) | `blake.downloader.blake_archive_scraper.BlakeArchiveScraper` |
| `acquire_missing_texts.py` | Thin-ish orchestrator (network) — Wikisource fetch logic still inline, targeted by a future pass | `blake.metadata` persistence |
| `redownload_texts.py` | Thin orchestrator (network) | `blake.downloader.gutenberg_redownload.redownload_texts` |
| `fix_text_files.py` | Thin orchestrator | `blake.corpus.text_repair.fix_text_files` |
| `migrate_filenames.py` | Thin-ish orchestrator | `blake.metadata.manager`, `blake.utils.file_utils` |
| `repopulate_db.py` | Thin-ish orchestrator | `blake.metadata.manager` |
| `generate_visualizations.py` | Thin orchestrator | `blake.viz.generate_visualizations.generate_all_visualizations` |
| `generate_manuscript_figures.py` | Thin orchestrator | `manuscript_tools.figures`, `manuscript_tools.cover` |
| `generate_cover_image.py` | Thin orchestrator | `manuscript_tools.cover` |
| `z_generate_manuscript_variables.py` | Thin orchestrator (template-pipeline hook, `z_` = runs last) | `manuscript_tools.variables`, `infrastructure.rendering.manuscript_injection` |

## Notes

- `z_generate_manuscript_variables.py` reads `analysis_output/` artifacts, so
  it fails (or drafts) if the corpus run hasn't happened. Run
  acquisition/analysis first. It locates the template repo root via
  `TEMPLATE_REPO_ROOT` (see its `_find_repo_root`).
- Network-touching scripts (`download_*`, `acquire_*`, `redownload_*`) hit
  external archives — run deliberately, not in doc/CI passes.
- Verify locally: `uv run python scripts/<script>.py --help`; full behaviour
  requires data.
- 2026-09 scripts audit: the logic formerly inline in
  `generate_visualizations.py`, `fix_text_files.py`, `redownload_texts.py`,
  and `download_complete_corpus.py` was moved verbatim into
  `blake/viz/generate_visualizations.py`, `blake/corpus/text_repair.py`,
  `blake/downloader/gutenberg_redownload.py`, and
  `blake/downloader/target_corpus.py`; `repopulate_db.py` now resolves
  `data/blake` from the script location instead of cwd.
