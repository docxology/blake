"""New inference admits a producer without relabeling retained analysis."""

import hashlib
import importlib
import json
import os
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace

import pytest

from blake.analysis import BlakeAnalyzer
from blake.corpus import BlakeCorpus, CorpusConfig, SourceRegistry
from blake.exceptions import AnalysisError
from blake.models import BlakeMetadata, BlakeWork, ExportConfig, SourceType, WorkType

SIDECAR = ".analysis-producer.json"
PAYLOAD = {"basic_stats": {"word_count": 2}, "entities": {"entities": []}}


def tree_bytes(*roots):
    result = {}
    for index, base in enumerate(roots):
        for parent, _dirs, names in os.walk(base, followlinks=False):
            for name in names:
                path = Path(parent) / name
                key = (index, path.relative_to(base).as_posix())
                result[key] = (
                    ("symlink", os.readlink(path))
                    if path.is_symlink()
                    else ("sha256", hashlib.sha256(path.read_bytes()).hexdigest())
                )
    return result


@pytest.fixture
def engines(monkeypatch):
    """Replace heavyweight engines, retaining the real public write paths."""
    module = importlib.import_module("blake.analysis.analyzer")
    calls = []

    class Engine:
        def __init__(self, *args, **kwargs):
            self.nlp = SimpleNamespace(
                meta={"name": "core_web_sm", "lang": "en", "version": "3.8.0"},
                pipe_names=["tagger", "parser", "lemmatizer", "ner"],
            )

        async def analyze_work(self, work):
            calls.append(work.id)
            return deepcopy(PAYLOAD)

        async def analyze_image(self, image):
            calls.append(image.id)
            return {"brightness": 0.5}

    for name in ("TextAnalyzer", "VisualAnalyzer", "CrossAnalyzer", "OntologyManager"):
        monkeypatch.setattr(module, name, Engine)
    return calls


@pytest.fixture
def work():
    return BlakeWork(
        id="producer-fixture",
        metadata=BlakeMetadata(
            id="producer-fixture",
            title="Producer fixture",
            source=SourceType.BLAKE_ARCHIVE,
            work_type=WorkType.POEM,
        ),
        text_content="Fixture words.",
    )


def write_profile(data, context):
    producer = importlib.import_module("blake.analysis_producer")
    record = {
        "schema_version": 1,
        "producer": context,
        "fingerprint": producer.producer_fingerprint(context),
    }
    path = data / SIDECAR
    path.write_text(json.dumps(record), encoding="utf-8")
    return path


@pytest.mark.asyncio
async def test_unbound_raw_cache_refuses_new_direct_inference(tmp_path, engines, work):
    analyzer = BlakeAnalyzer(tmp_path)
    cache = tmp_path / "analysis" / "retained_text_analysis.json"
    cache.write_text('{"retained": true}', encoding="utf-8")
    before = tree_bytes(tmp_path)
    before_work = work.model_dump(mode="json")

    with pytest.raises(
        (ValueError, AnalysisError), match="producer|profile|epoch|analysis|bound"
    ):
        await analyzer.analyze_work(work, ["text"])

    assert engines == []
    assert tree_bytes(tmp_path) == before
    assert work.model_dump(mode="json") == before_work


@pytest.mark.asyncio
@pytest.mark.parametrize("requested", [["text"], ["visual"]])
async def test_unbound_database_results_refuse_new_corpus_inference(
    tmp_path, engines, work, requested
):
    data, output = tmp_path / "data", tmp_path / "output"
    corpus = BlakeCorpus(data, output_dir=output, source_registry=SourceRegistry())
    await corpus.metadata_manager.save_work(work)
    await corpus.metadata_manager.save_analysis_result(work.id, "text", {"retained": 7})
    await corpus.clear_cache()
    assert (await corpus.get_work(work.id)).text_analysis == {"retained": 7}
    assert not list((data / "analysis").glob("*.json"))
    before = tree_bytes(data, output)

    with pytest.raises(
        (ValueError, AnalysisError), match="producer|profile|epoch|analysis|bound"
    ):
        await corpus.analyze_work(work.id, requested)

    assert engines == []
    assert tree_bytes(data, output) == before
    assert (await corpus.get_work(work.id)).text_analysis == {"retained": 7}


