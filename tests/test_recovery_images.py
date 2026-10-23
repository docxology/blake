from __future__ import annotations

import hashlib
import io
from pathlib import Path

import pytest

from blake.recovery import (
    CopyRecord,
    recover_images,
)

from .recovery_fixtures import local_http
from tests import recovery_fixtures

saved_sources = recovery_fixtures.saved_sources


def test_images_when_cached_bytes_decode_records_success(tmp_path: Path) -> None:
    from PIL import Image

    image_path = tmp_path / "images/control.P1.300.jpg"
    image_path.parent.mkdir()
    Image.new("RGB", (12, 8), "red").save(image_path)
    copy = CopyRecord(
        document_id="control",
        copy_id="control",
        work_id="control",
        title="Control",
        source_path="source.xml",
        source_sha256="a" * 64,
        object_ids=("control.P1",),
    )

    result, files = recover_images(tmp_path, [copy], offline=True, enabled=True)

    assert result.status == "complete"
    assert result.expected == result.downloaded == 1
    assert files[0].sha256 == hashlib.sha256(image_path.read_bytes()).hexdigest()


def test_images_when_cached_file_is_html_reports_failure(tmp_path: Path) -> None:
    path = tmp_path / "images/control.P1.300.jpg"
    path.parent.mkdir()
    path.write_bytes(b"<html>failure</html>")
    copy = CopyRecord(
        document_id="control",
        copy_id="control",
        work_id="control",
        title="Control",
        source_path="source.xml",
        source_sha256="a" * 64,
        object_ids=("control.P1",),
    )

    result, files = recover_images(tmp_path, [copy], offline=True, enabled=True)

    assert result.status == "incomplete"
    assert result.downloaded == 0
    assert len(result.failures) == 1
    assert not files


def test_images_when_http_provider_fails_stops_after_three_objects(
    tmp_path: Path,
) -> None:
    copy = CopyRecord(
        document_id="control",
        copy_id="control",
        work_id="control",
        title="Control",
        source_path="source.xml",
        source_sha256="a" * 64,
        object_ids=tuple(f"control.P{i}" for i in range(5)),
    )
    with local_http(b"provider failed", status=500) as url:
        result, files = recover_images(
            tmp_path, [copy], offline=False, enabled=True, image_base_url=url
        )

    assert result.downloaded == 0
    assert len(result.failures) == 3
    assert result.unattempted == ("control.P3", "control.P4")
    assert not files
    assert not list(tmp_path.rglob("*.jpg"))


def test_images_when_source_id_has_uppercase_uses_actual_lowercase_filename(
    tmp_path: Path,
) -> None:
    from PIL import Image

    body = io.BytesIO()
    Image.new("RGB", (5, 7), "blue").save(body, format="JPEG")
    copy = CopyRecord(
        document_id="Control",
        copy_id="Control",
        work_id="Control",
        title="Control",
        source_path="source.xml",
        source_sha256="a" * 64,
        object_ids=("Control.P1",),
    )
    with local_http(
        body.getvalue(), expected_path="/source/images/control.p1.300.jpg"
    ) as url:
        result, receipts = recover_images(
            tmp_path, [copy], offline=False, enabled=True, image_base_url=url
        )

    assert result.downloaded == result.expected == 1
    assert receipts[0].source_url == url + "/images/control.p1.300.jpg"
    assert (tmp_path / "images/Control.P1.300.jpg").read_bytes() == body.getvalue()


@pytest.mark.parametrize(
    "suffix,expected_dpi",
    [("Control.P1.300.jpg", "300"), ("control.p1.100.jpg", "100")],
)
def test_images_when_provider_has_case_or_resolution_exception_records_actual_source(
    tmp_path: Path, suffix: str, expected_dpi: str
) -> None:
    from PIL import Image

    buffer = io.BytesIO()
    Image.new("RGB", (5, 7), "blue").save(buffer, format="JPEG")
    copy = CopyRecord(
        document_id="Control",
        copy_id="Control",
        work_id="Control",
        title="Control",
        source_path="source.xml",
        source_sha256="a" * 64,
        object_ids=("Control.P1",),
    )
    with local_http(buffer.getvalue(), expected_path="/source/images/" + suffix) as url:
        result, receipts = recover_images(
            tmp_path, [copy], offline=False, enabled=True, image_base_url=url
        )

    assert result.downloaded == 1
    assert result.resolution_counts == {expected_dpi: 1}
    assert receipts[0].source_url == url + "/images/" + suffix
    assert receipts[0].path.endswith("." + expected_dpi + ".jpg")
    assert result.lower_resolution_ids == (
        ("Control.P1",) if expected_dpi == "100" else ()
    )


def test_images_when_exhaustive_attempts_every_object_after_failures(
    tmp_path: Path,
) -> None:
    copy = CopyRecord(
        document_id="control",
        copy_id="control",
        work_id="control",
        title="Control",
        source_path="source.xml",
        source_sha256="a" * 64,
        object_ids=tuple(f"control.P{i}" for i in range(4)),
    )
    with local_http(b"missing image", status=404) as url:
        result, _ = recover_images(
            tmp_path,
            [copy],
            offline=False,
            enabled=True,
            image_base_url=url,
            workers=2,
            max_consecutive_failures=None,
        )

    assert len(result.failures) == 4
    assert not result.unattempted
