"""Source-labelled record/theme/entity links from persisted analysis payloads."""

from __future__ import annotations

from typing import Any, Iterable

from ..models import BlakeWork


def build_theme_entity_network(works: Iterable[BlakeWork]) -> dict[str, Any]:
    """Deduplicate record links while retaining metadata and model provenance."""
    nodes: dict[str, dict[str, Any]] = {}
    edges: dict[tuple[str, str, str], dict[str, Any]] = {}

    def link(
        work_id: str, label: Any, kind: str, relationship: str, source: str
    ) -> None:
        if not isinstance(label, str) or not label.strip():
            return
        label = " ".join(label.split())
        identity = kind + ":" + label
        nodes.setdefault(identity, {"id": identity, "label": label, "type": kind})
        key = (work_id, identity, relationship)
        edge = edges.setdefault(
            key,
            {
                "source": work_id,
                "target": identity,
                "relationship": relationship,
                "sources": [],
            },
        )
        if source not in edge["sources"]:
            edge["sources"].append(source)

    for work in works:
        work_id = "work:" + work.id
        nodes[work_id] = {"id": work_id, "label": work.metadata.title, "type": "work"}
        for theme in work.metadata.themes:
            link(work_id, theme, "theme", "has_theme", "metadata")
        analysis = work.text_analysis
        themes = analysis.get("themes", {})
        if isinstance(themes, dict):
            for row in themes.get("themes", []):
                label = row[0] if isinstance(row, (list, tuple)) and row else row
                link(work_id, label, "theme", "has_theme", "text_analysis")
        entities = analysis.get("entities", [])
        groups = entities.values() if isinstance(entities, dict) else [entities]
        for group in groups:
            if not isinstance(group, (list, tuple)):
                continue
            for entity in group:
                label = entity.get("text") if isinstance(entity, dict) else entity
                link(work_id, label, "entity", "mentions", "text_analysis")
    return {
        "schema_version": 2,
        "nodes": list(nodes.values()),
        "edges": list(edges.values()),
    }
