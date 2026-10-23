from __future__ import annotations

import hashlib
import io
import json
import tarfile
from pathlib import Path

import pytest
from click.testing import CliRunner

from blake.recovery import recover_corpus
from blake.recovery_catalog import ERDMAN_COMMIT
from blake.text_search import Query
from blake.text_search.cli import main
from blake.text_search.models import SearchError
from blake.text_search.recovered import build_recovered_search, open_recovered_search
from tests.recovery_fixtures import COMMIT, seed_sources


@pytest.fixture
def captured(tmp_path: Path) -> Path:
    data = seed_sources(tmp_path)
    recover_corpus(data, commit=COMMIT, offline=True, images=False)
    return data


def test_projection_keeps_primary_readings_separate_from_raw_and_editorial(
    captured: Path,
) -> None:
    original = captured / "recovery/search.sqlite"
    before = hashlib.sha256(original.read_bytes()).hexdigest()

    snapshot = build_recovered_search(captured)

    assert snapshot.manifest.passages_by_plane == {"reading": 4, "xml": 6, "erdman": 3}
    assert snapshot.manifest.passages_by_role == {
        "primary": 3,
        "unverified": 7,
        "editorial": 3,
    }
    assert snapshot.index.search(Query(text="state")).total_occurrences == 2
    raw = snapshot.index.search(
        Query(
            text="unattested", scope="exploratory", author_id=None, source_plane="xml"
        )
    )
    assert raw.total_occurrences == 1
    assert raw.blake_primary_occurrences == 0
    assert raw.hits[0].passage.text_role == "unverified"
    mixed = snapshot.index.search(
        Query(
            text="Preface", scope="exploratory", author_id=None, source_plane="erdman"
        )
    )
    assert mixed.total_occurrences == 1
    assert mixed.blake_primary_occurrences == 0
    assert hashlib.sha256(original.read_bytes()).hexdigest() == before
    assert snapshot.directory.is_relative_to(captured / "search/recovered")
    assert snapshot.index.read_only


def test_projection_rerun_reuses_the_same_verified_snapshot(captured: Path) -> None:
    first = build_recovered_search(captured)
    second = build_recovered_search(captured)
    assert second.directory == first.directory
    assert second.manifest == first.manifest
    assert (
        open_recovered_search(captured).manifest.index.sha256
        == first.manifest.index.sha256
    )


@pytest.mark.parametrize(
    "relative",
    [
        "passages.jsonl",
        "texts/archive/mhh.a.txt",
        "search.sqlite",
        f"snapshot/{COMMIT}/works/mhh.a.xml",
    ],
)
def test_changed_captured_input_refuses_new_projection(
    captured: Path, relative: str
) -> None:
    path = captured / "recovery" / relative
    path.write_bytes(path.read_bytes() + b"changed")
    with pytest.raises(SearchError, match="checksum"):
        build_recovered_search(captured)
    assert not (captured / "search/recovered").exists()


def test_changed_derived_index_is_not_silently_rebuilt(captured: Path) -> None:
    snapshot = build_recovered_search(captured)
    snapshot.index.path.write_bytes(snapshot.index.path.read_bytes() + b"changed")
    with pytest.raises(SearchError, match="checksum"):
        open_recovered_search(captured)
    with pytest.raises(SearchError, match="checksum"):
        build_recovered_search(captured)


def test_index_membership_receipt_must_match_real_sqlite(captured: Path) -> None:
    snapshot = build_recovered_search(captured)
    path = snapshot.directory / "search-manifest.json"
    metadata = json.loads(path.read_text())
    metadata["passages"] += 1
    path.write_text(json.dumps(metadata))
    with pytest.raises(SearchError, match="membership"):
        open_recovered_search(captured)


def test_private_output_cannot_escape_through_symlink(
    captured: Path, tmp_path: Path
) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    (captured / "search").symlink_to(outside, target_is_directory=True)
    with pytest.raises(ValueError):
        build_recovered_search(captured)
    assert list(outside.iterdir()) == []


