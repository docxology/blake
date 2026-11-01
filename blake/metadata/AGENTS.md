# Metadata storage and search

Follow the [repository contract](../../AGENTS.md), [application boundary](../../docs/applications.md) and [verification profiles](../../docs/verification.md).

| Owner | Contract |
|---|---|
| [MetadataManager](manager.py) | Async orchestration: `process_work`, `save_work`, `load_work`, `load_all_works` and `search_works`. |
| [MetadataDatabase](database.py) | Synchronous SQLite persistence. The `works`, `images` and `analysis_results` tables preserve distinct work, image and saved-result units. |
| [MetadataProcessor](processor.py) | Async `process_work` normalizes/enhances a `BlakeWork`; inferred fields remain distinguishable from provider evidence. |
| [MetadataSearcher](search.py) | Synchronous in-memory `search_works(works, query, filters=None)`, relevance, facets and suggestions. |

Use the manager for corpus orchestration. Keep database migrations and saved
analysis round trips lossless: top-level analyses, nested unavailability, source
roles, rights, identifiers and image relations must survive reloads. Exercise
real temporary SQLite files when changing persistence. A title/description match
or inferred tag does not establish literary authorship or a verified mention.

The [portable methods](../../docs/shared-methods.md) own application retrieval
and evidence schemas. Applications consume explicit exports, not these internal
tables. Pipeline metadata search is distinct from pinned passage concordances;
do not merge their semantics or invent FTS guarantees from the SQLite indexes.

This module belongs to the optional `full` capability. Use its pinned Python
3.11 environment and scoped real-file tests; see the verification guide before
collecting the complete optional stack. No network acquisition or model download
is required for a metadata-only repair.
