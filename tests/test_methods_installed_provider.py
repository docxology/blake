"""Real selected metadata providers and unsupported filesystem boundaries."""

import shutil
from importlib import metadata

import pytest

from blake.methods.installed_records import metadata_directory
from tests.installed_distribution_fixtures import distribution, invoke


def test_selected_nonnormal_directory_is_never_replaced_by_a_decoy(tmp_path) -> None:
    _, original = distribution(tmp_path)
    selected = original.with_name(
        original.name.replace(".dist-info", "-extra.dist-info")
    )
    original.rename(selected)
    shutil.copytree(selected, original)
    for path in selected.iterdir():
        if path.is_file():
            path.write_bytes(
                path.read_bytes().replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")
            )
    for path in original.iterdir():
        if path.is_file():
            path.write_bytes(path.read_bytes().replace(b"\r\n", b"\n"))
    prefix = (
        "import sys\nfrom importlib import metadata\nfrom pathlib import Path\n"
        "class ActualSelection(metadata.DistributionFinder):\n"
        " def find_spec(self, fullname, path=None, target=None):\n"
        "  return None\n"
        " @classmethod\n"
        " def find_distributions(cls, context=metadata.DistributionFinder.Context()):\n"
        "  if context.name == 'sample-sdk':\n"
        f"   yield metadata.PathDistribution(Path({str(selected)!r}))\n"
        "sys.meta_path.insert(0, ActualSelection())\n"
        f"assert metadata.distribution('sample-sdk')._path == Path({str(selected)!r})\n"
    )
    result = invoke(tmp_path, prefix)
    assert result.returncode != 0
    assert "EvidenceError: installed_metadata" in result.stderr


@pytest.mark.parametrize(
    "failure", ["subclass", "missing_path", "not_path", "not_directory"]
)
def test_unsupported_selected_provider_is_a_named_refusal(tmp_path, failure) -> None:
    _, info = distribution(tmp_path)
    if failure == "subclass":

        class CustomProvider(metadata.PathDistribution):
            pass

        provider = CustomProvider(info)
    elif failure == "not_path":
        provider = metadata.PathDistribution("not-a-filesystem-Path")
    elif failure == "not_directory":
        provider = metadata.PathDistribution(info / "METADATA")
    else:
        provider = metadata.PathDistribution(info)
        del provider._path
    with pytest.raises(ValueError, match="installed_metadata"):
        metadata_directory(provider)


def test_missing_version_refuses_before_qualifying_files(tmp_path) -> None:
    _, info = distribution(tmp_path)
    (info / "METADATA").write_text("Name: sample-sdk\n")
    result = invoke(tmp_path)
    assert result.returncode != 0
    assert "EvidenceError: installed_distribution" in result.stderr
