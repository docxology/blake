import errno
import hashlib
import os
import sys
import subprocess
import json
import sqlite3
import pytest
from blake.methods.corpus import import_corpus, load_import, read_passages
from blake.methods.models import (
    FileReceipt,
    ProjectionPassage as Passage,
    ProjectionCorpusPin as CorpusPin,
    ResearchError,
)
from blake.methods.storage import (
    copy_new,
    digest,
    publish_projection,
    safe_path,
    write_new,
    publish_bytes,
)


@pytest.fixture
def captured(tmp_path):
    # Given real source bytes and SQLite rows with known authorship boundaries.
    source = tmp_path / "source"
    recovery = source / "recovery"
    projection = source / "search/pinned"
    recovery.mkdir(parents=True)
    projection.mkdir(parents=True)
    (recovery / "manifest.json").write_text('{"test_fixture":true}')
    (recovery / "input.txt").write_text("Retained source bytes")
    common = dict(
        work_id="test",
        title="Test",
        edition_id="ed",
        edition="Test",
        copy_id=None,
        locator="plate 32",
        locator_kind="plate",
        source_url="https://example.test/source",
        rights="Test only",
        source_sha256=None,
    )
    payloads = [
        common
        | dict(
            passage_id="p1",
            author_id="synthetic-author",
            text_role="primary",
            source_plane="reading",
            text="Moths fly. A butterfly is not a moth. Wings are not moths.",
        ),
        common
        | dict(
            passage_id="p2",
            author_id="mixed-edition",
            text_role="editorial",
            source_plane="erdman",
            text="Moth and wing. a.b and axb.",
        ),
    ]
    with sqlite3.connect(projection / "passages.sqlite") as db:
        db.execute(
            "CREATE TABLE passages (id TEXT PRIMARY KEY,payload TEXT,sha256 TEXT)"
        )
        db.executemany(
            "INSERT INTO passages VALUES(?,?,?)",
            [
                (
                    p["passage_id"],
                    json.dumps(p),
                    hashlib.sha256(p["text"].encode()).hexdigest(),
                )
                for p in payloads
            ],
        )
    m = dict(
        captured_manifest_sha256=digest(recovery / "manifest.json"),
        index=dict(
            path="passages.sqlite",
            size=(projection / "passages.sqlite").stat().st_size,
            sha256=digest(projection / "passages.sqlite"),
        ),
        inputs=[
            dict(
                path="input.txt",
                size=(recovery / "input.txt").stat().st_size,
                sha256=digest(recovery / "input.txt"),
            )
        ],
        passages=2,
        passage_ids=["p1", "p2"],
        passages_by_plane={"reading": 1, "erdman": 1},
        passages_by_role={"primary": 1, "editorial": 1},
    )
    (projection / "search-manifest.json").write_text(json.dumps(m))
    pin = CorpusPin(
        upstream_commit="test-fixture",
        captured_manifest_sha256=m["captured_manifest_sha256"],
        projection_manifest_sha256=digest(projection / "search-manifest.json"),
        projection_relative_path="search/pinned",
        index_sha256=m["index"]["sha256"],
        unresolved_images=0,
        scope_note="Synthetic test only",
    )
    return source, projection, pin, tmp_path / "imported", payloads


def test_import_is_independent_and_preserves_source(captured):
    source, projection, pin, dest, _ = captured
    before = digest(projection / "passages.sqlite")
    # When copying, then bytes agree while storage is independent and source unchanged.
    receipt = import_corpus(source, dest, pin)
    assert receipt.passages == 2
    assert (
        digest(dest / "passages.sqlite")
        == before
        == digest(projection / "passages.sqlite")
    )
    assert (dest / "passages.sqlite").stat().st_ino != (
        projection / "passages.sqlite"
    ).stat().st_ino


