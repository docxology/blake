# Copyright (c) 2026 Daniel Ari Friedman
"""Real imported source, Unicode tables and private-output custody controls."""

import json
import os
import re
from contextlib import contextmanager
from importlib.resources import files

from pathlib import Path

import pytest

from blake.methods.corpus import import_corpus
from blake.methods.models import ResearchError
from blake.methods.workspace import (
    _csp_hash,
    _json_script,
    build_search_workspace as _build_search_workspace,
    build_search_workspace_passages,
    WorkspaceBranding,
    unicode_search_tables,
)
from blake.methods.storage import digest


from tests.test_methods_custody import captured


def build_search_workspace(directory, pin, output):
    return _build_search_workspace(
        directory,
        pin,
        output,
        branding=WorkspaceBranding("Corpus", "Local instrument", "Local search"),
        producer_version="test",
        private_output_root=Path.cwd() / "analysis_output",
    )


@contextmanager
def working_directory(path):
    previous = Path.cwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(previous)


def test_unicode_tables_match_python_boundaries_and_expansions():
    folding, ranges = unicode_search_tables()
    assert folding["ß"] == "ss"
    assert folding["İ"] == "i\u0307"
    assert folding["\u03a3"] == "\u03c3"
    assert "😀" not in folding
    assert folding["𐐀"] == "𐐨"
    assert all(left[1] + 1 < right[0] for left, right in zip(ranges, ranges[1:]))
    for value in ("A", "_", "é", "Ⅷ", "²", "𐐀", "𐐨", "😀", "\u0307", " ", "-"):
        included = any(start <= ord(value) <= end for start, end in ranges)
        assert included == (value.isalnum() or value == "_")


def test_script_serialization_is_inert_and_lossless():
    unsafe = {"text": '</script><script>alert("x")</script>\u2028\u2029 @@SCRIPT@@'}
    encoded = _json_script(unsafe)
    assert "</script>" not in encoded
    assert "\u2028" not in encoded
    assert "\u2029" not in encoded
    assert json.loads(encoded) == unsafe
    assert len(_csp_hash("source")) == 44
    assert _csp_hash("source") != _csp_hash("changed")


def test_workspace_has_complete_bound_fulltexts_and_no_runtime_network(captured):
    source, _, pin, imported, payloads = captured
    import_corpus(source, imported, pin)
    with working_directory(imported.parent):
        output = Path("analysis_output/search")
        index = build_search_workspace(imported, pin, output)
        html = index.read_text()
        matched = re.search(
            r'<script id="search-data" type="application/json">(.*?)</script>', html, re.DOTALL
        )
        assert matched is not None
        payload = json.loads(matched[1])
        assert [unit["text"] for unit in payload["units"]] == [p["text"] for p in payloads]
        assert payload["corpus_pin"] == pin.model_dump(mode="json")
        assert payload["units"][0]["text_sha256"]
        assert "fetch(" not in html
        assert "XMLHttpRequest" not in html
        assert "connect-src 'none'" in html
        assert "window.blakeanSearch=api" in html
        assert "innerHTML" not in html
        assert "javascript:" not in html
        assert "@@STYLE@@" not in html
        assert str(imported) not in html
        receipt = json.loads((output / "search-manifest.json").read_text())
        assert receipt["source_units"] == 2
        assert receipt["index_sha256"] == pin.index_sha256
        assert receipt["outputs"][0]["sha256"] == digest(index)
        assert receipt["outputs"][0]["size"] == index.stat().st_size
        with pytest.raises(ResearchError, match="occupied_output"):
            build_search_workspace(imported, pin, output)


def test_workspace_refuses_public_paths_traversal_and_symlink(captured):
    source, _, pin, imported, _ = captured
    import_corpus(source, imported, pin)
    with working_directory(imported.parent):
        for destination in (Path("docs/search"), Path("analysis_output/../docs/search")):
            with pytest.raises(ResearchError, match="private_output_required"):
                build_search_workspace(imported, pin, destination)
        (Path.cwd() / "analysis_output").mkdir()
        (Path.cwd() / "link").symlink_to(Path.cwd() / "analysis_output", target_is_directory=True)
        with pytest.raises(ResearchError, match="symlink_output"):
            build_search_workspace(imported, pin, Path("link/search"))


def test_workspace_rejects_corrupted_projection_before_publication(captured):
    source, _, pin, imported, _ = captured
    import_corpus(source, imported, pin)
    with (imported / "passages.sqlite").open("ab") as stream:
        stream.write(b"corrupted")
    with working_directory(imported.parent), pytest.raises(ResearchError, match="import_checksum"):
        build_search_workspace(imported, pin, Path("analysis_output/search"))
    assert not (imported.parent / "analysis_output/search").exists()