@pytest.mark.asyncio
@pytest.mark.parametrize("skip_analysis", [False, True])
async def test_sealed_output_refuses_run_before_any_output_setup(
    tmp_path, monkeypatch, engines, skip_analysis
):
    data, output = tmp_path / "data", tmp_path / "output"
    corpus = BlakeCorpus(data, output_dir=output, source_registry=SourceRegistry())
    (output / "data").mkdir()
    (output / "data/publication_epoch.json").write_text(
        '{"schema_version": 1, "retained": true}', encoding="utf-8"
    )
    before = tree_bytes(data, output)

    def forbid_output_setup(*args):
        raise AssertionError("Output setup happened before sealed-epoch refusal")

    monkeypatch.setattr(corpus, "_prepare_output_dirs", forbid_output_setup)
    config = CorpusConfig(
        data_dir=data,
        output_dir=output,
        quick=True,
        skip_analysis=skip_analysis,
        skip_visualizations=True,
        skip_export=True,
        skip_reports=True,
        fixture_mode="never",
    )
    with pytest.raises(
        (ValueError, AnalysisError), match="producer|profile|epoch|sealed|saved"
    ):
        await corpus.run(config)

    assert engines == []
    assert tree_bytes(data, output) == before


@pytest.mark.asyncio
async def test_legacy_constructor_saved_load_and_fresh_export_do_not_stamp_or_reinfer(
    tmp_path, engines
):
    from blake.corpus.saved_epoch import load_saved_analysis_epoch
    from tests.test_saved_analysis_epoch import seed_epoch

    data, output, store, expected = seed_epoch(tmp_path)
    before = tree_bytes(data, output)
    corpus = BlakeCorpus(store, output_dir=output, source_registry=SourceRegistry())
    works = await corpus.get_all_works()
    loaded = load_saved_analysis_epoch(data, output)
    assert loaded["analysis_software_version"] == expected["analysis_software_version"]
    destination = tmp_path / "new-export"
    exported = await corpus.export_works(
        works,
        ExportConfig(format="json", output_dir=destination, include_images=False),
    )

    assert exported.exists()
    assert list(destination.rglob("*.json"))
    assert engines == []
    assert tree_bytes(data, output) == before
    assert not (data / SIDECAR).exists()
    assert not (store / SIDECAR).exists()
    assert not (output / SIDECAR).exists()


@pytest.mark.asyncio
async def test_fresh_inference_records_actual_profile_without_wrapping_raw_result(
    tmp_path, engines, work
):
    analyzer = BlakeAnalyzer(tmp_path)
    result = await analyzer.analyze_work(work, ["text"])
    producer = importlib.import_module("blake.analysis_producer")
    sidecar = json.loads((tmp_path / SIDECAR).read_bytes())

    assert set(sidecar) == {"schema_version", "producer", "fingerprint"}
    assert type(sidecar["schema_version"]) is int and sidecar["schema_version"] == 1
    context = producer.capture_installed_producer(analyzer=analyzer)
    assert sidecar["producer"] == context
    assert sidecar["fingerprint"] == producer.producer_fingerprint(context)
    raw_files = list((tmp_path / "analysis").glob("*.json"))
    assert len(raw_files) == 1
    assert json.loads(raw_files[0].read_bytes()) == result["text_analysis"] == PAYLOAD
    assert engines == [work.id]
    retained_sidecar = (tmp_path / SIDECAR).read_bytes()

    again = await analyzer.analyze_work(work, ["text"])

    assert again["text_analysis"] == PAYLOAD
    assert engines == [work.id, work.id]
    assert (tmp_path / SIDECAR).read_bytes() == retained_sidecar


