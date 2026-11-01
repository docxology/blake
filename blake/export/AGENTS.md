# Corpus export and optional API

Follow the [repository contract](../../AGENTS.md), [rights/method profiles](../../docs/methods.md) and [verification guide](../../docs/verification.md).

[BlakeExporter](exporter.py) orchestrates corpus exports:
`await exporter.export_works(works, config)`, where `config` is
`blake.models.ExportConfig` and owns the output directory. Its timestamped
subdirectory is not an immutable evidence epoch; callers must select safe new
output custody and retain original inputs. Compression removes that newly
created uncompressed export directory, so never point it at retained evidence.

[Format handlers](formats.py) have a different contract:
`await get_exporter("html").export_works(works, output_dir, config)`.
`get_exporter` returns JSON, CSV, PDF, HTML, Markdown/`md` or Parquet handlers.
Keep output extensions, empty-input behavior, provenance and structured analysis
fields consistent with the selected format. PDF uses ReportLab when available;
dependency availability is not a qualified native manuscript render. Corpus
exports are separate from the pinned docxology/template paper workflow.

[BlakeAPI](api.py) owns the optional FastAPI app at `BlakeAPI(corpus).app`.
Routes include `GET /works`, `GET /works/{work_id}`,
`GET /works/{work_id}/analysis`, `POST /works/{work_id}/analyze`,
`GET /search?q=...`, `GET /statistics`, `GET /export/{work_id}?format=...`
and `GET /health`. Preserve status codes, typed error responses, pagination
and rights/source metadata. Do not start a server to verify pure export changes.

Use the `full` capability for corpus exports, adding `api` for API work.
Test real temporary output files and real local requests as appropriate; never
substitute a mocked writer for an export gate. A successful export grants no
redistribution permission for provider content or private application material.
