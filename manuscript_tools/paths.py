"""Explicit authoring/output and read-only evidence roots for manuscript prep."""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Union

from blake.methods.common import EvidenceError


@dataclass(frozen=True)  # noqa: SLOTS_OK -- dataclass slots require Python 3.10.
class ManuscriptRoots:
    """Route writes to authoring; evidence supplies saved analytical inputs only."""

    authoring: Path
    evidence: Path

    @property
    def analysis(self) -> Path:
        return self.evidence / "analysis_output"

    @property
    def output(self) -> Path:
        return self.authoring / "output"


def manuscript_roots(
    project_root: Union[Path, str],
    evidence_root: Optional[Union[Path, str]] = None,
) -> ManuscriptRoots:
    """Resolve explicit roots once; never discover or substitute another capture.

    Defaults retain the single-project workflow. An explicit missing evidence
    root is an error even if the authoring tree has usable cached artifacts.
    Descendant-file custody remains enforced by the existing input verifiers.
    """
    if isinstance(evidence_root, str) and not evidence_root.strip():
        raise EvidenceError(
            "manuscript_blank_read_root", "Select a directory explicitly"
        )
    authoring = Path(project_root).absolute()
    evidence = (
        Path(evidence_root).absolute() if evidence_root is not None else authoring
    )
    for root in (authoring, evidence):
        if any(path.is_symlink() for path in (root, *root.parents)):
            raise EvidenceError("manuscript_root_symlink", str(root))
        if not root.is_dir():
            raise FileNotFoundError(root)
    return ManuscriptRoots(authoring=authoring.resolve(), evidence=evidence.resolve())