@pytest.mark.asyncio
async def test_fresh_corpus_summary_metadata_bind_actual_profile(
    tmp_path, engines, work
):
    producer = importlib.import_module("blake.analysis_producer")
    data, output = tmp_path / "data", tmp_path / "output"
    corpus = BlakeCorpus(data, output_dir=output, source_registry=SourceRegistry())
    text_file = data / "texts" / "fixture.txt"
    text_file.parent.mkdir(parents=True, exist_ok=True)
    text_bytes = work.text_content.encode("utf-8")
    text_file.write_bytes(text_bytes)
    work.metadata.file_path = text_file
    work.metadata.file_size = len(text_bytes)
    await corpus.metadata_manager.save_work(work)
    config = CorpusConfig(
        data_dir=data,
        output_dir=output,
        quick=True,
        analysis_types=["text"],
        skip_visualizations=True,
        skip_export=True,
        skip_reports=True,
        fixture_mode="never",
    )

    run = await corpus.run(config)

    assert run.status == "completed"
    context = producer.capture_installed_producer(analyzer=corpus.analyzer)
    fingerprint = producer.producer_fingerprint(context)
    for name in ("analysis_summary.json", "analysis_diagnostics.json"):
        record = json.loads((output / "analysis" / name).read_bytes())
        assert record["analysis_producer"] == context
        assert record["analysis_producer_fingerprint"] == fingerprint
    records = json.loads((output / "analysis/analysis_results.json").read_bytes())
    assert records
    assert all(row["metadata"]["analysis_producer"] == context for row in records)
    assert all(
        row["metadata"]["analysis_producer_fingerprint"] == fingerprint
        for row in records
    )
    for store in (data, output):
        sidecar = json.loads((store / SIDECAR).read_bytes())
        assert sidecar["producer"] == context
        assert sidecar["fingerprint"] == fingerprint
    assert engines == [work.id]


@pytest.mark.asyncio
@pytest.mark.parametrize("identity", ["numpy", "spacy", "lock_sha256"])
async def test_changed_installed_or_lock_identity_refuses_before_new_inference(
    tmp_path, engines, work, identity
):
    analyzer = BlakeAnalyzer(tmp_path)
    producer = importlib.import_module("blake.analysis_producer")
    old_context = deepcopy(producer.capture_installed_producer(analyzer=analyzer))
    if identity == "lock_sha256":
        old_context[identity] = "0" * 64
    else:
        old_context["packages"][identity] = "0.0.0"
    write_profile(tmp_path, old_context)
    (tmp_path / "analysis/retained.json").write_text('{"retained": 7}')
    before = tree_bytes(tmp_path)

    with pytest.raises(
        (ValueError, AnalysisError), match="producer|profile|epoch|analysis"
    ):
        await analyzer.analyze_work(work, ["text"])

    assert engines == []
    assert tree_bytes(tmp_path) == before


