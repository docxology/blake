# Copyright (c) 2026 Daniel Ari Friedman
"""Finite grouped-category composition without retrieval or application policy.

Zero mass is undefined. All groups remain in the inventory; only positive-mass
profiles enter the equal-group mean. A group is a supplied identity, not an
assertion of independent sampling. Category overlap is retained.


Size policy (# noqa: SIZE_OK): single user-owned generic API keeps its typed models
and arithmetic together.
"""

from collections.abc import Sequence
from itertools import accumulate
from math import fsum
from typing import Annotated, Literal, Optional

from pydantic import Field, model_validator

from .common import EvidenceError, FrozenModel
from .statistics_models import QuerySummary, Stratum

Count = Annotated[int, Field(ge=0, strict=True)]


class GroupCounts(FrozenModel):
    group_id: str = Field(min_length=1)
    source_units: Annotated[int, Field(gt=0, strict=True)]
    tokens: Count
    counts: tuple[Count, ...]
    matched_units: tuple[Count, ...]

    @model_validator(mode="after")
    def reconcile(self) -> "GroupCounts":
        if (
            not self.group_id.strip()
            or len(self.counts) != len(self.matched_units)
            or any(
                m > min(c, self.source_units) or bool(c) != bool(m)
                for c, m in zip(self.counts, self.matched_units)
            )
            or (not self.tokens and any(self.counts))
        ):
            raise EvidenceError(
                "composition_input", "group count/coverage/token inconsistency"
            )
        return self


