from __future__ import annotations

import hashlib
import html
import json
import re
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

import requests
from bs4 import BeautifulSoup

from ..metadata import MetadataManager
from ..models import BlakeMetadata, BlakeWork, LicenseType, SourceType
from .models import CorpusTargetEntry
from .targets import load_corpus_target, normalize_title

USER_AGENT = "BlakeAnalysisPlatform/1.0 (Academic Research)"
MIN_WORDS = 100
FALLBACK_MIN_WORDS_BY_TARGET = {
    "everlasting-gospel": 500,
    "poetical-sketches": 1000,
}
FALLBACK_TEXT_SOURCES = {
    "Project Gutenberg author page": SourceType.PROJECT_GUTENBERG,
    "Wikisource author page": SourceType.WIKIMEDIA,
}
FALLBACK_VALIDATION_DIR = "fallback_text_validations"


@dataclass(frozen=True)
class EvidencePullResult:
    target_id: str
    title: str
    candidate_source: str
    candidate_url: str
    evidence_type: str
    live_ok: bool | None
    match_confidence: float
    status: str
    reason: str
    authority_tier: str | None = None
    accepted_url: str | None = None
    words: int = 0
    checksum: str | None = None
    dry_run: bool = False
    http_status: int | None = None
    ok: bool | None = None
    action_taken: str | None = None
    evidence_note: str | None = None
    lead_status: str | None = None
    rights_note: str | None = None
    acceptance_policy: str | None = None
    review_priority: str | None = None
    direct_source_basis: str | None = None
    scholarship_note: str | None = None


def acquire_from_audit(
    audit_path: Path,
    data_dir: Path,
    *,
    min_confidence: float = 0.68,
    dry_run: bool = False,
) -> dict[str, Any]:
    audit_path = Path(audit_path)
    data_dir = Path(data_dir)
    payload = json.loads(audit_path.read_text(encoding="utf-8"))
    target = load_corpus_target(str(payload.get("target_profile") or "canonical"))
    entries_by_id = {entry.target_id: entry for entry in target.entries}
    manager = MetadataManager(data_dir)
    session = _session()

    results: list[EvidencePullResult] = []
    accepted_targets: set[str] = set()
    for row in payload.get("missing_evidence") or []:
        result = _process_candidate_row(
            row,
            entries_by_id,
            manager,
            data_dir,
            session,
            min_confidence=min_confidence,
            dry_run=dry_run,
            already_accepted=accepted_targets,
        )
        if result.status == "accepted":
            accepted_targets.add(result.target_id)
        results.append(result)

    summary = {
        "audit_path": str(audit_path),
        "data_dir": str(data_dir),
        "dry_run": dry_run,
        "min_confidence": min_confidence,
        "processed_candidates": len(results),
        "accepted": sum(result.status == "accepted" for result in results),
        "rejected": sum(result.status == "rejected" for result in results),
        "skipped": sum(result.status == "skipped" for result in results),
        "results": [asdict(result) for result in results],
    }
    review_path = (
        Path(payload.get("path", audit_path)).parent
        / "evidence_acquisition_review.json"
    )
    review = build_acquisition_review(
        payload,
        summary["results"],
        audit_path=audit_path,
        data_dir=data_dir,
        min_confidence=min_confidence,
        dry_run=dry_run,
    )
    review_path.parent.mkdir(parents=True, exist_ok=True)
    review_path.write_text(json.dumps(review, indent=2), encoding="utf-8")
    queue_path = review_path.with_name("evidence_acquisition_review_queue.md")
    queue_path.write_text(_review_queue_markdown(review), encoding="utf-8")
    summary["review_path"] = str(review_path)
    summary["review_queue_path"] = str(queue_path)
    summary["target_reviews"] = review["target_reviews"]
    if not dry_run:
        report_path = (
            Path(payload.get("path", audit_path)).parent / "evidence_acquisition.json"
        )
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
        summary["path"] = str(report_path)
    return summary