@pytest.mark.asyncio
@pytest.mark.parametrize("availability", ["different_version", "unavailable"])
async def test_actual_loaded_model_change_is_not_hidden_by_installed_distribution(
    tmp_path, engines, work, availability
):
    analyzer = BlakeAnalyzer(tmp_path)
    producer = importlib.import_module("blake.analysis_producer")
    old_context = producer.capture_installed_producer(analyzer=analyzer)
    write_profile(tmp_path, old_context)
    (tmp_path / "analysis/retained.json").write_text('{"retained": 7}')
    if availability == "unavailable":
        analyzer.text_analyzer.nlp = None
    else:
        analyzer.text_analyzer.nlp.meta["version"] = "3.7.1"
    assert producer.capture_installed_producer(analyzer=analyzer) != old_context
    before = tree_bytes(tmp_path)

    with pytest.raises(
        (ValueError, AnalysisError), match="producer|profile|epoch|analysis"
    ):
        await analyzer.analyze_work(work, ["text"])

    assert engines == []
    assert tree_bytes(tmp_path) == before


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "problem",
    ["json", "duplicate_key", "fingerprint", "oversize", "symlink", "hardlink"],
)
async def test_invalid_profile_never_authorizes_new_inference(
    tmp_path, engines, work, problem
):
    analyzer = BlakeAnalyzer(tmp_path)
    producer = importlib.import_module("blake.analysis_producer")
    context = producer.capture_installed_producer(analyzer=analyzer)
    sidecar = write_profile(tmp_path, context)
    raw = sidecar.read_text()
    if problem == "json":
        raw = "{"
    elif problem == "duplicate_key":
        raw = raw[:-1] + ', "schema_version": 1}'
    elif problem == "fingerprint":
        record = json.loads(raw)
        record["fingerprint"] = "0" * 64
        raw = json.dumps(record)
    elif problem == "oversize":
        raw = " " * (64 * 1024) + raw
    if problem in {"symlink", "hardlink"}:
        external = tmp_path.parent / (tmp_path.name + "-profile.json")
        sidecar.replace(external)
        if problem == "symlink":
            sidecar.symlink_to(external)
        else:
            os.link(external, sidecar)
    else:
        sidecar.write_text(raw)
    (tmp_path / "analysis/retained.json").write_text('{"retained": 7}')
    before = tree_bytes(tmp_path)

    with pytest.raises(
        (ValueError, AnalysisError), match="producer|profile|epoch|analysis"
    ):
        await analyzer.analyze_work(work, ["text"])

    assert engines == []
    assert tree_bytes(tmp_path) == before


@pytest.mark.asyncio
@pytest.mark.parametrize("entry", ["analyzer", "corpus"])
@pytest.mark.parametrize(
    "retained", ["other_work", "empty_result", "unknown_analysis_type"]
)
async def test_first_admission_checks_entire_retained_database(
    tmp_path, engines, work, entry, retained
):
    """A fresh selected work cannot bless another work's unbound old results."""
    data, output = tmp_path / "data", tmp_path / "output"
    corpus = BlakeCorpus(data, output_dir=output, source_registry=SourceRegistry())
    fresh = work.model_copy(deep=True)
    fresh.id = fresh.metadata.id = "fresh-B"
    fresh.metadata.title = "Fresh B"
    older = work.model_copy(deep=True)
    older.id = older.metadata.id = "older-A"
    older.metadata.title = "Retained A"
    for item in (older, fresh):
        text_file = data / "texts" / (item.id + ".txt")
        text_file.parent.mkdir(parents=True, exist_ok=True)
        text_bytes = item.text_content.encode("utf-8")
        text_file.write_bytes(text_bytes)
        item.metadata.file_path = text_file
        item.metadata.file_size = len(text_bytes)
    await corpus.metadata_manager.save_work(older)
    await corpus.metadata_manager.save_work(fresh)
    analysis_type = "external-note" if retained == "unknown_analysis_type" else "text"
    payload = {} if retained == "empty_result" else {"retained": 7}
    await corpus.metadata_manager.save_analysis_result(older.id, analysis_type, payload)
    await corpus.clear_cache()
    loaded = await corpus.get_work(fresh.id)
    assert not any(
        getattr(loaded, name)
        for name in (
            "text_analysis",
            "visual_analysis",
            "cross_analysis",
            "ontological_analysis",
        )
    )
    assert not list((data / "analysis").glob("*.json"))
    assert not (data / SIDECAR).exists()
    before = tree_bytes(data, output)
    before_work = fresh.model_dump(mode="json")

    with pytest.raises(
        (ValueError, AnalysisError), match="producer|profile|epoch|analysis|bound"
    ):
        if entry == "analyzer":
            await corpus.analyzer.analyze_work(fresh, ["text"])
        else:
            await corpus.analyze_work(fresh.id, ["text"])

    assert engines == []
    assert tree_bytes(data, output) == before
    assert fresh.model_dump(mode="json") == before_work
    assert not (data / SIDECAR).exists()
    assert not (output / SIDECAR).exists()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "dependency", ["opencv-python", "scikit-learn", "scikit-image"]
)
async def test_direct_analysis_dependency_drift_revokes_existing_profile(
    tmp_path, monkeypatch, engines, work, dependency
):
    """Changing a real direct engine version must change admission identity."""
    analyzer = BlakeAnalyzer(tmp_path)
    producer = importlib.import_module("blake.analysis_producer")
    context = producer.capture_installed_producer(analyzer=analyzer)
    write_profile(tmp_path, context)
    (tmp_path / "analysis/retained.json").write_text('{"retained": 7}')
    version = producer.metadata.version

    def changed_version(name):
        return "0.0.0" if name == dependency else version(name)

    monkeypatch.setattr(producer.metadata, "version", changed_version)
    before = tree_bytes(tmp_path)
    before_work = work.model_dump(mode="json")

    with pytest.raises(
        (ValueError, AnalysisError), match="producer|profile|epoch|analysis|bound"
    ):
        await analyzer.analyze_work(work, ["text"])

    assert engines == []
    assert tree_bytes(tmp_path) == before
    assert work.model_dump(mode="json") == before_work