@pytest.mark.parametrize("target", ["capture", "projection", "index", "input"])
def test_changed_input_cannot_be_imported(captured, target):
    source, projection, pin, dest, _ = captured
    targets = {
        "capture": source / "recovery/manifest.json",
        "projection": projection / "search-manifest.json",
        "index": projection / "passages.sqlite",
        "input": source / "recovery/input.txt",
    }
    with targets[target].open("ab") as stream:
        stream.write(b"changed")
    # When one input changes, then refuse without publishing a destination.
    with pytest.raises(ResearchError):
        import_corpus(source, dest, pin)
    assert not dest.exists()


def test_symlink_input_is_refused(captured):
    source, _, pin, dest, _ = captured
    old = source / "recovery/input.txt"
    saved = source / "recovery/saved.txt"
    old.rename(saved)
    old.symlink_to(saved)
    # When importing a symlinked input, then no target is published.
    with pytest.raises(ResearchError, match="symlink"):
        import_corpus(source, dest, pin)


def test_source_directory_symlink_is_refused(captured):
    source, _, pin, dest, _ = captured
    alias = source.parent / "alias"
    alias.symlink_to(source, target_is_directory=True)
    # When the declared source root is a link, then refuse.
    with pytest.raises(ResearchError, match="symlink"):
        import_corpus(alias, dest, pin)


def test_import_cannot_overwrite(captured):
    source, _, pin, dest, _ = captured
    dest.mkdir()
    # When a destination is occupied, then preserve it.
    with pytest.raises(ResearchError, match="occupied"):
        import_corpus(source, dest, pin)


def test_overlapping_destination_is_refused(captured):
    source, _, pin, _, _ = captured
    # When the destination enters upstream custody, then refuse.
    with pytest.raises(ResearchError, match="overlapping"):
        import_corpus(source, source / "derived", pin)


def test_corrupt_import_fails_on_open(captured):
    source, _, pin, dest, _ = captured
    import_corpus(source, dest, pin)
    with (dest / "passages.sqlite").open("ab") as stream:
        stream.write(b"damage")
    # When copied bytes change, then readers refuse.
    with pytest.raises(ResearchError, match="import_checksum"):
        load_import(dest, pin)


def test_altered_import_receipt_pin_is_untrusted(captured):
    source, _, pin, dest, _ = captured
    import_corpus(source, dest, pin)
    data = json.loads((dest / "import-receipt.json").read_text())
    data["corpus_pin"]["upstream_commit"] = "different"
    (dest / "import-receipt.json").write_text(json.dumps(data))
    # When a receipt claims new provenance, then the external pin wins.
    with pytest.raises(ResearchError, match="untrusted_import_pin"):
        load_import(dest, pin)


def test_raw_xml_cannot_be_promoted_to_primary(captured):
    payload = captured[4][0] | {"source_plane": "xml"}
    # When raw XML claims primary status, then refuse.
    with pytest.raises(ResearchError, match="primary_plane"):
        Passage.model_validate(payload)


def test_passage_hash_is_checked_independently(captured):
    projection = captured[1]
    with sqlite3.connect(projection / "passages.sqlite") as db:
        db.execute("UPDATE passages SET sha256=?", ("0" * 64,))
    # When a text hash is false, then reject even in an otherwise valid database.
    with pytest.raises(ResearchError, match="passage_binding"):
        read_passages(projection / "passages.sqlite")


@pytest.mark.parametrize("relative", ["../escape", "/absolute", "folder\\escape"])
def test_traversal_paths_are_refused(tmp_path, relative):
    # When the boundary receives traversal, then refuse.
    with pytest.raises(ResearchError, match="unsafe"):
        safe_path(tmp_path, relative)


def test_write_new_preserves_prior_bytes(tmp_path):
    path = tmp_path / "result"
    path.write_text("original")
    # When another run targets the same output, then preserve the original.
    with pytest.raises(ResearchError, match="occupied"):
        write_new(path, "new")
    assert path.read_text() == "original"


def test_overlap_check_normalizes_parent_segments(captured):
    source, _, pin, _, _ = captured
    (source.parent / "outer").mkdir()
    destination = source.parent / "outer" / ".." / "source" / "derived"
    with pytest.raises(ResearchError, match="overlapping"):
        import_corpus(source, destination, pin)