class GroupedInventory(FrozenModel):
    categories: tuple[str, ...] = Field(min_length=1)
    groups: tuple[GroupCounts, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def reconcile(self) -> "GroupedInventory":
        if (
            len(set(self.categories)) != len(self.categories)
            or any(not c.strip() for c in self.categories)
            or len({w.group_id for w in self.groups}) != len(self.groups)
            or any(len(w.counts) != len(self.categories) for w in self.groups)
        ):
            raise EvidenceError(
                "composition_input", "unique complete inventory required"
            )
        return self


class CompositionContrast(FrozenModel):
    category: str
    candidates: Count
    exact_text_candidates: Count
    matched_units: Count
    positive_groups: Count
    pooled_share: Optional[float]
    equal_nonempty_group_share: Optional[float]
    difference_percentage_points: Optional[float]
    minimum_groups_for_half: Optional[int]
    minimum_groups_for_four_fifths: Optional[int]
    effective_groups: Optional[float]


class OmissionEffect(FrozenModel):
    omitted_group_id: str
    omitted_source_units: Count
    omitted_tokens: Count
    removed_candidates: Count
    remaining_candidates: Count
    composition_tv_from_full: Optional[float]
    leading_category: Optional[str]


class CompositionAudit(FrozenModel):
    schema_version: Literal[1] = 1
    category_ids: tuple[str, ...]
    source_units: Count
    tokens: Count
    groups: Count
    nonempty_groups: Count
    category_candidates: Count
    pooled_vs_equal_nonempty_tv: Optional[float]
    categories: tuple[CompositionContrast, ...]
    omissions: tuple[OmissionEffect, ...]
    limits: str = (
        "Shares divide sums of declared category counts; overlap and repeated source "
        "units remain as supplied. "
        "Equal composition weights only groups with a positive category sum; empty "
        "groups have undefined composition and remain in coverage exports. "
        "Total variation "
        "is a finite profile distance, not a significance test. Effective groups are "
        "inverse concentration, not an independent-group count."
    )


def proportions(counts: Sequence[int]) -> Optional[tuple[float, ...]]:
    """Normalize a declared category vector; a zero mass has no composition."""
    if not counts or any(type(c) is not int or c < 0 for c in counts):
        raise EvidenceError(
            "composition_input", "nonempty nonnegative integer category counts required"
        )
    total = sum(counts)
    return tuple(c / total for c in counts) if total else None


def total_variation(left: Sequence[float], right: Sequence[float]) -> float:
    """Distance between two finite categorical probability profiles, in [0, 1]."""
    if (
        not left
        or len(left) != len(right)
        or any(
            type(value) not in (int, float) or not 0 <= value <= 1
            for value in (*left, *right)
        )
        or abs(fsum(left) - 1) > 1e-12
        or abs(fsum(right) - 1) > 1e-12
    ):
        raise EvidenceError(
            "composition_input", "two equally sized normalized profiles required"
        )
    return 0.5 * fsum(abs(a - b) for a, b in zip(left, right))


def minimum_groups(
    counts: Sequence[int], numerator: int, denominator: int
) -> Optional[int]:
    """Smallest descending group-count prefix reaching a declared rational mass."""
    if (
        type(numerator) is not int
        or type(denominator) is not int
        or not 0 < numerator <= denominator
    ):
        raise EvidenceError("composition_input", "fraction must lie in (0,1]")
    _ = proportions(counts)
    total = sum(counts)
    if not total:
        return None
    # The positive, validated mass guarantees a final prefix at the total.
    # Count the prefixes strictly below the threshold, then take the next rank.
    return 1 + sum(
        prefix * denominator < numerator * total
        for prefix in accumulate(sorted(counts, reverse=True))
    )


def composition_audit(
    inventory: GroupedInventory, summaries: tuple[QuerySummary, ...]
) -> CompositionAudit:
    """Contrast pooled categorical mass, mean within-group composition and omissions."""
    inventory = GroupedInventory.model_validate(inventory.model_dump())
    summaries = tuple(QuerySummary.model_validate(q.model_dump()) for q in summaries)
    categories, groups = inventory.categories, inventory.groups
    totals = tuple(sum(w.counts[i] for w in groups) for i in range(len(categories)))
    pooled = proportions(totals)
    profiles = tuple(p for w in groups if (p := proportions(w.counts)) is not None)
    balanced = (
        tuple(
            fsum(p[i] for p in profiles) / len(profiles) for i in range(len(categories))
        )
        if profiles
        else None
    )
    summary = {q.query_id: q for q in summaries}
    if len(summary) != len(summaries) or any(c not in summary for c in categories):
        raise EvidenceError(
            "composition_input", "complete unique shared summaries required"
        )
    rows: list[CompositionContrast] = []
    for i, category in enumerate(categories):
        q = summary[category]
        matched = sum(w.matched_units[i] for w in groups)
        if (
            totals[i],
            matched,
            sum(w.source_units for w in groups),
            sum(w.tokens for w in groups),
        ) != (
            q.copy_retaining.occurrences,
            q.copy_retaining.matched_units,
            q.copy_retaining.source_units,
            q.copy_retaining.tokens,
        ):
            raise EvidenceError(
                "composition_input",
                "group inventory does not reconcile with shared summary",
            )
        counts = tuple(w.counts[i] for w in groups)
        rows.append(
            CompositionContrast(
                category=category,
                candidates=totals[i],
                exact_text_candidates=q.exact_text.occurrences,
                matched_units=matched,
                positive_groups=sum(c > 0 for c in counts),
                pooled_share=pooled[i] if pooled is not None else None,
                equal_nonempty_group_share=balanced[i]
                if balanced is not None
                else None,
                difference_percentage_points=100 * (balanced[i] - pooled[i])
                if balanced is not None and pooled is not None
                else None,
                minimum_groups_for_half=minimum_groups(counts, 1, 2),
                minimum_groups_for_four_fifths=minimum_groups(counts, 4, 5),
                effective_groups=inverse_concentration(counts),
            )
        )
    omissions: list[OmissionEffect] = []
    for work in groups:
        remaining = tuple(total - count for total, count in zip(totals, work.counts))
        profile = proportions(remaining)
        omissions.append(
            OmissionEffect(
                omitted_group_id=work.group_id,
                omitted_source_units=work.source_units,
                omitted_tokens=work.tokens,
                removed_candidates=sum(work.counts),
                remaining_candidates=sum(remaining),
                composition_tv_from_full=total_variation(pooled, profile)
                if pooled is not None and profile is not None
                else None,
                leading_category=categories[
                    max(range(len(categories)), key=lambda i: remaining[i])
                ]
                if sum(remaining)
                else None,
            )
        )
    return CompositionAudit(
        category_ids=categories,
        source_units=sum(w.source_units for w in groups),
        tokens=sum(w.tokens for w in groups),
        groups=len(groups),
        nonempty_groups=len(profiles),
        category_candidates=sum(totals),
        pooled_vs_equal_nonempty_tv=total_variation(pooled, balanced)
        if pooled is not None and balanced is not None
        else None,
        categories=tuple(rows),
        omissions=tuple(omissions),
    )


def inverse_concentration(counts: Sequence[int]) -> Optional[float]:
    """Inverse sum of squared group shares, undefined for zero total mass."""
    shares = proportions(counts)
    return 1 / fsum(s * s for s in shares) if shares is not None else None


def inventory_from_strata(
    category_ids: tuple[str, ...], strata: tuple[Stratum, ...]
) -> GroupedInventory:
    """Select explicit category IDs from complete, nonoverlapping work strata.

    All selected queries must occur once per stratum, including zero rows.
    Per-query denominators and member identities must reconcile with each group.
    Other categories may be present and are not silently selected.
    """
    groups: list[GroupCounts] = []
    members: set[str] = set()
    for stratum in strata:
        queries = {q.query_id: q.measure for q in stratum.queries}
        ids = set(stratum.member_passage_ids)
        if (
            stratum.dimension != "work"
            or len(stratum.key) != 1
            or stratum.key[0] is None
            or len(queries) != len(stratum.queries)
            or not set(category_ids).issubset(queries)
            or len(ids) != len(stratum.member_passage_ids)
            or len(ids) != stratum.source_units
            or members.intersection(ids)
            or any(
                (queries[q].source_units, queries[q].tokens)
                != (stratum.source_units, stratum.tokens)
                for q in category_ids
            )
        ):
            raise EvidenceError(
                "composition_strata", "Require complete disjoint group strata"
            )
        members.update(ids)
        groups.append(
            GroupCounts(
                group_id=stratum.key[0],
                source_units=stratum.source_units,
                tokens=stratum.tokens,
                counts=tuple(queries[q].occurrences for q in category_ids),
                matched_units=tuple(queries[q].matched_units for q in category_ids),
            )
        )
    return GroupedInventory(categories=category_ids, groups=tuple(groups))