@pytest.mark.asyncio
async def test_source_provenance_metadata_is_preserved_without_blocking_fresh_analysis(
    tmp_path, engines, work
):
    """Generic source/recovery provenance is not a retained model-result row."""
    data, output = tmp_path / "data", tmp_path / "output"
    corpus = BlakeCorpus(data, output_dir=output, source_registry=SourceRegistry())
    text_file = data / "texts" / "provenance-fixture.txt"
    text_file.parent.mkdir(parents=True, exist_ok=True)
    text_bytes = work.text_content.encode("utf-8")
    text_file.write_bytes(text_bytes)
    work.metadata.file_path = text_file
    work.metadata.file_size = len(text_bytes)
    provenance = {"recovery": {"source_sha256": "a" * 64}}
    work.metadata.analysis_results = deepcopy(provenance)
    await corpus.metadata_manager.save_work(work)

    result = await corpus.analyze_work(work.id, ["text"])

    assert result["text_analysis"] == PAYLOAD
    assert engines == [work.id]
    loaded = await corpus.metadata_manager.load_work(work.id)
    assert loaded.metadata.analysis_results == provenance
    assert (data / SIDECAR).is_file()


@pytest.mark.asyncio
async def test_unavailable_database_stat_does_not_reserve_a_producer(
    tmp_path, monkeypatch, engines, work
):
    from blake.metadata.database import MetadataDatabase

    data = tmp_path / "data"
    analyzer = BlakeAnalyzer(data)
    database = data / "metadata/metadata.db"
    MetadataDatabase(database)
    before = tree_bytes(data)
    exists, is_symlink, lstat = Path.exists, Path.is_symlink, Path.lstat

    # Python 3.14+ predicates can suppress an unavailable stat as False.
    monkeypatch.setattr(Path, "exists", lambda p: False if p == database else exists(p))
    monkeypatch.setattr(
        Path, "is_symlink", lambda p: False if p == database else is_symlink(p)
    )

    def unavailable_stat(path):
        if path == database:
            raise PermissionError("Controlled unavailable analysis database stat")
        return lstat(path)

    monkeypatch.setattr(Path, "lstat", unavailable_stat)
    with pytest.raises(
        (ValueError, AnalysisError), match="producer|profile|epoch|analysis"
    ):
        await analyzer.analyze_work(work, ["text"])

    assert engines == []
    assert tree_bytes(data) == before
    assert not (data / SIDECAR).exists()