def build_acquisition_review(
    audit_payload: dict[str, Any],
    results: list[dict[str, Any]],
    *,
    audit_path: Path,
    data_dir: Path,
    min_confidence: float,
    dry_run: bool,
) -> dict[str, Any]:
    target_rows: dict[str, dict[str, Any]] = {}
    for row in audit_payload.get("missing_evidence") or []:
        target_id = str(row.get("target_id") or "")
        if target_id and target_id not in target_rows:
            target_rows[target_id] = {
                "target_id": target_id,
                "title": str(row.get("title") or target_id),
            }
    for result in results:
        target_id = str(result.get("target_id") or "")
        if target_id and target_id not in target_rows:
            target_rows[target_id] = {
                "target_id": target_id,
                "title": str(result.get("title") or target_id),
            }

    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for result in results:
        grouped[str(result.get("target_id") or "")].append(result)

    target_reviews: list[dict[str, Any]] = []
    for target_id, target_row in sorted(target_rows.items()):
        rows = grouped.get(target_id, [])
        status_counts = Counter(str(row.get("status") or "unknown") for row in rows)
        reason_counts = Counter(str(row.get("reason") or "") for row in rows)
        candidate_reviews = [_candidate_review(row) for row in rows]
        recommended = _recommended_action(rows)
        target_reviews.append(
            {
                "target_id": target_id,
                "title": target_row["title"],
                "candidate_count": len(rows),
                "status_counts": dict(sorted(status_counts.items())),
                "reason_counts": dict(sorted(reason_counts.items())),
                "recommended_action": recommended,
                "recommended_next_action": recommended,
                "candidates": candidate_reviews,
            }
        )

    unresolved = [
        row
        for row in target_reviews
        if row["status_counts"].get("accepted", 0) == 0
    ]
    review_queue = _review_queue_rows(target_reviews)
    return {
        "schema_version": "1.1",
        "artifact": "evidence_acquisition_review",
        "generated_at": datetime.now().isoformat(),
        "audit_path": str(audit_path),
        "data_dir": str(data_dir),
        "dry_run": dry_run,
        "min_confidence": min_confidence,
        "target_profile": audit_payload.get("target_profile") or "canonical",
        "target_count": len(target_reviews),
        "unresolved_target_count": len(unresolved),
        "candidate_count": len(results),
        "status_counts": dict(
            sorted(Counter(str(row.get("status") or "unknown") for row in results).items())
        ),
        "review_queue": review_queue,
        "target_reviews": target_reviews,
    }


def _candidate_review(row: dict[str, Any]) -> dict[str, Any]:
    source = str(row.get("candidate_source") or "unlabeled source candidate")
    reason = str(row.get("reason") or "")
    action_taken = str(row.get("action_taken") or "")
    candidate = {
        "candidate_source": source,
        "source": source,
        "candidate_url": row.get("candidate_url") or "",
        "evidence_type": row.get("evidence_type") or "unknown",
        "http_status": row.get("http_status"),
        "ok": row.get("ok"),
        "live_ok": row.get("live_ok"),
        "match_confidence": row.get("match_confidence"),
        "status": row.get("status") or "unknown",
        "reason": reason,
        "action_taken": action_taken,
        "evidence_note": row.get("evidence_note") or "",
        "lead_status": row.get("lead_status"),
        "rights_note": row.get("rights_note"),
        "acceptance_policy": row.get("acceptance_policy"),
        "review_priority": row.get("review_priority"),
        "direct_source_basis": row.get("direct_source_basis"),
        "scholarship_note": row.get("scholarship_note"),
        "accepted_url": row.get("accepted_url"),
        "words": row.get("words"),
        "checksum": row.get("checksum"),
    }
    candidate["recommended_next_action"] = _candidate_recommended_action(row)
    return candidate


