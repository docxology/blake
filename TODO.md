# TODO

Forward-only improvement backlog. Remove an item once its scope is delivered and
verified; do not keep finished work here as project history.

The first public destination/bundle decision is delivered in [publication.json](publication.json), including retained deposited assets and checksums. It was retired from this queue on 31 October 2026; those bounded publication receipts do not close the scientific/rights tasks below. [Project status](docs/PROJECT_STATUS.md) records completed units and [documentation](docs/README.md) routes current workflows.

## Scope Key

- Minor: one focused code, documentation, test, or generated-artifact cleanup.
- Medium: one workflow or module with tests and documentation updates.
- Major: cross-module, release, research-method, or product-shaping work.

Every item should preserve the source-governed corpus contract: distinguish
local evidence, source authority, generated summaries, and public redistribution
permission.

## Medium Improvements

- [ ] Publish the qualified 0.5.0 paper as the next Zenodo version when an
  authenticated credential is available. The two private credential requests
  expired without creating a deposition. Acceptance: verify the existing concept,
  upload the exact qualified PDF and public reproduction assets, publish through
  the ordinary API, verify anonymous downloads, then update the deposited-paper
  manifest and citation metadata. No acquisition or model rerun is part of this
  publication unit.

- [ ] Fallback-text corroboration review pass. Scope: use the generated
  fallback corroboration records to review every validated fallback text against
  at least one additional authority before public notes describe it as
  corroborated. Acceptance: every real validated target has a recorded reviewer
  decision, source URL, authority tier, license or terms note, checksum, date
  accessed, reviewer note, and whether corroboration is text-bearing or
  contextual.

- [ ] Partial-evidence pass. Scope: work through the unresolved evidence review
  queue and the strongest direct-source leads, prioritizing exact text-bearing
  sources over generic catalog pages. Acceptance: accepted targets update local
  evidence, source audit, coverage, acquisition review, analysis summaries,
  manuscript variables, and release-package corroboration; rejected targets keep
  explicit rejection reasons.

- [ ] Strengthen the Blake Archive resolver. Scope: isolate stable source-owned
  routes, object lists, TEI or transcription availability, and image-object
  metadata behind one resolver with retry and terms-aware exclusions. Acceptance:
  source audit distinguishes route visibility, metadata-only evidence,
  text-bearing source files, and rights-gated local image files.

- [ ] Complete analysis diagnostics decomposition. Scope: the diagnostics output
  now has a top-level summary and error categories; finish splitting the
  remaining monolithic metric builder into text, image, cross-modal, and
  ontology helper functions. Acceptance: generated diagnostics remain byte-stable
  except for intentional schema additions, and each helper has focused tests.

## Major Improvements

- [ ] Extend distribution-rights reference policy. Included rights-gated assets already enter public-release `blocked_reasons` through `public_release.py`; gated/safe fixture controls exist. Remaining scope: decide and test how every referenced asset and any explicit venue-specific clearance or exclusion enters admission. References are currently advisory, so this stronger policy is not closed. Keep raw transcriptions, TEI, images and caches within their actual terms/custody.

- [ ] Source-owned acquisition expansion. Scope: implement source-specific
  acquisition paths for high-value unresolved leads such as exact Wikisource
  pages, Morgan Library page sequences, Yale collection records, Blake Archive
  work/object metadata, and edition-specific scholarly controls. Acceptance:
  each adapter separates direct evidence, corroborating context, and rejection
  cases; no generic search page can alter coverage.

- [ ] Public explorer boundary. Scope: decide whether the Streamlit GUI, static
  workbench, REST API, or a separate static site is the public exploration
  surface. Acceptance: the chosen surface exposes only release-safe artifacts,
  displays rights and provenance per work, and can be smoke-tested from the
  generated public bundle.

- [ ] Research-method hardening for textual analysis. Scope: define which
  analyses are descriptive diagnostics, which are exploratory scholarship aids,
  and which are strong enough for manuscript claims. Acceptance: each analysis
  output has a method note, denominator, missingness caveat, deterministic seed
  or model version, and a test that catches silent empty-input success.

- [ ] Reproducible CI and release automation. Scope: design a CI profile that
  runs fast offline tests, fixture corpus generation, release preflight, package
  manifest checks, and documentation link checks without requiring private local
  caches. Acceptance: live acquisition remains opt-in, while release blockers
  are enforced on pull requests.

- [ ] Versioned corpus-target governance. Scope: define how target ledger changes
  are proposed, reviewed, versioned, and explained when categories, aliases,
  expected modalities, or source hints change. Acceptance: a target-ledger diff
  report names added, removed, renamed, and materially changed targets and
  updates coverage interpretation accordingly.

- [ ] Review the next corpus-bearing revision. Scope any changed capture, inference or literary claim after the current source-method/working-draft wave with its own independent source, generated-output, manuscript and rights review. The retained inspections do not supply peer review or whole-corpus scientific acceptance. Acceptance: each changed claim traces to its own artifact/source, changed native outputs pass complete page/browser checks, and exclusions retain explicit reasons.
