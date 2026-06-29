from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from PIL import Image, ImageDraw

from ..models import BlakeImage, BlakeMetadata, BlakeWork, LicenseType, SourceType, WorkType
from .models import CorpusCoverageRecord, CorpusTarget, CorpusTargetEntry, SourceRecord

CANONICAL_TARGET_PATH = Path(__file__).with_name("canonical_target.json")
CANONICAL_TARGET_VERSION = "2026-06-22"


def _date(year: int) -> datetime:
    return datetime(year, 1, 1)


def _entry(
    target_id: str,
    title: str,
    year: Optional[int],
    work_type: WorkType,
    category: str,
    *,
    expected_text: bool = True,
    expected_images: int = 0,
    expected_copies: Optional[int] = None,
    aliases: Optional[List[str]] = None,
    blake_archive_id: Optional[str] = None,
    notes: Optional[str] = None,
) -> CorpusTargetEntry:
    source_hints: Dict[str, List[str]] = {}
    if blake_archive_id:
        source_hints[SourceType.BLAKE_ARCHIVE.value] = [blake_archive_id]

    return CorpusTargetEntry(
        target_id=target_id,
        title=title,
        work_type=work_type,
        category=category,
        date_label=str(year) if year else None,
        creation_date=_date(year) if year else None,
        expected_text=expected_text,
        expected_images=expected_images,
        expected_copies=expected_copies,
        aliases=aliases or [],
        source_hints=source_hints,
        notes=notes,
    )


def _parse_year_from_label(label: Optional[str]) -> Optional[int]:
    if not label:
        return None
    match = re.search(r"\d{4}", label)
    return int(match.group()) if match else None


def _entry_from_ledger(row: List[Any], schema: List[str]) -> CorpusTargetEntry:
    data = dict(zip(schema, row))
    archive_id = data.get("blake_archive_id")
    source_hints: Dict[str, List[str]] = {}
    if archive_id:
        source_hints[SourceType.BLAKE_ARCHIVE.value] = [str(archive_id)]

    year = _parse_year_from_label(data.get("date_label"))
    expected_copies = data.get("expected_copies")
    if expected_copies is not None:
        expected_copies = int(expected_copies)

    return CorpusTargetEntry(
        target_id=str(data["target_id"]),
        title=str(data["title"]),
        work_type=WorkType(str(data["work_type"])),
        category=str(data["category"]),
        date_label=data.get("date_label"),
        creation_date=_date(year) if year else None,
        expected_text=bool(data.get("expected_text")),
        expected_images=int(data.get("expected_images") or 0),
        expected_copies=expected_copies,
        aliases=list(data.get("aliases") or []),
        source_hints=source_hints,
        notes=data.get("notes") or None,
    )


def load_corpus_target(profile: str = "canonical") -> CorpusTarget:
    payload = json.loads(CANONICAL_TARGET_PATH.read_text(encoding="utf-8"))
    if profile != payload.get("profile"):
        raise ValueError(f"Unknown corpus target profile: {profile}")

    schema = list(payload["schema"])
    entries = [_entry_from_ledger(row, schema) for row in payload["entries"]]

    return CorpusTarget(
        profile=profile,
        version=str(payload.get("version") or CANONICAL_TARGET_VERSION),
        description=str(payload["description"]),
        entries=entries,
    )


def normalize_title(value: Optional[str]) -> str:
    if not value:
        return ""
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def _value(value: object) -> str:
    return getattr(value, "value", str(value))


def _entry_lookup(target: CorpusTarget) -> Dict[str, CorpusTargetEntry]:
    lookup: Dict[str, CorpusTargetEntry] = {}
    for entry in target.entries:
        lookup[entry.target_id] = entry
        lookup[normalize_title(entry.target_id)] = entry
        lookup.setdefault(normalize_title(entry.title), entry)
        for alias in entry.aliases:
            lookup.setdefault(normalize_title(alias), entry)
        for source_ids in entry.source_hints.values():
            for source_id in source_ids:
                lookup.setdefault(normalize_title(source_id), entry)
    return lookup


def _entry_lookup_all(
    target: CorpusTarget,
    *,
    include_titles: bool = True,
    include_aliases: bool = True,
    include_source_hints: bool = True,
) -> Dict[str, List[CorpusTargetEntry]]:
    lookup: Dict[str, List[CorpusTargetEntry]] = {}

    def add(value: object, entry: CorpusTargetEntry) -> None:
        key = normalize_title(str(value) if value is not None else "")
        if not key:
            return
        bucket = lookup.setdefault(key, [])
        if entry not in bucket:
            bucket.append(entry)

    for entry in target.entries:
        add(entry.target_id, entry)
        if include_titles:
            add(entry.title, entry)
        if include_aliases:
            for alias in entry.aliases:
                add(alias, entry)
        if include_source_hints:
            for source_ids in entry.source_hints.values():
                for source_id in source_ids:
                    add(source_id, entry)
    return lookup


