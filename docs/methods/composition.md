# Finite grouped-category composition

`blake.methods.composition` is a lightweight Python 3.9+ API. It accepts counts,
not text or application vocabulary. It does not tokenize, match, deduplicate or
assign a category policy.

```python
from blake.methods.composition import inventory_from_strata, composition_audit

# statistics is a validated CountedStatistics from the shared counting API.
work_strata = tuple(s for s in statistics.strata if s.dimension == "work")
inventory = inventory_from_strata(("category_a", "category_b"), work_strata)
audit = composition_audit(inventory, statistics.queries)
```

`GroupCounts(group_id, source_units, tokens, counts, matched_units)` stores a
single group's ordered count vector. Counts, tokens and coverage are strict
nonnegative integers; booleans are refused. A group must contain at least one
source unit. Positive counts require positive matched-unit coverage and positive
tokens. Coverage cannot exceed either the count or the source-unit denominator.
`GroupedInventory(categories, groups)` requires nonempty unique category IDs and
group IDs, complete vectors, and explicit zeros. IDs and category order are supplied
by the caller. In a tied leading category, the first declared category wins.

`inventory_from_strata(category_ids, strata)` selects exactly the caller's IDs,
including zero rows, from complete shared work strata. It refuses missing or
duplicate query rows, inconsistent denominators, duplicate members and overlapping
group membership. Other declared categories may exist without being selected.
`composition_audit` reconciles selected category totals, matched units, source-unit
and token denominators against unique shared `QuerySummary` objects. Exact-text
counts come from those shared summaries; this API performs no new deduplication.

The standalone numerical functions are:

- `proportions(counts)`: normalize a nonempty vector of nonnegative integers.
  Zero mass returns `None`.
- `total_variation(left, right)`: half the L1 distance between equal-length,
  finite probability vectors. Each sum must be within `1e-12` of one. NaN,
  infinity, booleans, negative values and malformed shapes fail.
- `minimum_groups(counts, numerator, denominator)`: the shortest descending-count
  prefix reaching the rational mass. Integer cross-products preserve exact
  threshold comparisons. Fractions must be in `(0, 1]`; zero mass is undefined.
- `inverse_concentration(counts)`: inverse sum of squared group shares, or `None`
  for zero mass.

The audit reports pooled category shares, mean within-group shares across **only
positive-mass groups**, their percentage-point differences, total variation,
concentration thresholds, inverse concentration, and the profile distance after
each entire group is omitted. Zero-mass groups stay in the inventory and coverage
exports. An omission leaving zero mass has undefined distance and no leading
category. This composition mean is distinct from mean token rates, where a
positive-token group can have a defined zero rate.

All results describe the supplied finite inventory. Counts may overlap across
categories; repeated source units remain as supplied. Category mass is not a count
of entities, and group IDs do not establish independent observations. There is no
sampling inference, randomization or confidence interval.

Qualification uses an independent `(8,2), (0,2), (0,0)` three-group oracle: pooled
composition `(2/3,1/3)`, equal nonempty-group composition `(2/5,3/5)`, and total
variation `4/15`. Tests also cover zero and single groups, concentration endpoints,
exact rational thresholds, malformed inputs, shared exact-text counts and tied order.
