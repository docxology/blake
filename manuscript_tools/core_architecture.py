"""Source-derived retrieval profiles and declared responsibility boundaries.

This is a code diagnostic, independent of the retained analytical epoch. It
contains no source-provider expression and makes no application-result claims.
"""

import ast
import hashlib
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Final

from blake.methods.common import EvidenceError, FrozenModel
from blake.methods.producer import SourceBinding, source_hashes
from blake.methods.profiles import (
    ProfileDescription,
    RetrievalProfile,
    describe_profile,
)
from manuscript_tools.interval_illustration import interval_tokens


class ProfileOwner(FrozenModel):
    semantics: ProfileDescription
    entrypoint: str
    source_path: str


class Responsibility(FrozenModel):
    owner: str
    responsibility: str
    source_paths: tuple[str, ...]


class CoreArchitecture(FrozenModel):
    schema_version: str = "1"
    evidence_kind: str = "source-code diagnostic; no model inference"
    profiles: tuple[ProfileOwner, ...]
    responsibilities: tuple[Responsibility, ...]
    source_bindings: dict[str, str]
    source_binding_sha256: str


_ENTRYPOINTS: Final = {
    RetrievalProfile.REGEX_WORDS_V1: (
        "blake.methods.concordance.concordance_passages",
        "blake/methods/concordance.py",
    ),
    RetrievalProfile.LITERAL_CASEFOLD_V1: (
        "blake.methods.search.search_passages",
        "blake/methods/search.py",
    ),
    RetrievalProfile.NFKC_TOKENS_V2: (
        "blake.studies.scan_passages",
        "blake/studies.py",
    ),
}
_RESPONSIBILITIES: Final = (
    Responsibility(
        owner="Application policy",
        responsibility="Explicit forms, scope, review labels and interpretation",
        source_paths=(
            "blake/methods/annotations.py",
            "blake/methods/search_models.py",
            "blake/methods/projection_models.py",
        ),
    ),
    Responsibility(
        owner="Shared methods",
        responsibility=(
            "Validated schemas, retrieval, counting, interval support and tree layout"
        ),
        source_paths=(
            "blake/methods/profiles.py",
            "blake/methods/statistics.py",
            "blake/methods/hierarchy.py",
            "blake/methods/intervals.py",
        ),
    ),
    Responsibility(
        owner="Evidence adapters",
        responsibility="Caller-pinned source/copy identity, role and plane",
        source_paths=(
            "blake/applications.py",
            "blake/methods/corpus.py",
            "blake/methods/schema_conversion.py",
        ),
    ),
    Responsibility(
        owner="Publication preparation",
        responsibility="Explicit read root, saved epochs, computed tokens and figures",
        source_paths=(
            "manuscript_tools/paths.py",
            "manuscript_tools/publication.py",
            "manuscript_tools/variables.py",
            "manuscript_tools/figures.py",
            "manuscript_tools/method_types.py",
            "manuscript_tools/interval_illustration.py",
            "manuscript_tools/interval_figure.py",
            "manuscript_tools/figure_dispatch.py",
        ),
    ),
)


def build_core_architecture(source_root: Path) -> CoreArchitecture:
    """Bind profile declarations and responsibility references to current code bytes."""
    profiles = tuple(
        ProfileOwner(
            semantics=describe_profile(profile),
            entrypoint=_ENTRYPOINTS[profile][0],
            source_path=_ENTRYPOINTS[profile][1],
        )
        for profile in RetrievalProfile
    )
    paths = {p.source_path for p in profiles}
    paths.update(p for owner in _RESPONSIBILITIES for p in owner.source_paths)
    paths.update(
        (
            "blake/methods/common.py",
            "blake/methods/producer.py",
            "manuscript_tools/core_architecture.py",
            "manuscript_tools/core_profile_figure.py",
        )
    )
    bindings = source_hashes(
        tuple(
            SourceBinding(
                package,
                tuple(
                    sorted(
                        p[len(package) + 1 :]
                        for p in paths
                        if p.startswith(package + "/")
                    )
                ),
            )
            for package in ("blake", "manuscript_tools")
        )
    )
    for name, expected in bindings.items():
        path = source_root / name
        if any(p.is_symlink() for p in (path, *path.parents)) or not path.is_file():
            raise EvidenceError("architecture_source_missing", name)
        if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise EvidenceError("architecture_source_changed", name)
    for profile in profiles:
        definitions = ast.parse((source_root / profile.source_path).read_bytes()).body
        if not any(
            isinstance(item, ast.FunctionDef)
            and item.name == profile.entrypoint.rsplit(".", 1)[1]
            for item in definitions
        ):
            raise EvidenceError("architecture_entrypoint_missing", profile.entrypoint)
    payload = json.dumps(bindings, sort_keys=True, separators=(",", ":")).encode()
    return CoreArchitecture(
        profiles=profiles,
        responsibilities=_RESPONSIBILITIES,
        source_bindings=bindings,
        source_binding_sha256=hashlib.sha256(payload).hexdigest(),
    )


def architecture_tokens() -> Mapping[str, str]:
    """Compute manuscript quantities from the current executable source inventory."""
    evidence = build_core_architecture(Path(__file__).resolve().parents[1])
    return {
        "CORE_RETRIEVAL_PROFILE_COUNT": str(len(evidence.profiles)),
        "CORE_ARCHITECTURE_SOURCE_FILES": str(len(evidence.source_bindings)),
        "CORE_ARCHITECTURE_SOURCE_SHA256": evidence.source_binding_sha256,
        **interval_tokens(),
    }


CORE_FIGURE_BRIEF: Final = {
    "story_job": "Explain shared mechanisms and caller-owned research decisions.",
    "data_sources": ["blake/methods/profiles.py", "core_profile_ownership.json"],
    "claim": "Named retrieval contracts remain distinct and source-bound.",
    "encoding": "Directly labeled profile rows and responsibility lanes.",
    "caveat": (
        "Code diagnostic, not a fresh NLP run or a scientific application result."
    ),
    "static_mobile_fallback": "Static directly labeled PNG and companion SVG.",
    "qa_check": "Inspect final rendered text size and source-binding sidecar.",
    "accessibility_summary": (
        "Profiles list normalization and source spans; ownership lanes separate "
        "policy, methods, adapters and preparation."
    ),
    "statistical_question": (
        "Which contracts and responsibilities does this source candidate declare?"
    ),
    "data_shape": "Named profile records and source-file SHA-256 inventory.",
    "statistical_method": (
        "Exact enumeration and byte hashing; no statistical estimation."
    ),
    "missingness_or_scope": (
        "Public source mechanisms only; private decisions are not measured."
    ),
    "statistical_check": "All listed source bytes must match the imported producer.",
}


def core_figure_statistics() -> Mapping[str, str]:
    """Return quantities with the current source binding for the figure registry."""
    return architecture_tokens()


def fig_core_profile_ownership(analysis_output: Path, out_dir: Path) -> Path:
    """Keep the registered profile-figure entry point with its focused renderer."""
    from manuscript_tools.core_profile_figure import fig_core_profile_ownership as draw

    return draw(analysis_output, out_dir)
