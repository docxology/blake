"""Real immutable files and semantic-forgery controls for planned review batches."""

from __future__ import annotations

import csv
import io
import json
from pathlib import Path

import pytest

from blake.methods.annotations import csv_decisions
from blake.methods.models import EvidenceError
from blake.methods.review_batches import publish_review_batch, verify_review_batch
from blake.methods.runs import digest
from tests.review_planning_fixtures import make_hit
from tests.test_methods_review_planning import spec


def rebind_member(directory: Path, name: str) -> str:
    """Simulate a fully rehashed but semantically forged local batch."""
    data = json.loads((directory / "run.json").read_text())
    raw = (directory / name).read_bytes()
    for member in data["files"]:
        if member["name"] == name:
            member.update(size=len(raw), sha256=digest(raw))
    (directory / "run.json").write_text(json.dumps(data))
    return digest((directory / "run.json").read_bytes())


def test_roundtrip_when_a_fresh_unchanged_batch_is_verified(tmp_path):
    # Given: a real synthetic pool and a fresh output directory.
    hits = tuple(make_hit(i, str(i % 2), f"p{i}") for i in range(6))
    directory = tmp_path / "batch"
    receipt = publish_review_batch(hits, spec(), directory)
    pin = digest((directory / "run.json").read_bytes())
    # When: the caller supplies that exact receipt pin and original pool.
    verified = verify_review_batch(directory, pin, hits)
    # Then: checked models preserve provenance and the blank queue creates no decisions.
    assert verified.receipt == receipt
    assert verified.plan.spec == spec()
    assert (
        csv_decisions((directory / "review-queue.csv").read_bytes(), hits, "a" * 64)
        == ()
    )


def test_wrong_pin_when_the_batch_itself_is_valid(tmp_path):
    # Given: a successful unchanged batch and a different caller-held pin.
    hits = (make_hit(0, "alpha", "p0"),)
    directory = tmp_path / "batch"
    publish_review_batch(hits, spec(), directory)
    # When/Then: the exact valid file refuses at the receipt pin boundary.
    with pytest.raises(EvidenceError, match="review_run_pin"):
        verify_review_batch(directory, "f" * 64, hits)


def test_changed_pool_when_only_unselected_evidence_changes(tmp_path):
    # Given: a three-row pool and a one-row immutable batch.
    hits = tuple(make_hit(i, "alpha", f"p{i}") for i in range(3))
    directory = tmp_path / "batch"
    publish_review_batch(hits, spec(1), directory)
    pin = digest((directory / "run.json").read_bytes())
    index = next(
        i
        for i, h in enumerate(hits)
        if h.hit_id
        not in json.loads((directory / "plan.json").read_text())["selected_hit_ids"]
    )
    changed = tuple(
        h.model_copy(update={"context": "changed"}) if i == index else h
        for i, h in enumerate(hits)
    )
    # When/Then: integrity is over the full source pool, not merely selected rows.
    with pytest.raises(EvidenceError, match="review_batch_plan"):
        verify_review_batch(directory, pin, changed)


@pytest.mark.parametrize("name", ["hits.jsonl", "review-queue.csv", "plan.json"])
def test_checksum_refusal_when_a_declared_member_changes(tmp_path, name):
    # Given: a valid batch and original receipt pin.
    hits = (make_hit(0, "alpha", "p0"),)
    directory = tmp_path / "batch"
    publish_review_batch(hits, spec(), directory)
    pin = digest((directory / "run.json").read_bytes())
    (directory / name).write_bytes((directory / name).read_bytes() + b" ")
    # When/Then: even a syntactically harmless byte change refuses.
    with pytest.raises(EvidenceError, match="artifact_checksum"):
        verify_review_batch(directory, pin, hits)


def test_forged_hit_when_the_receipt_was_also_rehashed(tmp_path):
    # Given: changed source metadata plus a newly self-consistent artifact hash.
    hits = (make_hit(0, "alpha", "p0"),)
    directory = tmp_path / "batch"
    publish_review_batch(hits, spec(), directory)
    row = json.loads((directory / "hits.jsonl").read_text())
    row["locator"] = "invented locator"
    (directory / "hits.jsonl").write_text(json.dumps(row) + "\n")
    pin = rebind_member(directory, "hits.jsonl")
    # When/Then: independent original-pool membership still refuses the forgery.
    with pytest.raises(EvidenceError, match="review_batch_hits"):
        verify_review_batch(directory, pin, hits)


