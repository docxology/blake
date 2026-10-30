# Blake corpus and methods guidance

This repository owns reusable corpus acquisition, source custody, recovery,
portable schemas, retrieval, statistics and evidence methods. Applications own
their vocabularies, contextual judgments, domain models and manuscripts. Keep
new generic logic here and qualify the exact source adopted by each application.

## Choose the contract before editing

| Change | Read |
|---|---|
| Current status or next work | [Project status](docs/PROJECT_STATUS.md) and [verification scope](docs/verification.md) |
| Portable corpus, application integration or migration | [Application contract](docs/applications.md) and [shared methods](docs/shared-methods.md) |
| Matching, schemas, statistics, proximity, composition or hierarchy | [Shared methods](docs/shared-methods.md), the relevant module tests and [style guide](docs/style-guide.md) |
| Acquisition, recovery, NLP, vision or GUI | [README workflows](README.md), [method profiles](docs/methods.md) and the declared extras in `pyproject.toml` |
| Paper, figures, rendering or publication | [Reproducibility](docs/manuscript/08_reproducibility.md), [style guide](docs/style-guide.md) and the exact deposited identities in `publication.json` |

The default dependency-light installation serves portable methods. The active
corpus pipeline and NLP/vision capabilities use `full`; GUI/API and complete
test collection require their documented extras. Preserve those capabilities
when removing obsolete duplication. `BlakeCorpus` remains the corpus API; use
explicit `blake.applications`, `blake.studies` and `blake.methods` interfaces for
application evidence instead of an internal SQLite layout.

## Preserve evidence and working custody

- Follow the mounted GitVault contract and supported repository/common-store
  lease. Keep source, environments, caches and temporary files external; verify
  both Python prefixes. Preserve peer work and existing output epochs.
- Use caller-held pins and explicit schema conversion. Retain original source
  roles, authorship, copies, locators and offsets. A retrieval candidate is not
  an adjudicated literary mention; a zero is scoped to declared inputs.
- Give changed inputs, methods, selections and outputs new epochs. Keep each
  historical producer, failed attempt and reading ceiling attached to its bytes.
- Keep raw provider expression, full corpus bundles, search indexes and private
  application material in their authorized ignored custody. `publication.json`
  identifies the deposited paper; a later documentation commit does not create
  a new software, manuscript or Zenodo release.

## Qualify and deliver

Use `uv` and the pinned project toolchain. Follow [the verification guide](docs/verification.md)
for the Python 3.9 methods and Python 3.11 optional-stack gates, real local
fixtures/HTTP controls, installed-wheel checks and their distinct coverage
floors. Reproduce the failure and exercise a refusing control before declaring
a repair complete. Documentation changes need link/command/claim checks, not
tests that pin prose or a replay of unrelated heavy workloads.

For changed manuscripts, run the actual pinned template workflow, inspect the
physical output and bind source, native and publication evidence separately.
Before an authorized push, check staged scope, preserve private content, use an
ordinary non-force push and verify the remote head. Record unresolved scholarly,
image, browser/accessibility, hosted-CI and rights gates explicitly.
