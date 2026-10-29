"""Checksum-bound corpus bundles and preservation-first offline restoration."""

from __future__ import annotations

import hashlib
import io
import os
import re
import tarfile
import tempfile
from pathlib import Path, PurePosixPath
from uuid import uuid4

from .recovery_models import RecoveryError, RecoveryManifest, RecoveryModel
from .recovery_io import _atomic_write, _digest, _safe_path
from .recovery_integrity import verify_recovery


class BackupReceipt(RecoveryModel):
    filename: str
    size: int
    sha256: str
    manifest_sha256: str
    files: int
    archive_commit: str


class RestoreReceipt(RecoveryModel):
    backup_sha256: str
    restored: tuple[str, ...]
    unchanged: tuple[str, ...]
    quarantine: tuple[str, ...]
    report_path: str


class RestoreDrill(RecoveryModel):
    backup_sha256: str
    files_verified: int
    image_recovery_status: str
    corrupted_path: str
    detection_error: str
    repaired_files: tuple[str, ...]
    quarantine: tuple[str, ...]


def _file_digest(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _receipt_path(bundle: Path) -> Path:
    return bundle.with_name(bundle.name + ".json")


def _check_member_name(name: str) -> None:
    path = PurePosixPath(name)
    if (
        not path.parts
        or path.is_absolute()
        or ".." in path.parts
        or "\\" in name
        or str(path) != name
    ):
        raise RecoveryError(f"Unsafe backup member: {name}")


def verify_backup(
    bundle: Path, *, expected_sha256: str | None = None
) -> RecoveryManifest:
    """Verify the outer checksum and exact member closure before any restoration."""
    receipt = None
    if _receipt_path(bundle).is_file():
        receipt = BackupReceipt.model_validate_json(_receipt_path(bundle).read_bytes())
        if receipt.filename != bundle.name or receipt.size != bundle.stat().st_size:
            raise RecoveryError("Backup receipt does not match the selected file")
    expected = expected_sha256 or (receipt.sha256 if receipt is not None else None)
    if expected is None or not re.fullmatch(r"[a-f0-9]{64}", expected):
        raise RecoveryError(
            "Provide the saved backup receipt or an independent SHA-256"
        )
    if _file_digest(bundle) != expected:
        raise RecoveryError("Backup SHA-256 mismatch")
    with tarfile.open(bundle, mode="r:") as archive:
        members = archive.getmembers()
        names: set[str] = set()
        for member in members:
            _check_member_name(member.name)
            if not member.isfile() or member.name in names:
                raise RecoveryError(
                    f"Non-regular or duplicate backup member: {member.name}"
                )
            names.add(member.name)
        if "manifest.json" not in names:
            raise RecoveryError("Backup has no recovery manifest")
        handle = archive.extractfile("manifest.json")
        if handle is None:
            raise RecoveryError("Unreadable backup manifest")
        with handle:
            manifest_bytes = handle.read()
        if receipt is not None and _digest(manifest_bytes) != receipt.manifest_sha256:
            raise RecoveryError("Backup manifest checksum mismatch")
        manifest = RecoveryManifest.model_validate_json(manifest_bytes)
        expected_files = {entry.path: entry for entry in manifest.files}
        if not expected_files or len(expected_files) != len(manifest.files):
            raise RecoveryError("Backup manifest has empty or duplicate membership")
        if names != set(expected_files) | {"manifest.json"}:
            raise RecoveryError("Backup members do not match the manifest inventory")
        for member in members:
            if member.name == "manifest.json":
                continue
            entry = expected_files[member.name]
            if member.size != entry.size:
                raise RecoveryError(f"Backup size mismatch: {member.name}")
            handle = archive.extractfile(member)
            if handle is None:
                raise RecoveryError(f"Unreadable backup member: {member.name}")
            digest = hashlib.sha256()
            with handle:
                for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                    digest.update(chunk)
            if digest.hexdigest() != entry.sha256:
                raise RecoveryError(f"Backup member checksum mismatch: {member.name}")
    return manifest


def backup_recovery(data_dir: Path, destination: Path | None = None) -> Path:
    """Bundle every inventoried byte, including source files and decoded images."""
    manifest = verify_recovery(data_dir)
    root = data_dir / "recovery"
    manifest_bytes = (root / "manifest.json").read_bytes()
    manifest_sha = _digest(manifest_bytes)
    destination = (
        destination or data_dir / "backups" / f"recovery-{manifest_sha[:16]}.tar"
    )
    if destination.exists():
        prior = verify_backup(destination)
        if prior != manifest:
            raise RecoveryError(
                "Existing backup belongs to a different recovery snapshot"
            )
        return destination
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        dir=destination.parent, suffix=".tar", delete=False
    ) as handle:
        temporary = Path(handle.name)
    try:
        with tarfile.open(temporary, mode="w:") as archive:
            info = tarfile.TarInfo("manifest.json")
            info.mode = 0o600
            info.size = len(manifest_bytes)
            archive.addfile(info, io.BytesIO(manifest_bytes))
            for receipt in manifest.files:
                path = _safe_path(root, receipt.path)
                info = tarfile.TarInfo(receipt.path)
                info.mode = 0o600
                info.size = receipt.size
                with path.open("rb") as stream:
                    archive.addfile(info, stream)
        receipt = BackupReceipt(
            filename=destination.name,
            size=temporary.stat().st_size,
            sha256=_file_digest(temporary),
            manifest_sha256=manifest_sha,
            files=len(manifest.files),
            archive_commit=manifest.archive_commit,
        )
        verify_backup(temporary, expected_sha256=receipt.sha256)
        os.replace(temporary, destination)
        _atomic_write(
            _receipt_path(destination), receipt.model_dump_json(indent=2).encode()
        )
    finally:
        temporary.unlink(missing_ok=True)
    return destination


