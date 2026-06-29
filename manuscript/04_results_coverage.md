# Results: Target Coverage, Provenance, and Evidence Gaps {#sec:results_coverage}

This section reports the corpus state against the declared target ledger. The key result is not a simple complete/incomplete label: the local corpus represents {{TARGETS_REPRESENTED}} of {{TARGET_TOTAL}} ledger targets ({{REPRESENTATION_PCT}}%), but only {{TARGETS_PRESENT}} targets satisfy all required local evidence ({{COVERAGE_PCT}}%). The manifest therefore classifies the run as {{COVERAGE_STATUS}}. The audit then translates non-present targets into concrete search candidates so the next acquisition pass can be driven by recorded evidence rather than ad hoc title hunting. The results are consequently methodological as well as descriptive: the unresolved rows show where the corpus is well evidenced and where aggregate interpretation should stop.

## Ledger Results: Covered, Partial, and Missing Target Works

The target coverage matrix contains {{TARGETS_PRESENT}} present targets, {{WORKS_PARTIAL}} partial targets, and {{WORKS_MISSING}} missing targets. [@fig:coverage_status] plots the same denominator used by the manifest, and [@tbl:coverage] gives the status breakdown. The status labels are not neutral facts about Blake's oeuvre; they are modeled classifications that make inclusion rules, absences, and evidentiary obligations inspectable [@mccarty2005humanitiescomputing; @atkins1992corpus; @bowkerstar1999sorting].

![Coverage status against the {{TARGET_TOTAL}}-entry {{TARGET_PROFILE}} target ledger. Bars count local work-level evidence states: represented-but-partial records remain separate from fully evidenced records, and the denominator is the declared ledger rather than Blake's whole material archive.](../output/figures/coverage_status.png){#fig:coverage_status}

| Status | Works | % of ledger |
|---|---:|---:|
{{COVERAGE_TABLE_ROWS}}

: Coverage status breakdown. The denominator is the canonical work-level ledger, not the number of downloaded files. {#tbl:coverage}

The difference between representation and presence is visible in the evidence metrics. Text coverage across local works is {{TEXT_COVERAGE_PCT}}%, image coverage is {{IMAGE_COVERAGE_PCT}}%, and processing coverage is {{PROCESSING_COVERAGE_PCT}}%. These are local-work metrics: they describe the {{WORKS_PRESENT}} acquired works, not the unacquired target ledger.

## Category Results: Coverage by Work Area and Genre

Coverage is not evenly distributed by category. [@fig:category_coverage] shows stronger representation for visual and print categories, while manuscript and poem targets carry the remaining gaps. [@tbl:category_coverage] gives the category-level matrix.

![Stacked target coverage by ledger category. Segments count present, partial, missing, duplicate, or unverified target entries within each work area; the categories organize acquisition state and are not offered as literary period labels.](../output/figures/category_coverage.png){#fig:category_coverage}

| Category | Present | Partial | Missing | Total | Present % |
|---|---:|---:|---:|---:|---:|
{{CATEGORY_COVERAGE_TABLE_ROWS}}

: Category-level target coverage. Category rows expose where the remaining acquisition work is concentrated. {#tbl:category_coverage}

The local corpus contains {{WORK_TYPE_COUNT}} work types. The distribution by local work type is reported in [@tbl:work_types].

| Work type | Local works | % of local corpus |
|---|---:|---:|
{{WORK_TYPE_TABLE_ROWS}}

: Local work-type distribution. This table describes acquired works only and should not be read as a census of the target ledger. {#tbl:work_types}

The acquired chronology spans {{DATE_EARLIEST}} through {{DATE_LATEST}}, a {{DATE_SPAN_YEARS}}-year window across the dated local records. [@fig:chronology] shows the distribution by year and work type, making clear that the reported work-level corpus reaches across Blake's productive life while preserving category-specific evidence gaps.

![Dated local corpus records by year and work type across the {{DATE_EARLIEST}}-{{DATE_LATEST}} metadata window. Points use normalized work dates from local records; object-, copy-, and impression-specific dating remains outside this chronology.](../output/figures/chronology.png){#fig:chronology}

## Modality Results: Text, Image, and Metadata Evidence

The modal profile of the local corpus is mixed. [@fig:corpus_modalities] separates works with both text and image evidence, text only, image only, and metadata-only records. The joint text-image subset contains {{WORKS_WITH_BOTH}} works; the text-bearing subset contains {{WORKS_WITH_TEXT}} works; and the image-bearing subset contains {{WORKS_WITH_IMAGES}} works.

![Local evidence modalities across acquired corpus records. Bars separate text-plus-image, text-only, image-only, and metadata-only works, defining which material subset can support textual, visual, or cross-modal analysis in this run.](../output/figures/corpus_modalities.png){#fig:corpus_modalities}

This modality split explains why the corpus can be broadly represented while still partial. Visual works often have local image evidence but no transcribed text; some textual works have text but incomplete image evidence. The coverage ledger preserves that distinction instead of collapsing it into a single acquired/not-acquired flag.

## Gap Results: Search Candidates for Missing Evidence

The unresolved denominator is small but consequential. Source discovery matched {{SOURCE_MATCHED_TARGETS}} of {{TARGET_TOTAL}} ledger targets ({{SOURCE_MATCHED_PCT}}%), leaving {{SOURCE_UNMATCHED_TARGETS}} unmatched source-discovery targets: {{SOURCE_UNMATCHED_IDS_CSV}}. Those unmatched source-discovery targets are represented locally through explicit Wikisource fallback text, not through Archive-led discovery records. Locally, {{WORKS_PARTIAL}} targets are partial and {{WORKS_MISSING}} are missing. [@fig:evidence_gaps] groups the reasons. The row-level target ledger is moved out of the main argument into [@tbl:supp_evidence_gaps], so the results section can emphasize what the gaps mean rather than force the reader through every unresolved target. Missing evidence is therefore treated as an object of analysis, not just an inconvenience, because archival and digitized-corpus absences shape what downstream claims can mean [@klein2013absence; @borgman2015bigdata; @bode2018world].

![Evidence gaps preventing complete target-ledger coverage. Bars group non-present target records by missing expected text, image, source, or local-work evidence; each count is a candidate acquisition task, not proof that the named public source contains the missing material.](../output/figures/evidence_gaps.png){#fig:evidence_gaps}

The audit turns those gaps into {{MISSING_EVIDENCE_CANDIDATES}} bounded missing-evidence candidates across {{MISSING_EVIDENCE_TARGETS}} targets. The candidate set includes {{MISSING_EVIDENCE_TEXT}} text checks, {{MISSING_EVIDENCE_IMAGE}} image checks, and {{MISSING_EVIDENCE_SOURCE_MATCH}} source-match checks. [@tbl:supp_missing_evidence] preserves the full bounded search table with source label, endpoint status when available, confidence score, and action taken. That separation matters: fallback sources remain acquisition leads and corroboration records, not replacements for William Blake Archive authority.