def test_forged_decision_when_the_queue_was_also_rehashed(tmp_path):
    # Given: authored-looking cells smuggled into a declared blank planning queue.
    hits = (make_hit(0, "alpha", "p0"),)
    directory = tmp_path / "batch"
    publish_review_batch(hits, spec(), directory)
    rows = list(
        csv.DictReader(io.StringIO((directory / "review-queue.csv").read_text()))
    )
    rows[0].update(decision="accepted", reviewer="reader", rationale="claim")
    with (directory / "review-queue.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    pin = rebind_member(directory, "review-queue.csv")
    # When/Then: a planning receipt cannot manufacture an adjudication.
    with pytest.raises(EvidenceError, match="review_batch_queue"):
        verify_review_batch(directory, pin, hits)


def test_forged_order_when_members_and_counts_still_agree(tmp_path):
    # Given: the same selected set with a different claimed planning order.
    hits = tuple(make_hit(i, "alpha", f"p{i}") for i in range(4))
    directory = tmp_path / "batch"
    publish_review_batch(hits, spec(), directory)
    data = json.loads((directory / "plan.json").read_text())
    data["selected_hit_ids"].reverse()
    (directory / "plan.json").write_text(json.dumps(data))
    pin = rebind_member(directory, "plan.json")
    # When/Then: the deterministic selection order is part of the checked contract.
    with pytest.raises(EvidenceError, match="review_batch_plan"):
        verify_review_batch(directory, pin, hits)


@pytest.mark.parametrize(
    "field,value",
    [
        ("source_run_sha256", "f" * 64),
        ("source_context_sha256", "f" * 64),
        ("source_pool_sha256", "f" * 64),
        ("candidate_hits", 5),
        ("selected_hits", 5),
    ],
)
def test_receipt_disagreement_when_declared_plan_bindings_change(
    tmp_path, field, value
):
    # Given: a valid plan and forged receipt values, pinned by a mistaken caller.
    hits = (make_hit(0, "alpha", "p0"),)
    directory = tmp_path / "batch"
    publish_review_batch(hits, spec(), directory)
    data = json.loads((directory / "run.json").read_text())
    data[field] = value
    (directory / "run.json").write_text(json.dumps(data))
    pin = digest((directory / "run.json").read_bytes())
    # When/Then: artifact checksums do not replace receipt/plan consistency.
    with pytest.raises(EvidenceError, match="review_batch_receipt"):
        verify_review_batch(directory, pin, hits)


def test_extra_member_when_the_directory_is_not_the_declared_batch(tmp_path):
    # Given: a complete batch with an undeclared extra member.
    hits = (make_hit(0, "alpha", "p0"),)
    directory = tmp_path / "batch"
    publish_review_batch(hits, spec(), directory)
    (directory / "extra.txt").write_text("undeclared")
    # When/Then: exact directory membership is enforced.
    with pytest.raises(EvidenceError, match="review_batch_membership"):
        verify_review_batch(
            directory, digest((directory / "run.json").read_bytes()), hits
        )


def test_occupied_output_when_existing_bytes_must_be_preserved(tmp_path):
    # Given: an occupied output with a retained sentinel.
    directory = tmp_path / "batch"
    directory.mkdir()
    (directory / "sentinel").write_bytes(b"retain")
    # When/Then: no batch publication can overwrite it.
    with pytest.raises(FileExistsError):
        publish_review_batch((make_hit(0, "alpha", "p0"),), spec(), directory)
    assert (directory / "sentinel").read_bytes() == b"retain"


def test_linked_artifact_when_the_target_bytes_would_have_matched(tmp_path):
    # Given: a real retained payload moved outside the batch and linked back.
    hits = (make_hit(0, "alpha", "p0"),)
    directory = tmp_path / "batch"
    publish_review_batch(hits, spec(), directory)
    original = directory / "hits.jsonl"
    retained = original.rename(tmp_path / "retained.jsonl")
    original.symlink_to(retained)
    # When/Then: matching bytes do not authorize a symlink artifact.
    with pytest.raises(EvidenceError, match="symlink_artifact"):
        verify_review_batch(
            directory, digest((directory / "run.json").read_bytes()), hits
        )


def test_invalid_pool_when_publication_has_not_reserved_output(tmp_path):
    # Given: a duplicate original identity and a fresh destination.
    hit = make_hit(0, "alpha", "p0")
    directory = tmp_path / "batch"
    # When/Then: rejection precedes any output reservation.
    with pytest.raises(EvidenceError, match="review_duplicate_hit"):
        publish_review_batch((hit, hit), spec(), directory)
    assert not directory.exists()