def match_source_record(record: SourceRecord, target: CorpusTarget) -> Optional[CorpusTargetEntry]:
    entries = match_source_record_entries(record, target)
    return entries[0] if entries else None


def match_work(work: BlakeWork, target: CorpusTarget) -> Optional[CorpusTargetEntry]:
    entries = match_work_entries(work, target)
    return entries[0] if entries else None


def match_source_record_entries(
    record: SourceRecord, target: CorpusTarget
) -> List[CorpusTargetEntry]:
    id_lookup = _entry_lookup_all(
        target, include_titles=False, include_aliases=False, include_source_hints=True
    )
    id_candidates = [
        normalize_title(record.source_id),
        normalize_title(record.metadata.get("target_id")),
        normalize_title(record.metadata.get("work_id")),
    ]
    id_matches = _matching_entries(id_candidates, id_lookup)
    if id_matches:
        return id_matches

    title_lookup = _entry_lookup_all(
        target, include_titles=True, include_aliases=False, include_source_hints=False
    )
    return _matching_entries([normalize_title(record.title)], title_lookup)


def match_work_entries(work: BlakeWork, target: CorpusTarget) -> List[CorpusTargetEntry]:
    id_lookup = _entry_lookup_all(
        target, include_titles=False, include_aliases=False, include_source_hints=True
    )
    metadata = work.metadata
    id_candidates = [
        normalize_title(work.id),
        normalize_title(metadata.id),
        normalize_title(metadata.source_id),
    ]
    id_matches = _matching_entries(id_candidates, id_lookup)
    if id_matches:
        return id_matches

    title_lookup = _entry_lookup_all(
        target, include_titles=True, include_aliases=False, include_source_hints=False
    )
    return _matching_entries([normalize_title(metadata.title)], title_lookup)


def _matching_entries(
    candidates: List[str], lookup: Dict[str, List[CorpusTargetEntry]]
) -> List[CorpusTargetEntry]:
    matches: List[CorpusTargetEntry] = []
    seen: set[str] = set()
    for candidate in candidates:
        if candidate in lookup:
            for entry in lookup[candidate]:
                if entry.target_id not in seen:
                    seen.add(entry.target_id)
                    matches.append(entry)
    return matches


def build_target_coverage(
    target: CorpusTarget,
    works: Iterable[BlakeWork],
    source_records: Iterable[SourceRecord] = (),
) -> Tuple[List[CorpusCoverageRecord], Dict[str, int], str]:
    works_by_target: Dict[str, List[BlakeWork]] = {entry.target_id: [] for entry in target.entries}
    source_ids_by_target: Dict[str, List[str]] = {entry.target_id: [] for entry in target.entries}

    for work in works:
        for entry in match_work_entries(work, target):
            works_by_target[entry.target_id].append(work)

    for record in source_records:
        for entry in match_source_record_entries(record, target):
            source_ids_by_target[entry.target_id].append(record.stable_id)

    records: List[CorpusCoverageRecord] = []
    counts = {"present": 0, "partial": 0, "missing": 0, "duplicate": 0, "unverified": 0}

    for entry in target.entries:
        matched_works = works_by_target[entry.target_id]
        matched_sources = sorted(set(source_ids_by_target[entry.target_id]))
        notes: List[str] = []

        if len(matched_works) > 1:
            status = "duplicate"
            notes.append("Multiple local works match this target entry.")
        elif matched_works:
            work = matched_works[0]
            missing_text = entry.expected_text and not bool(work.text_content)
            missing_images = entry.expected_images > 0 and not bool(work.images)
            if missing_text:
                notes.append("Expected text is not available locally.")
            if missing_images:
                notes.append("Expected image evidence is not available locally.")
            status = "partial" if missing_text or missing_images else "present"
        elif matched_sources:
            status = "unverified"
            notes.append("Source discovery found this target, but no local work was saved.")
        else:
            status = "missing"

        counts[status] += 1
        records.append(
            CorpusCoverageRecord(
                target_id=entry.target_id,
                title=entry.title,
                category=entry.category,
                work_type=str(entry.work_type),
                expected_text=entry.expected_text,
                expected_images=entry.expected_images,
                expected_copies=entry.expected_copies,
                matched_work_ids=[work.id for work in matched_works],
                matched_source_ids=matched_sources,
                status=status,
                notes=notes,
            )
        )

    if not target.entries:
        coverage_status = "unscoped"
    elif counts["missing"] == counts["unverified"] == counts["partial"] == counts["duplicate"] == 0:
        coverage_status = "complete"
    elif sum(counts.values()) == counts["missing"]:
        coverage_status = "empty"
    else:
        coverage_status = "partial"

    counts["total"] = len(target.entries)
    return records, counts, coverage_status


