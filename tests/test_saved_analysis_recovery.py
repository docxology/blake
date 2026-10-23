"""Saved analysis records are recoverable through the complete work API."""

import sqlite3
from pathlib import Path

from pydantic import ValidationError
import pytest

from blake.metadata.database import MetadataDatabase
from tests.export_fixtures import export_work


def stored_database(tmp_path: Path):
    database = MetadataDatabase(tmp_path / "metadata/metadata.db")
    work = export_work(tmp_path / "input", rich=False)
    work.metadata.processed = True
    database.save_work(work)
    return database, work


def test_work_load_restores_latest_analysis_without_changing_history(
    tmp_path: Path,
) -> None:
    database, work = stored_database(tmp_path)
    database.save_analysis_result(work.id, "text", {"version": 1})
    database.save_analysis_result(work.id, "text", {"version": 2})
    database.save_analysis_result(work.id, "visual", {"image": {"brightness": 0.5}})
    database.save_analysis_result(work.id, "cross", {"overlap": 0.25})
    database.save_analysis_result(work.id, "ontology", {"concepts": ["test"]})
    database.save_analysis_result(work.id, "external-note", {"custody": "retain"})
    before = database.load_analysis_results(work.id)
    loaded = database.load_work(work.id)
    assert loaded.text_analysis == {"version": 2}
    assert loaded.visual_analysis == {"image": {"brightness": 0.5}}
    assert loaded.cross_analysis == {"overlap": 0.25}
    assert loaded.ontological_analysis == {"concepts": ["test"]}
    assert loaded.fully_processed is True
    assert database.load_analysis_results(work.id) == before
    assert len(before) == 6


def test_equal_timestamps_select_the_last_saved_record(tmp_path: Path) -> None:
    database, work = stored_database(tmp_path)
    database.save_analysis_result(work.id, "text", {"version": 1})
    database.save_analysis_result(work.id, "text", {"version": 2})
    with sqlite3.connect(database.db_path) as connection:
        connection.execute(
            "UPDATE analysis_results SET timestamp = ?", ("2026-01-01T00:00:00",)
        )
    assert database.load_analysis_results(work.id, "text")[0]["results"] == {
        "version": 2
    }
    assert database.load_work(work.id).text_analysis == {"version": 2}


def test_invalid_persisted_analysis_is_not_silently_replaced_with_empty(
    tmp_path: Path,
) -> None:
    database, work = stored_database(tmp_path)
    database.save_analysis_result(work.id, "text", {"version": 1})
    with sqlite3.connect(database.db_path) as connection:
        connection.execute("UPDATE analysis_results SET results = ?", ("[]",))
    with pytest.raises(ValidationError):
        database.load_work(work.id)
    assert database.load_analysis_results(work.id)[0]["results"] == []
