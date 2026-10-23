"""Register retained documents in the existing metadata API without losing prior work."""

from __future__ import annotations

from pathlib import Path


from .recovery_models import RIGHTS, RecoveryError
from .recovery_integrity import verify_recovery


def register_recovery(data_dir: Path) -> int:
    """Register retained source documents for the existing corpus API, preserving other works."""
    from .metadata.database import MetadataDatabase
    from .models import BlakeImage, BlakeMetadata, BlakeWork, SourceType, WorkType
    from .corpus.targets import load_corpus_target

    manifest = verify_recovery(data_dir)
    root = data_dir / "recovery"
    database = MetadataDatabase(data_dir / "metadata/metadata.db")
    receipts = {receipt.path: receipt for receipt in manifest.files}
    target_types = {
        archive_id.casefold(): entry.work_type
        for entry in load_corpus_target().entries
        for archive_id in entry.source_hints.get("blake_archive", [])
    }
    for copy in manifest.copies:
        identifier = f"recovered--{copy.document_id}"
        previous = database.load_work(identifier)
        provenance = {
            "document_id": copy.document_id,
            "source_sha256": copy.source_sha256,
            "source_path": copy.source_path,
            "text_role": copy.text_role,
            "archive_commit": manifest.archive_commit,
        }
        if previous is not None:
            if previous.metadata.analysis_results.get("recovery") != provenance:
                raise RecoveryError(
                    f"Existing work has different provenance; preserved: {identifier}"
                )
        source = receipts[copy.source_path]
        text_path = (root / copy.text_path).resolve() if copy.text_path else None
        images = []
        for object_id in copy.object_ids:
            relative = next(
                (
                    f"images/{object_id}.{dpi}.jpg"
                    for dpi in (300, 100)
                    if f"images/{object_id}.{dpi}.jpg" in receipts
                ),
                None,
            )
            if relative is not None:
                images.append(
                    BlakeImage(
                        id=f"{identifier}:{object_id}",
                        metadata_id=identifier,
                        title=f"{copy.title} ({object_id})",
                        file_path=(root / relative).resolve(),
                        dpi=int(relative.rsplit(".", 2)[1]),
                        original_url=receipts[relative].source_url,
                    )
                )
        metadata = BlakeMetadata(
            id=identifier,
            title=copy.title,
            source=SourceType.BLAKE_ARCHIVE,
            source_id=copy.copy_id,
            source_url=source.source_url,
            work_type=WorkType(target_types.get(copy.work_id, WorkType.MANUSCRIPT)),
            parent_work=copy.work_id,
            usage_terms=RIGHTS,
            file_path=text_path,
            analysis_results={
                "recovery": provenance,
                "image_depth": {
                    "expected_object_count": len(copy.object_ids),
                    "resolved_object_count": len(copy.object_ids),
                    "downloaded_image_count": len(images),
                    "image_depth_status": "complete"
                    if len(images) == len(copy.object_ids)
                    and all(image.dpi == 300 for image in images)
                    else "partial"
                    if images
                    else "missing",
                },
            },
        )
        if previous is not None:
            previous.metadata.analysis_results.update(metadata.analysis_results)
            metadata = previous.metadata.model_copy(
                update={"work_type": metadata.work_type, "file_path": text_path}
            )
        work = BlakeWork(
            id=identifier,
            metadata=metadata,
            images=images,
            text_content=text_path.read_text(encoding="utf-8") if text_path else None,
        )
        if previous is not None:
            work = previous.model_copy(
                update={
                    "metadata": metadata,
                    "images": images,
                    "text_content": work.text_content,
                }
            )
        database.save_work(work)
    return len(manifest.copies)