def build_fixture_works(data_dir: Path) -> List[BlakeWork]:
    image_dir = data_dir / "fixtures" / "images"
    image_dir.mkdir(parents=True, exist_ok=True)

    songs_image = _fixture_image(image_dir / "fixture-songsie-title.png", ["#f4d35e", "#1f6f8b", "#f95738"])
    mhh_image = _fixture_image(image_dir / "fixture-mhh-plate.png", ["#111111", "#c1121f", "#fdf0d5"])

    return [
        BlakeWork(
            id="fixture-songsie",
            metadata=BlakeMetadata(
                id="fixture-songsie",
                title="Songs of Innocence and of Experience",
                work_type=WorkType.ILLUMINATED_BOOK,
                source=SourceType.BLAKE_ARCHIVE,
                source_id="songsie",
                source_url="fixture://blake/songsie",
                api_source="fixture",
                creation_date=_date(1794),
                description="Offline fixture excerpt for corpus pipeline verification.",
                license_type=LicenseType.PUBLIC_DOMAIN,
                attribution="Offline Blake fixture corpus",
                usage_terms="Fixture data for deterministic tests and quick runs.",
                themes=["innocence", "experience", "imagination"],
                subjects=["childhood", "contraries", "vision"],
                processed=False,
            ),
            text_content=(
                "Little Lamb who made thee Dost thou know who made thee. "
                "Tyger Tyger burning bright In the forests of the night."
            ),
            images=[
                BlakeImage(
                    id="fixture-songsie-img-1",
                    metadata_id="fixture-songsie",
                    title="Songs fixture title plate",
                    file_path=songs_image,
                    original_url="fixture://blake/songsie/title",
                    width=96,
                    height=96,
                    dominant_colors=["#f4d35e", "#1f6f8b", "#f95738"],
                    related_text_id="fixture-songsie",
                    plate_number=1,
                )
            ],
            text_versions=[{"source": "fixture", "kind": "excerpt"}],
            text_analysis={"entities": [{"text": "Lamb"}, {"text": "Tyger"}]},
        ),
        BlakeWork(
            id="fixture-mhh",
            metadata=BlakeMetadata(
                id="fixture-mhh",
                title="The Marriage of Heaven and Hell",
                work_type=WorkType.ILLUMINATED_BOOK,
                source=SourceType.BLAKE_ARCHIVE,
                source_id="mhh",
                source_url="fixture://blake/mhh",
                api_source="fixture",
                creation_date=_date(1790),
                description="Offline fixture excerpt for multimodal analysis.",
                license_type=LicenseType.PUBLIC_DOMAIN,
                attribution="Offline Blake fixture corpus",
                usage_terms="Fixture data for deterministic tests and quick runs.",
                themes=["contraries", "religion", "energy"],
                subjects=["heaven", "hell", "proverbs"],
                processed=False,
            ),
            text_content=(
                "Without contraries is no progression. Attraction and repulsion, "
                "reason and energy, love and hate, are necessary to human existence."
            ),
            images=[
                BlakeImage(
                    id="fixture-mhh-img-1",
                    metadata_id="fixture-mhh",
                    title="Marriage fixture plate",
                    file_path=mhh_image,
                    original_url="fixture://blake/mhh/plate",
                    width=96,
                    height=96,
                    dominant_colors=["#111111", "#c1121f", "#fdf0d5"],
                    related_text_id="fixture-mhh",
                    plate_number=3,
                )
            ],
            text_versions=[{"source": "fixture", "kind": "excerpt"}],
            text_analysis={"entities": [{"text": "Heaven"}, {"text": "Hell"}]},
        ),
        BlakeWork(
            id="fixture-letters",
            metadata=BlakeMetadata(
                id="fixture-letters",
                title="Letters",
                work_type=WorkType.LETTER,
                source=SourceType.BLAKE_ARCHIVE,
                source_id="lt",
                source_url="fixture://blake/letters",
                api_source="fixture",
                creation_date=_date(1800),
                description="Offline fixture representative for Blake correspondence.",
                license_type=LicenseType.PUBLIC_DOMAIN,
                attribution="Offline Blake fixture corpus",
                usage_terms="Fixture data for deterministic tests and quick runs.",
                themes=["correspondence", "craft", "patronage"],
                subjects=["letter", "printing", "work"],
                processed=False,
            ),
            text_content=(
                "I write in the confidence that imagination is not a state: "
                "it is the human existence itself."
            ),
            text_versions=[{"source": "fixture", "kind": "representative excerpt"}],
            text_analysis={"entities": [{"text": "imagination"}]},
        ),
    ]


def _fixture_image(path: Path, colors: List[str]) -> Path:
    if path.exists():
        return path

    image = Image.new("RGB", (96, 96), colors[0])
    draw = ImageDraw.Draw(image)
    draw.rectangle((16, 16, 80, 80), fill=colors[1])
    draw.line((0, 95, 95, 0), fill=colors[2], width=8)
    image.save(path, format="PNG")
    return path
