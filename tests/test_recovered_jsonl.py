import tarfile
from pathlib import Path

from blake.recovery_pipeline import recover_corpus
from blake.text_search.recovered import build_recovered_search
from tests.recovery_fixtures import COMMIT, seed_sources, snapshot


def test_jsonl_preserves_unicode_separators_inside_a_single_json_record(
    tmp_path: Path,
) -> None:
    data = seed_sources(tmp_path)
    source = data / "recovery/sources" / f"blakearchive-{COMMIT}.tar.gz"
    entries = {}
    with tarfile.open(source, "r:gz") as archive:
        for member in archive.getmembers():
            handle = archive.extractfile(member)
            assert handle is not None
            entries[member.name.split("/", 1)[1]] = handle.read()
    entries["works/other.a.xml"] = (
        '<bad work="Other author"><phystext><l>federation\u2028state\u0085contraries</l></phystext></bad>'
    ).encode("utf-8")
    entries["works/spaced .xml"] = (
        b'<bad work="Spaced"><phystext><l>Spaced source identity.</l></phystext></bad>'
    )
    source.write_bytes(snapshot(entries))
    recover_corpus(data, commit=COMMIT, offline=True, images=False)

    result = build_recovered_search(data)

    passage = next(
        p for p in result.index.inventory() if p.passage_id == "archive:other.a"
    )
    assert "federation\u2028state\u0085contraries" in passage.text
    spaced = next(
        p for p in result.index.inventory() if p.passage_id == "archive:spaced "
    )
    assert "spaced%20.xml" in str(spaced.source_url)
    assert "snapshot/" in str(spaced.source_url) or "/works/" in str(spaced.source_url)
