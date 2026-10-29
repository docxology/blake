# `scripts/` — Thin Orchestrators (blake repo)

Maintenance, acquisition, and manuscript-support scripts. All logic lives in
`blake/` (mainly `blake/corpus/`, `blake/downloader/`, `blake/viz/`) or
`manuscript_tools/`; these scripts only bootstrap paths, parse args, and
delegate to a single package entrypoint.

| Script | Purpose | Delegates to | Command |
|--------|---------|--------------|---------|
| `run_pipeline.sh` | Shell wrapper for the canonical pipeline (syncs uv env, forwards options) | `run_all.py` | `./scripts/run_pipeline.sh [--quick]` |
| `download_complete_corpus.py` | Target-aware corpus download (Gutenberg + Blake Archive TEI), writes `MANIFEST.json` | `blake.downloader.target_corpus` | `uv run python scripts/download_complete_corpus.py` |
| `acquire_missing_texts.py` | Fill ledger gaps from Wikisource | `blake.metadata` (persistence; fetch logic still inline — see AGENTS.md) | `uv run python scripts/acquire_missing_texts.py` |
| `redownload_texts.py` | Re-pull Gutenberg texts, replacing corrupted EPUB-mislabeled files | `blake.downloader.gutenberg_redownload` | `uv run python scripts/redownload_texts.py` |
| `fix_text_files.py` | Repair `.txt` files that are actually EPUBs (rename + extract real text) | `blake.corpus.text_repair` | `uv run python scripts/fix_text_files.py` |
| `migrate_filenames.py` | Rename text files to the canonical `<id>_<title>.txt` scheme | `blake.metadata.manager`, `blake.utils.file_utils` | `uv run python scripts/migrate_filenames.py` |
| `repopulate_db.py` | Rebuild the SQLite metadata DB from downloaded JSON | `blake.metadata.manager` | `uv run python scripts/repopulate_db.py` |
| `generate_visualizations.py` | Standalone corpus visualizations (text/temporal/network/comparative/image) | `blake.viz.generate_visualizations` | `uv run python scripts/generate_visualizations.py` |
| `generate_manuscript_figures.py` | Paper figures into `output/figures/` | `manuscript_tools.figures`, `manuscript_tools.cover` | `uv run python scripts/generate_manuscript_figures.py` |
| `generate_cover_image.py` | Cover image generation | `manuscript_tools.cover` | `uv run python scripts/generate_cover_image.py` |
| `z_generate_manuscript_variables.py` | Produces `output/data/manuscript_variables.json` and injects manuscript variables (runs last by convention) | `manuscript_tools.variables`, `infrastructure.rendering.manuscript_injection` | `uv run python scripts/z_generate_manuscript_variables.py` |

`bootstrap.py` is the shared path-bootstrap helper the scripts import; it is
not a runnable orchestrator.
