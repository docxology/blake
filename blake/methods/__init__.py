# Copyright (c) 2026 Daniel Ari Friedman
"""Reusable research methods with explicit, independently versioned contracts."""

from .hierarchy import (
    EvidenceTree,
    EvidenceTreeNode,
    TreePlacement,
    layout_evidence_tree,
)
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
    "EvidenceTree",
    "EvidenceTreeNode",
    "ProjectionCorpusPin",
    "ProjectionPassage",
    "ResearchError",
    "RetrievalProfile",
    "TreePlacement",
    "describe_profile",
    "layout_evidence_tree",
]
