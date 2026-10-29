"""Retain the live Archive catalogues and complete pinned Erdman source edition."""

from __future__ import annotations

import io
import re
import tarfile
from pathlib import Path
from typing import Final

from pydantic import BaseModel, ConfigDict

from .recovery_models import CatalogRecovery, CopyRecord, FileReceipt, RecoveryError
from .recovery_io import _retain, _safe_path, fetch_file

ERDMAN_COMMIT: Final = "c12d8657788523550794c8765f1199adf76efa1b"


class WorkRow(BaseModel):
    model_config = ConfigDict(frozen=True, extra="ignore")
    bad_id: str


class ObjectRow(BaseModel):
    model_config = ConfigDict(frozen=True, extra="ignore")
    desc_id: str
    dbi: str | None = None


class WorkInventory(BaseModel):
    results: tuple[WorkRow, ...]


class ObjectInventory(BaseModel):
    results: tuple[ObjectRow, ...]


def recover_catalog(
    root: Path, copies: list[CopyRecord], *, offline: bool
) -> tuple[CatalogRecovery, list[FileReceipt]]:
    files: list[FileReceipt] = []
    raw_sources: list[bytes] = []
    paths = []
    for kind in ("work", "copy", "object"):
        url = f"https://blakearchive.org/api/{kind}/"
        relative = f"sources/live/{kind}-inventory.json"
        content = fetch_file(url, _safe_path(root, relative), offline=offline)
        files.append(_retain(root, relative, content, url))
        raw_sources.append(content)
        paths.append(relative)
    works = WorkInventory.model_validate_json(raw_sources[0]).results
    copy_rows = WorkInventory.model_validate_json(raw_sources[1]).results
    objects = ObjectInventory.model_validate_json(raw_sources[2]).results
    if not works or not copy_rows or not objects:
        raise RecoveryError("Archive returned an empty live catalogue")
    if len({row.bad_id for row in works}) != len(works) or len(
        {row.bad_id for row in copy_rows}
    ) != len(copy_rows):
        raise RecoveryError("Duplicate live work/copy identities")
    image_bindings: dict[str, str | None] = {}
    for row in objects:
        if row.desc_id in image_bindings and image_bindings[row.desc_id] != row.dbi:
            raise RecoveryError("Conflicting live object image bindings")
        image_bindings[row.desc_id] = row.dbi
    existing = {
        object_id.casefold() for copy in copies for object_id in copy.object_ids
    }
    valid = {
        row.dbi
        for row in objects
        if row.dbi and re.fullmatch(r"[A-Za-z0-9_.+-]+", row.dbi)
    }
    non_images = {row.dbi for row in objects if row.dbi and row.dbi not in valid}
    extra = sorted({value.casefold() for value in valid} - existing)
    url = f"https://codeload.github.com/blakearchive/erdman/tar.gz/{ERDMAN_COMMIT}"
    relative = f"sources/erdman-{ERDMAN_COMMIT}.tar.gz"
    content = fetch_file(url, _safe_path(root, relative), offline=offline)
    files.append(_retain(root, relative, content, url))
    prefix = f"erdman-{ERDMAN_COMMIT}/"
    with tarfile.open(fileobj=io.BytesIO(content), mode="r:gz") as archive:
        members = archive.getmembers()
        names = set()
        for member in members:
            if member.name == prefix.rstrip("/") and member.isdir():
                continue
            if not member.name.startswith(prefix) or not (
                member.isdir() or member.isfile()
            ):
                raise RecoveryError(f"Unsafe Erdman snapshot member: {member.name}")
            _safe_path(
                root, f"snapshot/erdman/{ERDMAN_COMMIT}/{member.name[len(prefix) :]}"
            )
            if member.name in names or member.size > 128 * 1024 * 1024:
                raise RecoveryError(
                    f"Duplicate or oversized Erdman snapshot member: {member.name}"
                )
            names.add(member.name)
        for member in members:
            if not member.isfile():
                continue
            handle = archive.extractfile(member)
            if handle is None:
                raise RecoveryError(f"Unreadable Erdman snapshot member: {member.name}")
            with handle:
                data = handle.read()
            filename = member.name[len(prefix) :]
            files.append(
                _retain(
                    root,
                    f"snapshot/erdman/{ERDMAN_COMMIT}/{filename}",
                    data,
                    f"https://raw.githubusercontent.com/blakearchive/erdman/{ERDMAN_COMMIT}/{filename}",
                )
            )
    if not any(receipt.path.endswith("/data/erd3.xml") for receipt in files):
        raise RecoveryError("Erdman snapshot has no main text XML")
    return CatalogRecovery(
        source_paths=tuple(paths),
        work_records=len(works),
        copy_records=len(copy_rows),
        object_records=len(objects),
        extra_image_ids=tuple(extra),
        non_image_references=tuple(sorted(non_images)),
        erdman_commit=ERDMAN_COMMIT,
    ), files
