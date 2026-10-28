# Copyright (c) 2026 Daniel Ari Friedman
"""Deliberate conversions between distinct source contracts, without role promotion."""

from .models import BundlePassage, ProjectionPassage


def bundle_to_projection(
    passages: tuple[BundlePassage, ...],
) -> tuple[ProjectionPassage, ...]:
    """Represent strict bundle passages under the retained projection schema."""
    return tuple(
        ProjectionPassage.model_validate(passage.model_dump(mode="json"))
        for passage in passages
    )


def projection_to_bundle(
    passages: tuple[ProjectionPassage, ...],
) -> tuple[BundlePassage, ...]:
    """Require stricter bundle validation explicitly, without guessing fields."""
    return tuple(
        BundlePassage.model_validate(passage.model_dump(mode="json"))
        for passage in passages
    )
