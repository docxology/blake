# Copyright (c) 2026 Daniel Ari Friedman
"""Regular-file custody and complete-file publication for derived data."""

import errno
import hashlib
import os
import secrets
import stat
from collections.abc import Generator
from contextlib import ExitStack, contextmanager
from pathlib import Path, PurePosixPath

from .models import FileReceipt, ResearchError


def digest(path: Path) -> str:
    with path.open("rb") as stream:
        checksum = hashlib.sha256()
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            checksum.update(chunk)
        return checksum.hexdigest()


def safe_path(root: Path, relative: str) -> Path:
    """Reject symlinks, traversal and nonregular inputs before reading bytes."""
    rel = PurePosixPath(relative)
    if rel.is_absolute() or ".." in rel.parts or not rel.parts or "\\" in relative:
        raise ResearchError("unsafe_path", relative)
    if any(part.is_symlink() for part in (root, *root.parents)):
        raise ResearchError("symlink_root", str(root))
    path = root.joinpath(*rel.parts)
    if any(part.is_symlink() for part in (path, *path.parents)):
        raise ResearchError("symlink_input", relative)
    if not path.is_file():
        raise ResearchError("missing_regular_file", relative)
    return path


def verify_file(root: Path, relative: str, size: int, expected: str) -> Path:
    path = safe_path(root, relative)
    if path.stat().st_size != size or digest(path) != expected:
        raise ResearchError("checksum_mismatch", relative)
    return path


@contextmanager
def _publication_directory(path: Path) -> Generator[int, None, None]:
    """Anchor every ancestor without following links, including newly made parents."""
    if (
        not hasattr(os, "O_NOFOLLOW")
        or not hasattr(os, "O_DIRECTORY")
        or any(
            function not in os.supports_dir_fd
            for function in (os.open, os.mkdir, os.stat, os.link, os.unlink)
        )
        or any(
            function not in os.supports_follow_symlinks
            for function in (os.stat, os.link)
        )
    ):
        raise ResearchError(
            "unsupported_publication", "Require nofollow directory-relative operations"
        )
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    with ExitStack() as stack:
        directory = os.open(path.anchor, flags)
        _ = stack.callback(os.close, directory)
        for component in path.parent.parts[1:]:
            try:
                try:
                    child = os.open(component, flags, dir_fd=directory)
                except FileNotFoundError:
                    os.mkdir(component, dir_fd=directory)
                    child = os.open(component, flags, dir_fd=directory)
            except OSError as exc:
                if exc.errno in (errno.ELOOP, errno.ENOTDIR):
                    raise ResearchError("symlink_output", str(path)) from exc
                raise
            _ = stack.callback(os.close, child)
            directory = child
        yield directory


def publish_bytes(path: Path, content: bytes) -> FileReceipt:
    """Publish complete bytes into an anchored directory inode, never a swapped path.

    Requires POSIX nofollow and descriptor-relative operations; unsupported systems
    fail explicitly. Renaming an opened ancestor does not redirect publication: the
    file remains in the captured directory, which may no longer have its old name.
    This protects pathname traversal, not hostile writes inside that directory.
    """
    absolute = path.absolute()
    with _publication_directory(absolute) as directory:
        try:
            existing = os.stat(absolute.name, dir_fd=directory, follow_symlinks=False)
        except FileNotFoundError:
            existing = None
        if existing is not None and stat.S_ISLNK(existing.st_mode):
            raise ResearchError("symlink_output", str(path))
        temporary = ".publish-" + secrets.token_hex(16)
        descriptor = os.open(
            temporary,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
            0o600,
            dir_fd=directory,
        )
        try:
            with os.fdopen(descriptor, "wb", closefd=False) as stream:
                _ = stream.write(content)
                stream.flush()
                os.fsync(stream.fileno())
            try:
                os.link(
                    temporary,
                    absolute.name,
                    src_dir_fd=directory,
                    dst_dir_fd=directory,
                    follow_symlinks=False,
                )
            except FileExistsError as exc:
                raise ResearchError("occupied_output", str(path)) from exc
        finally:
            try:
                os.close(descriptor)
            finally:
                os.unlink(temporary, dir_fd=directory)
    return FileReceipt(
        path=path.name, size=len(content), sha256=hashlib.sha256(content).hexdigest()
    )


def write_new(path: Path, content: str) -> None:
    """Publish UTF-8 text without replacing another run or following symlinks."""
    _ = publish_bytes(path, content.encode("utf-8"))


def copy_new(source: Path, destination: Path) -> None:
    """Copy independent bytes through complete, descriptor-anchored publication."""
    # Historically an occupied leaf link is an occupied copy destination.
    if destination.is_symlink():
        raise ResearchError("occupied_output", str(destination))
    _ = publish_bytes(destination, source.read_bytes())


def publish_projection(
    stage: Path,
    destination: Path,
    files: tuple[FileReceipt, ...],
    receipt_json: str,
) -> None:
    """Reserve a new directory atomically; publish the reader's completion marker last."""
    for entry in files:
        _ = verify_file(stage, entry.path, entry.size, entry.sha256)
    try:
        destination.mkdir()
    except FileExistsError as exc:
        raise ResearchError("occupied_output", str(destination)) from exc
    for entry in files:
        copy_new(stage / entry.path, destination / entry.path)
        _ = verify_file(destination, entry.path, entry.size, entry.sha256)
    # A failed partial destination is retained and has no valid completion marker.
    write_new(destination / "import-receipt.json", receipt_json)
