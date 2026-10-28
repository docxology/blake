"""Explicit evidence selection and input preservation through real preparation."""

import hashlib
import json
from pathlib import Path

import pytest

from manuscript_tools.figures import fig_nlp_embedding_pca
from manuscript_tools.paths import manuscript_roots
from manuscript_tools.variables import AnalysisOutputsMissing, generate_variables

pytest_plugins = ("tests.test_manuscript_tools",)


def file_hashes(root: Path) -> dict[str, str]:
    return {
        p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in root.rglob("*")
        if p.is_file()
    }


def test_default_routes_remain_in_one_project(tmp_path: Path) -> None:
    roots = manuscript_roots(tmp_path)
    assert roots.authoring == roots.evidence == tmp_path.resolve()
    assert roots.output == tmp_path / "output"
    assert roots.analysis == tmp_path / "analysis_output"


def test_explicit_missing_evidence_refuses_authoring_cache(tmp_path: Path) -> None:
    (tmp_path / "analysis_output").mkdir()
    with pytest.raises(FileNotFoundError):
        generate_variables(tmp_path, evidence_root=tmp_path / "missing")
    empty = tmp_path / "empty"
    empty.mkdir()
    with pytest.raises(AnalysisOutputsMissing):
        generate_variables(tmp_path, evidence_root=empty)


def test_symlink_root_is_rejected(tmp_path: Path) -> None:
    real = tmp_path / "real"
    real.mkdir()
    link = tmp_path / "linked"
    link.symlink_to(real, target_is_directory=True)
    with pytest.raises(ValueError):
        manuscript_roots(tmp_path, link)


@pytest.mark.parametrize("value", ["", " \t"])
def test_explicit_blank_root_is_rejected(tmp_path: Path, value: str) -> None:
    with pytest.raises(ValueError, match="manuscript_blank_read_root"):
        generate_variables(tmp_path, evidence_root=value)


def test_separate_evidence_is_used_without_mutating_it(
    tmp_path: Path,
    manuscript_fixture_root: Path,
) -> None:
    evidence = manuscript_fixture_root
    authoring = tmp_path / "authoring"
    (authoring / "analysis_output/reports").mkdir(parents=True)
    (authoring / "analysis_output/reports/statistics.json").write_text(
        json.dumps({"total_works": 987654})
    )
    legal = authoring / "docs/manuscript/legal_claim_ledger.yaml"
    legal.parent.mkdir(parents=True)
    legal.write_text("- claim_id: authoring_marker\n  value: source-owned\n")
    before = file_hashes(evidence)
    expected = json.loads(
        (evidence / "analysis_output/reports/statistics.json").read_bytes()
    )
    tokens = generate_variables(authoring, evidence_root=evidence)
    assert tokens["WORKS_PRESENT"] == str(expected["total_works"])
    assert tokens["AUTHORING_MARKER"] == "source-owned"
    figure = fig_nlp_embedding_pca(
        evidence / "analysis_output", authoring / "output/figures"
    )
    assert figure.is_file()
    assert figure.is_relative_to(authoring)
    assert file_hashes(evidence) == before


def test_explicit_evidence_does_not_disable_publication_admission(
    tmp_path: Path,
    manuscript_fixture_root: Path,
) -> None:
    docs = tmp_path / "docs/manuscript"
    docs.mkdir(parents=True)
    (docs / "14_supplement_recoverability.md").write_text(
        "{{RECOVERY_MANIFEST_SHA256}}"
    )
    with pytest.raises(ValueError, match="Verified publication evidence is missing"):
        generate_variables(tmp_path, evidence_root=manuscript_fixture_root)
