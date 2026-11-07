"""Admit new analysis writes without relabeling retained result stores."""

from __future__ import annotations

import hashlib
import json
import platform
import stat
import tomllib
from importlib import metadata
from pathlib import Path
from typing import Any

from .version import __version__

PRODUCER_SIDECAR = ".analysis-producer.json"
MAX_PROFILE_BYTES = 64 * 1024


class AnalysisProducerError(ValueError):
    """New analysis would overwrite an unbound or incompatible producer epoch."""


_SOURCES = (
    "version.py",
    "analysis_producer.py",
    "analysis/analyzer.py",
    "analysis/text_analysis.py",
    "analysis/visual_analysis.py",
    "analysis/cross_analysis.py",
    "analysis/ontology.py",
    "corpus/pipeline.py",
    "metadata/database.py",
)


def _sha256(path: Path) -> str:
    if path.is_symlink() or not path.is_file():
        raise AnalysisProducerError("Analysis producer source is unavailable or linked")
    digest = hashlib.sha256()
    try:
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError as exc:
        raise AnalysisProducerError("Analysis producer source is unavailable") from exc
    return digest.hexdigest()


def _loaded_model(engine: Any) -> dict[str, Any]:
    model = getattr(engine, "nlp", None)
    if model is None:
        return {"status": "unavailable"}
    meta = getattr(model, "meta", {})
    if not isinstance(meta, dict):
        raise AnalysisProducerError("Analysis producer model metadata is malformed")
    record: dict[str, Any] = {"status": "loaded"}
    for key in ("name", "version", "lang"):
        value = meta.get(key)
        if value is not None and (not isinstance(value, str) or len(value) > 256):
            raise AnalysisProducerError("Analysis producer model identity is malformed")
        record[key] = value
    pipes = getattr(model, "pipe_names", ())
    if not isinstance(pipes, (list, tuple)):
        raise AnalysisProducerError("Analysis producer model components are malformed")
    pipes = list(pipes)
    if len(pipes) > 128 or any(
        not isinstance(p, str) or not p.strip() or len(p) > 256 for p in pipes
    ):
        raise AnalysisProducerError("Analysis producer model components are malformed")
    record["pipeline"] = pipes
    return record


def capture_installed_producer(*, analyzer: Any = None) -> dict[str, Any]:
    """Observe installed and already-loaded identities, without initializing models."""
    package = Path(__file__).resolve().parent
    manifest = package.parent / "pyproject.toml"
    if manifest.exists() or manifest.is_symlink():
        _sha256(manifest)
        with manifest.open("rb") as stream:
            raw = stream.read(1024 * 1024 + 1)
        if len(raw) > 1024 * 1024:
            raise AnalysisProducerError("Analysis producer manifest is oversized")
        try:
            declared = tomllib.loads(raw.decode("utf-8"))
        except (ValueError, UnicodeError) as exc:
            raise AnalysisProducerError(
                "Analysis producer manifest is malformed"
            ) from exc
        project = declared.get("project")
        if isinstance(project, dict) and project.get("name") == "blake":
            metadata_root = package.parent
        else:
            metadata_root = package / "_resources"
    else:
        metadata_root = package / "_resources"
    versions = {}
    for name in (
        "numpy",
        "spacy",
        "thinc",
        "en-core-web-sm",
        "pillow",
        "pyarrow",
        "opencv-python",
        "scikit-image",
        "scikit-learn",
        "scipy",
        "nltk",
        "networkx",
        "torch",
        "transformers",
        "pandas",
        "pydantic",
        "blis",
        "confection",
        "cymem",
        "murmurhash",
        "preshed",
        "srsly",
        "tokenizers",
        "safetensors",
        "huggingface-hub",
    ):
        try:
            versions[name] = metadata.version(name)
        except metadata.PackageNotFoundError:
            versions[name] = None
    context = {
        "schema_version": 1,
        "software_version": __version__,
        "python": {
            "implementation": platform.python_implementation(),
            "version": platform.python_version(),
        },
        "packages": versions,
        "source_files": {"blake/" + name: _sha256(package / name) for name in _SOURCES},
        "manifest_sha256": _sha256(metadata_root / "pyproject.toml"),
        "lock_sha256": _sha256(metadata_root / "uv.lock"),
        "loaded_models": {
            name: (
                _loaded_model(getattr(analyzer, attribute, None))
                if analyzer is not None
                else {"status": "not_observed"}
            )
            for name, attribute in (
                ("text", "text_analyzer"),
                ("ontology", "ontology_manager"),
            )
        },
    }
    producer_fingerprint(context)
    return context