def _review_queue_rows(target_reviews: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for target in target_reviews:
        for candidate in target.get("candidates") or []:
            rows.append(
                {
                    "target_id": target["target_id"],
                    "title": target["title"],
                    "candidate_source": candidate["candidate_source"],
                    "evidence_type": candidate["evidence_type"],
                    "status": candidate["status"],
                    "match_confidence": candidate["match_confidence"],
                    "review_priority": candidate.get("review_priority"),
                    "recommended_next_action": candidate["recommended_next_action"],
                    "candidate_url": candidate["candidate_url"],
                    "reason": candidate["reason"],
                }
            )
    return rows


def _review_queue_markdown(review: dict[str, Any]) -> str:
    rows = review.get("review_queue") or []
    lines = [
        "# Evidence Acquisition Review Queue",
        "",
        "| Target | Title | Source | Evidence | Status | Confidence | Priority | Next Action |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            "| "
            + " | ".join(
                _md_cell(value)
                for value in [
                    row.get("target_id"),
                    row.get("title"),
                    row.get("candidate_source"),
                    row.get("evidence_type"),
                    row.get("status"),
                    row.get("match_confidence"),
                    row.get("review_priority") or "",
                    row.get("recommended_next_action"),
                ]
            )
            + " |"
        )
    if not rows:
        lines.append("| none | none | none | none | none |  |  | No review candidates. |")
    return "\n".join(lines) + "\n"


def _md_cell(value: Any) -> str:
    return str(value or "").replace("|", "\\|").replace("\n", " ").strip()


def _candidate_recommended_action(row: dict[str, Any]) -> str:
    status = str(row.get("status") or "")
    reason = str(row.get("reason") or "")
    action_taken = str(row.get("action_taken") or "")
    if status == "accepted":
        return "Corroborate accepted fallback text before any public resolved-status claim."
    if str(row.get("lead_status") or "") == "manual_review" or action_taken.startswith(
        "manual_review:"
    ):
        return (
            "Manual review only; exact-title/source validation, attribution, "
            "checksum, rights metadata, and regenerated coverage are required."
        )
    if "candidate endpoint was not live-ok" in reason:
        return "Rerun live audit or inspect endpoint manually before acquisition."
    if "candidate confidence below threshold" in reason:
        return "Leave unresolved unless a higher-confidence exact source is found."
    if "non-text evidence" in reason:
        return "Route through archive-all image-depth acquisition and rights review."
    if "source pull failed" in reason:
        return "Retry with backoff or inspect the source manually."
    if "no exact title or alias match" in reason:
        return "Reject until an exact title or accepted alias match is found."
    return "Keep unresolved until a source-owned candidate passes all validation gates."


def _recommended_action(rows: list[dict[str, Any]]) -> str:
    if any(row.get("status") == "accepted" for row in rows):
        return (
            "Fallback text passed local validation; corroborate against an "
            "additional editorial source before public release notes describe "
            "the target as fully resolved."
        )
    reasons = {str(row.get("reason") or "") for row in rows}
    if any(
        str(row.get("lead_status") or "") == "manual_review"
        or str(row.get("action_taken") or "").startswith("manual_review:")
        for row in rows
    ):
        return (
            "Manual source-owned review required; lead rows cannot be "
            "automatically accepted as corpus evidence."
        )
    if any(
        "no exact title or alias match" in reason
        or "search page" in reason
        or "catalog or versions page" in reason
        or "does not identify the target title" in reason
        for reason in reasons
    ):
        return (
            "Manual source-owned review required; do not accept search results, "
            "catalog/version pages, or non-exact title matches as fallback text."
        )
    if any("source pull failed" in reason for reason in reasons):
        return (
            "Retry the source pull with backoff or inspect the source manually; "
            "leave unresolved until text passes exact-title and completeness checks."
        )
    if reasons and all("non-text evidence" in reason for reason in reasons):
        return (
            "Route through archive-all image-depth acquisition and rights review; "
            "no automatic text fallback is available."
        )
    if any("candidate endpoint was not live-ok" in reason for reason in reasons):
        return (
            "Rerun the live audit or verify the endpoint manually before considering "
            "this candidate for acquisition."
        )
    if any("candidate confidence below threshold" in reason for reason in reasons):
        return (
            "Leave unresolved unless a higher-confidence exact source is found; "
            "do not lower thresholds to force acceptance."
        )
    return (
        "Leave unresolved and record source-owned evidence only when a validated "
        "text or rights-cleared image source is identified."
    )


def _process_candidate_row(
    row: dict[str, Any],
    entries_by_id: dict[str, CorpusTargetEntry],
    manager: MetadataManager,
    data_dir: Path,
    session: requests.Session,
    *,
    min_confidence: float,
    dry_run: bool,
    already_accepted: set[str],
) -> EvidencePullResult:
    target_id = str(row.get("target_id") or "")
    title = str(row.get("title") or target_id)
    source = str(row.get("candidate_source") or "")
    url = str(row.get("candidate_url") or "")
    entry = entries_by_id.get(target_id)
    base = {
        "target_id": target_id,
        "title": title,
        "candidate_source": source,
        "candidate_url": url,
        "evidence_type": str(row.get("evidence_type") or ""),
        "live_ok": row.get("ok") if isinstance(row.get("ok"), bool) else None,
        "match_confidence": float(row.get("match_confidence") or 0),
        "dry_run": dry_run,
        "http_status": row.get("http_status"),
        "ok": row.get("ok") if isinstance(row.get("ok"), bool) else None,
        "action_taken": row.get("action_taken"),
        "evidence_note": row.get("evidence_note"),
        "lead_status": row.get("lead_status"),
        "rights_note": row.get("rights_note"),
        "acceptance_policy": row.get("acceptance_policy"),
        "review_priority": row.get("review_priority"),
        "direct_source_basis": row.get("direct_source_basis"),
        "scholarship_note": row.get("scholarship_note"),
    }
    if target_id in already_accepted:
        return EvidencePullResult(
            **base, status="skipped", reason="target already accepted"
        )
    if str(row.get("lead_status") or "") == "manual_review" or str(
        row.get("action_taken") or ""
    ).startswith("manual_review:"):
        return EvidencePullResult(
            **base,
            status="skipped",
            reason="manual-review source lead cannot be automatically accepted",
        )
    if row.get("evidence_type") != "text":
        return EvidencePullResult(
            **base,
            status="skipped",
            reason="non-text evidence is handled by image-depth acquisition",
        )
    if row.get("ok") is not True:
        return EvidencePullResult(
            **base,
            status="skipped",
            reason="candidate endpoint was not live-ok in the audit",
        )
    if float(row.get("match_confidence") or 0) < min_confidence:
        return EvidencePullResult(
            **base, status="skipped", reason="candidate confidence below threshold"
        )
    if source not in FALLBACK_TEXT_SOURCES:
        return EvidencePullResult(
            **base,
            status="skipped",
            reason="source is corroborating/catalog-only for automatic text pull",
        )
    if entry is None:
        return EvidencePullResult(
            **base, status="rejected", reason="target id is not in the active ledger"
        )

    try:
        pull = (
            _pull_wikisource_text(session, entry, url)
            if source == "Wikisource author page"
            else _pull_gutenberg_text(session, entry, url)
        )
    except Exception as exc:
        return EvidencePullResult(
            **base, status="rejected", reason=f"source pull failed: {exc}"
        )

    if not pull:
        return EvidencePullResult(
            **base, status="rejected", reason="no exact title or alias match found"
        )

    accepted_url, text = pull
    validation_error = _validate_text(entry, text)
    if validation_error:
        return EvidencePullResult(
            **base,
            status="rejected",
            reason=validation_error,
            accepted_url=accepted_url,
        )

    checksum = hashlib.sha256(text.encode("utf-8")).hexdigest()
    words = len(text.split())
    if not dry_run:
        _save_validated_text(
            manager,
            data_dir,
            entry,
            source_type=FALLBACK_TEXT_SOURCES[source],
            source_label=source,
            source_url=accepted_url,
            text=text,
            checksum=checksum,
        )
    return EvidencePullResult(
        **base,
        status="accepted",
        reason="validated fallback text acquired",
        authority_tier="fallback_text_validated",
        accepted_url=accepted_url,
        words=words,
        checksum=checksum,
    )


def _session() -> requests.Session:
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})
    return session


