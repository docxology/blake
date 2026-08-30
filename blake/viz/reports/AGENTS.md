# `blake/viz/reports/` — Agent Notes

Human overview: `README.md` here. Repo-wide policy: See the lane-level policy at `/Volumes/external_drive/Git/template/projects/ongoing/AGENTS.md` (local-only tree, symlinked into the template checkout; never commit).

- Sibling subpackages: `dashboards/`, `engines/`, `integrations/`,
  `renderers/`, `reports/` — every child of `blake/viz/` is documented; none
  is undocumented.
- Renderers must stay headless-safe (`MPLBACKEND=Agg`) so pipeline runs work
  on servers; don't import pyplot at module import time.
- `engines/data_processor.py` is the shared normalization layer; renderers
  should not re-implement it.
- Verify: `uv run pytest tests/ -k viz -v` (unverified — check `tests/` for
  actual viz test coverage before relying on it).