@pytest.mark.parametrize(
    ("field", "value", "code"),
    [
        ("captured_manifest_sha256", "0" * 64, "source_binding"),
        ("passage_ids", ["p1", "p1"], "projection_membership"),
    ],
)
def test_rebound_metadata_still_must_reconcile(captured, field, value, code):
    source, projection, pin, dest, _ = captured
    path = projection / "search-manifest.json"
    metadata = json.loads(path.read_text())
    metadata[field] = value
    path.write_text(json.dumps(metadata))
    rebound = pin.model_copy(update={"projection_manifest_sha256": digest(path)})
    with pytest.raises(ResearchError, match=code):
        import_corpus(source, dest, rebound)


def test_import_refuses_a_dangling_destination_link(captured):
    source, _, pin, dest, _ = captured
    dest.symlink_to(dest.parent / "absent")
    with pytest.raises(ResearchError, match="symlink_output"):
        import_corpus(source, dest, pin)


def test_exclusive_copy_preserves_existing_file(tmp_path):
    source = tmp_path / "source"
    source.write_bytes(b"new bytes")
    destination = tmp_path / "destination"
    destination.write_bytes(b"prior owner")
    with pytest.raises(ResearchError, match="occupied_output"):
        copy_new(source, destination)
    assert destination.read_bytes() == b"prior owner"


def test_exclusive_copy_refuses_dangling_link(tmp_path):
    source = tmp_path / "source"
    source.write_bytes(b"new bytes")
    destination = tmp_path / "destination"
    destination.symlink_to(tmp_path / "absent")
    with pytest.raises(ResearchError, match="occupied_output"):
        copy_new(source, destination)
    assert destination.is_symlink()


def test_publication_cannot_replace_a_concurrently_created_empty_directory(tmp_path):
    stage = tmp_path / "stage"
    stage.mkdir()
    (stage / "payload").write_bytes(b"data")
    receipt = FileReceipt(path="payload", size=4, sha256=digest(stage / "payload"))
    target = tmp_path / "other-owner"
    target.mkdir()
    original_inode = target.stat().st_ino
    with pytest.raises(ResearchError, match="occupied_output"):
        publish_projection(stage, target, (receipt,), "{}")
    assert target.stat().st_ino == original_inode
    assert list(target.iterdir()) == []


def test_publish_bytes_receipt(tmp_path):
    payload = b"binary\x00\xff"
    receipt = publish_bytes(tmp_path / "binary", payload)
    assert (tmp_path / "binary").read_bytes() == payload
    assert receipt == FileReceipt(
        path="binary", size=8, sha256=hashlib.sha256(payload).hexdigest()
    )


def test_missing_input_is_rejected(tmp_path):
    with pytest.raises(ResearchError, match="missing_regular_file"):
        safe_path(tmp_path, "absent")


def test_publish_refuses_symlink_parent(tmp_path):
    actual = tmp_path / "actual"
    actual.mkdir()
    alias = tmp_path / "alias"
    alias.symlink_to(actual, target_is_directory=True)
    with pytest.raises(ResearchError, match="symlink_output"):
        publish_bytes(alias / "output", b"data")


def test_rebound_index_name_is_rejected(captured):
    source, projection, pin, dest, _ = captured
    path = projection / "search-manifest.json"
    data = json.loads(path.read_text())
    data["index"]["path"] = "other.sqlite"
    path.write_text(json.dumps(data))
    with pytest.raises(ResearchError, match="index_pin"):
        import_corpus(
            source,
            dest,
            pin.model_copy(update={"projection_manifest_sha256": digest(path)}),
        )


def test_load_import_returns_verified_rows(captured):
    source, _, pin, dest, _ = captured
    expected = import_corpus(source, dest, pin)
    receipt, passages = load_import(dest, pin)
    assert receipt == expected
    assert [p.passage_id for p in passages] == ["p1", "p2"]


def test_false_import_count_is_rejected(captured):
    source, _, pin, dest, _ = captured
    import_corpus(source, dest, pin)
    path = dest / "import-receipt.json"
    data = json.loads(path.read_text())
    data["passages"] = 99
    path.write_text(json.dumps(data))
    with pytest.raises(ResearchError, match="import_membership"):
        load_import(dest, pin)


