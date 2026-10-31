# Shared research methods

The 0.5.0 source separates reusable evidence methods from application policy.
Plain `uv sync` installs packaging, Click, Pydantic and typing extensions. Use
`uv sync --extra full` for acquisition, NLP, vision and the corpus pipeline.
The complete test suite includes GUI tests and requires
`uv sync --extra full --extra dev --extra gui`. GUI/API serving also needs `full`
and its surface extra.
Bounded source and installed-wheel qualification is recorded in
[verification scope](verification.md). This document describes an unreleased
candidate API; the recorded checks do not attest a published release.

Private applications own vocabularies, research questions, review labels,
branding and interpretation. Federalism and Entomology use those boundaries;
this package publishes neither their source corpora nor their research claims.
Shared conventions live in the [style guide](style-guide.md).

## Declared evidence hierarchies

`blake.methods.hierarchy` exports frozen Pydantic `EvidenceTreeNode(node_id,
label, parent_id=None)`, `EvidenceTree(nodes)`, `TreePlacement(node_id, depth,
row)` and `layout_evidence_tree(tree)`. Use keyword arguments and a tuple of nodes.
JSON admission uses `EvidenceTree.model_validate_json(...)`. IDs and labels must
be nonblank strings and are preserved exactly; invalid scalar types, duplicate
IDs, missing parents, self-edges, cycles and multiple roots are rejected.

```python
from blake.methods.hierarchy import EvidenceTree, EvidenceTreeNode, layout_evidence_tree

tree = EvidenceTree(nodes=(
    EvidenceTreeNode(node_id="root", label="Synthetic evidence"),
    EvidenceTreeNode(node_id="a", label="Source A", parent_id="root"),
    EvidenceTreeNode(node_id="b", label="Source B", parent_id="root"),
))
placements = layout_evidence_tree(tree)
```

Validation and layout are iterative. Output follows declared node order, even
when parents occur after their children. Leaves receive consecutive rows in
declared sibling traversal order; each parent receives the arithmetic mean of
all descendant leaf rows. Depth counts edges. Applications supply tree membership,
taxonomy, labels, interpretation and plotting; the core infers none of them.

## Choose a retrieval contract

Import the relevant module rather than inferring a profile from input shape.
`describe_profile(RetrievalProfile.… )` describes semantics;
`runtime_profile(...)` additionally records the actual Python and Unicode versions.
Profile metadata does not enter historical query fingerprints.

| Profile | Entry point | Matching contract |
|---|---|---|
| `REGEX_WORDS_V1` / `regex-ignorecase-source-spans-v1` | `blake.methods.concordance.concordance_passages` | Escaped alternatives, Python `re.IGNORECASE`, Unicode word boundaries, original spans |
| `LITERAL_CASEFOLD_V1` / `casefold-literal-source-spans-v1` | `blake.methods.search.search_passages` | Literal Unicode casefold, exact whitespace and punctuation, ANY/ALL, optional complete word windows |
| `NFKC_TOKENS_V2` / `nfkc-casefold-source-spans-v2` | Existing `blake.studies.scan_passages` | Explicit category forms over contiguous normalized tokens; punctuation and line breaks separate tokens |

These contracts intentionally disagree on some Unicode and phrase inputs.
Literal `ss` can match an entire `ß`; regex IGNORECASE does not make that expansion.
A literal phrase preserves whitespace, whereas a normalized token phrase may
cross punctuation. Concordance sorts variants by length only; the retained
statistics matcher has a distinct length-then-lexical tie order. Preserve each
contract's own oracle. The existing `blake.text_search` and `blake.studies` code
and source-hashed producer identities are unchanged by the extraction.

## Source contracts and custody

`blake.methods.models` exports `ProjectionPassage`, `ProjectionCorpusPin`,
`BundlePassage` and `BundleCorpusPin`. Historical projection schemas retain their
validation boundaries. Portable bundle schemas have stricter source bindings.
Use `bundle_to_projection(passages)` or `projection_to_bundle(passages)` from
`blake.methods.schema_conversion` explicitly. Conversion validates existing fields;
it does not supply missing provenance, change roles or convert pin meanings.

