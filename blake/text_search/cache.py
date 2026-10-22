"""Read only explicit saved-run text membership, retaining every matching file variant."""

import hashlib
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, ConfigDict, HttpUrl, StrictBool

from .models import Passage, SearchError


class SavedWork(BaseModel):
    model_config = ConfigDict(extra="ignore", frozen=True)
    id: str
    target_id: Optional[str] = None
    title: str
    source: str
    source_url: Optional[HttpUrl] = None
    has_text: StrictBool


class SavedRun(BaseModel):
    model_config = ConfigDict(extra="ignore", frozen=True)
    fixture_mode: StrictBool
    fixture_work_ids: tuple[str, ...] = ()
    work_records: tuple[SavedWork, ...]


class CacheImport(BaseModel):
    model_config = ConfigDict(frozen=True)
    manifest_sha256: str
    selected_work_ids: tuple[str, ...]
    missing_text_ids: tuple[str, ...]
    skipped_text_ids: tuple[str, ...]
    passages: tuple[Passage, ...]


def import_cache(manifest: Path, data_dir: Path) -> CacheImport:
    """Retain work identities and unknown edition status; never infer plate/line numbers."""
    raw = manifest.read_bytes()
    run = SavedRun.model_validate_json(raw)
    if run.fixture_mode:
        message = "Fixture runs cannot be indexed as primary sources"
        raise SearchError(message)
    root = (data_dir / "texts").resolve(strict=True)
    selected, missing, skipped, passages = [], [], [], []
    seen = set()
    for work in run.work_records:
        if work.id in seen:
            message = "Duplicate work ID in saved manifest"
            raise SearchError(message)
        seen.add(work.id)
        if not work.has_text or work.id in run.fixture_work_ids:
            skipped.append(work.id)
            continue
        if Path(work.id).name != work.id or any(char in work.id for char in "*?[]\\"):
            message = "Unsafe work ID in saved manifest"
            raise SearchError(message)
        selected.append(work.id)
        files = sorted(set(root.glob(f"{work.id}_*.txt")) | set(root.glob(f"{work.id}.txt")))
        if not files:
            missing.append(work.id)
        for path in files:
            owners = [candidate.id for candidate in run.work_records if path.name == f"{candidate.id}.txt" or path.name.startswith(f"{candidate.id}_")]
            if len(owners) > 1:
                message = "Ambiguous cache filename matches multiple manifest work IDs; review as explicit JSONL"
                raise SearchError(message)
            if path.is_symlink() or not path.is_file() or not path.resolve().is_relative_to(root):
                message = "Cache text must be a regular contained file"
                raise SearchError(message)
            if work.source_url is None:
                message = "Selected text lacks a source URL; review provenance before indexing"
                raise SearchError(message)
            content = path.read_bytes()
            text = content.decode("utf-8")
            digest = hashlib.sha256(content).hexdigest()
            if not text.strip():
                message = "Selected cache text is empty"
                raise SearchError(message)
            edition_id = f"cache:{work.id}:{path.name}"
            passages.append(Passage(passage_id=edition_id, work_id=work.target_id or f"{work.source}:{work.id}",
                author_id="william-blake-1757-1827", title=work.title,
                edition_id=edition_id, edition="Saved cache; source edition and copy not verified",
                locator=f"{path.name}: file lines 1-{len(text.splitlines())}", locator_kind="file_lines",
                source_url=work.source_url, rights="Local research cache; redistribution not granted",
                text_role="unverified", text=text, source_sha256=digest))
    return CacheImport(manifest_sha256=hashlib.sha256(raw).hexdigest(),
        selected_work_ids=tuple(selected), missing_text_ids=tuple(missing),
        skipped_text_ids=tuple(skipped), passages=tuple(passages))
