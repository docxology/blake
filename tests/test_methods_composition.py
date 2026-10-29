"""Independent finite numerical oracles, SDK boundary checks and real files.

Size policy (# noqa: SIZE_OK): user-owned focused suite includes independent oracles
and all boundary controls.
"""

import pytest

from blake.methods.composition import (
    GroupCounts,
    GroupedInventory,
    composition_audit,
    minimum_groups,
    proportions,
    total_variation,
)
from blake.methods.profiles import RetrievalProfile, runtime_profile
from blake.methods.statistics import analyze_inventory
from blake.methods.statistics_models import QuerySummary, SourceUnit


def oracle_inventory() -> tuple[GroupedInventory, tuple[QuerySummary, ...]]:
    # By hand: pooled (8/12,4/12), mean nonempty composition ((.8+0)/2,(.2+1)/2).
    # Their TV = |2/3-2/5| = 4/15. Zero-mass C must not add a fictitious profile.
    works = (
        GroupCounts(
            group_id="A", source_units=1, tokens=10, counts=(8, 2), matched_units=(1, 1)
        ),
        GroupCounts(
            group_id="B", source_units=1, tokens=10, counts=(0, 2), matched_units=(0, 1)
        ),
        GroupCounts(
            group_id="C", source_units=1, tokens=0, counts=(0, 0), matched_units=(0, 0)
        ),
    )
    units = tuple(
        SourceUnit(
            passage_id=w.group_id,
            work_id=w.group_id,
            title=w.group_id,
            edition_id="fixture",
            copy_id=None,
            text_sha256=str(i) * 64,
            tokens=w.tokens,
            occurrences=dict(zip(("alpha", "beta"), w.counts)),
        )
        for i, w in enumerate(works)
    )
    shared = analyze_inventory(
        units, ("alpha", "beta"), runtime_profile(RetrievalProfile.NFKC_TOKENS_V2)
    )
    return GroupedInventory(categories=("alpha", "beta"), groups=works), shared.queries


def test_independent_composition_and_omission_oracle() -> None:
    inventory, summaries = oracle_inventory()
    result = composition_audit(inventory, summaries)
    assert (
        result.source_units,
        result.tokens,
        result.groups,
        result.nonempty_groups,
    ) == (3, 20, 3, 2)
    assert result.pooled_vs_equal_nonempty_tv == pytest.approx(4 / 15)
    worm, fly = result.categories
    assert worm.pooled_share == pytest.approx(2 / 3)
    assert worm.equal_nonempty_group_share == pytest.approx(2 / 5)
    assert worm.difference_percentage_points == pytest.approx(-80 / 3)
    assert worm.effective_groups == 1
    assert fly.effective_groups == 2
    assert (worm.minimum_groups_for_half, worm.minimum_groups_for_four_fifths) == (1, 1)
    assert (fly.minimum_groups_for_half, fly.minimum_groups_for_four_fifths) == (1, 2)
    a, b, c = result.omissions
    assert a.composition_tv_from_full == pytest.approx(2 / 3)
    assert b.composition_tv_from_full == pytest.approx(2 / 15)
    assert c.composition_tv_from_full == 0
    assert (a.leading_category, b.leading_category) == ("beta", "alpha")


def test_zero_inventory_and_total_omission_are_undefined() -> None:
    inv, _summaries = oracle_inventory()
    zero_works = tuple(
        w.model_copy(update={"counts": (0, 0), "matched_units": (0, 0)})
        for w in inv.groups
    )
    units = tuple(
        SourceUnit(
            passage_id=w.group_id,
            work_id=w.group_id,
            title="fixture",
            edition_id="fixture",
            copy_id=None,
            text_sha256=str(i) * 64,
            tokens=w.tokens,
            occurrences={"alpha": 0, "beta": 0},
        )
        for i, w in enumerate(zero_works)
    )
    shared = analyze_inventory(
        units, ("alpha", "beta"), runtime_profile(RetrievalProfile.NFKC_TOKENS_V2)
    )
    result = composition_audit(
        GroupedInventory(categories=inv.categories, groups=zero_works), shared.queries
    )
    assert result.pooled_vs_equal_nonempty_tv is None
    assert result.nonempty_groups == 0
    assert all(
        c.pooled_share is None and c.effective_groups is None for c in result.categories
    )
    assert all(o.composition_tv_from_full is None for o in result.omissions)
    one = GroupedInventory(categories=inv.categories, groups=(inv.groups[0],))
    unit = SourceUnit(
        passage_id="A",
        work_id="A",
        title="fixture",
        edition_id="fixture",
        copy_id=None,
        text_sha256="a" * 64,
        tokens=10,
        occurrences={"alpha": 8, "beta": 2},
    )
    q = analyze_inventory(
        (unit,), inv.categories, runtime_profile(RetrievalProfile.NFKC_TOKENS_V2)
    ).queries
    assert composition_audit(one, q).omissions[0].composition_tv_from_full is None