def restore_backup(
    bundle: Path, data_dir: Path, *, expected_sha256: str | None = None
) -> RestoreReceipt:
    """Restore missing or damaged bytes, quarantining each conflicting local file."""
    manifest = verify_backup(bundle, expected_sha256=expected_sha256)
    root = data_dir / "recovery"
    run_id = uuid4().hex
    restored: list[str] = []
    unchanged: list[str] = []
    quarantined: list[str] = []
    targets = [entry.path for entry in manifest.files] + ["manifest.json"]
    for relative in targets:
        _safe_path(root, relative)
    with tarfile.open(bundle, mode="r:") as archive:
        for relative in targets:
            path = _safe_path(root, relative)
            handle = archive.extractfile(relative)
            if handle is None:
                raise RecoveryError(f"Unreadable backup member: {relative}")
            with handle:
                content = handle.read()
            if path.exists() and path.read_bytes() == content:
                unchanged.append(relative)
                continue
            if path.exists():
                quarantine = _safe_path(root, f"repairs/{run_id}/quarantine/{relative}")
                quarantine.parent.mkdir(parents=True, exist_ok=True)
                os.replace(path, quarantine)
                quarantined.append(str(quarantine.relative_to(root)))
            _atomic_write(path, content)
            restored.append(relative)
    verify_recovery(data_dir)
    report_path = f"repairs/{run_id}/restore.json"
    result = RestoreReceipt(
        backup_sha256=_file_digest(bundle),
        restored=tuple(restored),
        unchanged=tuple(unchanged),
        quarantine=tuple(quarantined),
        report_path=report_path,
    )
    _atomic_write(
        _safe_path(root, report_path), result.model_dump_json(indent=2).encode()
    )
    return result


def restore_drill(bundle: Path, destination: Path) -> RestoreDrill:
    """Prove restoration and corruption repair on a separate, initially empty copy."""
    if destination.exists() and (
        not destination.is_dir() or any(destination.iterdir())
    ):
        raise RecoveryError("Restore drill requires a separate empty destination")
    manifest = verify_backup(bundle)
    restore_backup(bundle, destination)
    selected = next(
        (entry.path for entry in manifest.files if entry.path.endswith(".txt")),
        manifest.files[0].path,
    )
    path = _safe_path(destination / "recovery", selected)
    _atomic_write(path, b"DELIBERATE RECOVERY NEGATIVE CONTROL\n")
    try:
        verify_recovery(destination)
    except RecoveryError as exc:
        detection = str(exc)
    else:
        raise RecoveryError(
            "Integrity verification accepted deliberately corrupted bytes"
        )
    repaired = restore_backup(bundle, destination)
    verified = verify_recovery(destination)
    if verified != manifest:
        raise RecoveryError("Restored manifest differs from the original backup")
    report = RestoreDrill(
        backup_sha256=repaired.backup_sha256,
        files_verified=len(verified.files),
        image_recovery_status=verified.images.status,
        corrupted_path=selected,
        detection_error=detection,
        repaired_files=repaired.restored,
        quarantine=repaired.quarantine,
    )
    _atomic_write(
        destination / "restore_drill.json", report.model_dump_json(indent=2).encode()
    )
    return report
