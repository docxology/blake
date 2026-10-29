"""Characterize retained schemas without requiring any private application."""

import json
import subprocess
import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

from blake.methods.compatibility import bundle_to_projection, projection_to_bundle
from blake.methods.models import (
    Artifact,
    BundleCorpusPin,
    BundlePassage,
    Concordance,
    EvidenceError,
    FileReceipt,
    Plane,
    ProjectionCorpusPin,
    ProjectionPassage,
    QuerySpec,
    ResearchError,
    Role,
)
from blake.methods.profiles import (
    PROFILES,
    RetrievalProfile,
    describe_profile,
    runtime_profile,
)


def source_fields() -> dict:
    return dict(
        passage_id="p1",
        work_id="synthetic",
        author_id="william-blake-1757-1827",
        title="Synthetic source",
        edition_id="ed",
        edition="Synthetic edition",
        copy_id=None,
        locator="section 1",
        locator_kind="section",
        source_url="https://example.org/source",
        rights="Synthetic test fixture",
        text_role="primary",
        source_plane="reading",
        text="One term.",
        source_sha256=None,
    )


def projection_pin() -> ProjectionCorpusPin:
    return ProjectionCorpusPin(
        upstream_commit="recorded-identity",
        captured_manifest_sha256="a" * 64,
        projection_manifest_sha256="b" * 64,
        projection_relative_path="search/pinned",
        index_sha256="c" * 64,
        unresolved_images=0,
        scope_note="Synthetic fixture",
    )


def test_projection_roundtrip_retains_field_order_and_enum_values() -> None:
    original = source_fields()
    passage = ProjectionPassage.model_validate(original)
    assert passage.model_dump(mode="json") == original
    assert list(json.loads(passage.model_dump_json())) == list(original)
    assert str(passage.text_role) == "primary"
    assert str(passage.source_plane) == "reading"
    assert tuple(Role) == (Role.PRIMARY, Role.EDITORIAL, Role.UNVERIFIED)
    assert tuple(Plane) == (Plane.READING, Plane.ERDMAN, Plane.XML)
    assert ProjectionPassage.__name__ == "Passage"


def test_projection_keeps_permissive_boundary_while_bundle_is_strict() -> None:
    data = {**source_fields(), "source_url": "relative-source", "title": ""}
    passage = ProjectionPassage.model_validate(data)
    assert passage.source_url == "relative-source"
    with pytest.raises(ValidationError):
        BundlePassage.model_validate(data)
    with pytest.raises(ValidationError):
        projection_to_bundle((passage,))


def test_primary_source_plane_guard_keeps_legacy_error() -> None:
    with pytest.raises(ResearchError) as caught:
        ProjectionPassage.model_validate({**source_fields(), "source_plane": "xml"})
    assert caught.value.code == "primary_plane"
    assert caught.value.detail == "p1"
    assert not isinstance(caught.value, ValueError)


def test_explicit_conversion_preserves_source_membership_and_roles() -> None:
    strict = BundlePassage.model_validate(source_fields())
    projected = bundle_to_projection((strict,))
    assert projected[0].text_role == Role.PRIMARY
    assert projected[0].source_sha256 is None
    assert projection_to_bundle(projected) == (strict,)


def test_distinct_pin_contracts_do_not_guess_input_type() -> None:
    projection = projection_pin()
    bundle = BundleCorpusPin(
        bundle_manifest_sha256="d" * 64,
        captured_manifest_sha256="a" * 64,
        projection_manifest_sha256="b" * 64,
        index_sha256="c" * 64,
    )
    assert type(bundle) is not type(projection)
    assert type(bundle).__name__ == type(projection).__name__ == "CorpusPin"
    with pytest.raises(ValidationError):
        ProjectionCorpusPin.model_validate(bundle.model_dump())
    with pytest.raises(ValidationError):
        BundleCorpusPin.model_validate(projection.model_dump())


def test_receipts_accept_upstream_extra_metadata_but_pins_forbid_it() -> None:
    receipt = FileReceipt.model_validate(
        dict(path="source.bin", size=0, sha256="0" * 64, source_url="provider metadata")
    )
    assert set(receipt.model_dump()) == {"path", "size", "sha256"}
    with pytest.raises(ValidationError):
        ProjectionCorpusPin.model_validate(
            {**projection_pin().model_dump(), "unknown": 1}
        )


def test_query_and_artifact_boundaries_reject_invalid_membership() -> None:
    with pytest.raises(ValidationError):
        QuerySpec(query_id="q", variants=(), note="synthetic")
    with pytest.raises(ValidationError):
        Artifact(name="../escape.json", size=1, sha256="a" * 64)
    with pytest.raises(ValidationError):
        Artifact(name="safe.json", size=-1, sha256="a" * 64)


def test_generic_concordance_requires_application_owned_interpretation() -> None:
    fields = dict(
        pin=projection_pin(),
        query_sha256="e" * 64,
        scanned_source_documents=0,
        rows=(),
        hits=(),
    )
    with pytest.raises(ValidationError):
        Concordance.model_validate(fields)
    result = Concordance.model_validate({**fields, "interpretation": "Synthetic scope"})
    assert result.model_dump(mode="json")["interpretation"] == "Synthetic scope"


def test_error_ancestry_and_machine_codes_stay_distinct() -> None:
    evidence = EvidenceError("named_boundary", "detail")
    assert isinstance(evidence, ValueError)
    assert evidence.code == "named_boundary"
    assert evidence.detail == "detail"
    assert str(evidence) == "named_boundary: detail"
    assert not isinstance(ResearchError("code", "detail"), ValueError)


def test_profiles_are_explicit_immutable_and_bound_to_actual_runtime() -> None:
    assert len(PROFILES) == 3
    for profile in RetrievalProfile:
        assert describe_profile(profile).profile == profile
        binding = runtime_profile(profile)
        assert binding.semantics == describe_profile(profile)
        assert binding.python == ".".join(str(part) for part in sys.version_info[:3])
        assert binding.unicode
    with pytest.raises(TypeError):
        PROFILES[RetrievalProfile.REGEX_WORDS_V1] = describe_profile(
            RetrievalProfile.LITERAL_CASEFOLD_V1
        )


def test_public_contracts_import_without_private_or_acquisition_modules() -> None:
    root = Path(__file__).resolve().parents[1]
    script = (
        "import sys; sys.path.insert(0, sys.argv[1]); import blake.methods; "
        "assert not any(name.startswith(('blakean_federalism','blakean_entomology')) "
        "for name in sys.modules); assert 'blake.recovery' not in sys.modules"
    )
    result = subprocess.run(
        [sys.executable, "-I", "-c", script, str(root)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
