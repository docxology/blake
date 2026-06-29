# TODO

Forward-only improvement backlog. Remove an item once its scope is delivered and
verified; do not keep finished work here as project history.

## Scope Key

- Minor: one focused code, documentation, test, or generated-artifact cleanup.
- Medium: one workflow or module with tests and documentation updates.
- Major: cross-module, release, research-method, or product-shaping work.

Every item should preserve the source-governed corpus contract: distinguish
local evidence, source authority, generated summaries, and public redistribution
permission.

## Minor Improvements

No open minor items are currently scoped. Add a new item here only when it is a
focused cleanup with a concrete verification command.

## Medium Improvements

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

- [ ] Public release decision. Scope: choose whether the first public artifact is
  GitHub-only, Zenodo, GitHub plus Zenodo, or another destination, then define
  the exact release bundle and review authority. Acceptance: destination-specific
  metadata, checksums, citation file, release notes, excluded-path proof, and
  post-release verification are all generated before publishing.

- [ ] Distribution rights gate. Scope: convert the current rights-gate report
  into a release blocker that must be explicitly cleared, excluded, or waived by
  venue-specific rationale before any public redistribution of source materials,
  mosaics, raw transcriptions, TEI, or image caches. Acceptance: release-package
  tooling fails closed when rights-gated artifacts are selected or referenced.

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

- [ ] End-to-end scholarly package audit. Scope: run an independent audit over
  code, docs, generated artifacts, manuscript claim language, release package,
  and rights exclusions before the first public release. Acceptance: every public
  claim traces to a generated artifact or cited source, and every excluded asset
  class has an explicit reason.
