# Copyright (c) 2026 Daniel Ari Friedman
"""Real RECORD parsing and physical installed-metadata byte custody."""

import csv
from importlib import metadata
from pathlib import Path

from packaging.utils import canonicalize_name

from .common import EvidenceError


def record_entries(
    distribution: metadata.Distribution,
) -> tuple[metadata.PackagePath, ...]:
    try:
        entries = distribution.files
    except (ValueError, TypeError, IndexError, csv.Error) as error:
        raise EvidenceError(
            "installed_record", "Malformed installation RECORD"
        ) from error
    if not entries or any(not entry.parts for entry in entries):
        raise EvidenceError("installed_record", "Missing or invalid RECORD inventory")
    return tuple(entries)


def metadata_bytes(
    distribution: metadata.Distribution,
    entries: tuple[metadata.PackagePath, ...],
    name: str,
) -> bytes:
    directory = metadata_directory(distribution)
    selected = tuple(
        entry
        for entry in entries
        if len(entry.parts) == 2
        and entry.parts[0] == directory.name
        and entry.name == name
    )
    if len(selected) != 1:
        raise EvidenceError("installed_metadata", "Missing or duplicate " + name)
    path = directory / name
    if path.is_symlink() or not path.is_file() or path.absolute() != path.resolve():
        raise EvidenceError("installed_metadata", "Nonregular " + name)
    raw = path.read_bytes()
    observed = distribution.read_text(name)
    if (
        not raw.strip()
        or observed is None
        or raw.decode("utf-8").replace("\r\n", "\n").replace("\r", "\n") != observed
    ):
        raise EvidenceError(
            "installed_metadata", "Metadata location/content differs: " + name
        )
    return raw


def metadata_directory(distribution: metadata.Distribution) -> Path:
    """Bind the selected filesystem provider; never substitute a guessed directory.

    CPython exposes the selected PathDistribution directory through _path. Keep
    this implementation boundary explicit and refuse unsupported providers.
    """
    if type(distribution) is not metadata.PathDistribution:
        raise EvidenceError("installed_metadata", "Unsupported metadata provider")
    try:
        selected = distribution._path
    except AttributeError as error:
        raise EvidenceError(
            "installed_metadata", "Selected metadata path unavailable"
        ) from error
    if (
        not isinstance(selected, Path)
        or not selected.is_dir()
        or not selected.name.endswith(".dist-info")
    ):
        raise EvidenceError(
            "installed_metadata", "Require filesystem dist-info metadata"
        )
    name = distribution.metadata.get("Name")
    if not name:
        raise EvidenceError("installed_metadata", "Distribution name disappeared")
    root = selected.parent
    candidates = tuple(
        path
        for path in root.glob("*.dist-info")
        if path.is_dir()
        and canonicalize_name(path.name.removesuffix(".dist-info").rpartition("-")[0])
        == canonicalize_name(name)
    )
    if len(candidates) != 1 or candidates[0].absolute() != selected.absolute():
        raise EvidenceError(
            "installed_metadata", "Require one normal distribution directory"
        )
    return selected