def test_exact_text_count_comes_from_sdk_not_private_dedup() -> None:
    unit = SourceUnit(
        passage_id="A",
        work_id="A",
        title="fixture",
        edition_id="fixture",
        copy_id=None,
        text_sha256="a" * 64,
        tokens=10,
        occurrences={"alpha": 8, "beta": 2},
    )
    twin = unit.model_copy(update={"passage_id": "B", "copy_id": "copyB"})
    shared = analyze_inventory(
        (unit, twin),
        ("alpha", "beta"),
        runtime_profile(RetrievalProfile.NFKC_TOKENS_V2),
    )
    inv = GroupedInventory(
        categories=("alpha", "beta"),
        groups=(
            GroupCounts(
                group_id="A",
                source_units=2,
                tokens=20,
                counts=(16, 4),
                matched_units=(2, 2),
            ),
        ),
    )
    result = composition_audit(inv, shared.queries)
    assert [(c.candidates, c.exact_text_candidates) for c in result.categories] == [
        (16, 8),
        (4, 2),
    ]


@pytest.mark.parametrize("counts", [(), (-1, 2), (True, 2), (1.0, 2)])
def test_malformed_category_vectors_reject(counts: tuple) -> None:
    with pytest.raises(ValueError):
        proportions(counts)


@pytest.mark.parametrize(
    "left,right",
    [
        ((), ()),
        ((1.0,), (0.5, 0.5)),
        ((float("nan"),), (1.0,)),
        ((1.1, -0.1), (0.0, 1.0)),
        ((0.2, 0.2), (0.5, 0.5)),
    ],
)
def test_invalid_profiles_reject(left: tuple, right: tuple) -> None:
    with pytest.raises(ValueError):
        total_variation(left, right)


def test_distance_endpoints_and_thresholds() -> None:
    assert total_variation((1.0, 0.0), (0.0, 1.0)) == 1
    assert total_variation((0.5, 0.5), (0.5, 0.5)) == 0
    assert minimum_groups((4, 1, 0), 4, 5) == 1
    assert minimum_groups((3, 1, 1), 4, 5) == 2
    assert minimum_groups((0, 0), 1, 2) is None
    with pytest.raises(ValueError):
        minimum_groups((1,), 0, 1)
    with pytest.raises(ValueError):
        minimum_groups((1,), 2, 1)


def test_inventory_integrity_controls() -> None:
    inv, q = oracle_inventory()
    with pytest.raises(ValueError):
        GroupedInventory(categories=("alpha", "alpha"), groups=inv.groups)
    with pytest.raises(ValueError):
        GroupedInventory(
            categories=inv.categories, groups=(inv.groups[0], inv.groups[0])
        )
    with pytest.raises(ValueError):
        GroupCounts(
            group_id="A", source_units=1, tokens=0, counts=(1,), matched_units=(1,)
        )
    with pytest.raises(ValueError):
        GroupCounts(
            group_id="A", source_units=1, tokens=1, counts=(1,), matched_units=(2,)
        )
    with pytest.raises(ValueError):
        composition_audit(inv, q[:-1])
    with pytest.raises(ValueError):
        composition_audit(inv, q + q)
    wrong = GroupedInventory(categories=inv.categories, groups=inv.groups[:2])
    with pytest.raises(ValueError):
        composition_audit(wrong, q)