@pytest.mark.asyncio
@pytest.mark.parametrize("problem", ["dangling_metadata", "orphan_wal"])
async def test_absent_database_with_retained_marker_is_not_a_fresh_store(
    tmp_path, engines, work, problem
):
    data = tmp_path / "data"
    analyzer = BlakeAnalyzer(data)
    metadata = data / "metadata"
    if problem == "dangling_metadata":
        target = tmp_path / "unavailable-metadata"
        metadata.symlink_to(target, target_is_directory=True)
    else:
        metadata.mkdir()
        (metadata / "metadata.db-wal").write_bytes(b"preserve journal observation")
    before = tree_bytes(data)

    with pytest.raises(
        (ValueError, AnalysisError), match="producer|profile|epoch|analysis"
    ):
        await analyzer.analyze_work(work, ["text"])

    assert engines == []
    assert tree_bytes(data) == before
    assert not (data / SIDECAR).exists()
    if problem == "dangling_metadata":
        assert metadata.is_symlink() and metadata.readlink() == target
        assert not target.exists()


@pytest.mark.asyncio
async def test_skip_analysis_refuses_unbound_database_before_acquisition_prunes(
    tmp_path, monkeypatch, engines, work
):
    from blake.corpus import SourceRecord

    data, output = tmp_path / "data", tmp_path / "output"
    registry = SourceRegistry()
    corpus = BlakeCorpus(data, output_dir=output, source_registry=registry)
    await corpus.metadata_manager.save_work(work)
    await corpus.metadata_manager.save_analysis_result(work.id, "text", {})
    calls = []

    async def discover():
        calls.append("discovery")
        return [
            SourceRecord(
                source_type=SourceType.PROJECT_GUTENBERG,
                source_id="replacement-work",
                title="Replacement fixture",
                work_type=WorkType.POEM,
            )
        ]

    async def no_network_audit(*args, **kwargs):
        return {}

    monkeypatch.setattr(registry, "discover_all", discover)
    monkeypatch.setattr(corpus, "_build_source_audit_with_errors", no_network_audit)
    before = tree_bytes(data, output)
    config = CorpusConfig(
        data_dir=data,
        output_dir=output,
        quick=False,
        skip_analysis=True,
        skip_visualizations=True,
        skip_export=True,
        skip_reports=True,
        fixture_mode="never",
    )
    refusal = None
    try:
        await corpus.run(config)
    except ValueError as exc:
        refusal = exc

    assert tree_bytes(data, output) == before
    assert refusal is not None
    assert "fresh analysis epoch" in str(refusal)
    assert calls == []
    assert engines == []
    assert not (data / SIDECAR).exists()
    assert not (output / SIDECAR).exists()


@pytest.mark.asyncio
async def test_skip_analysis_accepts_source_provenance_without_stamping_data(
    tmp_path, engines, work
):
    data, output = tmp_path / "data", tmp_path / "output"
    work.metadata.analysis_results = {
        "source_custody": {"sha256": "a" * 64, "reviewed": False}
    }
    corpus = BlakeCorpus(data, output_dir=output, source_registry=SourceRegistry())
    await corpus.metadata_manager.save_work(work)
    before = tree_bytes(data)
    result = await corpus.run(
        CorpusConfig(
            data_dir=data,
            output_dir=output,
            quick=True,
            skip_analysis=True,
            skip_visualizations=True,
            skip_export=True,
            skip_reports=True,
            fixture_mode="never",
        )
    )

    assert result.status == "completed"
    assert tree_bytes(data) == before
    assert engines == []
    assert not (data / SIDECAR).exists()
    assert (output / SIDECAR).exists()
    summary = json.loads((output / "analysis/analysis_summary.json").read_bytes())
    assert summary["analysis_results_current"] is False
    assert summary["analysis_producer"] is None
    assert summary["analysis_producer_fingerprint"] is None