def _title_keys(entry: CorpusTargetEntry) -> set[str]:
    values = [entry.target_id, entry.title, *entry.aliases]
    return {normalize_title(value) for value in values if normalize_title(value)}


def _is_title_match(entry: CorpusTargetEntry, value: str) -> bool:
    candidate = normalize_title(value)
    keys = _title_keys(entry)
    return candidate in keys or any(candidate.endswith(key) for key in keys)


def _pull_wikisource_text(
    session: requests.Session, entry: CorpusTargetEntry, candidate_url: str
) -> tuple[str, str] | None:
    search_query = _query_from_url(candidate_url) or f"{entry.title} William Blake"
    response = session.get(
        "https://en.wikisource.org/w/api.php",
        params={
            "action": "query",
            "format": "json",
            "list": "search",
            "srsearch": search_query,
            "srlimit": "10",
        },
        timeout=30,
    )
    response.raise_for_status()
    rows = response.json().get("query", {}).get("search", [])
    for result in rows:
        page_title = str(result.get("title") or "")
        if not _is_title_match(entry, page_title):
            continue
        raw_response = session.get(
            f"https://en.wikisource.org/wiki/{page_title.replace(' ', '_')}",
            params={"action": "raw"},
            timeout=30,
        )
        raw_response.raise_for_status()
        text = clean_wikitext(raw_response.text)
        return (
            f"https://en.wikisource.org/wiki/{page_title.replace(' ', '_')}",
            text,
        )
    return None