def producer_fingerprint(context: dict[str, Any]) -> str:
    if (
        not isinstance(context, dict)
        or type(context.get("schema_version")) is not int
        or context["schema_version"] != 1
    ):
        raise AnalysisProducerError("Unsupported analysis producer profile")
    try:
        raw = json.dumps(
            context, sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode()
    except (ValueError, TypeError, RecursionError) as exc:
        raise AnalysisProducerError("Analysis producer profile is malformed") from exc
    if len(raw) > MAX_PROFILE_BYTES - 1024:
        raise AnalysisProducerError("Analysis producer profile is oversized")
    return hashlib.sha256(raw).hexdigest()


def _pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result = {}
    for key, value in pairs:
        if key in result:
            raise AnalysisProducerError("Duplicate analysis producer profile key")
        result[key] = value
    return result


def _roots(data_dir: Path | None, output_dir: Path | None) -> list[Path]:
    roots = []
    for selected in (data_dir, output_dir):
        if selected is None:
            continue
        root = Path(selected).absolute()
        if root.is_symlink() or (root.exists() and not root.is_dir()):
            raise AnalysisProducerError(
                "Analysis producer store must be a real directory"
            )
        if root.resolve() not in [p.resolve() for p in roots]:
            roots.append(root)
    return roots


def _read_profile(path: Path, context: dict[str, Any]) -> None:
    try:
        info = path.lstat()
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
            raise AnalysisProducerError(
                "Analysis producer profile must be an independent regular file"
            )
        with path.open("rb") as stream:
            raw = stream.read(MAX_PROFILE_BYTES + 1)
    except OSError as exc:
        raise AnalysisProducerError("Analysis producer profile is unavailable") from exc
    if len(raw) > MAX_PROFILE_BYTES:
        raise AnalysisProducerError("Analysis producer profile is oversized")
    try:
        record = json.loads(raw, object_pairs_hook=_pairs)
    except (ValueError, UnicodeError, RecursionError) as exc:
        raise AnalysisProducerError("Analysis producer profile is malformed") from exc
    if (
        not isinstance(record, dict)
        or set(record) != {"schema_version", "producer", "fingerprint"}
        or type(record["schema_version"]) is not int
        or record["schema_version"] != 1
        or record["fingerprint"] != producer_fingerprint(record["producer"])
        or record["fingerprint"] != producer_fingerprint(context)
    ):
        raise AnalysisProducerError(
            "Analysis producer differs; use a fresh analysis epoch"
        )


def validate_analysis_destinations(
    data_dir: Path | None,
    output_dir: Path | None,
    context: dict[str, Any],
    *,
    existing_selected_results: bool = False,
) -> None:
    """Read-only preflight; legacy reads never call this new-write admission."""
    producer_fingerprint(context)
    for root in _roots(data_dir, output_dir):
        if output_dir is not None and root.resolve() == Path(output_dir).resolve():
            if (root / "data").is_symlink():
                raise AnalysisProducerError(
                    "Analysis producer output data must be a real directory"
                )
            for name in ("publication_epoch.json", "derived_epoch_receipt.json"):
                marker = root / "data" / name
                if marker.exists() or marker.is_symlink():
                    raise AnalysisProducerError(
                        "A sealed analysis epoch cannot be reused for writes"
                    )
        analysis = root / "analysis"
        if analysis.is_symlink() or (analysis.exists() and not analysis.is_dir()):
            raise AnalysisProducerError(
                "Analysis producer result store must be a real directory"
            )
        sidecar = root / PRODUCER_SIDECAR
        if sidecar.exists() or sidecar.is_symlink():
            _read_profile(sidecar, context)
        else:
            retained_database = False
            if data_dir is not None and root.resolve() == Path(data_dir).resolve():
                from .metadata.database import MetadataDatabase

                try:
                    retained_database = MetadataDatabase.has_retained_analysis(
                        root / "metadata" / "metadata.db"
                    )
                except (ValueError, OSError) as exc:
                    raise AnalysisProducerError(
                        "Analysis producer cannot admit the retained database"
                    ) from exc
            if (
                (analysis.exists() and any(analysis.iterdir()))
                or retained_database
                or (
                    data_dir is not None
                    and root.resolve() == Path(data_dir).resolve()
                    and existing_selected_results
                )
            ):
                raise AnalysisProducerError(
                    "Unbound retained analysis requires a fresh analysis epoch"
                )


def record_new_producer_sidecar(
    data_dir: Path | None, output_dir: Path | None, context: dict[str, Any]
) -> None:
    """Reserve only admitted fresh stores.

    Existing matching receipts stay byte-identical.
    """
    from .methods.common import ResearchError
    from .methods.storage import write_new

    validate_analysis_destinations(data_dir, output_dir, context)
    record = {
        "schema_version": 1,
        "producer": context,
        "fingerprint": producer_fingerprint(context),
    }
    raw = json.dumps(record, indent=2, allow_nan=False) + "\n"
    if len(raw.encode()) > MAX_PROFILE_BYTES:
        raise AnalysisProducerError("Analysis producer profile is oversized")
    for root in _roots(data_dir, output_dir):
        sidecar = root / PRODUCER_SIDECAR
        if not sidecar.exists() and not sidecar.is_symlink():
            root.mkdir(parents=True, exist_ok=True)
            try:
                write_new(sidecar, raw)
            except ResearchError as exc:
                if exc.code != "occupied_output":
                    raise
        _read_profile(sidecar, context)


def has_retained_analysis(work: Any) -> bool:
    return any(
        bool(getattr(work, name, None))
        for name in (
            "text_analysis",
            "visual_analysis",
            "cross_analysis",
            "ontological_analysis",
        )
    )


def producer_metadata(context: dict[str, Any]) -> dict[str, Any]:
    return {
        "analysis_producer": context,
        "analysis_producer_fingerprint": producer_fingerprint(context),
    }
