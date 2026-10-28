# Copyright (c) 2026 Daniel Ari Friedman
"""Behavioral controls for explicit, uncapped lexical studies."""

import pytest
from pydantic import ValidationError

from blake.studies import (
    StudyError,
    StudySpec,
    StudyTerm,
    scan_passages,
    summarize,
)
from blake.text_search.models import Passage
from blake.text_search.normalize import spans, tokenize


def passage(text: str, identity: str = "p1", **changes) -> Passage:
    values = dict(
        passage_id=identity,
        work_id="work",
        author_id="william-blake-1757-1827",
        title="Synthetic source",
        edition_id="copy-a",
        edition="Synthetic edition",
        copy_id="A",
        locator="page 1",
        locator_kind="page",
        source_url="https://example.org/synthetic",
        rights="Synthetic test text",
        text_role="primary",
        source_plane="reading",
        text=text,
        source_sha256="f" * 64,
    )
    values.update(changes)
    return Passage.model_validate(values)


def spec(*terms: StudyTerm) -> StudySpec:
    return StudySpec(study_id="synthetic", title="Synthetic study", terms=terms)


def term(identity: str, *forms: str) -> StudyTerm:
    return StudyTerm(term_id=identity, forms=forms, group="synthetic")


def test_whole_tokens_retain_homographs_and_explicit_historical_forms():
    # Given a substring trap, a verb and explicit historical spellings.
    source = passage("A giant and an ant fly past Emmet, EMMETT and emmetts.")
    registry = spec(
        term("ant", "ant", "Emmet", "emmett", "emmetts"), term("fly", "fly")
    )

    # When candidates are retrieved without semantic classification.
    result = scan_passages((source,), registry)

    # Then giant is excluded, while the verb and every declared spelling remain.
    assert [hit.expression for hit in result.hits] == [
        "ant",
        "fly",
        "Emmet",
        "EMMETT",
        "emmetts",
    ]
    assert sum(hit.term_id == "ant" for hit in result.hits) == 4


@pytest.mark.parametrize(
    ("text", "form"),
    [
        ("The earth-\nWorm stirs.", "earth worm"),
        ("\uff25\uff4d\uff4d\uff45\uff54 crawls.", "emmet"),
        ("A ﬂy and a fly.", "fly"),
        ("The bee\u2019s path.", "bee"),
        ("The cafe\u0301 houses a bee.", "bee"),
    ],
)
def test_original_unicode_offsets_match_the_shared_span_oracle(text, form):
    # Given punctuation and Unicode transformations in original source text.
    source = passage(text)
    registry = spec(term("candidate", form))
    expected = spans(tokenize(text), form)

    # When the compiled batch matcher scans the source.
    result = scan_passages((source,), registry)

    # Then source offsets and unchanged expression agree with the shared oracle.
    assert [(hit.start, hit.end, hit.expression) for hit in result.hits] == [
        (match.start, match.end, match.matched_text) for match in expected
    ]
    assert all(text[hit.start : hit.end] == hit.expression for hit in result.hits)


def test_unlimited_occurrences_and_duplicate_normalized_forms():
    # Given more matches than the interactive search display cap.
    source = passage(" ".join(["fly"] * 1201))
    registry = spec(term("fly", "fly", "FLY", "\uff46\uff4c\uff59"))

    # When a study scans all occurrences.
    result = scan_passages((source,), registry)

    # Then every span appears once for its category, without pagination.
    assert len(result.hits) == 1201
    assert len({hit.hit_id for hit in result.hits}) == 1201
    assert summarize(result).total_occurrences == 1201


def test_zero_cells_and_source_denominators_preserve_roles_and_planes():
    # Given the same word in primary, unverified and editorial source units.
    sources = (
        passage("bee", "primary"),
        passage("bee bee", "unverified", text_role="unverified"),
        passage(
            "bee text",
            "editorial",
            text_role="editorial",
            source_plane="erdman",
            author_id="mixed-edition",
        ),
        passage("<bee>bee</bee>", "xml", text_role="unverified", source_plane="xml"),
    )
    registry = spec(term("bee", "bee"), term("absent", "notpresent"))

    # When all declared source planes are scanned.
    result = scan_passages(sources, registry)

    # Then the 18 category cells and 18 author denominator cells include zeros.
    assert len(result.rows) == 18
    assert len(result.denominators) == 18
    counts = {
        (row.term_id, row.text_role, row.source_plane): row.occurrences
        for row in result.rows
    }
    assert counts[("bee", "primary", "reading")] == 1
    assert counts[("bee", "unverified", "reading")] == 2
    assert counts[("bee", "editorial", "erdman")] == 1
    assert counts[("bee", "unverified", "xml")] == 3
    assert all(row.occurrences == 0 for row in result.rows if row.term_id == "absent")
    assert sum(row.passages for row in result.denominators) == 4
    assert sum(row.word_tokens for row in result.denominators) == 8
    assert summarize(result).blake_primary_occurrences == 1


def test_primary_counts_require_identified_blake_authorship():
    # Given a primary-labeled reading by another named author.
    source = passage("bee", author_id="another-author")

    # When it matches the vocabulary.
    result = scan_passages((source,), spec(term("bee", "bee")))

    # Then its source role remains primary but it is not a Blake-primary hit.
    assert result.hits[0].text_role == "primary"
    assert result.hits[0].blake_primary is False
    assert summarize(result).blake_primary_occurrences == 0