`blake.applications.load_bundle` remains the portable-bundle reader described in
[applications](applications.md). `blake.methods.corpus.import_corpus` and
`load_import` handle pinned projection directories. Both require caller-held
expected pins; finding a manifest beside a payload does not make it trusted.
Copied inputs are independent bytes, and modified bound inputs are rejected.

`storage.publish_bytes(path, content)` publishes complete exclusive bytes and
returns a filename, size and digest receipt. Occupied outputs remain untouched.
The writer holds verified directory descriptors and uses no-follow traversal;
a concurrent parent rename cannot redirect publication into its replacement.
Platforms without the required descriptor operations fail explicitly.
Keep failed partial runs for inspection and choose a fresh output for a rerun.

## Literal search and concordance

`search.literal_spans(text, terms, *, whole_words)` is the direct shared span
implementation used by search and application adapters. It returns complete
Unicode casefold matches with original offsets and rejects empty terms rather
than admitting a non-advancing search. Empty term inventories return no spans.


This synthetic example requires no corpus download:

```python
from blake.methods.models import ProjectionPassage
from blake.methods.search import search_passages
from blake.methods.search_models import SearchRequest

unit = ProjectionPassage(
    passage_id="synthetic-1", work_id="example", author_id="synthetic",
    title="Synthetic example", edition_id="example-1", edition="Example",
    locator="1", locator_kind="section", source_url="https://example.test/1",
    rights="Synthetic example", text_role="primary", source_plane="reading",
    text="Alpha beta alpha.",
)
result = search_passages(
    (unit,),
    SearchRequest(terms=("alpha", "beta"), mode="all", window_words=2, limit=1),
)
print(result.total_occurrences, result.returned_hits)  # 3 1
```

Requests accept one to eight nonblank, casefold-distinct terms. Primary text is
the default role; `role=None` explicitly includes all roles. Plane and work filters
are conjunctive. ALL requires every term in a single stored source unit. Its
optional 1–200-word window requires at least two terms and retains every occurrence
participating in a complete qualifying window, including phrase tokens.

Offsets count original Unicode codepoints, including astral characters. A match
cannot highlight part of an expanded casefold character. Each term is
nonoverlapping with itself; different terms can occupy the same source span.
Results order hits by passage identity, start, end and term. Counts and facets are
computed before `limit`; eligible zero-hit groups and token denominators remain
present. A group with no word tokens has a null normalized rate, not a zero rate.

`search_corpus(directory, expected_pin, request)` verifies a projection before
searching. For regex retrieval use
`concordance_passages(passages, queries, pin, interpretation)` or the directory
wrapper `concordance(directory, queries, expected_pin, interpretation)`.
`QuerySpec` contains `query_id`, explicit `variants` and `note`. The interpretation
argument is required and belongs to the caller. Concordance emits every query ×
plane × role cell, including zeros. `query_fingerprint` retains its original JSON
serialization and does not append profile metadata.

## Aggregate studies, counted statistics and sensitivity

`search_study.build_search_study(passages, pin, selected)` accepts an ordered tuple
of `(query_id, terms)` selections. It searches every role, retains all eligible
facet denominators and validates counts. The shared module supplies no selections.
Its `SearchStudy` contains aggregates rather than contexts or passage bodies.

`statistics.analyze_corpus(passages, queries)` retains the historical regex
statistics contract and primary-reading source inventory. Query summaries include
copy-retaining and exact-text comparisons, work-level summaries and omissions;
associations distinguish copy-retaining, exact-text and work-presence units.
Exact text equality is a sensitivity grouping, not a license to merge edition or
copy identities in the underlying corpus.

For counts produced by another declared matcher, use
`statistics.analyze_inventory(units, query_ids, profile)`, where `units` are
`statistics_models.SourceUnit` records and `profile` is a `RuntimeProfile`.
Every unit must have a nonnegative count for every declared query, including
zeros, and its token denominator. Identical text hashes must agree on counts and
tokens. This path aggregates the supplied inventory without silently rerunning
regex matching or labeling NFKC counts as regex results. It binds the counted
inventory and profile; the caller still owns the source pin and count production.

