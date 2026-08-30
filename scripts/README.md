# `scripts/` — Thin Orchestrators (blake repo)

Maintenance, acquisition, and manuscript-support scripts. All logic lives in
`blake/` (mainly `blake/corpus/`) or `manuscript_tools/`; these scripts only
orchestrate I/O.

| Script | What it does |
|--------|--------------|
| `run_pipeline.sh` | Shell wrapper for the canonical pipeline |
| `download_complete_corpus.py` / `download_complete_archive.py` | Full-corpus / full-Archive acquisition |
| `acquire_missing_texts.py` / `redownload_texts.py` | Fill ledger gaps / re-pull texts |
| `fix_text_files.py` | Normalize downloaded text files |
| `migrate_filenames.py` | Rename files to canonical scheme |
| `repopulate_db.py` | Rebuild the SQLite metadata DB |
| `generate_visualizations.py` | Standalone viz generation |
| `generate_manuscript_figures.py` | Paper figures via `manuscript_tools.figures` |
| `generate_cover_image.py` | Cover generation via `manuscript_tools.cover` |
| `z_generate_manuscript_variables.py` | Produces `output/data/manuscript_variables.json` for template rendering (runs last by convention) |