def test_copy_repetition_and_exact_text_groups_remain_separate_counts():
    # Given two copies with identical transcription bytes and another text.
    sources = (
        passage("bee", "a"),
        passage("bee", "b", edition_id="copy-b", copy_id="B"),
        passage("bee bee", "c", edition_id="copy-c", copy_id="C"),
    )

    # When the complete source membership is scanned.
    result = scan_passages(sources, spec(term("bee", "bee")))

    # Then occurrences, copies and byte-identical groups describe different units.
    summary = summarize(result)
    assert (
        summary.total_occurrences,
        summary.matched_passages,
        summary.matched_editions,
        summary.exact_text_groups,
    ) == (4, 3, 3, 2)
    assert sum(row.exact_text_groups for row in result.denominators) == 2


def test_overlapping_categories_are_distinct_category_span_hits():
    # Given two application categories intentionally naming one expression.
    source = passage("honey-bee")
    registry = spec(term("bee", "bee"), term("honeybee", "honey bee"))

    # When both explicit forms match.
    result = scan_passages((source,), registry)

    # Then category-specific hits retain their own spans and stable identities.
    assert [(hit.term_id, hit.expression) for hit in result.hits] == [
        ("honeybee", "honey-bee"),
        ("bee", "bee"),
    ]
    assert len({hit.hit_id for hit in result.hits}) == 2
    assert result.hit_definition == "category-source-span"


def test_normalization_expansion_deduplicates_one_category_source_span():
    # Given one Unicode character normalized to two separated numeric tokens.
    source = passage("\u00bd")
    registry = spec(term("fraction", "1", "2"))

    # When both forms identify the same original character interval.
    result = scan_passages((source,), registry)

    # Then that category retains one source-span candidate.
    assert [(hit.start, hit.end, hit.expression) for hit in result.hits] == [
        (0, 1, "\u00bd")
    ]


def test_phrase_prefix_without_complete_contiguous_match_is_excluded():
    # Given first-token matches with a missing or different remaining phrase.
    source = passage("honey pot and honey")

    # When an explicit two-token form is searched.
    result = scan_passages((source,), spec(term("honeybee", "honey bee")))

    # Then prefix matches do not become phrase occurrences.
    assert result.hits == ()
    assert all(row.occurrences == 0 for row in result.rows)


def test_stable_ids_ignore_input_order_but_bind_source_expression():
    # Given identical source membership in different tuple orders.
    first = passage("bee", "a")
    second = passage("fly", "b")
    registry = spec(term("bee", "bee"), term("fly", "fly"))

    # When both memberships are scanned and a source text is subsequently changed.
    original = scan_passages((second, first), registry)
    reordered = scan_passages((first, second), registry)
    changed = scan_passages((passage("bee bee", "a"), second), registry)

    # Then ordering is stable and altered source bytes invalidate the old hit ID.
    assert original == reordered
    assert original.hits[0].hit_id != changed.hits[0].hit_id


def test_registry_digest_binds_declared_forms_and_notes():
    # Given registries with different declared retrieval and interpretation scope.
    source = passage("bee")
    old = spec(term("bee", "bee"))
    revised = spec(
        StudyTerm(term_id="bee", forms=("bee", "bees"), group="insect", note="review")
    )

    # When the same source is scanned under each registry.
    first = scan_passages((source,), old)
    second = scan_passages((source,), revised)

    # Then the identical visible match does not erase the registry change.
    assert first.hits[0].expression == second.hits[0].expression
    assert first.spec_sha256 != second.spec_sha256


def test_text_free_summary_omits_provider_expression_and_context():
    # Given a private source carrying a sentinel outside the matched expression.
    source = passage("private-provider-sentinel a bee")
    result = scan_passages((source,), spec(term("bee", "bee")))

    # When a distributable aggregate is requested.
    summary = summarize(result).model_dump(mode="json")

    # Then neither hits nor source text can escape through summary serialization.
    assert "hits" not in summary
    assert "private-provider-sentinel" not in str(summary)
    assert "expression" not in str(summary)
    assert summary["total_occurrences"] == 1


@pytest.mark.parametrize("forms", [("",), ("---",), ("bee", "   ")])
def test_empty_normalized_forms_are_rejected(forms):
    # Given a form that cannot identify source words.
    with pytest.raises(ValidationError, match="empty_normalized_form"):
        # When it crosses the registry boundary, then it is rejected.
        StudyTerm(term_id="invalid", forms=forms, group="synthetic")


def test_duplicate_term_ids_are_rejected():
    # Given two categories with an ambiguous shared machine identity.
    with pytest.raises(ValidationError, match="duplicate_term_id"):
        # When the registry is parsed, then it is rejected.
        spec(term("same", "bee"), term("same", "fly"))


def test_empty_registry_is_rejected():
    # Given a vocabulary with no declared search categories.
    with pytest.raises(ValidationError):
        # When parsed, then absence cannot masquerade as an exhaustive search.
        spec()


def test_duplicate_passage_ids_are_rejected():
    # Given two byte-distinct records with one source identity.
    with pytest.raises(StudyError, match="duplicate_passage_id"):
        # When scanned, then the ambiguous source membership is rejected.
        scan_passages((passage("bee"), passage("fly")), spec(term("bee", "bee")))


def test_empty_source_membership_retains_declared_zero_rows():
    # Given a declared vocabulary and explicitly empty source membership.
    registry = spec(term("bee", "bee"))

    # When that bounded membership is scanned.
    result = scan_passages((), registry)

    # Then zero source units remain distinct from missing category rows.
    assert result.scanned_passages == 0
    assert len(result.rows) == 9
    assert result.denominators == ()
    assert all(row.occurrences == 0 for row in result.rows)
    assert summarize(result).total_occurrences == 0
