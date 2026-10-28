# Copyright (c) 2026 Daniel Ari Friedman
"""Numerical oracles for copy-sensitive descriptive corpus statistics."""

import math

import pytest

from blake.methods.statistics import analyze_corpus
from blake.methods.models import (
    ProjectionPassage as Passage,
    QuerySpec,
    ResearchError,
    Role,
)


def unit(identity, text, work="w1", **changes: object):
    return Passage.model_validate(
        dict(
            passage_id=identity,
            work_id=work,
            author_id="invented",
            title=work,
            edition_id=identity,
            edition="fixture",
            copy_id=identity,
            locator="fixture",
            locator_kind="file_lines",
            source_url="https://example.test/",
            rights="synthetic fixture",
            text_role="primary",
            source_plane="reading",
            text=text,
        )
        | changes
    )


def queries(*names: str):
    return tuple(QuerySpec(query_id=n, variants=(n,), note="fixture") for n in names)


def summary(report, query):
    return next(q for q in report.queries if q.query_id == query)


def pair(report, universe, left, right):
    return next(
        p
        for p in report.cooccurrences
        if p.universe == universe and (p.left_query, p.right_query) == (left, right)
    )


def test_counts_and_weighting_have_hand_computed_oracles():
    data = (
        unit("a", "seed leaf"),
        unit("b", "seed seed"),
        unit("c", "leaf", "w2"),
        unit("d", "seed leaf"),
    )
    report = analyze_corpus(data, queries("seed", "leaf", "absent"))
    seed = summary(report, "seed")
    assert report.primary_source_units == 4
    assert report.primary_work_groups == 2
    assert report.primary_tokens == 7
    assert seed.copy_retaining.occurrences == 4
    assert seed.copy_retaining.matched_units == 3
    assert seed.copy_retaining.rate_per_10000_tokens == pytest.approx(40000 / 7)
    assert seed.copy_retaining.coverage_fraction == 0.75
    assert seed.exact_text.occurrences == 3
    assert seed.exact_text.source_units == 3
    assert seed.exact_text.tokens == 5
    assert seed.work_balanced_rate_per_10000_tokens == pytest.approx(10000 / 3)
    assert seed.work_balanced_coverage_fraction == 0.5
    assert seed.maximum_work_occurrence_share == 1
    assert seed.work_occurrence_hhi == 1
    omitted = {v.omitted_work_id: v.remaining for v in seed.leave_one_work_out}
    assert omitted["w1"].rate_per_10000_tokens == 0
    assert omitted["w2"].rate_per_10000_tokens == pytest.approx(20000 / 3)
    assert len(report.exact_duplicate_groups) == 1
    assert report.exact_duplicate_groups[0].passage_ids == ("a", "d")
    assert report.deduplicated_passage_ids == ("a", "b", "c")
    strata = [s for s in report.strata if s.dimension == "work"]
    assert [(s.key, s.member_passage_ids) for s in strata] == [
        (("w1",), ("a", "b", "d")),
        (("w2",), ("c",)),
    ]


def test_pairwise_document_associations_have_independent_set_oracles():
    data = (
        unit("a", "seed leaf"),
        unit("b", "seed seed"),
        unit("c", "leaf", "w2"),
        unit("d", "seed leaf"),
    )
    report = analyze_corpus(data, queries("seed", "leaf", "absent"))
    value = pair(report, "copy_retaining", "leaf", "seed")
    assert (
        value.unit_count,
        value.left_matches,
        value.right_matches,
        value.both_matches,
        value.either_matches,
    ) == (4, 3, 3, 2, 4)
    assert value.jaccard == 0.5
    assert value.right_given_left == pytest.approx(2 / 3)
    assert value.left_given_right == pytest.approx(2 / 3)
    assert value.lift == pytest.approx(8 / 9)
    dedup = pair(report, "exact_text", "leaf", "seed")
    assert dedup.unit_count == 3
    assert dedup.both_matches == 1
    assert dedup.lift == 0.75
    work = pair(report, "work_presence", "leaf", "seed")
    assert work.unit_count == 2
    assert (work.left_matches, work.right_matches, work.both_matches) == (2, 1, 1)
    assert work.jaccard == 0.5
    assert work.lift == 1


