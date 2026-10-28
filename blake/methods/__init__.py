# Copyright (c) 2026 Daniel Ari Friedman
"""Reusable research methods with explicit, independently versioned contracts."""

from .models import (
    Artifact,
    BundleCorpusPin,
    BundlePassage,
    EvidenceError,
    ProjectionCorpusPin,
    ProjectionPassage,
    ResearchError,
)
from .profiles import RetrievalProfile, describe_profile

__all__ = [
    "Artifact",
    "BundleCorpusPin",
    "BundlePassage",
    "EvidenceError",
    "ProjectionCorpusPin",
    "ProjectionPassage",
    "ResearchError",
    "RetrievalProfile",
    "describe_profile",
]
