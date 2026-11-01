# Copyright (c) 2026 Daniel Ari Friedman
"""Verify installed Git metadata, RECORD bytes and actual imported origins.

This deliberately refuses editable/archive installs: it qualifies a caller-held
Git selection. Wheel qualification is a distinct source-bound workflow. RECORD
is mutable local metadata, so agreement is not proof against a malicious owner.
"""

import base64
import hashlib
import importlib
import sys
from importlib import metadata
from pathlib import Path, PurePosixPath
from types import ModuleType

from packaging.utils import canonicalize_name
from pydantic import ValidationError

from .common import EvidenceError
from .installed_models import (
    GitDirectURL,
    InstalledFile,
    InstalledGitPackage,
    InstalledSelection,
)
from .installed_records import metadata_bytes, metadata_directory, record_entries


def _hash(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _inventory(
    entries: tuple[metadata.PackagePath, ...], package: str, root: Path
) -> tuple[InstalledFile, ...]:
    verified: dict[str, InstalledFile] = {}
    for entry in entries:
        if entry.parts[0] != package:
            continue
        relative = PurePosixPath(*entry.parts[1:])
        if (
            entry.is_absolute()
            or ".." in entry.parts
            or relative.as_posix() == "."
            or relative.as_posix() in verified
        ):
            raise EvidenceError(
                "installed_record", "Invalid or duplicate package member"
            )
        path = root.joinpath(*relative.parts)
        if (
            path.is_symlink()
            or not path.is_file()
            or path.resolve() != root.joinpath(*relative.parts)
        ):
            raise EvidenceError("installed_file", str(relative))
        data = path.read_bytes()
        expected = entry.hash
        actual = base64.urlsafe_b64encode(hashlib.sha256(data).digest()).rstrip(b"=")
        if (
            expected is None
            or expected.mode != "sha256"
            or expected.value != actual.decode("ascii")
            or entry.size != len(data)
        ):
            raise EvidenceError("installed_file", str(relative))
        verified[relative.as_posix()] = InstalledFile(
            path=relative.as_posix(), size=len(data), sha256=_hash(data)
        )
    actual_paths: set[str] = set()
    for path in root.rglob("*"):
        if path.is_symlink():
            raise EvidenceError("installed_file", "Symbolic package member")
        if path.is_file() and "__pycache__" not in path.parts:
            actual_paths.add(path.relative_to(root).as_posix())
    if "__init__.py" not in verified or actual_paths != set(verified):
        raise EvidenceError(
            "installed_inventory", "Recorded and actual package files differ"
        )
    return tuple(verified[name] for name in sorted(verified))


def _module_origin(module: ModuleType, root: Path, files: set[str]) -> None:
    filename = getattr(module, "__file__", None)
    if filename is None:
        raise EvidenceError("installed_import", "Imported module has no file origin")
    path = Path(filename)
    try:
        relative = path.resolve().relative_to(root).as_posix()
    except ValueError as error:
        raise EvidenceError(
            "installed_import", "Imported module is outside package"
        ) from error
    if path.is_symlink() or path.absolute() != path.resolve() or relative not in files:
        raise EvidenceError(
            "installed_import", "Imported module is not a recorded file"
        )
    locations = getattr(module, "__path__", None)
    if locations is not None and tuple(Path(p).resolve() for p in locations) != (
        path.parent,
    ):
        raise EvidenceError("installed_import", "Imported package search path differs")


def _imports(
    package: str, root: Path, files: tuple[InstalledFile, ...]
) -> tuple[str, ...]:
    importlib.import_module(package)
    members = {item.path for item in files}
    names = []
    for name, module in tuple(sys.modules.items()):
        if name == package or name.startswith(package + "."):
            if module is None:
                raise EvidenceError("installed_import", "Unresolved package import")
            _module_origin(module, root, members)
            names.append(name)
    return tuple(sorted(names))


def verify_installed_git(
    package: str, expected_commit: str, distribution_name: str = ""
) -> InstalledGitPackage:
    """Refuse mismatched metadata, shadow imports or drifted package bytes.

    Call immediately before admitting a new producer stage. The result describes
    this observation, not future imports or a rendered/released artifact.
    No files are written and no acquisition or optional analysis engine is run.
    """
    try:
        selection = InstalledSelection(
            package=package, commit=expected_commit, distribution_name=distribution_name
        )
    except ValidationError as error:
        raise EvidenceError(
            "installed_selection", "Use string names and a full Git commit"
        ) from error
    name = selection.distribution_name or selection.package
    try:
        distribution = metadata.distribution(name)
    except metadata.PackageNotFoundError as error:
        raise EvidenceError("installed_distribution", name) from error
    try:
        # Refuse unsupported providers before calling their metadata accessors.
        _ = metadata_directory(distribution)
        declared_name = distribution.metadata.get("Name")
        version = distribution.metadata.get("Version")
        if (
            not declared_name
            or not version
            or canonicalize_name(declared_name) != canonicalize_name(name)
        ):
            raise EvidenceError(
                "installed_distribution", "Distribution identity differs"
            )
        entries = record_entries(distribution)
        observed = {
            key: metadata_bytes(distribution, entries, key)
            for key in ("direct_url.json", "METADATA", "RECORD")
        }
        raw_origin = observed["direct_url.json"]
        try:
            origin = GitDirectURL.model_validate_json(raw_origin)
        except ValidationError as error:
            raise EvidenceError(
                "installed_git_origin", "A normal Git install is required"
            ) from error
        if origin.vcs_info.commit_id != expected_commit:
            raise EvidenceError(
                "installed_git_pin", "Installed commit differs from caller pin"
            )
        root = Path(distribution.locate_file(package))
        if root.is_symlink() or not root.is_dir() or root.absolute() != root.resolve():
            raise EvidenceError(
                "installed_package", "Package root is not a regular directory"
            )
        root = root.absolute()
        files = _inventory(entries, package, root)
        imports = _imports(package, root, files)
        # Real package initialization can change files/metadata. Qualify the state
        # at return as well as before import, without claiming protection from races.
        final_entries = record_entries(distribution)
        if _inventory(final_entries, package, root) != files or any(
            metadata_bytes(distribution, final_entries, key) != raw
            for key, raw in observed.items()
        ):
            raise EvidenceError(
                "installed_changed", "Installation changed during import"
            )
        return InstalledGitPackage(
            distribution=declared_name,
            package=package,
            version=version,
            commit=origin.vcs_info.commit_id,
            package_root=root,
            direct_url_sha256=_hash(raw_origin),
            metadata_sha256=_hash(observed["METADATA"]),
            record_sha256=_hash(observed["RECORD"]),
            files=files,
            imported_modules=imports,
        )
    except (OSError, UnicodeError) as error:
        raise EvidenceError(
            "installed_io", "Installed package cannot be read"
        ) from error


__all__ = ["InstalledGitPackage", "verify_installed_git"]
