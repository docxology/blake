"""Source bindings and the source-derived publication figure have real controls."""

import hashlib
import json
import shutil
from pathlib import Path

import pytest
from PIL import Image

from blake.methods.common import EvidenceError
from blake.methods.schema_conversion import projection_to_bundle
from blake.methods.concordance import concordance_passages
from blake.methods.models import ProjectionPassage, QuerySpec
from blake.methods.profiles import RetrievalProfile
from blake.methods.search import search_passages
from blake.methods.search_models import SearchRequest
from blake.studies import StudySpec, StudyTerm, scan_passages
from manuscript_tools.core_architecture import (
    architecture_tokens,
    build_core_architecture,
    fig_core_profile_ownership,
)
from tests.test_methods_contracts import projection_pin, source_fields


def test_architecture_binds_every_named_source_and_entrypoint() -> None:
    root = Path(__file__).resolve().parents[1]
    evidence = build_core_architecture(root)
    assert len(evidence.profiles) == 3
    assert len({p.entrypoint for p in evidence.profiles}) == 3
    for relative, expected in evidence.source_bindings.items():
        assert hashlib.sha256((root / relative).read_bytes()).hexdigest() == expected
    assert (
        architecture_tokens()["CORE_ARCHITECTURE_SOURCE_SHA256"]
        == evidence.source_binding_sha256
    )


def test_missing_and_modified_sources_are_rejected(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    with pytest.raises(EvidenceError, match="architecture_source_missing"):
        build_core_architecture(tmp_path)
    evidence = build_core_architecture(root)
    for relative in evidence.source_bindings:
        destination = tmp_path / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(root / relative, destination)
    assert build_core_architecture(tmp_path) == evidence
    (tmp_path / "blake/methods/profiles.py").write_text("changed semantics")
    with pytest.raises(EvidenceError, match="architecture_source_changed"):
        build_core_architecture(tmp_path)


def test_code_figure_has_bound_sidecar_and_decodable_outputs(tmp_path: Path) -> None:
    output = tmp_path / "figures"
    path = fig_core_profile_ownership(tmp_path / "unused", output)
    with Image.open(path) as image:
        image.load()
        assert image.width > 1500 and image.height > 1000
    assert "<svg" in path.with_suffix(".svg").read_text()
    saved = json.loads(path.with_suffix(".json").read_bytes())
    expected = build_core_architecture(Path(__file__).resolve().parents[1])
    assert saved == expected.model_dump(mode="json")
    assert not (tmp_path / "unused").exists()


def test_semantic_profiles_disagree_on_their_declared_boundaries() -> None:
    """Synthetic counterexamples prevent treating named profiles as aliases."""
    passage = ProjectionPassage.model_validate(
        {**source_fields(), "text": "ß state,\nnation"}
    )
    regex = concordance_passages(
        (passage,),
        (QuerySpec(query_id="synthetic", variants=("ss",), note="test"),),
        projection_pin(),
        "Synthetic profile qualification only",
    )
    literal = search_passages((passage,), SearchRequest(terms=("ss",)))
    assert len(regex.hits) == 0
    assert literal.total_occurrences == 1
    phrase = search_passages((passage,), SearchRequest(terms=("state nation",)))
    normalized = scan_passages(
        projection_to_bundle((passage,)),
        StudySpec(
            study_id="synthetic",
            title="Synthetic profile qualification",
            terms=(
                StudyTerm(term_id="phrase", group="synthetic", forms=("state nation",)),
            ),
        ),
    )
    assert phrase.total_occurrences == 0
    assert len(normalized.hits) == 1
    with pytest.raises(ValueError):
        RetrievalProfile("undeclared-profile")