@pytest.mark.parametrize("moment", ["before_temporary", "before_link"])
def test_parent_swap_cannot_redirect_publication(tmp_path, moment):
    parent = tmp_path / "destination"
    parent.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    held = tmp_path / "held"
    swapped = []

    def swap(frame, event, argument):
        if event != "c_call" or swapped:
            return
        if (
            moment == "before_temporary"
            and argument is os.open
            and "temporary" in frame.f_locals
        ) or (moment == "before_link" and argument is os.link):
            parent.rename(held)
            parent.symlink_to(outside, target_is_directory=True)
            swapped.append(True)

    previous = sys.getprofile()
    sys.setprofile(swap)
    try:
        receipt = publish_bytes(parent / "result", b"private-payload")
    finally:
        sys.setprofile(previous)
    assert swapped
    assert list(outside.iterdir()) == []
    assert [p.name for p in held.iterdir()] == ["result"]
    assert (held / "result").read_bytes() == b"private-payload"
    assert receipt.sha256 == hashlib.sha256(b"private-payload").hexdigest()


def test_ancestor_swap_during_traversal_is_rejected(tmp_path):
    parent = tmp_path / "destination"
    parent.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    swapped = []

    def swap(frame, event, argument):
        if (
            event == "c_call"
            and argument is os.open
            and not swapped
            and frame.f_locals.get("component") == "destination"
        ):
            parent.rename(tmp_path / "held")
            parent.symlink_to(outside, target_is_directory=True)
            swapped.append(True)

    previous = sys.getprofile()
    sys.setprofile(swap)
    try:
        with pytest.raises(ResearchError, match="symlink_output"):
            publish_bytes(parent / "result", b"private-payload")
    finally:
        sys.setprofile(previous)
    assert swapped
    assert list(outside.iterdir()) == []
    assert list((tmp_path / "held").iterdir()) == []


def test_occupied_publication_cleans_own_temporary(tmp_path):
    path = tmp_path / "result"
    path.write_bytes(b"prior")
    with pytest.raises(ResearchError, match="occupied_output"):
        publish_bytes(path, b"replacement")
    assert sorted(p.name for p in tmp_path.iterdir()) == ["result"]
    assert path.read_bytes() == b"prior"


def test_missing_nested_directories_are_created_without_source_links(tmp_path):
    path = tmp_path / "first" / "second" / "result"
    publish_bytes(path, b"complete")
    assert path.read_bytes() == b"complete"
    assert path.stat().st_nlink == 1