def test_node_differential_oracle_and_no_cap_counts(tmp_path, captured):
    import subprocess
    import random
    from blake.methods.search import search_passages
    from blake.methods.search_models import SearchRequest
    from blake.methods.workspace import _source_data
    from tests.test_methods_search import passage

    _, _, pin, _, _ = captured
    folding, ranges = unicode_search_tables()
    rng = random.Random(105)
    texts = ["🜁 Straße ﬃ İ 𐐀", "ß ﬃ", "a b c", "! ?", "state " * 1500, "é é"]
    texts.extend(
        "".join(rng.choice(("a", "b", " ", "!", "_", "𐐀", "ß")) for _ in range(25))
        for _ in range(50)
    )
    units = tuple(passage(text, str(i).zfill(3)) for i, text in enumerate(texts))
    data = dict(
        corpus_pin=pin.model_dump(mode="json"),
        folding=folding,
        word_ranges=ranges,
        whitespace=[chr(c) for c in range(0x110000) if chr(c).isspace()],
        units=_source_data(units),
    )
    requests = [
        SearchRequest(terms=terms, mode=mode, whole_words=whole, limit=1, window_words=width)
        for terms in (
            ("STRASSE", "ffi", "i\u0307", "𐐨"),
            ("a", "b"),
            ("!", "?"),
            ("ss", "ffi"),
            ("é", "é"),
        )
        for mode, width in (("any", None), ("all", None), ("all", 1), ("all", 2), ("all", 200))
        for whole in (True, False)
    ]
    requests.append(SearchRequest(terms=("state",), limit=1))
    script = files("blake.methods").joinpath("resources/corpus-search.js")
    runner = 'const fs=require("fs");const {createCorpusSearch}=require(process.argv[1]);const x=JSON.parse(fs.readFileSync(0,"utf8"));console.log(JSON.stringify(x.requests.map(createCorpusSearch(x.data).run)));'
    result = subprocess.run(
        ["node", "-e", runner, str(script)],
        input=json.dumps(dict(data=data, requests=[r.model_dump(mode="json") for r in requests])),
        text=True,
        capture_output=True,
        check=True,
    )
    actual = json.loads(result.stdout)
    expected = [
        search_passages(units, r).model_copy(update={"corpus_pin": pin}).model_dump(mode="json")
        for r in requests
    ]
    assert actual == expected
    assert actual[-1]["total_occurrences"] == 1500 and actual[-1]["returned_hits"] == 1
    # A deliberately corrupted expected offset must fail the same comparison.
    actual[-1]["hits"][0]["start"] += 1
    with pytest.raises(AssertionError):
        assert actual == expected


def test_workspace_callback_custody_and_duplicate_units(tmp_path, captured):
    from tests.test_methods_search import passage

    _, _, pin, _, _ = captured
    root = tmp_path / "private"
    args = dict(
        branding=WorkspaceBranding("<script>", "&brand", "footer"),
        producer_version="test",
        private_output_root=root,
    )

    def changed():
        raise ResearchError("search_source_changed", "control")

    with pytest.raises(ResearchError, match="search_source_changed"):
        build_search_workspace_passages(
            (passage("x"),), pin, root / "changed", revalidate=changed, **args
        )
    assert not (root / "changed").exists()
    with pytest.raises(ResearchError, match="duplicate_passage"):
        build_search_workspace_passages(
            (passage("x"), passage("y")), pin, root / "duplicate", revalidate=changed, **args
        )

    def verified():
        return None

    index = build_search_workspace_passages(
        (passage("x"),), pin, root / "ok", revalidate=verified, **args
    )
    assert "&lt;script&gt;" in index.read_text()
    resources = tmp_path / "resources"
    resources.mkdir()
    (resources / "corpus-search.html").write_text("missing markers")
    (resources / "corpus-search.css").write_text("body{}")
    with pytest.raises(ResearchError, match="search_template_marker"):
        build_search_workspace_passages(
            (passage("x"),),
            pin,
            root / "bad",
            revalidate=verified,
            resource_directory=resources,
            **args,
        )


def test_workspace_revalidates_before_exclusive_directory_creation(tmp_path, captured):
    from tests.test_methods_search import passage

    _, _, pin, _, _ = captured
    output = tmp_path / "private" / "race"

    def competing_writer():
        output.mkdir(parents=True)
        (output / "owner.txt").write_text("other writer")

    with pytest.raises(ResearchError, match="occupied_output"):
        build_search_workspace_passages(
            (passage("x"),),
            pin,
            output,
            branding=WorkspaceBranding("Corpus", "Local", "Local"),
            producer_version="test",
            private_output_root=tmp_path / "private",
            revalidate=competing_writer,
        )
    assert (output / "owner.txt").read_text() == "other writer"
    assert not (output / "index.html").exists()
