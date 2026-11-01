# Exact interval support

`blake.methods.intervals` calculates half-open support within a single
caller-declared coordinate frame. It works with the dependency-light methods
installation on Python 3.9 and later. A frame may represent original source
codepoints or integer hours; the application declares its units and identity.
Never combine offsets from different source units or clocks in one call.

## Admission and operations

`Interval(start=a, end=b)` requires strict nonnegative integers and `a <= b`.
Booleans, strings, floats, extra fields and reversed endpoints are rejected.
Equal endpoints represent empty support. Public operations revalidate existing
models, including instances constructed or copied without Pydantic validation.
The models are frozen. Inputs may be iterables and are not modified.

| Function | Result |
|---|---|
| `interval_union(intervals)` | Sorted maximal positive components; overlap and adjacency coalesce |
| `interval_measure(intervals)` | Integer length of the union, counting each coordinate once |
| `interval_support_at_least(intervals, minimum=2)` | Canonical support covered by at least the declared number of record indices |
| `interval_intersection(left, right)` | Canonical support shared by both operands |
| `interval_difference(left, right)` | Every canonical fragment of left support outside right support |
| `count_overlapping_pairs(intervals)` | Number of unordered record-index pairs with strict positive intersection |

Union, intersection and difference discard empty support and multiplicity.
Threshold support requires a positive strict integer and counts duplicate
positive records separately. Its default measures support with at least two
records, which differs from excess summed length and from pair counts.
Pair counting keeps
separate indices for duplicate positive records. Empty records contribute no
pairs, and `[0, 2)` and `[2, 4)` do not intersect. These distinctions are
deliberate: union support, summed record lengths and overlapping pair counts
answer different questions.

```python
from blake.methods.intervals import (
    Interval,
    count_overlapping_pairs,
    interval_difference,
    interval_measure,
    interval_union,
)

records = (Interval(start=0, end=4), Interval(start=2, end=6),
           Interval(start=6, end=8), Interval(start=2, end=6))
assert interval_union(records) == (Interval(start=0, end=8),)
assert interval_measure(records) == 8
assert count_overlapping_pairs(records) == 3
assert interval_difference(records, (Interval(start=3, end=5),)) == (
    Interval(start=0, end=3), Interval(start=5, end=8),
)
```

## Geometry and interpretation

For a finite collection of records $I_i=[a_i,b_i)$, support is

$$
U(I)=\bigcup_i I_i,\qquad
\mu(I)=\sum_{[a,b)\in\operatorname{components}(U(I))}(b-a).
$$

The indexed-pair count is

$$
P(I)=\sum_{i<j}\mathbf{1}\{\max(a_i,a_j)<\min(b_i,b_j)\}.
$$

Positive duplicate records increase $P$ while leaving $U$ unchanged.
For finite inputs, $0\leq\mu(I)\leq\sum_i(b_i-a_i)$. Applications must
separately establish any source-length upper bound. An empty interval is valid
set geometry; an empty lexical hit can still be invalid under an application's
evidence contract.

The implementation sorts input intervals and does not enumerate every
coordinate or construct the pair list. Union and pair counting take
$O(n\log n)$ time. Threshold support uses combined endpoint events and the
same asymptotic bound. Binary operations canonicalize both operands and scan the
resulting components. Arithmetic uses Python integers without float conversion.

Applications own eligibility, source/copy grouping, interval activation,
missing-window policy and interpretation. A corpus application's source slices
must be checked against the exact original text before geometry is computed.
A timing application's filing conditions must determine active protection
before subtraction. Zero uncovered support does not establish political
legitimacy; source occupancy does not establish reading or adjudication.

The [literal search](../shared-methods.md#choose-a-retrieval-contract) window
algorithm has a different contract: closed feasible integer origins may be
negative and preserve term-count constraints. It does not use this module.

## Verification

The interval tests compare canonical results against independent integer-set
oracles over finite multisets, preserve record multiplicity, exercise both
binary operands and reject invalid ordinary inputs and forged models.
Deliberately incorrect endpoint, deduplication, raw-length and fragment-loss
rules must fail those same contract tests. See [verification scope](../verification.md)
for the actual source and normal installed-wheel qualifications. Application
analyses and manuscripts require their own input and producer bindings.
