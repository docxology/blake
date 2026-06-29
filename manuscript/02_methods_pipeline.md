# Methods: Target Ledger, Source Audit, and Local Acquisition {#sec:methods_pipeline}

The *blake* pipeline is organized as a {{PHASE_COUNT}}-phase DAG: discovery, acquisition, metadata, analysis, visualizations, export, and reports. [@fig:pipeline_dag] shows the execution structure. Discovery builds normalized source records; acquisition materializes local works; metadata writes the manifest; analysis enriches works with text, visual, cross-modal, and ontology outputs; visualization and reporting serialize reader-facing evidence. The run reported here completed {{PHASES_COMPLETED}} phases with status {{RUN_STATUS}}; phases not rerun in a given validation command are shown as reuse or not-rerun states rather than as missing evidence. The pipeline is deliberately manuscript-facing: the same JSON artifacts that validate the run also populate tables, captions, and quantitative prose, following scientific-computing practice around automation, versioned artifacts, and reproducible computational claims [@sandve2013ten; @wilson2014best].

![Saved corpus workflow as a {{PHASE_COUNT}}-phase directed acyclic graph. Phase cards report the saved-run action for each phase: acquisition reused the existing local corpus without a live re-fetch and is marked as reused existing local evidence, while analysis and downstream reporting generated current artifacts. Each card prints the evidence or artifact count used by downstream manuscript outputs. The diagram is a provenance view of this target-ledger run, not a claim that every external Blake source has been mirrored.](../output/figures/pipeline_dag.png){#fig:pipeline_dag}

## Target Ledger: Work-Level Denominator for Coverage Claims

The completeness authority is the target ledger under the {{TARGET_PROFILE}} profile, version {{TARGET_VERSION}}, with {{TARGET_TOTAL}} work-level entries. The ledger is canonical for the pipeline rather than for Blake studies as a whole: it operationalizes a work-level target set derived from Blake bibliographies, editions, Archive identifiers, and visual catalogues [@bentley1977blakebooks; @bentley1995supplement; @bentley2004records; @butlin1981paintings; @erdman1988complete; @viscomi1993blake]. It records target identifiers, titles, work types, categories, expected text evidence, expected image evidence, aliases, and source hints. It is intentionally work-level rather than object-level: copy, plate, impression, and image provenance are attached below works, but every object or image is not promoted to a separate top-level target. This scope keeps the reported denominator aligned with the question of whether the project has local evidence for Blake work targets, while leaving a future path for copy-, object-, and relation-aware mirroring [@viscomi1993blake; @essick1980printmaker; @phillips2000songs; @foxfletcher2018relations].

## Source Registry: Provider Authority and Fallback Order

The source registry contains {{SOURCE_REGISTRY_COUNT}} providers: {{SOURCE_PROVIDERS_CSV}}. The William Blake Archive is treated as the primary authority when sources disagree [@blakearchive; @eaves1999standards; @viscomi2002digital; @jones2006wba]. Project Gutenberg [@projectgutenberg], Wikisource [@wikisourceblake], Internet Archive [@internetarchive], the Erdman edition [@erdman1988complete], Tate [@tateblake], the British Museum [@britishmuseumblake], HathiTrust [@hathitrustblake], and the Blake Quarterly Essick finding list [@essick1969] are used as corroborating or fallback sources rather than as equal canonical authorities. That ordering reflects textual-scholarship concerns with source authority, edition history, and the material conditions under which textual evidence becomes computable [@mcgann1991textual; @mckenzie1999bibliography].

| Source | Discovered records |
|---|---|
{{SOURCE_DISCOVERY_TABLE_ROWS}}

: Source discovery records by provider. Counts are normalized source records, not automatically accepted corpus targets; matching to the target ledger happens in the audit layer. {#tbl:source_discovery}

| Provider | Source type | Status | Records | Error |
|---|---|---|---:|---|
{{PROVIDER_DISCOVERY_TABLE_ROWS}}

: Provider discovery health for the saved run. A provider failure is recorded as review evidence and does not imply that already acquired local works are invalid. {#tbl:provider_discovery_health}

## Acquisition Path: Reproducible Fetching and Drift Resistance

The acquisition path builds Archive-backed work records from the target ledger and the public GitHub TEI inventory; live per-work Archive API metadata is attempted opportunistically as enrichment, not as the only catalog source. In this run the enrichment status was `{{ARCHIVE_METADATA_STATUS}}`: {{ARCHIVE_METADATA_SUCCEEDED}} of {{ARCHIVE_METADATA_ATTEMPTED}} attempted metadata requests succeeded, {{ARCHIVE_METADATA_FAILED}} failed, and {{ARCHIVE_METADATA_SKIPPED}} were skipped after the bounded budget or degradation guard. The fallback source for work-record construction was {{ARCHIVE_METADATA_FALLBACK_SOURCE}}. TEI acquisition uses actual inventory filenames before falling back to inferred copy-letter patterns, treating TEI as a structured encoding model rather than a plain-text dump [@teiP5; @burnard2014tei; @derose1990text]. Image acquisition normalizes object identifiers before trying Archive and Wayback image URL variants. Text-canon targets without primary Archive work ids are handled through an explicit Wikisource fallback script, with the fallback source recorded in local metadata rather than folded into Archive authority. The source audit found {{GITHUB_WORK_XML_COUNT}} work XML files and {{GITHUB_WORK_PREFIX_COUNT}} distinct work prefixes in the GitHub works API, then sampled {{ARCHIVE_API_SAMPLE_COUNT}} Archive work API records, of which {{ARCHIVE_API_SAMPLE_OK}} responded successfully. The resulting discovery set produced {{SOURCE_RECORDS_DISCOVERED}} normalized source records and matched {{SOURCE_MATCHED_TARGETS}} ledger targets ({{SOURCE_MATCHED_PCT}}%). Endpoint status is evidence about a run-time source environment, not a permanent property of the cited resource; long-lived digital humanities projects and public web corpora both face changing interfaces, link rot, reference rot, time-varying representations, and provider-specific access policies [@reed2014managing; @klein2014reference; @vandesompel2013memento].

## Provenance Audit: Evidence Traces and Missing-Work Search

Every local work stores source type, source identifier, source URL, license fields, and image source URLs where available. The audit layer separately records endpoint status for the research sources, so source availability is not inferred from successful local acquisition alone. It also emits missing-evidence candidates for targets that remain missing or partial, separating text, image, and source-match searches. This makes provenance a recorded relationship among sources, acquisition activities, derived artifacts, and manuscript claims rather than an informal note [@w3cprov2013overview; @rocrate2022]. [@fig:source_audit] summarizes the checked endpoints, and [@tbl:source_audit] retains the exact checked status table used for this manuscript.

![Reviewed source endpoints used by the acquisition and fallback-source audit. Rows record endpoint availability during this run; reachable status supports source review but does not by itself prove that a candidate title or object was acquired.](../output/figures/source_audit.png){#fig:source_audit}

| Source endpoint | Status | OK | Content type |
|---|---:|---|---|
{{SOURCE_AUDIT_TABLE_ROWS}}

: Live source audit table. Statuses describe endpoint availability during this run and do not by themselves prove that a candidate title was acquired. {#tbl:source_audit}
