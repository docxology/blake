# Target-aware corpus orchestration

Follow the [repository contract](../../AGENTS.md), [workflow guide](../../README.md),
[method profiles](../../docs/methods.md) and [verification guide](../../docs/verification.md).

| Owner | Invariant |
|---|---|
| [pipeline.py](pipeline.py) | `BlakeCorpus` coordinates acquisition, metadata, optional analysis, visualizations, export and reports. It remains the corpus API; [blake/cli.py](../cli.py) registers the `blake corpus` commands. |
| [models.py](models.py) | `CorpusConfig`, `SourceRecord`, target/coverage and phase models validate pipeline boundaries. |
| [targets.py](targets.py), [canonical_target.json](canonical_target.json) | Completeness is measured against the versioned target ledger. A ledger change is a content decision. Local files alone establish no completeness. |
| [sources.py](sources.py) | Async `SourceProvider.discover()` and `fetch(record, ...)` preserve source/copy identity and bounded acquisition policy. |
| [source_audit.py](source_audit.py) | Source/audit health and missing-evidence reason codes remain stable downstream contracts. |
| [evidence_acquisition.py](evidence_acquisition.py) | Audit-driven acquisition retains failures and original evidence. |
| [release_preflight.py](release_preflight.py), [public_release.py](public_release.py) | Local release staging only. Archive depth and image acquisition options confer no redistribution rights. |
| [visualizations.py](visualizations.py), [network.py](network.py) | Source-derived coverage/lexical graphics retain their denominators and explicit heuristic limits. |

The pipeline belongs to the optional `full` Python 3.11 capability. Its
constructor creates data/output directories and initializes orchestration
components; avoid constructing it for dependency-light shared-method imports.
Use explicit `blake.applications`, `blake.studies` and `blake.methods` contracts
for applications instead of internal SQLite layouts.

Choose a scoped test lane from the verification guide. A changed provider needs
real local HTTP and invalid/missing-response controls; changed saved data needs
real SQLite/file round trips. A quick fixture run is a separate bounded
operation in a new GitVault data/output epoch, not routine proof of live corpus
coverage. Never rerun acquisition, recovery or native production merely to
check documentation. Keep all inputs, caches, temporary files, result epochs
and failed attempts on GitVault under supported leases.