def _pull_gutenberg_text(
    session: requests.Session, entry: CorpusTargetEntry, candidate_url: str
) -> tuple[str, str] | None:
    response = session.get(candidate_url, timeout=30)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    ebook_ids: list[str] = []
    for link in soup.select("li.booklink a[href*='/ebooks/'], a[href*='/ebooks/']"):
        title = " ".join(link.get_text(" ", strip=True).split())
        href = str(link.get("href") or "")
        match = re.search(r"/ebooks/(\d+)", href)
        if match and _is_title_match(entry, title):
            ebook_ids.append(match.group(1))
    for ebook_id in list(dict.fromkeys(ebook_ids)):
        for text_url in (
            f"https://www.gutenberg.org/cache/epub/{ebook_id}/pg{ebook_id}.txt",
            f"https://www.gutenberg.org/files/{ebook_id}/{ebook_id}-0.txt",
            f"https://www.gutenberg.org/files/{ebook_id}/{ebook_id}.txt",
        ):
            text_response = session.get(text_url, timeout=30)
            if text_response.status_code != 200:
                continue
            text = clean_plain_text(text_response.text)
            if _validate_text(entry, text) is None:
                return text_url, text
    return None


def _query_from_url(url: str) -> str:
    parsed = urlparse(url)
    query = parse_qs(parsed.query)
    value = query.get("search") or query.get("query")
    return value[0] if value else ""


def _validate_text(entry: CorpusTargetEntry, text: str) -> str | None:
    head_raw = text[:1000]
    if (
        "Search results" in text[:500]
        or "There were no results matching the query" in text
    ):
        return "pulled content is a search page, not a transcription"
    if (
        re.search(r"(?im)^\s*\{\{versions\b", head_raw)
        or "A typeset collection of William Blake's Poetry" in head_raw
    ):
        return "pulled content is a catalog or versions page, not a transcription"
    words = len(text.split())
    min_words = max(MIN_WORDS, FALLBACK_MIN_WORDS_BY_TARGET.get(entry.target_id, 0))
    if words < min_words:
        return f"pulled content is too short ({words} words; minimum {min_words})"
    head = " ".join(text.split()[:400])
    if not any(
        normalize_title(key) in normalize_title(head)
        for key in [entry.title, *entry.aliases]
    ):
        return "pulled content does not identify the target title near the start"
    return None


def clean_wikitext(raw: str) -> str:
    text = re.sub(r"<!--.*?-->", "", raw, flags=re.DOTALL)
    text = re.sub(r"\{\{header\b.*?\n\}\}", "", text, flags=re.DOTALL)
    text = re.sub(r"\{\{[^{}\n]*\}\}", "", text)
    text = re.sub(r"<h[1-6][^>]*>(.*?)</h[1-6]>", r"\n\1\n", text, flags=re.DOTALL)
    text = re.sub(r"</?(poem|br|p|div|span)[^>]*>", "\n", text)
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(
        r"\[\[([^][]+)\]\]", lambda match: match.group(1).split("|")[-1], text
    )
    text = re.sub(r"\[(https?://\S+)\s+([^\]]+)\]", r"\2", text)
    text = re.sub(r"\[https?://[^\]]+\]", "", text)
    return clean_plain_text(text)


def clean_plain_text(raw: str) -> str:
    lines: list[str] = []
    previous_blank = False
    for line in raw.splitlines():
        line = html.unescape(line).replace("\u200b", "").replace("\xa0", " ")
        line = re.sub(r"\s+", " ", line).strip()
        if not line:
            if lines and not previous_blank:
                lines.append("")
            previous_blank = True
            continue
        lines.append(line)
        previous_blank = False
    return "\n".join(lines).strip()