`proximity.build_proximity_study(passages, pin, grid)` accepts a `ProximityGrid`
of explicit `SearchRequest` objects. Each request uses ALL, at least two terms,
whole words, `limit=1` and `context_chars=0`. Eligibility is identical across the
grid. For each term tuple, widths are unique and increasing; a final null width
means document-level ALL. The aggregate counts still include all participating
occurrences, despite the one-hit display cap. It reports per-term totals, source
coverage, token denominators and facets. Proximity is a retrieval constraint,
not evidence that two expressions have the same meaning or institutional role.

## Deterministic review workloads

`review_planning.plan_review` ranks a caller-verified hit pool using explicit
source-facet strata, a seed and a global source-unit cap. `review_batches`
publishes and verifies immutable blank batches; the application owns source
scope, original-run admission and authored decisions. Selection is an
operational workload, not probability sampling or adjudication. See the
[complete planning contract](methods/review-planning.md) for the byte grammar,
capacity/shortfall semantics, custody and refusing controls.

## Review queues, run membership and producer closure

`annotations.queue_row` creates the fourteen-column review record from a
`StudyHit`; evidence fields are immutable and decision fields start blank.
`csv_decisions(raw, hits, run_sha256)` accepts unchanged candidate rows, including
selected subsets and UTF-8 BOM input. It rejects altered evidence, duplicate or
unknown identities, malformed columns and partially filled blank decisions.
It returns neutral `DecisionInput` records. Applications validate allowed labels,
reviewer/rationale requirements and domain-specific locators before acceptance.

Use `validate_decision_membership` to bind decisions to one run and known unique
candidates, then `count_decisions` with explicit permitted labels. Unreviewed
candidates remain unreviewed. A syntactic CSV admission is not a scholarly review.

`runs.reserve`, `write_new`, `read_regular`, `verify_artifacts` and
`require_run_pin` provide exclusive outputs, regular-file checks, exact declared
artifact membership, byte receipts and a pinned completion receipt. The
application supplies the expected artifact names and validates result schemas
and policy. These low-level checks do not choose an application's artifact set.
`require_run_pin` returns the checked receipt bytes; `verify_artifacts` returns
the checked payload bytes keyed by name. Parse those returned bytes. Reopening
the paths after verification would admit a concurrent replacement.

`producer.source_hashes` exposes the namespaced per-file receipts;
`producer.source_binding_sha256` accepts explicit `SourceBinding(package, paths)`
records and hashes namespaced source bytes. Include delegated shared methods,
models and browser resources alongside application wrappers. The function checks
listed bytes; the application is responsible for listing the full source closure.
A new closure requires a new producer epoch. Never rewrite historical receipts to
make earlier runs appear to have used the extracted implementation.

## Offline workspace

`workspace.build_search_workspace(directory, pin, output, *, branding,
producer_version, private_output_root, resource_directory=None)` verifies a local
projection and publishes an offline HTML workspace and manifest. `branding` is a
`WorkspaceBranding(title, brand, footer)` value; labels are HTML-escaped.
`private_output_root` is required. Optional application resources override only
HTML and CSS; the matcher always comes from the shared JavaScript resource.

For already verified passages, use `build_search_workspace_passages` with the
same explicit policy and a required `revalidate` callback. The callback must raise
if the source binding has changed; it executes immediately before publication.
The directory wrapper rechecks the pinned index itself. Output paths reject
symlinks, traversal and occupied destinations.

The payload carries producer Python Unicode folding, word-membership and
whitespace tables, original source fields and full texts. Inert JSON and hashed
script/style CSP declarations prevent source strings becoming executable markup;
runtime network connections are disabled. The manifest binds source pin, resource
hashes, payload and output bytes. Browser results use original-codepoint offsets
and distinguish total matches, returned-hit cap and twenty-hit display pages.
Node differential tests compare the same shared engine against Python.

## Installation profiles

The core is qualified on actual Python 3.9 and 3.11. A normal wheel installation
uses eight distributions and supports portable-bundle reading and these methods.
Use `uv sync --extra recovery` for source recovery and recovered-projection export;
this adds HTML parsing, image verification and platform certificate support.
Use `uv sync --extra full --extra dev --extra gui` for the complete test suite,
including its Streamlit native tests. The full workflow is qualified
separately on Python 3.11;
the core's Python 3.9 result does not qualify that optional stack.

This is a private full-text artifact. Do not put its HTML or payload into a public
source or release archive merely because the template and matcher are public.
Provider rights and application review remain separate from byte verification.
