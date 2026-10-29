# Copyright (c) 2026 Daniel Ari Friedman
"""Validate and lay out declared evidence trees without application policy.

Depth counts parent edges; rows have no temporal or metric interpretation.
Validation and layout take linear time and space without Python recursion.
"""

from typing import Annotated, ClassVar, Optional

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StrictStr,
    field_validator,
    model_validator,
)
from typing_extensions import Self

from .common import EvidenceError


class _TreeModel(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(
        frozen=True, extra="forbid", strict=True, revalidate_instances="always"
    )


class EvidenceTreeNode(_TreeModel):
    """An application-declared node; labels and identifiers are never normalized."""

    node_id: StrictStr
    label: StrictStr
    parent_id: Optional[StrictStr] = None

    @field_validator("node_id", "label", "parent_id")
    @classmethod
    def require_content(cls, value: Optional[str]) -> Optional[str]:
        if value is not None and not value.strip():
            raise EvidenceError("tree_blank_text", "IDs and labels need content")
        return value


class EvidenceTree(_TreeModel):
    """One connected rooted tree, retaining the caller's declared node order."""

    nodes: tuple[EvidenceTreeNode, ...]

    @model_validator(mode="after")
    def validate_tree(self) -> Self:
        if not self.nodes:
            raise EvidenceError("tree_empty", "Declare at least one node")
        by_id = {node.node_id: node for node in self.nodes}
        if len(by_id) != len(self.nodes):
            raise EvidenceError("tree_duplicate_id", "Node IDs must be unique")
        roots = [node.node_id for node in self.nodes if node.parent_id is None]
        if len(roots) != 1:
            raise EvidenceError("tree_root_count", str(len(roots)))
        children: dict[str, list[str]] = {identity: [] for identity in by_id}
        for node in self.nodes:
            if node.parent_id == node.node_id:
                raise EvidenceError("tree_self_edge", node.node_id)
            if node.parent_id is not None:
                if node.parent_id not in by_id:
                    raise EvidenceError("tree_missing_parent", node.parent_id)
                children[node.parent_id].append(node.node_id)
        pending = [roots[0]]
        reached: set[str] = set()
        while pending:
            identity = pending.pop()
            if identity in reached:
                raise EvidenceError("tree_cycle", identity)
            reached.add(identity)
            pending.extend(children[identity])
        if len(reached) != len(by_id):
            raise EvidenceError("tree_disconnected_cycle", "All nodes must reach root")
        return self


class TreePlacement(_TreeModel):
    """A topological edge depth and a nonnegative descendant-leaf mean row."""

    node_id: StrictStr
    depth: Annotated[int, Field(ge=0)]
    row: Annotated[float, Field(ge=0, allow_inf_nan=False)]

    @field_validator("node_id")
    @classmethod
    def require_identity(cls, value: str) -> str:
        if not value.strip():
            raise EvidenceError("tree_blank_text", "Node ID needs content")
        return value


def layout_evidence_tree(tree: EvidenceTree) -> tuple[TreePlacement, ...]:
    """Place leaves by sibling traversal; weight parents by every descendant leaf.

    Returned placements follow input node order, even for child-before-parent
    declarations. Revalidate model instances at this public boundary as well.
    """
    admitted = EvidenceTree.model_validate(tree)
    children: dict[str, list[str]] = {node.node_id: [] for node in admitted.nodes}
    root = ""
    for node in admitted.nodes:
        if node.parent_id is None:
            root = node.node_id
        else:
            children[node.parent_id].append(node.node_id)
    pending = [(root, 0)]
    traversal: list[str] = []
    depths: dict[str, int] = {}
    leaf_sums: dict[str, float] = {}
    leaf_counts: dict[str, int] = {}
    next_row = 0
    while pending:
        identity, depth = pending.pop()
        traversal.append(identity)
        depths[identity] = depth
        if children[identity]:
            pending.extend((child, depth + 1) for child in reversed(children[identity]))
        else:
            leaf_sums[identity] = float(next_row)
            leaf_counts[identity] = 1
            next_row += 1
    for identity in reversed(traversal):
        if children[identity]:
            leaf_sums[identity] = sum(leaf_sums[child] for child in children[identity])
            leaf_counts[identity] = sum(
                leaf_counts[child] for child in children[identity]
            )
    return tuple(
        TreePlacement(
            node_id=node.node_id,
            depth=depths[node.node_id],
            row=leaf_sums[node.node_id] / leaf_counts[node.node_id],
        )
        for node in admitted.nodes
    )
