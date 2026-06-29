from __future__ import annotations

from typing import Any

from .models import BlakeWork, SourceType


def enum_value(value: Any) -> str:
    return str(getattr(value, "value", value) or "")


def source_authority_tier(work: BlakeWork) -> str:
    analysis = work.metadata.analysis_results or {}
    tier = analysis.get("source_authority_tier")
    if tier:
        return str(tier)
    if enum_value(work.metadata.source) == SourceType.BLAKE_ARCHIVE.value:
        return "archive_primary"
    if analysis.get("validated_fallback_text"):
        return "fallback_text_validated"
    return "corroborating_or_legacy"


def rights_disposition_for_tier(authority_tier: str) -> str:
    if authority_tier == "archive_primary":
        return "exclude_raw_source_materials_from_public_bundle"
    if authority_tier == "fallback_text_validated":
        return "conditional_corroboration_required"
    return "review_before_public_redistribution"


def work_provenance(work: BlakeWork) -> dict[str, Any]:
    analysis = work.metadata.analysis_results or {}
    fallback = analysis.get("validated_fallback_text") or {}
    authority_tier = source_authority_tier(work)
    checksum = (
        work.metadata.checksum
        or fallback.get("checksum")
        or analysis.get("checksum")
        or None
    )
    source_url = (
        work.metadata.source_url
        or fallback.get("source_url")
        or fallback.get("accepted_url")
        or None
    )
    return {
        "source_url": source_url,
        "source_id": work.metadata.source_id,
        "source": enum_value(work.metadata.source),
        "source_authority_tier": authority_tier,
        "checksum": checksum,
        "run_id": analysis.get("run_id") or analysis.get("corpus_run_id"),
        "rights_disposition": analysis.get("rights_disposition")
        or rights_disposition_for_tier(authority_tier),
        "license_type": enum_value(work.metadata.license_type),
        "attribution": work.metadata.attribution,
        "usage_terms": work.metadata.usage_terms,
    }


def manifest_context_for_work(
    work: BlakeWork, manifest: dict[str, Any] | None
) -> dict[str, Any]:
    if not manifest:
        return {}
    target_id = None
    work_record = None
    for row in manifest.get("work_records") or []:
        if str(row.get("id") or "") == work.id:
            work_record = row
            target_id = row.get("target_id")
            break
    target_record = None
    if target_id:
        for row in manifest.get("target_records") or []:
            if str(row.get("target_id") or "") == str(target_id):
                target_record = row
                break
    return {
        "target_id": target_id,
        "target_title": (target_record or {}).get("title"),
        "coverage_status": (target_record or {}).get("status"),
        "coverage_notes": (target_record or {}).get("notes") or [],
        "source_authority_tier": (work_record or {}).get("source_authority_tier"),
        "has_text": (work_record or {}).get("has_text"),
        "has_images": (work_record or {}).get("has_images"),
        "image_count": (work_record or {}).get("image_count"),
    }
