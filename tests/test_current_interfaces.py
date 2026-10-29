"""Current entry points expose real commands and preserve contract boundaries."""

import subprocess
import sys

import pytest
from pydantic import ValidationError

from blake.methods.models import Plane, ProjectionPassage, ResearchError, Role
from blake.methods import search


@pytest.mark.parametrize(
    ("arguments", "exit_code", "message"),
    ((("--help",), 0, "restore-drill"), (("--unknown-option",), 2, "No such option")),
)
def test_recovery_module_when_invoked_runs_click(
    arguments: tuple[str, ...], exit_code: int, message: str
) -> None:
    # Given the public recovery command module and a real Python process.
    command = [sys.executable, "-m", "blake.recovery_commands", *arguments]
    # When invoking help or an invalid option.
    result = subprocess.run(command, capture_output=True, text=True, timeout=30, check=False)
    # Then the real command parser responds, including its rejecting path.
    assert result.returncode == exit_code
    assert message in result.stdout + result.stderr


def test_schema_conversion_when_projection_is_not_strict_rejects() -> None:
    from blake.methods.schema_conversion import projection_to_bundle

    # Given a valid projection whose source locator is not a strict bundle URL.
    passage = ProjectionPassage(
        passage_id="synthetic",
        work_id="synthetic",
        author_id="synthetic",
        title="Synthetic",
        edition_id="synthetic",
        edition="Synthetic",
        locator="section 1",
        locator_kind="section",
        source_url="relative-source",
        rights="Synthetic",
        text_role=Role.PRIMARY,
        source_plane=Plane.READING,
        text="Synthetic text.",
    )
    # When explicitly converting to the strict bundle schema.
    # Then mismatched source contracts are refused.
    with pytest.raises(ValidationError):
        projection_to_bundle((passage,))


def test_public_span_implementation_preserves_downstream_unicode_contract() -> None:
    assert search.literal_spans(
        "Straße ﬃ", ("ss", "ffi"), whole_words=False
    ) == (("ss", 4, 5), ("ffi", 7, 8))
    assert search.literal_spans("Straße", ("s",), whole_words=False) == (("s", 0, 1),)
    assert search.literal_spans("text", (), whole_words=False) == ()
    with pytest.raises(ResearchError, match="empty_term"):
        search.literal_spans("text", ("",), whole_words=False)