def test_undefined_quantities_are_explicit_not_zero():
    report = analyze_corpus((unit("a", "..."),), queries("...", "none", "missing"))
    present = summary(report, "...")
    assert present.copy_retaining.tokens == 0
    assert present.copy_retaining.occurrences == 1
    assert present.copy_retaining.rate_per_10000_tokens is None
    assert present.work_balanced_rate_per_10000_tokens is None
    assert present.leave_one_work_out[0].remaining.coverage_fraction is None
    absent = summary(report, "none")
    assert absent.maximum_work_occurrence_share is None
    assert absent.work_occurrence_hhi is None
    value = pair(report, "copy_retaining", "missing", "none")
    assert value.jaccard is None
    assert value.lift is None
    assert value.right_given_left is None
    assert value.left_given_right is None
    asymmetry = pair(report, "copy_retaining", "...", "none")
    assert asymmetry.jaccard == 0
    assert asymmetry.right_given_left == 0
    assert asymmetry.left_given_right is None


def test_roles_and_planes_do_not_contaminate_primary_statistics():
    primary = unit("a", "seed")
    editorial = unit("b", "seed " * 100, source_plane="erdman", text_role="editorial")
    unverified = unit("c", "seed " * 100, source_plane="xml", text_role="unverified")
    report = analyze_corpus((primary, editorial, unverified), queries("seed"))
    assert report.total_source_units == 3
    assert report.primary_source_units == 1
    assert summary(report, "seed").copy_retaining.occurrences == 1
    assert [(x.plane.value, x.role.value, x.units) for x in report.source_census] == [
        ("erdman", "editorial", 1),
        ("reading", "primary", 1),
        ("xml", "unverified", 1),
    ]


def test_regex_boundaries_variants_and_unicode_tokens_match_search_contract():
    query = QuerySpec(
        query_id="seeds", variants=("seed", "seeds", "seed"), note="fixture"
    )
    report = analyze_corpus(
        (unit("a", "SEED Seeds seedment seedsman éseed seed2 seed_ seed."),), (query,)
    )
    assert report.primary_tokens == 8
    assert report.queries[0].copy_retaining.occurrences == 3
    assert report.cooccurrences == ()


def test_multitoken_variants_use_occurrences_per_word_token():
    query = QuerySpec(
        query_id="phrase", variants=("green canopy", "green"), note="fixture"
    )
    value = analyze_corpus((unit("a", "Green brotherhood green"),), (query,)).queries[0]
    assert value.copy_retaining.tokens == 3
    assert value.copy_retaining.occurrences == 2
    assert value.copy_retaining.rate_per_10000_tokens == pytest.approx(20000 / 3)


def test_stratification_preserves_work_and_missing_copy_identity():
    report = analyze_corpus(
        (unit("a", "seed", copy_id=None), unit("b", "leaf", "w2", copy_id=None)),
        queries("seed"),
    )
    strata = [s for s in report.strata if s.dimension == "copy"]
    assert [s.key for s in strata] == [("w1", None), ("w2", None)]
    assert all(s.source_units == 1 for s in strata)


def test_order_invariance_and_content_bindings():
    data = (unit("z", "seed"), unit("a", "leaf", "w2"))
    query = queries("seed", "leaf")
    expected = analyze_corpus(data, query)
    assert analyze_corpus(data[::-1], query[::-1]) == expected
    changed = analyze_corpus(
        (data[0].model_copy(update={"text": "Seed"}), data[1]), query
    )
    assert changed.source_sha256 != expected.source_sha256
    role_changed = analyze_corpus(
        (data[0], data[1].model_copy(update={"text_role": Role.UNVERIFIED})), query
    )
    assert role_changed.source_sha256 != expected.source_sha256
    altered_query = (query[0].model_copy(update={"note": "revised"}), query[1])
    assert analyze_corpus(data, altered_query).query_sha256 != expected.query_sha256
    assert all(
        v.copy_retaining.coverage_fraction is not None
        and math.isfinite(v.copy_retaining.coverage_fraction)
        for v in expected.queries
    )


