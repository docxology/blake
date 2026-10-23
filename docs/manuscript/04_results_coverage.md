# Results: Target Coverage, Provenance, and Evidence Gaps {#sec:results_coverage}

The saved corpus represents {{TARGETS_REPRESENTED}} of {{TARGET_TOTAL}} ledger targets ({{REPRESENTATION_PCT}}%), while {{TARGETS_PRESENT}} satisfy the declared local evidence profile ({{COVERAGE_PCT}}%). The manifest classifies overall coverage as {{COVERAGE_STATUS}}. Representation includes accepted or duplicate local matches; it excludes missing and unverified ledger states. It is not a claim that every matched source/copy record is a distinct work or a validated primary transcription.

## Target-Ledger Results

The ledger classifies {{TARGETS_PRESENT}} targets as present, {{WORKS_PARTIAL}} as partial, and {{WORKS_MISSING}} as missing. Duplicate and unverified states remain explicit in [@tbl:coverage]. These classifications express the pipeline's modeling and evidence rules, rather than independent facts about the limits of Blake's oeuvre [@mccarty2005humanitiescomputing; @atkins1992corpus; @bowkerstar1999sorting].

![Coverage states for the {{TARGET_TOTAL}}-entry {{TARGET_PROFILE}} ledger. Present, partial, missing, duplicate, and unverified states remain distinct. Counts use the declared work-level target denominator rather than downloaded files or local source records.](../../output/figures/coverage_status.png){#fig:coverage_status}

| Status | Targets | % of ledger |
|---|---:|---:|
{{COVERAGE_TABLE_ROWS}}

: Coverage states against the pipeline-canonical target ledger. {#tbl:coverage}

![Coverage states by ledger category. Segments count modeled target states within each category. Category labels do not independently validate source metadata, genre, dating, or historical representativeness.](../../output/figures/category_coverage.png){#fig:category_coverage}

| Category | Present | Partial | Missing | Total | Present % |
|---|---:|---:|---:|---:|---:|
{{CATEGORY_COVERAGE_TABLE_ROWS}}

: Target coverage by declared ledger category. Duplicate and unverified targets contribute to category totals; the present percentage measures only fully satisfied targets. {#tbl:category_coverage}

## Local Record and Modality Results

This offline epoch reconstructs target states from retained local records and does
not import discovery-only candidates as verified holdings. A target can therefore
be missing locally even when a prior discovery ledger retained an unverified lead.
That ledger state is separate from the primary/unverified authorship labels on
reading transcriptions.

The {{WORKS_PRESENT}} local records include {{WORK_TYPE_COUNT}} metadata work-type labels. Those labels describe the retained metadata and can include defaults or unresolved classification; they are not a newly validated genre census. Text availability is {{TEXT_COVERAGE_PCT}}%, image availability is {{IMAGE_COVERAGE_PCT}}%, and processing coverage is {{PROCESSING_COVERAGE_PCT}}% of local records.

| Metadata work type | Local records | % of local records |
|---|---:|---:|
{{WORK_TYPE_TABLE_ROWS}}

: Work-type labels recorded in local metadata, separate from the target-ledger categories. {#tbl:work_types}

The text-bearing subset contains {{WORKS_WITH_TEXT}} records, the image-bearing subset {{WORKS_WITH_IMAGES}}, and the joint subset {{WORKS_WITH_BOTH}}. Repeated source/copy records and reused image files can contribute to several record-level counts.

![Available modalities across local records. Bars distinguish text-plus-image, text-only, image-only, and metadata-only records. These are evidence-presence counts, not a population sample or a census of independent Blake works.](../../output/figures/corpus_modalities.png){#fig:corpus_modalities}

## Retained Evidence Gaps and Search Queue

The unresolved targets remain part of the result. [@fig:evidence_gaps] summarizes missing expected evidence; [@tbl:supp_evidence_gaps] gives the target-level rows. Missingness shapes the scope of subsequent computational claims [@klein2013absence; @borgman2015bigdata; @bode2018world].

![Evidence gaps derived from non-present target states. Counts group missing expected text, image, source, or local-record evidence. A gap is an acquisition or review task, not evidence that a named remote provider contains the missing item.](../../output/figures/evidence_gaps.png){#fig:evidence_gaps}

The retained audit generates {{MISSING_EVIDENCE_CANDIDATES}} candidates across {{MISSING_EVIDENCE_TARGETS}} targets: {{MISSING_EVIDENCE_TEXT}} text checks, {{MISSING_EVIDENCE_IMAGE}} image checks, and {{MISSING_EVIDENCE_SOURCE_MATCH}} source-match checks. [@tbl:supp_missing_evidence] preserves their source hints, confidence scores, and actions. This offline run did not refresh provider discovery or endpoint health. An unchecked status remains unchecked; source leads do not become corpus evidence without identity, attribution, rights, and content validation.
