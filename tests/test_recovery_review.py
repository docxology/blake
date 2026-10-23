from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from blake.recovery_review import reviewed_blocks


def annotation_control(tmp_path: Path) -> tuple[bytes, Path]:
    source = b'<bad><phystext><l n="control.1">Original Esq<hi>re</hi><choice><reg>Esquire</reg></choice></l></phystext></bad>'
    path = tmp_path / "reviews.json"
    path.write_text(
        json.dumps(
            {
                "reviews": [
                    {
                        "review_id": "synthetic-annotation",
                        "source_sha256": hashlib.sha256(source).hexdigest(),
                        "line_locator": "control.1",
                        "original_prefix": "Original Esqre",
                        "annotation_xml": "<choice><reg>Esquire</reg></choice>",
                        "reason": "Synthetic control",
                        "source_url": "https://example.org/control",
                        "markup_reference": "https://example.org/markup",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    return source, path


def test_review_when_exact_bytes_match_retains_original_once(tmp_path: Path) -> None:
    source, path = annotation_control(tmp_path)

    blocks, reviews = reviewed_blocks(source, path)

    assert [(block.locator, block.text) for block in blocks] == [
        ("control.1", "Original Esqre")
    ]
    assert reviews == ("synthetic-annotation",)


def test_review_when_source_bytes_change_does_not_apply_rule(tmp_path: Path) -> None:
    source, path = annotation_control(tmp_path)

    with pytest.raises(ValueError, match="lacks an original reading"):
        reviewed_blocks(source.replace(b"Original", b"Changed"), path)


@pytest.mark.parametrize(
    "field,value",
    [
        ("original_prefix", "wrong context"),
        ("line_locator", "missing"),
        ("annotation_xml", "<choice/>"),
    ],
)
def test_review_when_review_context_is_wrong_refuses(
    tmp_path: Path, field: str, value: str
) -> None:
    source, path = annotation_control(tmp_path)
    reviews = json.loads(path.read_text())
    reviews["reviews"][0][field] = value
    path.write_text(json.dumps(reviews), encoding="utf-8")

    with pytest.raises(ValueError):
        reviewed_blocks(source, path)
