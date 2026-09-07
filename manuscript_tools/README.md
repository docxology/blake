# `manuscript_tools/` — Manuscript Support Package

Python package backing the blake corpus paper (`docs/manuscript/` at repo root):
cover image generation, manuscript figures, NLP diagnostics, and the
manuscript-variable producer that feeds template token substitution.

| File | What it does |
|------|--------------|
| `cover.py` | `generate_cover()` — builds the cover from `docs/manuscript/assets/cover_blakean_source.png` (or draws one if absent) |
| `figures.py` | Manuscript figures from `analysis_output/` artifacts |
| `nlp_diagnostics.py` | Builds/saves NLP diagnostics for the paper |
| `variables.py` | Manuscript-variable producer (auto-injected at render; no hard-coded counts) |

Invoked by `scripts/z_generate_manuscript_variables.py` and
`scripts/generate_manuscript_figures.py` (thin orchestrators at repo root).
