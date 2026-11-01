"""Physical metadata location controls beyond package-byte verification."""

import csv
import shutil

import pytest

from tests.installed_distribution_fixtures import distribution, invoke, record


@pytest.mark.parametrize("mutation", ["unlisted", "decoy"])
def test_metadata_file_membership_and_location_must_agree(tmp_path, mutation) -> None:
    _, info = distribution(tmp_path)
    path = info / "RECORD"
    with path.open(newline="") as stream:
        rows = list(csv.reader(stream))
    if mutation == "unlisted":
        rows = [row for row in rows if not row[0].endswith("/METADATA")]
    else:
        decoy = tmp_path / "decoy.dist-info/METADATA"
        decoy.parent.mkdir()
        decoy.write_text("Name: wrong\nVersion: 9\n")
        for row in rows:
            if row[0].endswith("/METADATA"):
                row[0] = decoy.relative_to(tmp_path).as_posix()
    with path.open("w", newline="") as stream:
        csv.writer(stream).writerows(rows)
    result = invoke(tmp_path)
    assert result.returncode != 0
    assert "EvidenceError: installed_metadata" in result.stderr


@pytest.mark.parametrize("name", ["METADATA", "direct_url.json", "RECORD"])
def test_equal_normalized_decoy_is_not_the_distribution_file(tmp_path, name) -> None:
    _, info = distribution(tmp_path)
    for item in ("METADATA", "direct_url.json"):
        path = info / item
        path.write_bytes(
            path.read_bytes().rstrip(b"\r\n").replace(b"\n", b"\r\n") + b"\r\n"
        )
    record(tmp_path, info)
    path = info / "RECORD"
    with path.open(newline="") as stream:
        rows = list(csv.reader(stream))
    decoy = tmp_path / "decoy.dist-info" / name
    decoy.parent.mkdir()
    for row in rows:
        if row[0] == info.name + "/" + name:
            row[0] = decoy.relative_to(tmp_path).as_posix()
    with path.open("w", newline="") as stream:
        csv.writer(stream).writerows(rows)
    actual = (info / name).read_bytes()
    decoy.write_bytes(actual.replace(b"\r\n", b"\n"))
    assert actual != decoy.read_bytes()
    result = invoke(tmp_path)
    assert result.returncode != 0
    assert "EvidenceError: installed_metadata" in result.stderr


def test_multiple_normal_distribution_directories_are_ambiguous(tmp_path) -> None:
    _ = distribution(tmp_path)
    other = tmp_path / "sample_sdk-9.9.9.dist-info"
    other.mkdir()
    (other / "METADATA").write_text("Name: sample-sdk\nVersion: 9.9.9\n")
    shutil.copyfile(tmp_path / "sample_sdk-1.2.3.dist-info/RECORD", other / "RECORD")
    result = invoke(tmp_path)
    assert result.returncode != 0
    assert "EvidenceError: installed_" in result.stderr


def test_empty_direct_url_is_a_named_metadata_refusal(tmp_path) -> None:
    _, info = distribution(tmp_path)
    (info / "direct_url.json").write_bytes(b"")
    result = invoke(tmp_path)
    assert result.returncode != 0
    assert "EvidenceError: installed_metadata" in result.stderr
