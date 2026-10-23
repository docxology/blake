"""Explicit nested component errors, separate from top-level result failures."""

from __future__ import annotations

from typing import Any


def component_errors(records: list[dict[str, Any]]) -> list[dict[str, str]]:
    """Count explicit component errors once in the identified result ledger."""
    errors: list[dict[str, str]] = []

    def visit(value: Any, path: tuple[str, ...], identity: str) -> None:
        if isinstance(value, dict):
            if value.get("error") and len(path) >= 2:
                errors.append(
                    {
                        "work_id": identity,
                        "path": ".".join(path),
                        "error": str(value["error"]),
                    }
                )
            for key, child in value.items():
                if key != "error":
                    visit(child, path + (str(key),), identity)
        elif isinstance(value, list):
            for index, child in enumerate(value):
                visit(child, path + (str(index),), identity)

    identities = [record["work_id"] for record in records]
    if len(set(identities)) != len(identities):
        raise ValueError("Duplicate publication result identity")
    for record in records:
        visit(record["results"], (), record["work_id"])
    return errors
