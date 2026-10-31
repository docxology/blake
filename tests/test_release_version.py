"""Version identity and prerelease semantics are observable package contracts."""

import json
import re
from pathlib import Path

import pytest
from packaging.version import Version

import blake
from blake.corpus.public_release import _github_release_metadata


def test_package_and_visualization_share_one_version():
    import blake.viz

    assert blake.viz.__version__ == blake.__version__


def test_release_metadata_marks_current_development_or_candidate_version():
    metadata = _github_release_metadata("Blake", "github")
    assert metadata["tag_name"] == "v" + blake.__version__
    assert metadata["draft"] is True
    assert metadata["prerelease"] is Version(blake.__version__).is_prerelease


@pytest.mark.parametrize(
    "version,prerelease",
    [
        ("0.2.0rc1", True),
        ("0.2.0.dev1", True),
        ("0.2.0a1", True),
        ("0.2.0", False),
        ("0.2.0.post1", False),
        ("0.2.0+local.rc1", False),
    ],
)
def test_release_channel_uses_validated_version(version, prerelease):
    metadata = _github_release_metadata("Blake", "github", version=version)
    assert metadata["prerelease"] is prerelease
    assert metadata["tag_name"] == "v" + version


def test_release_rejects_invalid_version():
    with pytest.raises(ValueError):
        _github_release_metadata("Blake", "github", version="not a release")


def test_source_metadata_cites_current_software_and_preserves_archived_identity():
    root = Path(__file__).resolve().parents[1]
    metadata = json.loads((root / "codemeta.json").read_text())
    assert metadata["version"] == blake.__version__
    assert metadata["isBasedOn"]["version"] == "0.1.0"
    assert (
        metadata["isBasedOn"]["identifier"] == "https://doi.org/10.5281/zenodo.21047574"
    )
    citation = (root / "CITATION.cff").read_text()
    assert re.search(
        r'^version: "' + re.escape(blake.__version__) + r'"$', citation, re.M
    )
    assert not re.search(r"^doi:", citation, re.M)
    assert metadata["identifier"] == "https://github.com/docxology/blake"
    deposit = json.loads((root / ".zenodo.json").read_text())
    publication = json.loads((root / "publication.json").read_text())
    assert deposit["version"] == publication["version"]
    assert deposit["doi"] == publication["zenodo"]["doi"]
    assert deposit["publication_date"] == publication["publication_date"]
    assert deposit["upload_type"] == "publication"
    assert deposit["publication_type"] == "workingpaper"
    assert metadata["citation"] == "https://doi.org/" + deposit["doi"]
    preferred = citation.split("preferred-citation:", 1)[1]
    assert '  version: "' + publication["version"] + '"' in preferred
    assert '  doi: "' + deposit["doi"] + '"' in preferred
    assert '    doi: "10.5281/zenodo.23601681"' in citation
    assert '    version: "0.1.0"' in citation
    assert '    doi: "10.5281/zenodo.21047574"' in citation


def test_public_version_contract_names_software_methods_and_dashboard():
    info = blake.version_info()
    assert info["package_version"] == blake.__version__
    assert info["methods_profile"] == "local-source-evidence-v2"
    assert info["dashboard_schema_version"] == 2
