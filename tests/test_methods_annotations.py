"""Real-file candidate identity controls without application policy imports."""

import csv
from pathlib import Path

import pytest

from blake.methods.annotations import (
    DecisionInput,
    ReviewQueueRow,
    csv_decisions,
    queue_identity,
    queue_row,
    validate_decision_membership,
)
from blake.methods.models import EvidenceError
from blake.studies import StudyHit


@pytest.fixture
def hit() -> StudyHit:
    return StudyHit(
        hit_id="a" * 64,
        term_id="term",
        group="group",
        passage_id="p",
        work_id="w",
        title="Synthetic",
        edition_id="e",
        copy_id=None,
        locator="section",
        source_url="https://example.org",
        rights="test",
        author_id="test",
        text_role="unverified",
        source_plane="reading",
        source_sha256=None,
        text_sha256="b" * 64,
        start=0,
        end=4,
        expression="test",
        context="test text",
        blake_primary=False,
    )


def write_rows(path, rows):
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(ReviewQueueRow.__annotations__))
        writer.writeheader()
        writer.writerows(rows)
    return path.read_bytes()


def test_roundtrip(hit, tmp_path: Path):
    row = queue_row(hit)
    assert len(queue_identity(row)) == 10
    raw = write_rows(tmp_path / "blank.csv", [row])
    assert csv_decisions(raw, (hit,), "c" * 64) == ()
    row.update(decision="accepted", reviewer="reader", rationale="synthetic")
    raw = write_rows(tmp_path / "edited.csv", [row])
    decisions = csv_decisions(b"\xef\xbb\xbf" + raw, (hit,), "c" * 64)
    validate_decision_membership(decisions, (hit,), "c" * 64)
    assert decisions[0].decision == "accepted"


@pytest.mark.parametrize("field", list(ReviewQueueRow.__annotations__)[:10])
def test_changed_immutable_even_blank(hit, tmp_path, field):
    row = queue_row(hit)
    row[field] += "changed"
    raw = write_rows(tmp_path / "changed.csv", [row])
    with pytest.raises(
        EvidenceError, match="csv_candidate_changed|unknown_or_duplicate_hit"
    ):
        csv_decisions(raw, (hit,), "c" * 64)


@pytest.mark.parametrize("field", ["reviewer", "rationale", "verification_locator"])
def test_partial(hit, tmp_path, field):
    row = queue_row(hit)
    row[field] = "partial"
    with pytest.raises(EvidenceError, match="partial_csv_annotation"):
        csv_decisions(write_rows(tmp_path / "partial.csv", [row]), (hit,), "c" * 64)


def test_duplicate(hit, tmp_path):
    with pytest.raises(EvidenceError, match="unknown_or_duplicate_hit"):
        csv_decisions(
            write_rows(tmp_path / "duplicate.csv", [queue_row(hit)] * 2),
            (hit,),
            "c" * 64,
        )


@pytest.mark.parametrize(
    "tail,code",
    [
        (b'"unterminated', "csv_format"),
        (b"x\n", "csv_row_width"),
        (b"," * 14 + b"\n", "csv_row_width"),
    ],
)
def test_malformed(hit, tail, code):
    raw = (",".join(ReviewQueueRow.__annotations__) + "\n").encode() + tail
    with pytest.raises(EvidenceError, match=code):
        csv_decisions(raw, (hit,), "c" * 64)


def test_header(hit):
    with pytest.raises(EvidenceError, match="csv_header"):
        csv_decisions(b"wrong\n", (hit,), "c" * 64)


@pytest.mark.parametrize(
    "mutation,code",
    [
        ("pin", "decision_run_pin"),
        ("unknown", "unknown_or_duplicate_hit"),
        ("duplicate", "unknown_or_duplicate_hit"),
    ],
)
def test_decision_pins(hit, mutation, code):
    decision = DecisionInput(
        run_sha256="d" * 64 if mutation == "pin" else "c" * 64,
        hit_id="unknown" if mutation == "unknown" else hit.hit_id,
        decision="accepted",
        reviewer="reader",
        rationale="test",
    )
    with pytest.raises(EvidenceError, match=code):
        validate_decision_membership(
            (decision,) * (2 if mutation == "duplicate" else 1), (hit,), "c" * 64
        )


def test_arbitrary_decision_counts():
    from blake.methods.annotations import count_decisions

    decision = DecisionInput(
        run_sha256="c" * 64,
        hit_id="x",
        decision="accepted",
        reviewer="reader",
        rationale="test",
    )
    result = count_decisions((decision,), 2, ("accepted", "deferred"))
    assert result.decisions == {"accepted": 1, "deferred": 0}
    assert result.unreviewed_hits == 1
    with pytest.raises(EvidenceError, match="unknown_decision"):
        count_decisions((decision,), 2, ("deferred",))
    with pytest.raises(EvidenceError, match="decision_count"):
        count_decisions((decision,), 0, ("accepted",))