@pytest.mark.parametrize(
    ("data", "query", "code"),
    [
        ((), queries("seed"), "statistics_membership"),
        ((unit("a", "seed"),), (), "statistics_queries"),
        (
            (unit("a", "seed"), unit("a", "leaf")),
            queries("seed"),
            "statistics_membership",
        ),
        (
            (unit("a", "seed", text_role="unverified"),),
            queries("seed"),
            "statistics_primary",
        ),
        ((unit("a", "seed"),), queries("seed", "seed"), "statistics_queries"),
        ((unit("a", "seed"),), queries(" "), "statistics_queries"),
        (
            (unit("a", "seed"),),
            (QuerySpec(query_id="x", variants=(" ",), note="fixture"),),
            "empty_variant",
        ),
    ],
)
def test_invalid_inputs_are_real_failing_controls(data, query, code):
    with pytest.raises(ResearchError) as error:
        analyze_corpus(data, query)
    assert error.value.code == code


def test_zero_token_work_is_explicitly_excluded_from_rate_mean():
    data = (unit("a", "..."), unit("b", "seed", "w2"))
    report = analyze_corpus(data, queries("seed"))
    value = summary(report, "seed")
    assert report.primary_work_groups == 2
    assert value.rate_work_groups == 1
    assert value.work_balanced_rate_per_10000_tokens == 10000
    assert value.work_balanced_coverage_fraction == 0.5
    assert type(report).model_validate_json(report.model_dump_json()) == report


@pytest.mark.parametrize(
    "changes",
    [
        {"passage_id": " "},
        {"work_id": ""},
        {"edition_id": " "},
        {"copy_id": " "},
    ],
)
def test_empty_group_identities_are_rejected(changes):
    with pytest.raises(ResearchError, match="statistics_membership"):
        analyze_corpus((unit("a", "seed", **changes),), queries("seed"))


def test_grouped_edition_and_copy_units_reconcile_separately():
    data = (
        unit("a", "seed", edition_id="e", copy_id="c"),
        unit("b", "leaf", edition_id="e", copy_id="c", title="variant title"),
    )
    report = analyze_corpus(data, queries("seed"))
    for dimension in ("work", "edition", "copy"):
        strata = [s for s in report.strata if s.dimension == dimension]
        assert len(strata) == 1
        assert strata[0].source_units == 2
        assert strata[0].titles == ("variant title", "w1")
        assert strata[0].queries[0].measure.coverage_fraction == 0.5


def test_counted_inventory_preserves_declared_profile_and_counts():
    from blake.methods.statistics import analyze_inventory
    from blake.methods.profiles import RetrievalProfile, runtime_profile

    legacy = analyze_corpus(
        (unit("a", "seed leaf"), unit("b", "seed leaf")), queries("seed")
    )
    result = analyze_inventory(
        legacy.units, ("seed",), runtime_profile(RetrievalProfile.NFKC_TOKENS_V2)
    )
    assert result.queries == legacy.queries
    assert result.profile == "nfkc-casefold-source-spans-v2"
    assert result.tokenization != legacy.tokenization
    assert result.queries[0].exact_text.source_units == 1


@pytest.mark.parametrize(
    "change",
    [
        {"tokens": -1},
        {"occurrences": {"other": 1}},
        {"occurrences": {"seed": -1}},
        {"passage_id": " "},
    ],
)
def test_inventory_refuses_incomplete_or_negative_counts(change):
    from blake.methods.statistics import analyze_inventory
    from blake.methods.profiles import RetrievalProfile, runtime_profile

    inventory = analyze_corpus((unit("a", "seed"),), queries("seed")).units
    with pytest.raises(ResearchError, match="statistics_inventory"):
        analyze_inventory(
            (inventory[0].model_copy(update=change),),
            ("seed",),
            runtime_profile(RetrievalProfile.REGEX_WORDS_V1),
        )


def test_inventory_rejects_inconsistent_duplicate_text_counts():
    from blake.methods.statistics import analyze_inventory
    from blake.methods.profiles import RetrievalProfile, runtime_profile

    inventory = analyze_corpus(
        (unit("a", "seed"), unit("b", "seed")), queries("seed")
    ).units
    with pytest.raises(ResearchError, match="statistics_inventory"):
        analyze_inventory(
            (inventory[0], inventory[1].model_copy(update={"tokens": 99})),
            ("seed",),
            runtime_profile(RetrievalProfile.REGEX_WORDS_V1),
        )
