"""Real hierarchy boundaries, ordering and descendant weighting controls."""

import json
import subprocess
import sys
from pathlib import Path
from typing import Optional, Union

import pytest
from pydantic import ValidationError

from blake.methods.hierarchy import (
    EvidenceTree,
    EvidenceTreeNode,
    TreePlacement,
    layout_evidence_tree,
)


def node(identity: str, parent: Optional[str] = None) -> EvidenceTreeNode:
    return EvidenceTreeNode(node_id=identity, label=identity, parent_id=parent)


def test_single_node_and_json_roundtrip() -> None:
    tree = EvidenceTree(nodes=(node("r"),))
    assert layout_evidence_tree(tree) == (TreePlacement(node_id="r", depth=0, row=0.0),)
    assert EvidenceTree.model_validate_json(tree.model_dump_json()) == tree


def test_declared_siblings_and_output_order_with_unequal_subtrees() -> None:
    # Leaf order is b1,b2,a. A mean of child means would give root 1.25.
    tree = EvidenceTree(
        nodes=(
            node("b1", "b"),
            node("r"),
            node("b", "r"),
            node("a", "r"),
            node("b2", "b"),
        )
    )
    rows = layout_evidence_tree(tree)
    assert [(p.node_id, p.depth, p.row) for p in rows] == [
        ("b1", 2, 0.0),
        ("r", 0, 1.0),
        ("b", 1, 0.5),
        ("a", 1, 2.0),
        ("b2", 2, 1.0),
    ]
    assert layout_evidence_tree(tree) == rows


def test_deep_tree_does_not_use_recursion() -> None:
    nodes = (node("0"),) + tuple(node(str(i), str(i - 1)) for i in range(1, 6000))
    rows = layout_evidence_tree(EvidenceTree(nodes=nodes))
    assert rows[-1] == TreePlacement(node_id="5999", depth=5999, row=0.0)
    assert all(p.row == 0.0 for p in rows)


@pytest.mark.parametrize(
    "nodes",
    [
        (),
        (node("r"), node("r")),
        (node("a"), node("b")),
        (node("a", "b"), node("b", "a")),
        (node("r"), node("a", "missing")),
        (node("r"), node("a", "a")),
        (node("r"), node("a", "b"), node("b", "a")),
    ],
)
def test_invalid_graphs_reject(nodes: tuple[EvidenceTreeNode, ...]) -> None:
    with pytest.raises(ValidationError):
        EvidenceTree(nodes=nodes)


@pytest.mark.parametrize(
    "field,value",
    [
        ("node_id", ""),
        ("node_id", " \t"),
        ("node_id", 7),
        ("label", "\n"),
        ("label", b"a"),
        ("label", True),
        ("parent_id", " "),
        ("parent_id", 2),
        ("unexpected", "value"),
    ],
)
def test_node_boundary_rejects_coercion_and_blanks(
    field: str, value: Union[str, bytes, int]
) -> None:
    with pytest.raises(ValidationError):
        EvidenceTreeNode.model_validate({"node_id": "a", "label": "A", field: value})


def test_labels_are_preserved_and_nodes_are_frozen() -> None:
    admitted = EvidenceTreeNode(node_id=" a ", label="  Scientific label  ")
    assert admitted.node_id == " a "
    assert admitted.label == "  Scientific label  "
    for value in (
        admitted,
        EvidenceTree(nodes=(admitted,)),
        TreePlacement(node_id=" a ", depth=0, row=0.0),
    ):
        with pytest.raises(ValidationError):
            value.__setattr__(next(iter(type(value).model_fields)), "changed")


@pytest.mark.parametrize(
    "fields",
    [
        {"depth": True},
        {"depth": "1"},
        {"depth": -1},
        {"depth": 1.5},
        {"row": "1"},
        {"row": True},
        {"row": -1.0},
        {"row": float("inf")},
        {"row": float("nan")},
        {"node_id": " "},
        {"node_id": 1},
    ],
)
def test_placement_boundary_rejects_invalid_values(
    fields: dict[str, Union[str, int, float]],
) -> None:
    with pytest.raises(ValidationError):
        TreePlacement.model_validate({"node_id": "r", "depth": 0, "row": 0.0, **fields})


def test_layout_revalidates_bypassed_models() -> None:
    invalid = EvidenceTree.model_construct(nodes=(node("a"), node("b")))
    with pytest.raises(ValidationError):
        layout_evidence_tree(invalid)
    invalid_node = EvidenceTreeNode.model_construct(
        node_id=4, label="A", parent_id=None
    )
    with pytest.raises(ValidationError):
        EvidenceTree(nodes=(invalid_node,))


def test_imports_are_dependency_light_in_fresh_process() -> None:
    root = str(Path(__file__).resolve().parents[1])
    result = subprocess.run(
        [
            sys.executable,
            "-I",
            "-c",
            "import sys,json; sys.path.insert(0,sys.argv[1]); "
            "from blake.methods.hierarchy import EvidenceTreeNode; "
            "print(json.dumps(sorted(sys.modules)))",
            root,
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    loaded = json.loads(result.stdout)
    assert not any(
        n.startswith(
            (
                "numpy",
                "matplotlib",
                "spacy",
                "torch",
                "blake.recovery",
                "blakean_federalism",
                "blakean_entomology",
            )
        )
        for n in loaded
    )
