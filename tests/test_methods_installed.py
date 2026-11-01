"""Real dist-info, imported files and RECORD controls; no mocked metadata."""

import csv
import hashlib
import json

import pytest

from blake.methods.installed import verify_installed_git
from tests.installed_distribution_fixtures import COMMIT, distribution, invoke, record


def test_verifies_actual_imported_git_distribution_and_full_package(tmp_path) -> None:
    # Given a complete on-disk distribution and real imports in a fresh process.
    package, _ = distribution(tmp_path)
    (package / "empty_data_directory").mkdir()
    result = invoke(tmp_path)
    # When caller-held commit, imported origins and all recorded bytes agree.
    assert result.returncode == 0, result.stderr
    receipt = json.loads(result.stdout)
    # Then the receipt binds actual bytes and metadata without running optional engines.
    assert receipt["commit"] == COMMIT
    assert receipt["version"] == "1.2.3"
    assert receipt["package_root"] == str(package)
    assert [item["path"] for item in receipt["files"]] == ["__init__.py", "child.py"]
    assert receipt["imported_modules"] == ["sample_sdk", "sample_sdk.child"]
    assert len(receipt["record_sha256"]) == 64


@pytest.mark.parametrize(
    "mutation",
    [
        "wrong_commit",
        "editable",
        "archive",
        "bad_json",
        "missing_origin",
        "missing_record",
        "changed_bytes",
        "same_size",
        "missing_file",
        "unrecorded_file",
        "symlink_file",
        "symlink_directory",
        "bad_hash",
        "missing_hash",
        "bad_size",
        "duplicate_record",
        "escape",
        "metadata_name",
        "shadow_package",
        "mixed_child",
        "extended_path",
        "no_origin",
        "unknown_origin",
        "unresolved_import",
        "symlink_root",
        "unreadable_file",
    ],
)
def test_refuses_real_metadata_code_and_import_mutations(tmp_path, mutation) -> None:
    # Given real package files and a valid original installation record.
    package, info = distribution(tmp_path)
    origin = info / "direct_url.json"
    prefix = ""
    if mutation in {
        "wrong_commit",
        "editable",
        "archive",
        "bad_json",
        "missing_origin",
    }:
        raw = json.loads(origin.read_text())
        if mutation == "wrong_commit":
            raw["vcs_info"]["commit_id"] = "b" * 40
        elif mutation == "editable":
            raw = {"url": "file:///fixture", "dir_info": {"editable": True}}
        elif mutation == "archive":
            raw = {"url": "file:///fixture.whl", "archive_info": {"hash": "sha256=x"}}
        if mutation == "missing_origin":
            origin.unlink()
        else:
            origin.write_text("{" if mutation == "bad_json" else json.dumps(raw))
    elif mutation == "missing_record":
        (info / "RECORD").unlink()
    elif mutation in {"changed_bytes", "same_size", "missing_file", "symlink_file"}:
        child = package / "child.py"
        if mutation == "changed_bytes":
            child.write_text("VALUE = 700\n")
        elif mutation == "same_size":
            child.write_text("VALUE = 9\n")
        else:
            child.unlink()
            if mutation == "symlink_file":
                outside = tmp_path / "outside.py"
                outside.write_text("VALUE = 7\n")
                child.symlink_to(outside)
    elif mutation == "unrecorded_file":
        (package / "extra.py").write_text("VALUE = 1\n")
    elif mutation == "symlink_directory":
        (package / "extra").symlink_to(info, target_is_directory=True)
    elif mutation in {
        "bad_hash",
        "missing_hash",
        "bad_size",
        "duplicate_record",
        "escape",
    }:
        path = info / "RECORD"
        with path.open(newline="") as stream:
            rows = list(csv.reader(stream))
        row = next(item for item in rows if item[0] == "sample_sdk/child.py")
        if mutation == "bad_hash":
            row[1] = "sha512=invalid"
        elif mutation == "missing_hash":
            row[1] = ""
        elif mutation == "bad_size":
            row[2] = "999"
        elif mutation == "duplicate_record":
            rows.append(row)
        else:
            row[0] = "sample_sdk/../outside.py"
        with path.open("w", newline="") as stream:
            csv.writer(stream).writerows(rows)
    elif mutation == "metadata_name":
        (info / "METADATA").write_text("Name: another\nVersion: 1.2.3\n")
    elif mutation in {"shadow_package", "mixed_child"}:
        shadow = tmp_path / "shadow"
        shadow.mkdir()
        (shadow / "__init__.py").write_text("")
        path = str(shadow / "__init__.py")
        target = "sample_sdk" if mutation == "shadow_package" else "sample_sdk.child"
        prefix = (
            "import importlib.util, sys\n"
            + ("import sample_sdk\n" if mutation == "mixed_child" else "")
            + "spec = importlib.util.spec_from_file_location("
            + repr(target)
            + ", "
            + repr(path)
            + ")\n"
            + "module = importlib.util.module_from_spec(spec)\n"
            + "sys.modules["
            + repr(target)
            + "] = module\n"
        )
    elif mutation == "extended_path":
        prefix = "import sample_sdk\nsample_sdk.__path__.append('/outside')\n"
    elif mutation == "no_origin":
        prefix = "import sample_sdk\nsample_sdk.__file__ = None\n"
    elif mutation == "unknown_origin":
        prefix = (
            "import sample_sdk\nfrom pathlib import Path\n"
            "sample_sdk.__file__ = str(Path(sample_sdk.__file__)"
            ".with_name('absent.py'))\n"
        )
    elif mutation == "unresolved_import":
        prefix = "import sample_sdk, sys\nsys.modules['sample_sdk.pending'] = None\n"
    elif mutation == "symlink_root":
        moved = tmp_path / "moved_package"
        package.rename(moved)
        package.symlink_to(moved, target_is_directory=True)
    elif mutation == "unreadable_file":
        (package / "child.py").chmod(0)
    result = invoke(tmp_path, prefix)
    if mutation == "unreadable_file":
        (package / "child.py").chmod(0o600)
    # When a caller tries to qualify the mutated installation.
    assert result.returncode != 0
    # Then a named refusal, rather than a successful receipt, is returned.
    assert "EvidenceError:" in result.stderr
    assert result.stdout == ""