def test_kernel_write_failure_removes_only_own_temporary(tmp_path):
    sentinel = tmp_path / "prior"
    sentinel.write_bytes(b"preserve")
    script = """
import errno, os, resource, signal, sys
from pathlib import Path
from blake.methods.storage import publish_bytes
root = Path(sys.argv[1])
def descriptor_count():
    total = 0
    for descriptor in range(256):
        try:
            os.fstat(descriptor)
        except OSError as exc:
            assert exc.errno == errno.EBADF
        else:
            total += 1
    return total
before = descriptor_count()
soft, hard = resource.getrlimit(resource.RLIMIT_FSIZE)
signal.signal(signal.SIGXFSZ, signal.SIG_IGN)
resource.setrlimit(resource.RLIMIT_FSIZE, (1, hard))
try:
    try:
        publish_bytes(root / "result", b"exceeds-kernel-limit")
    except OSError as exc:
        assert exc.errno == errno.EFBIG
    else:
        raise AssertionError("kernel write limit was not exercised")
finally:
    resource.setrlimit(resource.RLIMIT_FSIZE, (soft, hard))
assert descriptor_count() == before
assert sorted(p.name for p in root.iterdir()) == ["prior"]
assert (root / "prior").read_bytes() == b"preserve"
print("EFBIG refused; own temporary removed; descriptors restored; peer bytes preserved")
"""
    result = subprocess.run(
        [sys.executable, "-c", script, str(tmp_path)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "EFBIG refused" in result.stdout


def test_rival_target_at_link_is_preserved_and_temporary_removed(tmp_path):
    path = tmp_path / "result"
    fired = []

    def occupy(frame, event, argument):
        if event == "c_call" and argument is os.link and not fired:
            path.write_bytes(b"rival")
            fired.append(True)

    previous = sys.getprofile()
    sys.setprofile(occupy)
    try:
        with pytest.raises(ResearchError, match="occupied_output"):
            publish_bytes(path, b"ours")
    finally:
        sys.setprofile(previous)
    assert fired
    assert [p.name for p in tmp_path.iterdir()] == ["result"]
    assert path.read_bytes() == b"rival"


def test_temporary_collision_preserves_other_owner_and_closes_directories(tmp_path):
    fired = []

    def occupy(frame, event, argument):
        if (
            event == "c_call"
            and argument is os.open
            and not fired
            and "temporary" in frame.f_locals
        ):
            (tmp_path / frame.f_locals["temporary"]).write_bytes(b"rival")
            fired.append(True)

    previous = sys.getprofile()
    sys.setprofile(occupy)
    try:
        with pytest.raises(FileExistsError):
            publish_bytes(tmp_path / "result", b"ours")
    finally:
        sys.setprofile(previous)
    assert fired
    paths = list(tmp_path.iterdir())
    assert len(paths) == 1
    assert paths[0].read_bytes() == b"rival"


def test_publish_refuses_dangling_output_symlink(tmp_path):
    path = tmp_path / "result"
    path.symlink_to(tmp_path / "absent")
    with pytest.raises(ResearchError, match="symlink_output"):
        publish_bytes(path, b"ours")
    assert path.is_symlink()
    assert not (tmp_path / "absent").exists()


def test_kernel_directory_error_is_not_silently_retried(tmp_path):
    with pytest.raises(OSError) as caught:
        publish_bytes(tmp_path / ("x" * 300) / "result", b"ours")
    assert caught.value.errno == errno.ENAMETOOLONG
    assert list(tmp_path.iterdir()) == []


def test_projection_parent_swap_before_copy_never_exposes_source_bytes(tmp_path):
    stage = tmp_path / "stage"
    stage.mkdir()
    (stage / "payload").write_bytes(b"retained-private-source")
    entry = FileReceipt(path="payload", size=23, sha256=digest(stage / "payload"))
    destination = tmp_path / "destination"
    outside = tmp_path / "outside"
    outside.mkdir()
    swapped = []

    def swap(frame, event, argument):
        if event == "call" and frame.f_code is copy_new.__code__ and not swapped:
            destination.rename(tmp_path / "held")
            destination.symlink_to(outside, target_is_directory=True)
            swapped.append(True)

    previous = sys.getprofile()
    sys.setprofile(swap)
    try:
        with pytest.raises(ResearchError, match="symlink_output"):
            publish_projection(stage, destination, (entry,), "{}")
    finally:
        sys.setprofile(previous)
    assert swapped
    assert list(outside.iterdir()) == []
    assert list((tmp_path / "held").iterdir()) == []
    assert digest(stage / "payload") == entry.sha256


def test_copy_after_anchor_swap_keeps_original_inode_destination(tmp_path):
    source = tmp_path / "source"
    source.write_bytes(b"copied-private-bytes")
    destination = tmp_path / "destination"
    destination.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    held = tmp_path / "held"
    swapped = []

    def swap(frame, event, argument):
        if event == "c_call" and argument is os.link and not swapped:
            destination.rename(held)
            destination.symlink_to(outside, target_is_directory=True)
            swapped.append(True)

    previous = sys.getprofile()
    sys.setprofile(swap)
    try:
        copy_new(source, destination / "payload")
    finally:
        sys.setprofile(previous)
    assert swapped
    assert list(outside.iterdir()) == []
    assert (held / "payload").read_bytes() == source.read_bytes()
    assert (held / "payload").stat().st_ino != source.stat().st_ino
    assert [p.name for p in held.iterdir()] == ["payload"]
