# Reproducibility: Regenerating Evidence, Figures, Web, and PDF Outputs {#sec:reproducibility}

The manuscript is generated from the same artifacts that drive the corpus workbench. This design treats reproducibility as an artifact relation: source records, local files, analysis outputs, figures, variables, and manuscript claims can be regenerated and inspected as a chain rather than as disconnected products [@peng2011reproducible; @sandve2013ten; @wilson2014best; @w3cprov2013overview]. The preservation target is therefore not a single PDF snapshot, but the documented relation among inputs, local cache state, commands, hashes, derived JSON, figures, and rendered outputs [@owens2018digitalpreservation]. Reproduction begins by refreshing the bounded live source audit with the same Archive API sample size reported in the methods:

```bash
uv run blake corpus audit-sources --limit {{ARCHIVE_API_SAMPLE_LIMIT}} --output-dir analysis_output --archive-scope archive-inventory
```

The audit records {{SOURCE_RECORDS_DISCOVERED}} discovered source records, {{SOURCE_MATCHED_TARGETS}} matched target records, {{SOURCE_UNMATCHED_TARGETS}} unmatched source-discovery target records, {{PROVIDER_DISCOVERY_FAILURES}} provider discovery failures, the {{SOURCE_URL_CHECKED}} reviewed source endpoints shown in [@tbl:source_audit], and the missing-evidence candidates shown in [@tbl:supp_missing_evidence]. It also records Archive metadata enrichment as `{{ARCHIVE_METADATA_STATUS}}` with {{ARCHIVE_METADATA_SUCCEEDED}} of {{ARCHIVE_METADATA_ATTEMPTED}} attempts succeeding, so a successful local run cannot hide live API degradation.

Validated fallback text evidence is then pulled only from audit candidates that pass the confidence and authority policy:

```bash
uv run blake corpus acquire-evidence --from-audit analysis_output/data/source_audit.json
```

For an optional object-depth acquisition refresh, the acquisition pass uses the opt-in Archive mirror mode. This is a remote acquisition refresh, not the saved local rerun reported here; use it only when the local evidence cache needs to be rebuilt under the source providers' terms:

```bash
uv run blake corpus run --output-dir analysis_output --fixture-mode never --viz-profile core --format json --archive-scope archive-inventory --image-mode archive-all --image-dpi 300 --max-images-per-work none
```

The main corpus outputs can then be regenerated from local data without reacquiring remote assets. This is the command used for the saved analysis state reported here; it reruns text, visual, cross-modal, and ontology analysis over the existing local corpus:

```bash
uv run blake corpus run --skip-download --output-dir analysis_output --fixture-mode never --viz-profile core --format json --archive-scope archive-inventory --image-mode archive-all --image-dpi 300 --max-images-per-work none
```

This command rebuilds the manifest, current analysis results, analysis diagnostics, visualization datasets, exports, and reports without reacquiring remote assets. The run reported here completed with status {{RUN_STATUS}}, processed {{WORKS_PRESENT}} local works, analyzed {{ANALYSIS_WORKS_ANALYZED}} of {{ANALYSIS_WORKS_TOTAL}} works with analysis status `{{ANALYSIS_STATUS}}`, and wrote a manifest with {{TARGET_TOTAL}} target entries. The analysis ledger marks current results as `{{ANALYSIS_RESULTS_CURRENT}}`, records {{ANALYSIS_ERROR_COUNT}} analysis errors, and exposes {{ANALYSIS_DIAGNOSTIC_SECTIONS}} diagnostics. It also refreshes the source-audit payload with coverage-aware missing-evidence candidates when a manifest is available.

The manuscript cover, cover provenance, and figures are regenerated from the JSON artifacts:

```bash
uv run python scripts/generate_manuscript_figures.py
```

The cover asset is written to `output/cover/cover_blakean.png`, and its prompt/provenance record is written to `analysis_output/data/cover_image_provenance.json`. The cover is configured through `paper.cover.image` in `manuscript/config.yaml`, so the sibling template renderer uses the same release-safe cover path as the PDF title page. A future release package could expose the same corpus, manuscript, preservation, and provenance relationships through a research-object packaging format rather than only through the project tree [@owens2018digitalpreservation; @rocrate2022].

The manuscript token layer is then hydrated by the rendering pipeline, or directly with the template repository on the import path:

```bash
TEMPLATE_REPO_ROOT=/path/to/template uv run python scripts/z_generate_manuscript_variables.py
```

Finally, from the sibling template repository, the PDF can be rendered and the publication output can be validated:

```bash
uv run python scripts/03_render_pdf.py --project working/blake
uv run python scripts/04_validate_output.py --project working/blake
```

No result number in the manuscript body is hand-entered. Values such as {{WORKS_PRESENT}} local works, {{TARGETS_PRESENT}} present targets, {{WORDS_TOTAL}} words, {{TOTAL_IMAGES}} images, {{IMAGE_DEPTH_DOWNLOADED_IMAGES}} downloaded object images, {{NETWORK_NODES}} graph nodes, {{NETWORK_EDGES}} graph edges, {{MISSING_EVIDENCE_CANDIDATES}} missing-evidence candidates, and {{ACQUISITION_REVIEW_MANUAL_CANDIDATES}} manual-review source leads are injected from `output/data/manuscript_variables.json`, which is itself computed from `analysis_output/`. This keeps the prose, tables, figures, and gap-search narrative synchronized with the latest corpus run. If the software is released as a citable research tool, the corpus paper should also provide software citation metadata rather than treating code as an invisible implementation detail [@smith2016software].
