"""Apply narrowly reviewed transcription rules only to their exact source bytes."""

from __future__ import annotations

import hashlib
from pathlib import Path
from xml.etree import ElementTree as ET

from pydantic import BaseModel, ConfigDict

from .transcription import TranscribedBlock, extract_primary_blocks


class AnnotationReview(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    review_id: str
    source_sha256: str
    line_locator: str
    original_prefix: str
    annotation_xml: str
    reason: str
    source_url: str
    markup_reference: str


class TranscriptionReviews(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    reviews: tuple[AnnotationReview, ...]


def reviewed_blocks(
    source: bytes, reviews_path: Path | None = None
) -> tuple[tuple[TranscribedBlock, ...], tuple[str, ...]]:
    """Exclude reviewed editorial annotations while preserving source originals and tails."""
    reviews_path = (
        reviews_path
        or Path(__file__).with_name("corpus") / "transcription_reviews.json"
    )
    reviews = TranscriptionReviews.model_validate_json(reviews_path.read_bytes())
    digest = hashlib.sha256(source).hexdigest()
    selected = [review for review in reviews.reviews if review.source_sha256 == digest]
    xml = source.decode("utf-8-sig")
    if not selected:
        return extract_primary_blocks(xml), ()
    root = ET.fromstring(xml)
    applied = []
    for review in selected:
        lines = [
            line for line in root.iter("l") if line.get("n") == review.line_locator
        ]
        if len(lines) != 1:
            raise ValueError(f"Reviewed line is not unique: {review.review_id}")
        line = lines[0]
        prefix = line.text or ""
        matched = False
        for index, child in enumerate(list(line)):
            if (
                child.tag == "choice"
                and ET.tostring(child, encoding="unicode").strip()
                == review.annotation_xml
            ):
                if matched or prefix != review.original_prefix:
                    raise ValueError(
                        f"Reviewed original context differs: {review.review_id}"
                    )
                tail = child.tail or ""
                preceding = list(line)[:index]
                if preceding:
                    preceding[-1].tail = (preceding[-1].tail or "") + tail
                else:
                    line.text = (line.text or "") + tail
                line.remove(child)
                matched = True
                continue
            prefix += "".join(child.itertext()) + (child.tail or "")
        if not matched:
            raise ValueError(f"Reviewed annotation is absent: {review.review_id}")
        applied.append(review.review_id)
    return extract_primary_blocks(ET.tostring(root, encoding="unicode")), tuple(applied)
