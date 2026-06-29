from __future__ import annotations

import hashlib
import json
import re
import xml.etree.ElementTree as ET
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional, Union
from urllib.parse import quote_plus

import aiohttp

from ..models import SourceType
from .models import CorpusCoverageRecord, CorpusTarget, CorpusTargetEntry, SourceRecord
from .targets import match_source_record, normalize_title

SOURCE_URLS = [
    {"label": "William Blake Archive", "url": "https://www.blakearchive.org/"},
    {
        "label": "Blake Archive GitHub repository",
        "url": "https://github.com/blakearchive/data",
    },
    {
        "label": "Blake Archive GitHub works inventory",
        "url": "https://raw.githubusercontent.com/blakearchive/data/master/works/__contents__.xml",
    },
    {
        "label": "Blake Archive GitHub works API",
        "url": "https://api.github.com/repos/blakearchive/data/contents/works?ref=master",
    },
    {"label": "Erdman edition", "url": "https://erdman.blakearchive.org/"},
    {
        "label": "Project Gutenberg author page",
        "url": "https://www.gutenberg.org/ebooks/author/295",
    },
    {
        "label": "Wikisource author page",
        "url": "https://en.wikisource.org/wiki/Author:William_Blake",
    },
    {
        "label": "Internet Archive advanced search",
        "url": "https://archive.org/advancedsearch.php?q=creator:%28William+Blake%29&fl%5B%5D=identifier&fl%5B%5D=title&rows=25&page=1&output=json",
    },
    {
        "label": "British Museum collection search",
        "url": "https://www.britishmuseum.org/collection/search?agent=William+Blake",
    },
    {
        "label": "Tate artist page",
        "url": "https://www.tate.org.uk/art/artists/william-blake-39",
    },
    {
        "label": "HathiTrust Blake record",
        "url": "https://catalog.hathitrust.org/Record/102153075",
    },
    {
        "label": "Blake Quarterly Essick finding list",
        "url": "https://bq.blakearchive.org/3.2.essick",
    },
]

MAX_TEXT_SAMPLE_CHARS = 2000
MAX_NORMALIZED_SNIPPET_CHARS = 360
MAX_JSON_NAME_SAMPLE = 25


def provider_reason_code(row: Dict[str, Any]) -> str:
    status = str(row.get("status") or "").lower()
    record_count = int(row.get("record_count") or 0)
    detail = " ".join(
        str(row.get(key) or "")
        for key in ("error", "message", "reason", "provider", "source_type")
    ).lower()
    if status == "completed" and record_count > 0:
        return "ok"
    if status == "completed":
        return "empty_result"
    if status in {"skipped", "disabled"}:
        return "skipped"
    if "timeout" in detail or "timed out" in detail:
        return "timeout"
    if "429" in detail or "throttle" in detail or "rate limit" in detail:
        return "throttled"
    if any(token in detail for token in ["terms", "license", "rights", "permission", "403"]):
        return "source_terms_review"
    if any(token in detail for token in ["parse", "xml", "json", "decode"]):
        return "parse_failure"
    if any(token in detail for token in ["http", "status", "client error", "server error", "404", "500", "502", "503"]):
        return "http_failure"
    if status in {"error", "failed"}:
        return "error"
    if not status:
        return "unknown"
    return status.replace(" ", "_")


