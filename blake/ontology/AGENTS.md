# `blake/ontology/` — Agent Notes

Small, mostly-static knowledge module. Each file carries its own module
docstring; public surface is defined in `__init__.py`. Human overview:
`README.md` here. Repo-wide policy: See the lane-level policy at `/Volumes/external_drive/Git/template/projects/ongoing/AGENTS.md` (local-only tree, symlinked into the template checkout; never commit).

- `concepts.py`, `themes.py`, `symbols.py` define data + detectors; keep
  entries scholarly and cite-worthy (this project treats wrong public claims
  as worse than missing data).
- `export.py` output formats are consumed downstream; changing a schema key is
  a breaking change for any saved exports.
- Verify with `uv run pytest tests/ -k ontology -v` (unverified whether
  ontology-specific tests exist; check `tests/` before relying on that filter).