def test_inverse_concentration_and_exact_rational_thresholds() -> None:
    from blake.methods.composition import inverse_concentration

    assert inverse_concentration((0, 0)) is None
    assert inverse_concentration((10, 0)) == 1
    assert inverse_concentration((3, 3, 3)) == pytest.approx(3)
    # Integer products avoid floating-point rounding at a rational threshold.
    assert minimum_groups((10**30, 10**30, 0), 1, 2) == 1
    assert minimum_groups((2, 2, 2), 2, 3) == 2
    assert minimum_groups((0, 2, 2), 1, 1) == 2
    for numerator, denominator in ((True, 1), (1, True), (1, 0), (1, -1)):
        with pytest.raises(ValueError):
            minimum_groups((1,), numerator, denominator)


@pytest.mark.parametrize(
    "left,right",
    [((True,), (1.0,)), ((float("inf"),), (1.0,)), ((float("-inf"),), (1.0,))],
)
def test_additional_invalid_profiles(left: tuple, right: tuple) -> None:
    with pytest.raises(ValueError):
        total_variation(left, right)


def test_strata_selection_and_integrity() -> None:
    from blake.methods.composition import inventory_from_strata

    inv, _ = oracle_inventory()
    units = tuple(
        SourceUnit(
            passage_id=w.group_id,
            work_id=w.group_id,
            title="fixture",
            edition_id="e",
            copy_id=None,
            text_sha256=str(i) * 64,
            tokens=w.tokens,
            occurrences=dict(zip(inv.categories, w.counts)),
        )
        for i, w in enumerate(inv.groups)
    )
    stats = analyze_inventory(
        units, inv.categories, runtime_profile(RetrievalProfile.NFKC_TOKENS_V2)
    )
    strata = tuple(s for s in stats.strata if s.dimension == "work")
    assert inventory_from_strata(inv.categories, strata) == inv
    broken = (
        strata[0].model_copy(update={"dimension": "edition"}),
        strata[0].model_copy(update={"key": ()}),
        strata[0].model_copy(update={"key": (None,)}),
        strata[0].model_copy(update={"queries": strata[0].queries * 2}),
        strata[0].model_copy(update={"queries": ()}),
        strata[0].model_copy(update={"source_units": 2}),
        strata[0].model_copy(update={"tokens": 100}),
        strata[0].model_copy(
            update={"member_passage_ids": strata[0].member_passage_ids * 2}
        ),
    )
    for bad in broken:
        with pytest.raises(ValueError):
            inventory_from_strata(inv.categories, (bad,))
    with pytest.raises(ValueError):
        inventory_from_strata(inv.categories, (strata[0], strata[0]))
    with pytest.raises(ValueError):
        inventory_from_strata(("missing",), strata)
    for changes in ({"categories": ("",)}, {"categories": ("alpha",)}, {"groups": ()}):
        with pytest.raises(ValueError):
            GroupedInventory.model_validate({**inv.model_dump(), **changes})
    for changes in (
        {"group_id": " "},
        {"counts": (1,), "matched_units": (0,)},
        {"matched_units": ()},
        {"counts": (True, 0)},
    ):
        with pytest.raises(ValueError):
            GroupCounts.model_validate({**inv.groups[0].model_dump(), **changes})


def test_tied_leader_uses_declared_category_order() -> None:
    inv, _ = oracle_inventory()
    units = tuple(
        SourceUnit(
            passage_id=str(i),
            work_id=str(i),
            title="fixture",
            edition_id="e",
            copy_id=None,
            text_sha256=str(i) * 64,
            tokens=2,
            occurrences={"beta": 1, "alpha": 1},
        )
        for i in range(2)
    )
    stats = analyze_inventory(
        units, ("beta", "alpha"), runtime_profile(RetrievalProfile.NFKC_TOKENS_V2)
    )
    from blake.methods.composition import inventory_from_strata

    inventory = inventory_from_strata(
        ("beta", "alpha"), tuple(s for s in stats.strata if s.dimension == "work")
    )
    result = composition_audit(inventory, stats.queries)
    assert all(o.leading_category == "beta" for o in result.omissions)
    assert result.pooled_vs_equal_nonempty_tv == 0
