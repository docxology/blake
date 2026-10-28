# Copyright (c) 2026 Daniel Ari Friedman
"""Explicit source closure bindings for new application producer epochs."""

import json
from collections.abc import Sequence
from importlib.resources import files
from typing import NamedTuple

from .runs import digest


class SourceBinding(NamedTuple):
    package: str
    paths: tuple[str, ...]


def source_hashes(bindings: Sequence[SourceBinding]) -> dict[str, str]:
    """Return namespaced byte receipts for an explicitly declared dependency closure."""
    sources: dict[str, str] = {}
    for binding in bindings:
        package = files(binding.package)
        for name in binding.paths:
            key = binding.package + "/" + name
            if key in sources:
                raise ValueError("duplicate producer source: " + key)
            sources[key] = digest(package.joinpath(name).read_bytes())
    return sources


def source_binding_sha256(bindings: Sequence[SourceBinding]) -> str:
    """Hash namespaced source bytes, including the caller's delegated methods."""
    return digest(
        json.dumps(source_hashes(bindings), sort_keys=True, separators=(",", ":")).encode()
    )
