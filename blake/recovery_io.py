"""Immutable source-file custody, safe archive extraction and atomic derived writes."""

from __future__ import annotations

import hashlib
import io
import os
import ssl
import sys
import tarfile
import tempfile
import time
import zipfile
from collections.abc import Callable
from http.client import IncompleteRead
from pathlib import Path, PurePosixPath
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


from .recovery_models import MAX_MEMBER_BYTES, RecoveryError, FileReceipt


def _digest(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _safe_path(root: Path, relative: str) -> Path:
    """Reject traversal and symlink escapes before touching source files."""
    parts = PurePosixPath(relative)
    if (
        parts.is_absolute()
        or not parts.parts
        or ".." in parts.parts
        or "\\" in relative
        or str(parts) != relative
    ):
        raise RecoveryError(f"Unsafe recovery path: {relative}")
    path = root / relative
    if not path.resolve().is_relative_to(root.resolve()):
        raise RecoveryError(f"Recovery path escapes storage: {relative}")
    if any(
        parent.is_symlink() for parent in (path, *path.parents) if parent != root.parent
    ):
        raise RecoveryError(f"Symlink in recovery path: {relative}")
    return path


def _atomic_write(path: Path, content: bytes) -> None:
    """Commit complete bytes only; interrupted writes never replace valid files."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as handle:
        temporary = Path(handle.name)
        try:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        except OSError:
            temporary.unlink(missing_ok=True)
            raise
    try:
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def fetch_file(
    url: str,
    path: Path,
    *,
    offline: bool = False,
    validate: Callable[[bytes], None] | None = None,
) -> bytes:
    """Reuse saved bytes or fetch with bounded retries and atomic persistence."""
    if path.is_file():
        content = path.read_bytes()
        if validate is not None:
            validate(content)
        return content
    if offline:
        raise RecoveryError(f"Offline recovery requires cached source: {path}")
    request = Request(
        url, headers={"User-Agent": "BlakeCorpusRecovery/1.0 (local research)"}
    )
    for attempt in range(3):
        try:
            if sys.version_info >= (3, 10):
                import truststore

                context = truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
            else:
                context = ssl.create_default_context()
            with urlopen(request, timeout=45, context=context) as response:
                content = response.read()
                length = response.headers.get("Content-Length")
                if length is not None and len(content) != int(length):
                    raise RecoveryError(f"Truncated response from {url}")
            if not content:
                raise RecoveryError(f"Empty response from {url}")
            if validate is not None:
                validate(content)
            _atomic_write(path, content)
            return content
        except HTTPError as exc:
            if attempt == 2 or 400 <= exc.code < 500 and exc.code not in {408, 429}:
                raise RecoveryError(f"Could not recover {url}: {exc}") from exc
            time.sleep(attempt + 1)
        except (URLError, TimeoutError, ConnectionError, IncompleteRead) as exc:
            if attempt == 2:
                raise RecoveryError(f"Could not recover {url}: {exc}") from exc
            time.sleep(attempt + 1)
    raise AssertionError("unreachable retry state")


def _retain(
    root: Path, relative: str, content: bytes, url: str | None = None
) -> FileReceipt:
    path = _safe_path(root, relative)
    if path.exists():
        if path.read_bytes() != content:
            raise RecoveryError(
                f"Existing recovery file differs; preserve and review: {path}"
            )
    else:
        _atomic_write(path, content)
    return FileReceipt(
        path=relative, size=len(content), sha256=_digest(content), source_url=url
    )


def _derive(
    root: Path, relative: str, content: bytes, url: str | None = None
) -> FileReceipt:
    path = _safe_path(root, relative)
    if path.exists() and path.read_bytes() != content:
        previous = path.read_bytes()
        history = f"history/{relative}.{_digest(previous)}.bak"
        _retain(root, history, previous, url)
        _atomic_write(path, content)
    return _retain(root, relative, content, url)


def retain_recipe(root: Path) -> FileReceipt:
    package = Path(__file__).parent
    project = package.parent
    metadata = package / "_resources"
    if not metadata.is_dir():
        metadata = project
    paths = {
        str(path.relative_to(project)): path
        for path in set(package.rglob("*.py")) | set(package.rglob("*.json"))
    }
    paths.update(
        {name: metadata / name for name in ("pyproject.toml", "uv.lock", "LICENSE")}
    )
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:") as archive:
        for name, path in sorted(paths.items()):
            content = path.read_bytes()
            info = tarfile.TarInfo(name)
            info.mode = 0o644
            info.size = len(content)
            archive.addfile(info, io.BytesIO(content))
    content = buffer.getvalue()
    return _retain(root, f"recipe/{_digest(content)}.tar", content)


def unpack_snapshot(root: Path, content: bytes, commit: str) -> list[FileReceipt]:
    """Retain every regular member; never use unrestricted tar extraction."""
    prefix = f"data-{commit}/"
    files: list[FileReceipt] = []
    seen: set[str] = set()
    with tarfile.open(fileobj=io.BytesIO(content), mode="r:gz") as archive:
        members = archive.getmembers()
        for member in members:
            if member.name == prefix.rstrip("/") and member.isdir():
                continue
            if not member.name.startswith(prefix):
                raise RecoveryError(
                    f"Snapshot is not the requested commit: {member.name}"
                )
            relative = member.name[len(prefix) :]
            _safe_path(root, f"snapshot/{commit}/{relative}")
            if not member.isdir() and not member.isfile():
                raise RecoveryError(f"Non-regular snapshot member: {member.name}")
            if member.size > MAX_MEMBER_BYTES:
                raise RecoveryError(f"Oversized snapshot member: {member.name}")
            if member.isfile() and relative in seen:
                raise RecoveryError(f"Duplicate snapshot member: {member.name}")
            seen.add(relative)
        for member in members:
            if not member.isfile():
                continue
            handle = archive.extractfile(member)
            if handle is None:
                raise RecoveryError(f"Unreadable snapshot member: {member.name}")
            with handle:
                data = handle.read()
            relative = member.name[len(prefix) :]
            files.append(
                _retain(
                    root,
                    f"snapshot/{commit}/{relative}",
                    data,
                    f"https://raw.githubusercontent.com/blakearchive/data/{commit}/{relative}",
                )
            )
    if not any(f.path.endswith("/works/__contents__.xml") for f in files):
        raise RecoveryError("Archive snapshot has no work inventory")
    return files


def _work_sources(root: Path, files: list[FileReceipt]) -> list[FileReceipt]:
    """Expand XML copies delivered inside ZIPs as well as ordinary XML files."""
    result = [
        f
        for f in files
        if "/works/" in f.path
        and f.path.endswith(".xml")
        and not f.path.endswith("/__contents__.xml")
    ]
    for source in tuple(files):
        if "/works/" not in source.path or not source.path.endswith(".zip"):
            continue
        with zipfile.ZipFile(root / source.path) as archive:
            for info in archive.infolist():
                if info.is_dir():
                    continue
                if info.file_size > MAX_MEMBER_BYTES:
                    raise RecoveryError(f"Oversized ZIP member: {info.filename}")
                relative = f"expanded/{Path(source.path).name}/{info.filename}"
                _safe_path(root, relative)
                receipt = _retain(root, relative, archive.read(info), source.source_url)
                files.append(receipt)
                member_path = PurePosixPath(info.filename)
                if (
                    info.filename.endswith(".xml")
                    and not info.filename.endswith("__contents__.xml")
                    and "__MACOSX" not in member_path.parts
                    and not member_path.name.startswith("._")
                ):
                    result.append(receipt)
    return result