def _save_validated_text(
    manager: MetadataManager,
    data_dir: Path,
    entry: CorpusTargetEntry,
    *,
    source_type: SourceType,
    source_label: str,
    source_url: str,
    text: str,
    checksum: str,
) -> None:
    text_path = data_dir / "texts" / f"{entry.target_id}.txt"
    text_path.parent.mkdir(parents=True, exist_ok=True)
    text_path.write_text(text, encoding="utf-8")

    existing = manager.database.load_work(entry.target_id)
    if existing:
        work = existing
        work.text_content = text
        work.metadata.file_path = text_path
        work.metadata.file_size = len(text.encode("utf-8"))
        work.metadata.mime_type = "text/plain"
        work.metadata.checksum = checksum
    else:
        metadata = BlakeMetadata(
            id=entry.target_id,
            title=entry.title,
            author="William Blake",
            work_type=entry.work_type,
            creation_date=entry.creation_date,
            source=source_type,
            source_id=entry.target_id,
            source_url=source_url,
            api_source="validated_fallback_text",
            license_type=LicenseType.PUBLIC_DOMAIN,
            attribution=f"{source_label}; text by William Blake",
            usage_terms="Public-domain fallback transcription validated by exact title match and local completeness checks.",
            file_path=text_path,
            file_size=len(text.encode("utf-8")),
            mime_type="text/plain",
            checksum=checksum,
        )
        work = BlakeWork(id=entry.target_id, metadata=metadata, text_content=text)

    acquisition = {
        "target_id": entry.target_id,
        "title": entry.title,
        "authority_tier": "fallback_text_validated",
        "source": source_label,
        "source_url": source_url,
        "checksum": checksum,
        "words": len(text.split()),
        "validated_at": datetime.now().isoformat(),
        "validation": {
            "title_match": True,
            "minimum_words": MIN_WORDS,
            "non_search_result": True,
        },
    }
    work.metadata.analysis_results = dict(work.metadata.analysis_results or {})
    work.metadata.analysis_results["source_authority_tier"] = "fallback_text_validated"
    work.metadata.analysis_results["validated_fallback_text"] = acquisition
    work.text_versions.append(
        {
            "source": source_label,
            "source_url": source_url,
            "kind": "validated_fallback_text",
            "authority_tier": "fallback_text_validated",
            "checksum": checksum,
        }
    )
    _write_validated_fallback_marker(data_dir, entry.target_id, acquisition)
    manager.database.save_work(work)


def _validated_fallback_marker_path(data_dir: Path, target_id: str) -> Path:
    return data_dir / "metadata" / FALLBACK_VALIDATION_DIR / f"{target_id}.json"


def _write_validated_fallback_marker(
    data_dir: Path, target_id: str, acquisition: dict[str, Any]
) -> Path:
    marker_path = _validated_fallback_marker_path(data_dir, target_id)
    marker_path.parent.mkdir(parents=True, exist_ok=True)
    marker_path.write_text(json.dumps(acquisition, indent=2), encoding="utf-8")
    return marker_path


def load_validated_fallback_marker(
    data_dir: Path, target_id: str
) -> dict[str, Any] | None:
    marker_path = _validated_fallback_marker_path(data_dir, target_id)
    if not marker_path.exists():
        return None
    try:
        marker = json.loads(marker_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    if marker.get("authority_tier") != "fallback_text_validated":
        return None
    if not marker.get("checksum"):
        return None
    return marker


def apply_validated_fallback_marker(data_dir: Path, work: BlakeWork) -> bool:
    marker = load_validated_fallback_marker(data_dir, work.id)
    if marker is None:
        return False

    text_path = data_dir / "texts" / f"{work.id}.txt"
    text = work.text_content
    if text_path.exists():
        text = text_path.read_text(encoding="utf-8")
    if not text:
        return False

    checksum = hashlib.sha256(text.encode("utf-8")).hexdigest()
    if checksum != marker.get("checksum"):
        return False

    work.text_content = text
    work.metadata.file_path = text_path
    work.metadata.file_size = len(text.encode("utf-8"))
    work.metadata.mime_type = "text/plain"
    work.metadata.checksum = checksum
    work.metadata.analysis_results = dict(work.metadata.analysis_results or {})
    work.metadata.analysis_results["source_authority_tier"] = "fallback_text_validated"
    work.metadata.analysis_results["validated_fallback_text"] = marker

    if not any(
        version.get("kind") == "validated_fallback_text"
        and version.get("checksum") == checksum
        for version in work.text_versions
    ):
        work.text_versions.append(
            {
                "source": marker.get("source"),
                "source_url": marker.get("source_url"),
                "kind": "validated_fallback_text",
                "authority_tier": "fallback_text_validated",
                "checksum": checksum,
            }
        )
    return True
