"""Create a fresh analysis store while preserving the captured source corpus."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import tempfile

from blake.metadata.database import MetadataDatabase
from blake.recovery_io import _safe_path


def prepare_analysis_epoch(project_root: Path, destination: str) -> Path:
    """Copy text and metadata; reference original images without copying their bytes."""
    root = project_root.resolve()
    source = _safe_path(root, "blake_data")
    target = _safe_path(root, destination)
    if target.exists() or not target.is_relative_to(source / "publication"):
        raise ValueError(
            "Analysis destination must be a new blake_data/publication directory"
        )
    database_path = _safe_path(source, "metadata/metadata.db")
    database_sha = hashlib.sha256(database_path.read_bytes()).hexdigest()
    works = MetadataDatabase(database_path).load_all_works()
    if not works:
        raise ValueError("No captured work records are available")
    target.parent.mkdir(parents=True, exist_ok=True)
    receipts = []
    with tempfile.TemporaryDirectory(prefix="epoch-", dir=target.parent) as temporary:
        stage = Path(temporary)
        database = MetadataDatabase(stage / "metadata/metadata.db")
        for original in works:
            work = original.model_copy(deep=True)
            if Path(work.id).name != work.id or work.id in (".", ".."):
                raise ValueError("Unsafe work identity in captured metadata")
            receipt = {"work_id": work.id, "has_text": bool(work.text_content)}
            if work.text_content:
                raw = work.text_content.encode("utf-8")
                relative = "texts/" + work.id + ".txt"
                path = stage / relative
                path.parent.mkdir(exist_ok=True)
                path.write_bytes(raw)
                work.metadata.file_path = target / relative
                work.metadata.file_size = len(raw)
                receipt.update(
                    {
                        "text_sha256": hashlib.sha256(raw).hexdigest(),
                        "text_path": relative,
                    }
                )
            for image in work.images:
                if image.file_path:
                    _safe_path(source, image.file_path.relative_to(source).as_posix())
            work.text_analysis = {}
            work.visual_analysis = {}
            work.cross_analysis = {}
            work.ontological_analysis = {}
            work.processing_errors = []
            work.fully_processed = False
            work.metadata.processed = False
            database.save_work(work)
            receipt["image_references"] = len(work.images)
            receipts.append(receipt)
        if hashlib.sha256(database_path.read_bytes()).hexdigest() != database_sha:
            raise ValueError("Captured metadata changed during analysis preparation")
        payload = {
            "schema_version": 1,
            "source_metadata_sha256": database_sha,
            "works": receipts,
            "images_copied": False,
            "source_corpus_modified": False,
        }
        (stage / "epoch-inputs.json").write_text(json.dumps(payload, indent=2))
        if target.exists():
            raise ValueError("Analysis destination became occupied")
        os.rename(stage, target)
    return target


def run_analysis_epoch(project_root: Path, data_dir: str, seed: int) -> Path:
    """Run a prepared epoch without overwriting a prior analysis output tree."""
    if type(seed) is not int or not 0 <= seed < 2**32:
        raise ValueError("Analysis seed must be an unsigned 32-bit integer")
    root = project_root.resolve()
    data = _safe_path(root, data_dir)
    if not data.is_relative_to(root / "blake_data/publication"):
        raise ValueError("Analysis requires a prepared publication data store")
    inputs = json.loads(_safe_path(data, "epoch-inputs.json").read_bytes())
    original = _safe_path(root, "blake_data/metadata/metadata.db")
    if (
        hashlib.sha256(original.read_bytes()).hexdigest()
        != inputs["source_metadata_sha256"]
    ):
        raise ValueError("Captured metadata changed after epoch preparation")
    output = _safe_path(root, "analysis_output")
    if output.exists() and any(output.iterdir()):
        raise ValueError(
            "Preserve existing analysis_output and use a fresh reproduction checkout"
        )
    os.environ.update(
        {
            "OPENBLAS_NUM_THREADS": "1",
            "OMP_NUM_THREADS": "1",
            "MKL_NUM_THREADS": "1",
            "HF_HUB_OFFLINE": "1",
            "TRANSFORMERS_OFFLINE": "1",
            "MPLBACKEND": "Agg",
        }
    )
    os.environ.setdefault("MPLCONFIGDIR", str(root / ".cache/matplotlib"))
    os.environ.setdefault("HF_HOME", str(root / ".cache/huggingface"))
    os.environ.setdefault("NLTK_DATA", str(root / "blake_data/nltk_data"))
    import asyncio
    import random
    import sys
    import time
    import cv2
    import numpy as np
    from blake import __version__
    from blake.corpus import BlakeCorpus, CorpusConfig
    from blake.corpus.saved_epoch import file_sha256
    from blake.recovery_io import _atomic_write

    protected = (
        "recovery/manifest.json",
        "recovery/search.sqlite",
        "recovery/passages.jsonl",
        "metadata/metadata.db",
    )
    before = {
        name: file_sha256(_safe_path(root / "blake_data", name)) for name in protected
    }
    closure = {
        str(path.relative_to(root)): file_sha256(path)
        for path in sorted((root / "blake").rglob("*"))
        if path.is_file() and path.suffix in {".py", ".json"}
    }
    for relative in (
        "uv.lock",
        "manuscript_tools/epoch.py",
        "manuscript_tools/nlp_diagnostics.py",
    ):
        closure[relative] = file_sha256(_safe_path(root, relative))
    np.random.seed(seed)
    random.seed(seed)
    cv2.setNumThreads(1)
    receipt = {
        "started": time.time(),
        "python": sys.version,
        "prefix": sys.prefix,
        "base_prefix": sys.base_prefix,
        "seed": seed,
        "source_bindings": closure,
        "protected_before": before,
        "software_at_analysis": __version__,
        "data_dir": str(data),
        "source_acquisition": False,
        "live_discovery": False,
    }
    receipt_path = _safe_path(output, "data/analysis_epoch_receipt.json")
    try:
        config = CorpusConfig(
            data_dir=data,
            output_dir=output,
            quick=True,
            fixture_mode="never",
            viz_profile="core",
            archive_scope="archive-inventory",
            image_mode="archive-all",
            image_dpi=300,
            max_images_per_work=None,
        )
        corpus = BlakeCorpus(data, output_dir=output, config=config)
        result = asyncio.run(corpus.run(config))
        receipt["pipeline"] = result.model_dump(mode="json")
        receipt["analysis_summary"] = json.loads(
            (output / "analysis/analysis_summary.json").read_bytes()
        )
        receipt["protected_after"] = {
            name: file_sha256(_safe_path(root / "blake_data", name))
            for name in protected
        }
        if receipt["protected_after"] != before or any(
            file_sha256(root / name) != digest for name, digest in closure.items()
        ):
            raise ValueError("Source or producer bytes changed during analysis")
        if result.status != "completed":
            raise ValueError("Analysis pipeline did not complete")
        receipt["status"] = "completed"
    except BaseException as exc:
        receipt.update({"status": "error", "error": repr(exc)})
        raise
    finally:
        receipt["seconds"] = time.time() - receipt["started"]
        _atomic_write(receipt_path, json.dumps(receipt, indent=2).encode())
    return receipt_path
