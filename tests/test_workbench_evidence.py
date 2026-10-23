"""Workbench denominators and errors use the current pipeline contracts."""

from types import SimpleNamespace
import json

import pytest

from blake.corpus.visualizations import CorpusVisualizationBuilder


def test_represented_includes_duplicate_matches_while_resolution_remains_separate(
    tmp_path,
):
    builder = CorpusVisualizationBuilder(tmp_path)
    statuses = ["present", "partial", "duplicate", "missing", "unverified"]
    result = builder._dataset_statistics(
        {"target_coverage_matrix": [{"status": state} for state in statuses]},
        SimpleNamespace(target_total=5),
    )
    assert result["coverage"]["represented"] == 3
    assert result["coverage"]["represented_pct"] == 60.0
    assert result["coverage"]["unresolved"] == 4


def test_workbench_reports_nonzero_canonical_top_level_and_nested_errors(tmp_path):
    builder = CorpusVisualizationBuilder(tmp_path)
    result = builder._source_health_statistics(
        {
            "analysis_summary": {
                "error_count": 2,
                "error_ledger": [{"error": "one"}, {"error": "two"}],
            },
            "nested_component_error_count": 3,
        }
    )
    assert result["analysis_error_count"] == 2
    assert result["analysis_nested_error_count"] == 3


@pytest.mark.parametrize(
    "state", ["current", "stale", "missing", "malformed", "duplicate"]
)
def test_nested_errors_require_a_current_identified_ledger(tmp_path, state):
    (tmp_path / "data").mkdir()
    (tmp_path / "analysis").mkdir()
    (tmp_path / "data/source_audit.json").write_text("{}")
    (tmp_path / "analysis/analysis_summary.json").write_text(
        json.dumps(
            {
                "analysis_results_current": state != "stale",
                "error_count": 0,
            }
        )
    )
    row = {
        "work_id": "record",
        "results": {"text_analysis": {"topics": {"error": "short"}}},
    }
    path = tmp_path / "analysis/analysis_results.json"
    if state != "missing":
        path.write_text(
            "malformed"
            if state == "malformed"
            else json.dumps([row, row] if state == "duplicate" else [row])
        )
    builder = CorpusVisualizationBuilder(tmp_path)
    if state == "duplicate":
        with pytest.raises(ValueError, match="Duplicate"):
            builder._source_health()
    else:
        health = builder._source_health()
        assert health["nested_component_error_count"] == (
            1 if state == "current" else None
        )
        assert "analysis_results" not in health
