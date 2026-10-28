# Copyright (c) 2026 Daniel Ari Friedman
"""Application-neutral run custody with explicit completion markers."""

import hashlib
import stat
from collections.abc import Sequence, Set
from pathlib import Path

from .models import Artifact, EvidenceError, ResearchError
from .storage import publish_bytes


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def safe_directory(path: Path) -> None:
    if any(part.is_symlink() for part in (path, *path.parents)):
        raise EvidenceError("symlink_directory", str(path))


def reserve(path: Path) -> None:
    """Reserve exclusively and retain failed partial runs for inspection."""
    safe_directory(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.mkdir()


def read_regular(path: Path, kind: str = "artifact") -> bytes:
    """Refuse links and nonregular inputs before reading a run member."""
    safe_directory(path.parent)
    if path.is_symlink():
        raise EvidenceError("symlink_" + kind, str(path))
    if not stat.S_ISREG(path.stat().st_mode):
        raise EvidenceError("nonregular_" + kind, str(path))
    return path.read_bytes()


def write_new(path: Path, raw: bytes) -> Artifact:
    """Publish complete bytes exclusively under the shared producer epoch."""
    safe_directory(path.parent)
    try:
        receipt = publish_bytes(path, raw)
    except ResearchError as exc:
        if exc.code == "occupied_output":
            raise FileExistsError(str(path)) from exc
        raise EvidenceError(exc.code, exc.detail) from exc
    return Artifact(name=receipt.path, size=receipt.size, sha256=receipt.sha256)


def verify_artifacts(
    directory: Path, artifacts: Sequence[Artifact], expected_names: Set[str]
) -> dict[str, bytes]:
    """Return the exact bytes checked against the declared artifact receipts."""
    safe_directory(directory)
    names = [artifact.name for artifact in artifacts]
    if len(set(names)) != len(names) or set(names) != expected_names:
        raise EvidenceError("artifact_membership", str(directory))
    payloads: dict[str, bytes] = {}
    for artifact in artifacts:
        raw = read_regular(directory / artifact.name)
        if len(raw) != artifact.size or digest(raw) != artifact.sha256:
            raise EvidenceError("artifact_checksum", artifact.name)
        payloads[artifact.name] = raw
    return payloads


def require_run_pin(directory: Path, expected: str) -> bytes:
    """Return the exact completion bytes checked against the caller's trusted pin."""
    raw = read_regular(directory / "run.json", "receipt")
    if digest(raw) != expected:
        raise EvidenceError("review_run_pin", str(directory))
    return raw