def test_cli_private_entry_point_builds_queries_and_refuses_generic_rebuild(
    captured: Path,
) -> None:
    runner = CliRunner()
    root = ["--data-dir", str(captured)]
    missing = runner.invoke(main, [*root, "--recovered", "query", "state"])
    assert missing.exit_code != 0
    built = runner.invoke(main, [*root, "build-recovered"])
    assert built.exit_code == 0, built.output
    primary = runner.invoke(main, [*root, "--recovered", "query", "state"])
    assert primary.exit_code == 0, primary.output
    payload = json.loads(primary.output)
    assert payload["total_occurrences"] == payload["blake_primary_occurrences"] == 2
    assert len(payload["captured_manifest_sha256"]) == 64
    exploratory = runner.invoke(
        main,
        [
            *root,
            "--recovered",
            "query",
            "Preface",
            "--scope",
            "exploratory",
            "--plane",
            "erdman",
        ],
    )
    assert exploratory.exit_code == 0, exploratory.output
    assert json.loads(exploratory.output)["blake_primary_occurrences"] == 0
    refused = runner.invoke(
        main, [*root, "--recovered", "build", str(captured / "recovery/passages.jsonl")]
    )
    assert refused.exit_code != 0
    conflict = runner.invoke(
        main,
        [
            *root,
            "--recovered",
            "--index",
            str(captured / "recovery/search.sqlite"),
            "coverage",
        ],
    )
    assert conflict.exit_code != 0


def test_empty_erdman_page_is_retained_but_not_counted_as_searchable(
    tmp_path: Path,
) -> None:
    data = seed_sources(tmp_path)
    raw = data / "recovery/sources/erdman/pages.json"
    pages = json.loads(raw.read_text())
    pages.append({"id": 3, "page_id": "blank", "contents": "  "})
    raw.write_text(json.dumps(pages))
    recover_corpus(data, commit=COMMIT, offline=True, images=False)
    snapshot = build_recovered_search(data)
    assert snapshot.manifest.source_counts.erdman_page_records == 4
    assert snapshot.manifest.source_counts.erdman_searchable_pages == 3
    assert snapshot.manifest.empty_erdman_page_ids == ("blank",)


def test_full_erdman_xml_parts_remain_editorial_raw_sources(tmp_path: Path) -> None:
    data = seed_sources(tmp_path)
    live = data / "recovery/sources/live"
    live.mkdir()
    for kind, rows in {
        "work": [{"bad_id": "mhh"}],
        "copy": [{"bad_id": "mhh.a"}],
        "object": [{"desc_id": "mhh.a.01", "dbi": "mhh.a.P1"}],
    }.items():
        (live / f"{kind}-inventory.json").write_text(json.dumps({"results": rows}))
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as archive:
        for n in range(1, 5):
            text = f"<TEI><note>ERDMANANNOTATION{n}</note></TEI>".encode()
            info = tarfile.TarInfo(f"erdman-{ERDMAN_COMMIT}/data/erd{n}.xml")
            info.size = len(text)
            archive.addfile(info, io.BytesIO(text))
    (data / f"recovery/sources/erdman-{ERDMAN_COMMIT}.tar.gz").write_bytes(
        buffer.getvalue()
    )
    recover_corpus(data, commit=COMMIT, offline=True, images=False, full=True)
    snapshot = build_recovered_search(data)
    assert snapshot.manifest.source_counts.erdman_xml_parts == 4
    assert snapshot.manifest.source_counts.raw_xml_documents == 10
    result = snapshot.index.search(
        Query(
            text="ERDMANANNOTATION1",
            scope="exploratory",
            author_id=None,
            source_plane="xml",
        )
    )
    assert result.total_occurrences == 1
    assert result.blake_primary_occurrences == 0
    assert result.hits[0].passage.text_role == "editorial"


@pytest.mark.parametrize(
    "field",
    [
        "role",
        "plane",
        "source_counts",
        "input_identity",
        "missing_input",
        "duplicate_input",
        "omitted_pages",
        "archive_identity",
    ],
)
def test_metadata_only_tamper_is_not_accepted_as_verified_coverage(
    captured: Path, field: str
) -> None:
    snapshot = build_recovered_search(captured)
    path = snapshot.directory / "search-manifest.json"
    metadata = json.loads(path.read_text())
    if field == "role":
        metadata["passages_by_role"]["primary"] = 999
    elif field == "plane":
        metadata["passages_by_plane"]["xml"] = 999
    elif field == "source_counts":
        metadata["source_counts"]["archive_documents"] = 999
    elif field == "input_identity":
        metadata["inputs"][0]["sha256"] = "0" * 64
    elif field == "missing_input":
        metadata["inputs"].pop()
    elif field == "duplicate_input":
        metadata["inputs"].append(metadata["inputs"][0])
    elif field == "omitted_pages":
        metadata["empty_erdman_page_ids"] = ["not-a-page"]
    else:
        metadata["archive_commit"] = "b" * 40
    path.write_text(json.dumps(metadata))
    with pytest.raises(SearchError):
        open_recovered_search(captured)
