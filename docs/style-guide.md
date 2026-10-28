# Shared Blake syntax and evidence conventions

This guide is authoritative for shared methods and manuscript syntax. Application
guides add vocabulary, review policy and disciplinary limits and link here.
Their scientific decisions remain local to those applications.

## Python and API boundaries

Support Python 3.9 for the dependency-light core. Retain Click and the dependency
profiles in `pyproject.toml`; a generic tooling preference does not justify an
interpreter or dependency migration. Use fully annotated public functions,
explicit optional returns and immutable Pydantic boundary models. New schemas
forbid undeclared fields and reject invalid scalar types. Preserve scientific
labels exactly; checking nonblank content does not authorize stripping, case
folding or interpreting it. Boundary parsing must raise a named, actionable error.

Use the existing `EvidenceError(code, detail)` for new shared evidence failures;
Pydantic may wrap it as a `ValidationError`. Historical `ResearchError` and bundle
errors retain their ancestry and codes. Catch specific failures at orchestration
boundaries. Missing files, changed pins and unavailable results are errors or
explicit unavailable states, never fabricated zero measurements or silent fallbacks.
Do not retrofit stricter schemas or different matchers onto historical APIs.

Use iterative algorithms when depth is controlled by input. Evidence-tree depth
is an edge count, not a date, taxonomic rank or branch length. Tree leaves follow
declared sibling traversal order; an internal row is the mean of all descendant
leaf rows, weighted by leaf membership rather than by child count.

## Deterministic evidence and artifact custody

Name the executable source root, evidence read root and generated output root in
the run instructions and receipt. The manuscript read-root override is explicit:
`--evidence-root` or `BLAKE_MANUSCRIPT_EVIDENCE_ROOT`. An explicit missing or invalid
root must fail; do not search other checkouts or substitute cached aggregate data.
The default remains the authoring project's own evidence tree. The read root
does not change which source code or manuscript prose executes.

Use caller-held manifest pins and the existing projection/bundle loaders. Verify
regular files and hashes, retain source/copy identity, edition, locator, rights,
source hash, text role and source plane. A conversion between schemas does not
infer missing custody or promote authorship. A bounded stage is not a full
recovery inventory. Full recovery, backup verification, selected-source admission
and publication rendering are separate qualifications.

Write a fresh epoch for new model outputs, producer closures, selections or
review decisions. Preserve the original analytical producer, saved payloads,
negative controls and earlier failures. Source-only diagrams and recomputed
display diagnostics do not repeat old inference. Hash the exact files consumed
and generated; canonical JSON uses sorted keys and explicit separators where
the relevant API specifies them. Retain declared sequence order when it is
semantic. Never change historical serialization merely to standardize style.

Publish exclusive completion receipts after their artifacts and refuse occupied
run destinations. Record explicit expected artifacts and the complete delegated
producer closure. Source verification does not attest an installed Git package,
provider permission, rendered-page acceptance or scientific validity.

## Retrieval semantics and counting units

Always name the retrieval profile. Regex IGNORECASE, literal casefold and NFKC
token matching intentionally disagree on Unicode expansion, punctuation and
whitespace. Preserve original-codepoint spans and the exact source expression.
Do not compare rates from different tokenizers as if their denominators agreed.
Query fingerprints retain their own historical serialization contracts.

State the unit beside every count: matched occurrences, stored passages/source
units, source/copy documents, exact-text groups, distinct work identifiers,
ledger targets, image associations or unique image files. Exact-text grouping is
a sensitivity analysis; it does not merge source identities. Count eligible
zero-hit units before result/display caps. A zero token denominator gives an
unavailable normalized rate, not a measured zero. Record role, plane, author,
work and window filters with the query. ALL over a source unit differs from ALL
inside a complete word window.

## Markdown, mathematics and cross-references

Write prose in Markdown. Use descriptive headings with stable identifiers such
as `{#sec:shared_methods}`; refer to sections with `[@sec:shared_methods]`.
Use backticks for API names, paths and literal profile identities. Use fenced
code blocks with a language tag for executable examples. Examples containing
synthetic text must identify it as synthetic rather than imply Blake attribution.

Use `$...$` for inline mathematics and `$$...$$` for display mathematics. Define
symbols, populations and units before presenting an equation. Keep LaTeX layout
commands in `preamble.md`; do not embed ad hoc spacing fixes in scientific prose.

Every result number, measured count, percentage and figure-caption quantity in
`NN_*.md` uses a `{{UPPERCASE_TOKEN}}` computed by manuscript tooling. Tokens must
resolve to nonempty values under strict hydration. Source-owned legal quantities
stay in their claim ledger. Do not put unsubstituted quantities in configuration
titles or subtitles. New code-diagnostic quantities must identify their source
binding separately from the saved analytical run.

Use Pandoc citation keys from `references.bib`, with locators for quotations and
specific source claims. Never add a Blake quotation without freshly retrieved
primary expression, edition/copy/plate locator and retained source hash. Do not
change a reading ceiling or label a search as a scholarly reading.

Reference figures by generated filename and a unique `{#fig:stable_label}`;
cross-reference with `[@fig:stable_label]`. Let the renderer assign figure numbers.
The registry records inputs, encoding, accessibility summary, limitations and
checks. Captions distinguish source-derived diagnostics from measurements of
retained texts or images. Inspect physical rendered pages after final integration.

## Claim discipline and qualification

Separate implementation behavior, local runtime evidence, source claims and
scholarly interpretation. Lexical matches do not establish semantic equivalence,
species identification, causal relationships or statistical significance. A tree
layout supplies no phylogeny. A successful pipeline can contain explicit component
errors. Preserve them in artifacts, tokens and prose.

Verification uses real files, numerical oracles and rejecting controls. Reproduce
an actual bug before fixing it. Record commands, interpreter prefixes, exit codes,
coverage and artifact hashes. A source-stage test result must not be silently
upgraded to installed-package, hosted-CI, browser, native-PDF or release acceptance.
