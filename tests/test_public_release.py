import hashlib
import json
import zipfile
from pathlib import Path

from blake.corpus.public_release import (
    PublicReleaseAsset,
    _rights_gate_violations,
    write_public_release_package,
    write_public_release_preflight,
)


def _write_file(path: Path, content: str = "") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _write_png(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(
        bytes.fromhex(
            "89504E470D0A1A0A0000000D49484452000000010000000108060000001F15C489"
            "0000000A49444154789C6360000002000154A24F5D0000000049454E44AE426082"
        )
    )


def _seed_public_release_fixture(
    root: Path, *, blocked_reference: bool = False
) -> None:
    _write_file(root / "LICENSE", "MIT")
    _write_file(root / "README.md", "Blake public release fixture")
    _write_file(
        root / "pyproject.toml",
        'Repository = "https://github.com/docxology/blake"\nHomepage = "https://github.com/docxology/blake"\n',
    )
    _write_file(root / "run_all.py", "print('run')\n")
    _write_file(root / "blake_viewer.py", "print('viewer')\n")
    _write_file(root / "blake" / "__init__.py", "__version__ = '0.1.0'\n")
    _write_file(root / "blake" / "cli.py", "print('cli')\n")
    _write_file(root / "manuscript_tools" / "figures.py", "FIGURES = []\n")
    _write_file(root / "scripts" / "acquire_missing_texts.py", "TARGETS = []\n")
    _write_file(
        root / "tests" / "placeholder_test.py",
        "def test_placeholder():\n    assert True\n",
    )
    _write_file(
        root / "analysis_output" / "corpus_manifest.json",
        json.dumps(
            {
                "target_records": [
                    {
                        "target_id": "bb203",
                        "title": "Tiriel",
                        "matched_source_ids": ["blake_archive:bb203"],
                    }
                ]
            }
        ),
    )
    _write_file(
        root / "analysis_output" / "data" / "source_audit.json",
        json.dumps({"status": "ok", "candidate_count": 1}),
    )
    _write_file(
        root / "analysis_output" / "analysis" / "analysis_summary.json",
        json.dumps({"status": "completed"}),
    )
    _write_file(
        root / "analysis_output" / "reports" / "private_release_preflight.json",
        json.dumps({"status": "none"}),
    )
    _write_file(
        root / "analysis_output" / "visualizations" / "visualization_summary.json",
        json.dumps({"datasets": ["target_coverage_matrix"]}),
    )
    _write_file(
        root / "output" / "data" / "manuscript_variables.json",
        json.dumps({"WORKS_PRESENT": 1}),
    )
    _write_png(root / "output" / "cover" / "cover_blakean.png")
    _write_png(root / "output" / "figures" / "target_coverage_matrix.png")
    _write_file(
        root / "blake_data" / "texts" / "bb203.txt",
        "Tiriel\nvalidated validated validated",
    )
    _write_file(
        root / "blake_data" / "metadata" / "fallback_text_validations" / "bb203.json",
        json.dumps(
            {
                "target_id": "bb203",
                "title": "Tiriel",
                "authority_tier": "fallback_text_validated",
                "source": "Wikisource author page",
                "source_url": "https://en.wikisource.org/wiki/Tiriel",
                "checksum": hashlib.sha256(
                    "Tiriel\nvalidated validated validated".encode("utf-8")
                ).hexdigest(),
                "words": 4,
                "validated_at": "2026-06-27T00:00:00",
                "validation": {
                    "title_match": True,
                    "minimum_words": 100,
                    "non_search_result": True,
                },
            }
        ),
    )

    if blocked_reference:
        _write_file(
            root / "analysis_output" / "data" / "source_audit.json",
            json.dumps(
                {
                    "status": "ok",
                    "candidate_count": 1,
                    "reference": "output/figures/all_acquired_images_mosaic.png",
                }
            ),
        )


def test_public_release_preflight_reports_ready(tmp_path):
    _seed_public_release_fixture(tmp_path)

    report = write_public_release_preflight(
        tmp_path,
        output_dir=tmp_path / "analysis_output",
        data_dir=tmp_path / "blake_data",
        release_dir=tmp_path / "analysis_output" / "releases" / "public_release",
    )

    assert report["status"] == "ready"
    assert report["corroborated_fallback_target_count"] == 1
    assert report["corroboration"]["validated_targets"][0]["status"] == "ready"
    target = report["corroboration"]["validated_targets"][0]
    assert target["validated_source"]["authority_tier"] == "fallback_text_validated"
    assert target["validated_source"]["license_or_terms"] == "not recorded"
    assert target["validated_source"]["reviewer_note"]
    assert target["validated_source"]["text_bearing"] is True
    assert target["corroborating_sources"][0]["evidence_role"]
    assert "text_bearing" in target["corroborating_sources"][0]
    assert report["manifest"]["status"] == "ready"
    assert all(
        asset["decision_reason"] for asset in report["manifest"]["included_assets"]
    )
    assert report["manifest"]["github_release"]["tag_name"] == "v0.1.0"
    assert (
        report["manifest"]["zenodo_metadata"]["metadata"]["upload_type"] == "software"
    )


def test_public_release_package_writes_archive_and_metadata(tmp_path):
    _seed_public_release_fixture(tmp_path)
    release_dir = tmp_path / "analysis_output" / "releases" / "public_release"

    package = write_public_release_package(
        tmp_path,
        output_dir=tmp_path / "analysis_output",
        data_dir=tmp_path / "blake_data",
        release_dir=release_dir,
    )

    assert package["status"] == "ready"
    archive_path = Path(package["archive_path"])
    manifest_path = Path(package["manifest_path"])
    github_notes = Path(package["github_release_notes_path"])
    zenodo_path = Path(package["zenodo_metadata_path"])
    citation_path = Path(package["citation_path"])
    checksums_path = Path(package["checksums_path"])

    assert archive_path.exists()
    assert manifest_path.exists()
    assert github_notes.exists()
    assert zenodo_path.exists()
    assert citation_path.exists()
    assert checksums_path.exists()

    with zipfile.ZipFile(archive_path) as zf:
        names = set(zf.namelist())

    assert "README.md" in names
    assert "output/cover/cover_blakean.png" in names
    assert "analysis_output/corpus_manifest.json" in names


def test_corpus_payload_dirs_are_never_bundled(tmp_path):
    """Rights-gated corpus payloads (exports + data) must not enter the bundle even
    though they are .json under analysis_output. Regression for the transcription leak."""
    _seed_public_release_fixture(tmp_path)
    _write_file(
        tmp_path
        / "analysis_output"
        / "exports"
        / "json"
        / "blake_export_x"
        / "blake_works.json",
        json.dumps([{"title": "Tiriel", "text_content": "x" * 500_000}]),
    )

    package = write_public_release_package(
        tmp_path,
        output_dir=tmp_path / "analysis_output",
        data_dir=tmp_path / "blake_data",
        release_dir=tmp_path / "analysis_output" / "releases" / "public_release",
    )

    assert package["status"] == "ready"
    archive_path = Path(package["archive_path"])
    with zipfile.ZipFile(archive_path) as zf:
        names = set(zf.namelist())
    assert not any(name.startswith("analysis_output/exports/") for name in names)
    assert not any(name.startswith("analysis_output/data/") for name in names)
    assert not any(name.endswith("blake_works.json") for name in names)


def test_content_leak_absolute_home_path_excluded(tmp_path):
    """A generated artifact carrying an absolute local path is dropped from the bundle."""
    _seed_public_release_fixture(tmp_path)
    _write_file(
        tmp_path / "analysis_output" / "reports" / "leaky_report.json",
        # Built by concatenation so this test's own source does not contain the
        # literal absolute-path pattern (which the all-roots scanner would flag).
        json.dumps({"path": "/Users/" + "someone/projects/blake/output/cover.png"}),
    )

    report = write_public_release_preflight(
        tmp_path,
        output_dir=tmp_path / "analysis_output",
        data_dir=tmp_path / "blake_data",
        release_dir=tmp_path / "analysis_output" / "releases" / "public_release",
    )

    included = {a["source_path"] for a in report["manifest"]["included_assets"]}
    excluded = {a["source_path"]: a for a in report["manifest"]["excluded_assets"]}
    assert "analysis_output/reports/leaky_report.json" not in included
    assert (
        excluded["analysis_output/reports/leaky_report.json"]["matched_rule"]
        == "content-leak-scan"
    )


def test_content_leak_large_text_payload_excluded(tmp_path):
    """A generated JSON embedding a large text field is dropped from the bundle."""
    _seed_public_release_fixture(tmp_path)
    _write_file(
        tmp_path / "analysis_output" / "visualizations" / "big_text.json",
        json.dumps({"body": "y" * 50_000}),
    )

    report = write_public_release_preflight(
        tmp_path,
        output_dir=tmp_path / "analysis_output",
        data_dir=tmp_path / "blake_data",
        release_dir=tmp_path / "analysis_output" / "releases" / "public_release",
    )

    excluded = {a["source_path"]: a for a in report["manifest"]["excluded_assets"]}
    assert "analysis_output/visualizations/big_text.json" in excluded
    assert (
        excluded["analysis_output/visualizations/big_text.json"]["matched_rule"]
        == "content-leak-scan"
    )


def test_no_bundled_file_contains_absolute_home_path(tmp_path):
    """End-to-end guarantee: nothing in the built ZIP leaks a /Users or /home path."""
    _seed_public_release_fixture(tmp_path)
    package = write_public_release_package(
        tmp_path,
        output_dir=tmp_path / "analysis_output",
        data_dir=tmp_path / "blake_data",
        release_dir=tmp_path / "analysis_output" / "releases" / "public_release",
    )
    archive_path = Path(package["archive_path"])
    with zipfile.ZipFile(archive_path) as zf:
        for name in zf.namelist():
            if name.rsplit(".", 1)[-1] in {
                "json",
                "md",
                "txt",
                "yaml",
                "yml",
                "toml",
                "cff",
            }:
                text = zf.read(name).decode("utf-8", errors="ignore")
                assert "/Users/" not in text, f"{name} leaks an absolute home path"
                assert "/home/" not in text, f"{name} leaks an absolute home path"


def test_rights_gate_violations_flags_gated_paths():
    """The rights gate is wired into go/no-go: a gated path in the included set blocks."""
    gated = PublicReleaseAsset(
        source_path="blake_data/texts/x.txt",
        bundle_path="blake_data/texts/x.txt",
        kind="generated",
        category="local-cache",
        size_bytes=1,
        sha256="0" * 64,
    )
    safe = PublicReleaseAsset(
        source_path="blake/cli.py",
        bundle_path="blake/cli.py",
        kind="source",
        category="source-code",
        size_bytes=1,
        sha256="0" * 64,
    )
    violations = _rights_gate_violations([gated, safe])
    assert len(violations) == 1
    assert "rights-gated" in violations[0]
    assert "blake_data/texts/x.txt" in violations[0]
