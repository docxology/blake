"""Typed boundaries shared by manuscript projections."""
from __future__ import annotations

from typing import TypedDict


class CategoryCoverage(TypedDict):
    """Category counts retained in the statistical JSON sidecar."""

    category: str
    target_total: int
    open_targets: int
    open_pct: float
    status_counts: dict[str, int]


class ImageDepthRow(TypedDict, total=False):
    """Numeric fields consumed from an image-depth evidence row."""

    local_image_count: int | float | str | None
    downloaded_image_count: int | float | str | None


def local_image_count(row: ImageDepthRow) -> int:
    """Prefer an explicit local count, including zero, over downloaded count."""
    value = row.get("local_image_count")
    if value is None:
        value = row.get("downloaded_image_count")
    return int(value or 0)


def authority_label(tier: str) -> str:
    """Display source authority without changing historical machine identities."""
    if tier in {"archive_primary", "fallback_text_validated"}:
        return tier.replace("_", " ")
    return "corroborating/unclassified"