@pytest.mark.parametrize(
    "package,commit",
    [("../escape", COMMIT), ("", COMMIT), ("blake", "main"), ("blake", "A" * 40)],
)
def test_invalid_selection_refuses_before_import(package, commit) -> None:
    with pytest.raises(ValueError):
        verify_installed_git(package, commit)


def test_missing_distribution_is_named() -> None:
    with pytest.raises(ValueError, match="installed_distribution"):
        verify_installed_git("missing_sdk_for_real_control", COMMIT)


@pytest.mark.parametrize(
    "mutation",
    ["integer", "decimal", "empty_path", "columns", "oversized", "missing_columns"],
)
def test_malformed_record_is_a_named_refusal(tmp_path, mutation) -> None:
    _, info = distribution(tmp_path)
    rows = {
        "integer": "sample_sdk/child.py,sha256=x,not-an-integer\n",
        "decimal": "sample_sdk/child.py,sha256=x,1.5\n",
        "empty_path": ",sha256=x,1\n",
        "columns": "sample_sdk/extra.py,sha256=x,1,extra\n",
        "oversized": "x" * 200000 + ",sha256=x,1\n",
        "missing_columns": "sample_sdk/extra.py\n",
    }
    path = info / "RECORD"
    with path.open("a") as stream:
        stream.write(rows[mutation])
    result = invoke(tmp_path)
    assert result.returncode != 0
    assert "EvidenceError: installed_" in result.stderr


@pytest.mark.parametrize(
    "mutation", ["extra", "changed", "metadata", "record", "metadata_name"]
)
def test_import_side_effects_cannot_leave_a_stale_success(tmp_path, mutation) -> None:
    package, info = distribution(tmp_path)
    target = {
        "extra": "Path(__file__).with_name('extra.py').write_text('VALUE=1\\n')",
        "changed": "Path(__file__).with_name('child.py').write_text('VALUE=9\\n')",
        "metadata": (
            "Path(__file__).parent.parent.joinpath("
            "'sample_sdk-1.2.3.dist-info/direct_url.json').write_text('{}')"
        ),
        "record": (
            "p=Path(__file__).parent.parent/'sample_sdk-1.2.3.dist-info/RECORD'; "
            "p.write_bytes(p.read_bytes()+b'\\n')"
        ),
        "metadata_name": (
            "Path(__file__).parent.parent.joinpath("
            "'sample_sdk-1.2.3.dist-info/METADATA').write_text('')"
        ),
    }[mutation]
    (package / "__init__.py").write_text(
        "from pathlib import Path\nfrom . import child\n" + target + "\n"
    )
    record(tmp_path, info)
    result = invoke(tmp_path)
    assert result.returncode != 0
    assert "EvidenceError: installed_" in result.stderr


def test_metadata_receipts_hash_physical_crlf_bytes(tmp_path) -> None:
    _, info = distribution(tmp_path)
    path = info / "METADATA"
    path.write_bytes(path.read_bytes().replace(b"\n", b"\r\n"))
    record(tmp_path, info)
    result = invoke(tmp_path)
    assert result.returncode == 0, result.stderr
    receipt = json.loads(result.stdout)
    for name, key in (
        ("METADATA", "metadata_sha256"),
        ("RECORD", "record_sha256"),
        ("direct_url.json", "direct_url_sha256"),
    ):
        assert receipt[key] == hashlib.sha256((info / name).read_bytes()).hexdigest()


@pytest.mark.parametrize(
    "package,commit,distribution_name",
    [
        (None, COMMIT, ""),
        ("blake", None, ""),
        ("unused_sdk", COMMIT, False),
    ],
)
def test_invalid_scalar_types_refuse_at_selection(
    package, commit, distribution_name
) -> None:
    with pytest.raises(ValueError, match="installed_selection"):
        verify_installed_git(package, commit, distribution_name)