def classify_provider_rows(rows: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    provider_rows = []
    for row in rows:
        payload = dict(row)
        payload.setdefault("reason_code", provider_reason_code(payload))
        provider_rows.append(payload)
    return provider_rows


@dataclass(frozen=True)
class MissingEvidenceCandidate:
    target_id: str
    title: str
    evidence_type: str
    candidate_source: str
    candidate_url: str
    http_status: Optional[int]
    ok: Optional[bool]
    match_confidence: float
    action_taken: str
    evidence_note: str
    lead_status: Optional[str] = None
    rights_note: Optional[str] = None
    acceptance_policy: Optional[str] = None
    review_priority: Optional[str] = None
    direct_source_basis: Optional[str] = None
    scholarship_note: Optional[str] = None


@dataclass(frozen=True)
class MissingEvidenceReport:
    target_count: int
    candidate_count: int
    by_evidence_type: Dict[str, int]
    candidates: List[MissingEvidenceCandidate]

    def to_payload(self) -> Dict[str, Any]:
        return {
            "target_count": self.target_count,
            "candidate_count": self.candidate_count,
            "by_evidence_type": self.by_evidence_type,
            "candidates": [asdict(candidate) for candidate in self.candidates],
        }


async def build_source_audit(
    target: CorpusTarget,
    records: Iterable[SourceRecord],
    *,
    include_live: bool = True,
    limit: int = 12,
    coverage_records: Iterable[Union[CorpusCoverageRecord, Dict[str, Any]]] = (),
    provider_discovery: Iterable[Dict[str, Any]] = (),
    archive_metadata_enrichment: Optional[Dict[str, Any]] = None,
    source_leads: Iterable[Dict[str, Any]] = (),
) -> Dict[str, Any]:
    source_records = list(records)
    provider_rows = classify_provider_rows(provider_discovery)
    provider_failures = [
        row for row in provider_rows if str(row.get("status") or "") != "completed"
    ]
    provider_record_total = sum(int(row.get("record_count") or 0) for row in provider_rows)
    metadata_report = dict(archive_metadata_enrichment or {})
    matched_target_ids = {
        entry.target_id
        for record in source_records
        if (entry := match_source_record(record, target)) is not None
    }
    unmatched = [
        entry.target_id
        for entry in target.entries
        if entry.target_id not in matched_target_ids
    ]
    duplicate_aliases = _duplicate_aliases(target)

    payload: Dict[str, Any] = {
        "generated_at": datetime.now().isoformat(),
        "target_profile": target.profile,
        "target_version": target.version,
        "target_total": target.total,
        "records_discovered": len(source_records),
        "matched_target_count": len(matched_target_ids),
        "unmatched_target_count": len(unmatched),
        "unmatched_target_ids": unmatched,
        "duplicate_alias_count": len(duplicate_aliases),
        "duplicate_aliases": duplicate_aliases,
        "fallback_sources": {
            "text": [
                "Project Gutenberg",
                "Wikisource",
                "Internet Archive",
                "Erdman edition",
            ],
            "visual_catalog": [
                "British Museum",
                "Tate",
                "HathiTrust",
                "Blake Quarterly Essick finding list",
            ],
        },
        "provider_discovery": {
            "providers": provider_rows,
            "provider_count": len(provider_rows),
            "failure_count": len(provider_failures),
            "record_count": provider_record_total,
            "records_used": sum(
                int(row.get("record_count") or 0)
                for row in provider_rows
                if row.get("records_used")
            ),
        },
        "metadata_enrichment_report": metadata_report,
        "live": {
            "enabled": include_live,
            "checked_urls": [],
            "github_work_xml_count": None,
            "github_work_prefix_count": None,
            "github_contents_resource_count": None,
            "archive_api_sample": [],
            "archive_metadata_enrichment": metadata_report,
        },
    }

    if not include_live:
        attach_missing_evidence(
            payload, target, source_records, coverage_records, source_leads=source_leads
        )
        return payload

    timeout = aiohttp.ClientTimeout(total=30)
    headers = {"User-Agent": "BlakeAnalysisPlatform/1.0 (Academic Research)"}
    async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
        checked = []
        for source in SOURCE_URLS:
            checked.append(await _check_url(session, source["label"], source["url"]))
        payload["live"]["checked_urls"] = checked

        github_api = next(
            (
                row
                for row in checked
                if row["label"] == "Blake Archive GitHub works API"
            ),
            {},
        )
        if github_api.get("json_xml_count") is not None:
            payload["live"]["github_work_xml_count"] = github_api.get("json_xml_count")
            payload["live"]["github_work_prefix_count"] = github_api.get(
                "json_prefix_count"
            )
        elif isinstance(github_api.get("json_names"), list):
            xml_names = [
                name
                for name in github_api["json_names"]
                if str(name).endswith(".xml") and name != "__contents__.xml"
            ]
            payload["live"]["github_work_xml_count"] = len(xml_names)
            payload["live"]["github_work_prefix_count"] = len(
                {name.split(".", 1)[0].lower() for name in xml_names}
            )

        contents_row = next(
            (
                row
                for row in checked
                if row["label"] == "Blake Archive GitHub works inventory"
            ),
            {},
        )
        if contents_row.get("xml_resource_count") is not None:
            payload["live"]["github_contents_resource_count"] = contents_row.get(
                "xml_resource_count"
            )

        archive_ids = []
        for entry in target.entries:
            archive_ids.extend(
                entry.source_hints.get(SourceType.BLAKE_ARCHIVE.value, [])
            )
        for work_id in archive_ids[:limit]:
            payload["live"]["archive_api_sample"].append(
                await _check_archive_work(session, work_id)
            )

    attach_missing_evidence(
        payload, target, source_records, coverage_records, source_leads=source_leads
    )
    return payload


def _xml_resource_counts(body: str) -> Dict[str, int]:
    try:
        root = ET.fromstring(body)
    except ET.ParseError:
        return {}
    names = [
        elem.attrib.get("filename") or elem.attrib.get("name") or ""
        for elem in root.iter()
    ]
    xml_names = [
        name for name in names if name.endswith(".xml") and name != "__contents__.xml"
    ]
    return {
        "xml_resource_count": len(xml_names),
        "xml_prefix_count": len({name.split(".", 1)[0].lower() for name in xml_names}),
    }


def _json_name_counts(payload: Any) -> Dict[str, Any]:
    if not isinstance(payload, list):
        return {}
    names = [
        str(item.get("name"))
        for item in payload
        if isinstance(item, dict) and item.get("name")
    ]
    xml_names = [
        name for name in names if name.endswith(".xml") and name != "__contents__.xml"
    ]
    return {
        "json_count": len(payload),
        "json_names_sample": names[:MAX_JSON_NAME_SAMPLE],
        "json_xml_count": len(xml_names),
        "json_prefix_count": len(
            {name.split(".", 1)[0].lower() for name in xml_names}
        ),
    }


def attach_missing_evidence(
    payload: Dict[str, Any],
    target: CorpusTarget,
    records: Iterable[SourceRecord],
    coverage_records: Iterable[Union[CorpusCoverageRecord, Dict[str, Any]]] = (),
    source_leads: Iterable[Dict[str, Any]] = (),
) -> Dict[str, Any]:
    live = payload.get("live") or {}
    report = build_missing_evidence_report(
        target,
        records,
        coverage_records=coverage_records,
        checked_urls=live.get("checked_urls") or [],
        archive_api_sample=live.get("archive_api_sample") or [],
        source_leads=source_leads,
    )
    report_payload = report.to_payload()
    payload["missing_evidence"] = report_payload["candidates"]
    payload["missing_evidence_summary"] = {
        "target_count": report_payload["target_count"],
        "candidate_count": report_payload["candidate_count"],
        "by_evidence_type": report_payload["by_evidence_type"],
    }
    return payload


def build_missing_evidence_report(
    target: CorpusTarget,
    records: Iterable[SourceRecord],
    *,
    coverage_records: Iterable[Union[CorpusCoverageRecord, Dict[str, Any]]] = (),
    checked_urls: Iterable[Dict[str, Any]] = (),
    archive_api_sample: Iterable[Dict[str, Any]] = (),
    source_leads: Iterable[Dict[str, Any]] = (),
) -> MissingEvidenceReport:
    matched_target_ids = {
        entry.target_id
        for record in records
        if (entry := match_source_record(record, target)) is not None
    }
    entries_by_id = {entry.target_id: entry for entry in target.entries}
    checked_by_label = {str(row.get("label")): row for row in checked_urls}
    archive_by_id = {str(row.get("work_id")): row for row in archive_api_sample}
    leads_by_target: Dict[str, List[Dict[str, Any]]] = {}
    for lead in source_leads:
        if not isinstance(lead, dict):
            continue
        target_id = str(lead.get("target_id") or "")
        if target_id:
            leads_by_target.setdefault(target_id, []).append(dict(lead))

    gap_records = list(_gap_records(target, coverage_records, matched_target_ids))
    candidates: List[MissingEvidenceCandidate] = []
    for gap in gap_records:
        entry = entries_by_id.get(str(gap["target_id"]))
        if entry is None:
            continue
        evidence_types = _evidence_types_for_gap(entry, gap)
        for evidence_type in evidence_types:
            candidates.extend(
                _candidate_rows(
                    entry,
                    evidence_type,
                    str(gap.get("note") or ""),
                    checked_by_label,
                    archive_by_id,
                )
            )
            candidates.extend(
                _manual_source_lead_rows(
                    entry,
                    evidence_type,
                    str(gap.get("note") or ""),
                    leads_by_target.get(entry.target_id, []),
                )
            )

    by_type = Counter(candidate.evidence_type for candidate in candidates)
    return MissingEvidenceReport(
        target_count=len({candidate.target_id for candidate in candidates}),
        candidate_count=len(candidates),
        by_evidence_type=dict(sorted(by_type.items())),
        candidates=candidates,
    )


def _manual_source_lead_rows(
    entry: CorpusTargetEntry,
    evidence_type: str,
    note: str,
    leads: Iterable[Dict[str, Any]],
) -> List[MissingEvidenceCandidate]:
    rows: List[MissingEvidenceCandidate] = []
    for lead in leads:
        lead_evidence = str(lead.get("evidence_type") or "")
        if lead_evidence and lead_evidence != evidence_type:
            continue
        rows.append(
            MissingEvidenceCandidate(
                target_id=entry.target_id,
                title=entry.title,
                evidence_type=evidence_type,
                candidate_source=str(lead.get("source_owner") or "manual source lead"),
                candidate_url=str(lead.get("url") or ""),
                http_status=None,
                ok=None,
                match_confidence=float(lead.get("match_confidence") or 0.67),
                action_taken=(
                    "manual_review: source-owned lead only; exact-title validation, "
                    "attribution, checksum, rights metadata, and regenerated coverage "
                    "are required before any target status changes."
                ),
                evidence_note=(
                    note
                    + (
                        f" Lead status: {lead.get('status')}; "
                        f"rights note: {lead.get('rights_note')}."
                    )
                ).strip(),
                lead_status=str(lead.get("status") or "manual_review"),
                rights_note=str(lead.get("rights_note") or ""),
                acceptance_policy=str(
                    lead.get("acceptance_policy")
                    or "Manual review only; exact-title/source validation, attribution, checksum, rights metadata, and regenerated coverage are required before any target status changes."
                ),
                review_priority=str(lead.get("review_priority") or "medium"),
                direct_source_basis=str(lead.get("direct_source_basis") or ""),
                scholarship_note=str(lead.get("scholarship_note") or ""),
            )
        )
    return rows


def _gap_records(
    target: CorpusTarget,
    coverage_records: Iterable[Union[CorpusCoverageRecord, Dict[str, Any]]],
    matched_target_ids: set[str],
) -> Iterable[Dict[str, Any]]:
    saw_coverage = False
    for record in coverage_records:
        payload = (
            record.model_dump(mode="json")
            if hasattr(record, "model_dump")
            else dict(record)
        )
        if payload.get("status") == "present":
            continue
        saw_coverage = True
        notes = payload.get("notes") or []
        if notes:
            for note in notes:
                gap = dict(payload)
                gap["note"] = str(note)
                yield gap
        else:
            payload["note"] = "No complete local evidence is available for this target."
            yield payload

    if saw_coverage:
        return

    for entry in target.entries:
        if entry.target_id not in matched_target_ids:
            yield {
                "target_id": entry.target_id,
                "title": entry.title,
                "status": "missing",
                "note": "No source-discovery record matched this canonical target.",
            }


def _evidence_types_for_gap(entry: CorpusTargetEntry, gap: Dict[str, Any]) -> List[str]:
    note = str(gap.get("note") or "").lower()
    status = str(gap.get("status") or "")
    evidence_types: List[str] = []
    if "text" in note or (status == "missing" and entry.expected_text):
        evidence_types.append("text")
    if "image" in note or (status == "missing" and entry.expected_images > 0):
        evidence_types.append("image")
    if status in {"missing", "unverified"} or "source" in note:
        evidence_types.append("source_match")
    if not evidence_types:
        evidence_types.append("source_match")
    return list(dict.fromkeys(evidence_types))


def _candidate_rows(
    entry: CorpusTargetEntry,
    evidence_type: str,
    note: str,
    checked_by_label: Dict[str, Dict[str, Any]],
    archive_by_id: Dict[str, Dict[str, Any]],
) -> List[MissingEvidenceCandidate]:
    rows: List[MissingEvidenceCandidate] = []
    archive_ids = entry.source_hints.get(SourceType.BLAKE_ARCHIVE.value, [])
    query = quote_plus(entry.title)
    archive_id = archive_ids[0] if archive_ids else ""

    if archive_id:
        if evidence_type in {"source_match", "text"}:
            rows.append(
                _candidate(
                    entry,
                    evidence_type,
                    "William Blake Archive work API",
                    f"https://www.blakearchive.org/api/work/{archive_id}",
                    note,
                    checked_by_label,
                    archive_by_id.get(archive_id),
                    0.96,
                    "Checked Archive API metadata and GitHub TEI inventory before external fallbacks.",
                )
            )
        if evidence_type == "text":
            rows.append(
                _candidate(
                    entry,
                    evidence_type,
                    "Blake Archive GitHub TEI inventory",
                    f"https://github.com/blakearchive/data/tree/master/works?plain=1&q={quote_plus(archive_id)}",
                    note,
                    checked_by_label,
                    None,
                    0.9,
                    "Search exact Archive id in the live TEI filename inventory.",
                )
            )
        if evidence_type == "image":
            rows.append(
                _candidate(
                    entry,
                    evidence_type,
                    "William Blake Archive image/API metadata",
                    f"https://www.blakearchive.org/api/work/{archive_id}",
                    note,
                    checked_by_label,
                    archive_by_id.get(archive_id),
                    0.88,
                    "Use Archive object/image metadata before museum-catalog corroboration.",
                )
            )

    if evidence_type == "source_match" and not archive_id:
        rows.extend(
            [
                _candidate(
                    entry,
                    evidence_type,
                    "Project Gutenberg author page",
                    f"https://www.gutenberg.org/ebooks/search/?query={query}",
                    note,
                    checked_by_label,
                    None,
                    0.64,
                    "Search text-canon fallback holdings for a title or alias match.",
                ),
                _candidate(
                    entry,
                    evidence_type,
                    "Wikisource author page",
                    f"https://en.wikisource.org/w/index.php?search={query}+William+Blake",
                    note,
                    checked_by_label,
                    None,
                    0.62,
                    "Search public transcription holdings for a title or alias match.",
                ),
                _candidate(
                    entry,
                    evidence_type,
                    "Internet Archive advanced search",
                    (
                        "https://archive.org/advancedsearch.php?q="
                        f"title%3A%28{query}%29+AND+creator%3A%28William+Blake%29"
                        "&fl%5B%5D=identifier&fl%5B%5D=title&rows=10&output=json"
                    ),
                    note,
                    checked_by_label,
                    None,
                    0.56,
                    "Search facsimile and edition metadata for title corroboration.",
                ),
            ]
        )

    if evidence_type == "text":
        rows.extend(
            [
                _candidate(
                    entry,
                    evidence_type,
                    "Project Gutenberg author page",
                    f"https://www.gutenberg.org/ebooks/search/?query={query}",
                    note,
                    checked_by_label,
                    None,
                    0.72,
                    "Record as corroborating text evidence only; do not override Archive authority.",
                ),
                _candidate(
                    entry,
                    evidence_type,
                    "Wikisource author page",
                    f"https://en.wikisource.org/w/index.php?search={query}+William+Blake",
                    note,
                    checked_by_label,
                    None,
                    0.68,
                    "Record as corroborating transcription evidence when title/alias matches.",
                ),
                _candidate(
                    entry,
                    evidence_type,
                    "Internet Archive advanced search",
                    (
                        "https://archive.org/advancedsearch.php?q="
                        f"title%3A%28{query}%29+AND+creator%3A%28William+Blake%29"
                        "&fl%5B%5D=identifier&fl%5B%5D=title&rows=10&output=json"
                    ),
                    note,
                    checked_by_label,
                    None,
                    0.62,
                    "Record facsimile or derivative-edition evidence as fallback provenance.",
                ),
                _candidate(
                    entry,
                    evidence_type,
                    "HathiTrust Blake record",
                    f"https://catalog.hathitrust.org/Search/Home?lookfor={query}&searchtype=title",
                    note,
                    checked_by_label,
                    None,
                    0.56,
                    "Use catalog records as bibliographic corroboration, not primary text authority.",
                ),
            ]
        )

    if evidence_type == "image":
        rows.extend(
            [
                _candidate(
                    entry,
                    evidence_type,
                    "British Museum collection search",
                    f"https://www.britishmuseum.org/collection/search?keyword={query}&agent=William+Blake",
                    note,
                    checked_by_label,
                    None,
                    0.58,
                    "Use as visual/catalog corroboration for image provenance.",
                ),
                _candidate(
                    entry,
                    evidence_type,
                    "Tate artist page",
                    f"https://www.tate.org.uk/search?q={query}+William+Blake",
                    note,
                    checked_by_label,
                    None,
                    0.52,
                    "Use as visual/catalog corroboration when the work is in Tate holdings.",
                ),
                _candidate(
                    entry,
                    evidence_type,
                    "Blake Quarterly Essick finding list",
                    f"https://bq.blakearchive.org/3.2.essick?search={query}",
                    note,
                    checked_by_label,
                    None,
                    0.48,
                    "Use as a reproduction finding aid, not as local image evidence.",
                ),
            ]
        )

    return rows


def _candidate(
    entry: CorpusTargetEntry,
    evidence_type: str,
    source_label: str,
    url: str,
    note: str,
    checked_by_label: Dict[str, Dict[str, Any]],
    direct_status: Optional[Dict[str, Any]],
    confidence: float,
    action: str,
) -> MissingEvidenceCandidate:
    checked = direct_status or checked_by_label.get(source_label) or {}
    return MissingEvidenceCandidate(
        target_id=entry.target_id,
        title=entry.title,
        evidence_type=evidence_type,
        candidate_source=source_label,
        candidate_url=url,
        http_status=checked.get("status"),
        ok=checked.get("ok") if "ok" in checked else None,
        match_confidence=confidence,
        action_taken=action,
        evidence_note=note,
    )


async def _check_url(
    session: aiohttp.ClientSession, label: str, url: str
) -> Dict[str, Any]:
    row: Dict[str, Any] = {
        "label": label,
        "url": url,
        "status": None,
        "ok": False,
        "content_type": None,
    }
    try:
        async with session.get(url) as response:
            body = await response.text(errors="ignore")
            snippet = _normalized_snippet(body)
            row.update(
                {
                    "status": response.status,
                    "ok": 200 <= response.status < 400,
                    "content_type": response.headers.get("content-type"),
                    "bytes_sampled": len(body),
                    "body_sha256": hashlib.sha256(body.encode("utf-8")).hexdigest(),
                    "sample_truncated": len(body) > len(snippet),
                    "normalized_snippet": snippet,
                }
            )
            if "application/json" in str(row["content_type"]):
                try:
                    payload = json.loads(body)
                    if isinstance(payload, list):
                        row.update(_json_name_counts(payload))
                    elif isinstance(payload, dict):
                        row["json_keys"] = sorted(payload.keys())[:25]
                        response_body = payload.get("response")
                        if isinstance(response_body, dict):
                            docs = response_body.get("docs")
                            if isinstance(docs, list):
                                row["json_result_count"] = len(docs)
                except Exception:
                    row["normalized_snippet"] = snippet
            else:
                row.update(_xml_resource_counts(body))
                row["normalized_snippet"] = snippet
    except Exception as exc:
        row["error"] = str(exc)
    return row


def _normalized_snippet(body: str, *, limit: int = MAX_NORMALIZED_SNIPPET_CHARS) -> str:
    return re.sub(r"\s+", " ", body).strip()[:limit]


async def _check_archive_work(
    session: aiohttp.ClientSession, work_id: str
) -> Dict[str, Any]:
    url = f"https://www.blakearchive.org/api/work/{work_id}"
    row: Dict[str, Any] = {"work_id": work_id, "url": url, "status": None, "ok": False}
    try:
        async with session.get(url) as response:
            row["status"] = response.status
            row["ok"] = 200 <= response.status < 400
            if row["ok"]:
                payload = await response.json()
                row["title"] = payload.get("title")
                row["medium"] = payload.get("medium")
                row["image"] = payload.get("image")
    except Exception as exc:
        row["error"] = str(exc)
    return row


def _duplicate_aliases(target: CorpusTarget) -> Dict[str, List[str]]:
    alias_map: Dict[str, List[str]] = {}
    for entry in target.entries:
        values = [entry.target_id, entry.title, *entry.aliases]
        for source_ids in entry.source_hints.values():
            values.extend(source_ids)
        for value in values:
            key = normalize_title(value)
            if key:
                alias_map.setdefault(key, []).append(entry.target_id)
    return {
        key: sorted(set(target_ids))
        for key, target_ids in alias_map.items()
        if len(set(target_ids)) > 1 and not re.fullmatch(r"\d+", key)
    }
