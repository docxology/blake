# Deterministic review planning

Blake 0.5.0 adds a shared workload planner and immutable blank review batches.
Applications verify their original runs, choose their source scope and validate
authored decisions. Blake ranks the supplied candidates and checks the resulting
batch. A selected candidate remains unreviewed until an authorized reviewer records a decision
through the application's existing review process.

## Declare the workload

Use the existing `blake.studies.StudyHit` records from an independently verified
application run. The Python API accepts ordinarily validated immutable models;
deliberate `model_construct` or `model_copy(update=...)` validator bypasses are
outside that typed contract. Parse actual JSON bytes with `model_validate_json`
at file/CLI boundaries. Count fields are strict positive/nonnegative integers;
booleans and numeric strings are rejected.

```python
from blake.methods.review_planning import plan_review
from blake.methods.review_planning_models import ReviewPlanSpec, ReviewSelection

selection = ReviewSelection(
    target_size=25,
    seed="review-workload-1",
    strata_fields=("term_id", "source_plane", "text_role"),
    unit_field="text_sha256",
    max_per_unit=1,
)
# Supply caller-held pins and the already verified, explicitly scoped hit pool.
spec = ReviewPlanSpec(
    source_run_sha256=original_run_sha256,
    source_context_sha256=application_request_sha256,
    selection=selection,
    excluded_hit_ids=reviewed_ids_in_scope,
)
plan = plan_review(verified_hits, spec)
```

All selection fields are explicit. Allowed stratum fields are `term_id`, `group`,
`source_plane`, `text_role`, `work_id`, `edition_id` and `author_id`. Declare at
least one, without duplicates. Missing source values remain literal values,
including an empty work identifier. This profile does not group optional copy
identifiers or repair source metadata.

Choose `passage_id` for a stored source-unit cap or `text_sha256` for an exact
whole-text cap. Equal text hashes do not merge the underlying copy or edition
identities. They also do not detect embedded poems in larger works or establish
independence between observations. Excluded hit IDs must be unique and belong
to the actual supplied pool; the spec stores them in lexical order.

## Ordering and capacity

Profile `hash-round-robin-review-v1` uses SHA-256 ranking and a lexical tie break.
The ranking payload is the UTF-8 encoding of compact JSON arrays:

```text
["hash-round-robin-review-v1", seed, "stratum", [facet_value, ...]]
["hash-round-robin-review-v1", seed, "hit", hit_id]
```

JSON uses `ensure_ascii=False`, sorted object keys, separators `(',', ':')` and
`allow_nan=False`, without a trailing newline. Strings are retained verbatim;
Unicode normalization is not added. Unpaired surrogates refuse before output
reservation. Python RNG state and input order do not affect the result.

Each stratum's candidates are hash-ranked. Visit hash-ranked active strata in
round-robin order, selecting the next candidate whose declared unit has capacity.
Discard candidates blocked by the global unit cap. Stop at the target or when
all queues are exhausted. Preserve the selection order, all stratum counts,
eligible-unit count and exact target shortfall. Stratum summaries display in
lexical key order, separately from the selection order.

With eligible occurrence counts `n(u)` and cap `c`, selected count is
`min(target_size, sum(min(c, n(u)) for u in eligible_units))`. The algorithm is
greedy: it can exhaust a stratum's shared units. For example, A has candidates
on units 1 and 2; B has only unit 1. If A first uses unit 1 with cap 1, B receives
no candidate although another order could cover both strata. There is no stratum
quota optimization, probability-sampling guarantee or inferential weighting.

## Bind the complete pool and a fresh batch

The source-pool SHA hashes every field of every supplied hit, including excluded
and unselected hits: serialize each complete `StudyHit.model_dump(mode='json')`
using the JSON grammar above, sort rows by hit ID, append one LF to each row and
stream all rows through SHA-256. The empty pool has the SHA-256 of empty bytes.
Duplicate hit IDs, nonpositive spans, blank passage/term identities and conflicting
metadata for one passage identity refuse. Span, expression, context, term, group
and hit ID may differ between occurrences; the remaining passage metadata must
agree. The original role, authorship, locator, copy and source hashes survive.

`publish_review_batch(hits, spec, output)` reserves a fresh directory and writes:

| Member | Meaning |
|---|---|
| `plan.json` | Frozen policy, pins, full-pool digest, ordered IDs and counts |
| `hits.jsonl` | Complete selected hit records in planning order |
| `review-queue.csv` | The existing fourteen-column format, with four blank decision columns |
| `run.json` | Last completion receipt; exact three-member hashes/sizes, counts, pins and actual source/runtime producer |

The shared writer takes no source paths. Applications enforce their private
output root and source/output ancestry before calling it. Existing directories,
symlink ancestors and linked artifacts refuse. Preserve a failed partial attempt
and use a fresh output epoch rather than modifying it into an apparent success.
The receipt's source-run/context hashes are caller declarations, not proof that
an application run or a scholarly reading was verified by the generic method.

## Verify and continue authored review

`verify_review_batch(directory, expected_receipt_sha256, hits)` returns a
`VerifiedReviewBatch` containing the checked receipt and plan. It verifies exact
directory membership, artifact bytes, the deterministic recomputation, every
selected hit field/order, canonical hit serialization and the blank queue bytes.
A self-consistently rehashed forgery still fails comparison with the supplied
original pool. Verification retains the historical producer rather than assigning
the current verifier's version to old outputs.

Applications must independently load their pinned request and original source
run, validate **all** provided decisions against that complete run before scope
filtering, and compare the entire derived `ReviewPlanSpec` with the verified plan.
They report global and scoped reviewed counts separately. Edited decision queues
are authored inputs for the existing review workflow; do not overwrite the blank
batch or relabel its completion receipt as a decision receipt.

The dependency-light Python 3.9 and optional-stack Python 3.11 gates are separate.
See [verification](../verification.md), [review custody](../shared-methods.md#review-queues-run-membership-and-producer-closure)
and the [application boundary](../applications.md). This operational method adds
no literary labels, manuscript results, source acquisition or new paper deposit.
