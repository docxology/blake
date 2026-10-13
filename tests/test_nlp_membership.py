import json

from manuscript_tools.nlp_diagnostics import build_nlp_diagnostics


def test_nlp_diagnostics_excludes_stale_cache_and_reports_missing_members(tmp_path):
    text_dir = tmp_path / "blake_data" / "texts"
    analysis_dir = tmp_path / "blake_data" / "analysis"
    viz_dir = tmp_path / "analysis_output" / "visualizations"
    for directory in (text_dir, analysis_dir, viz_dir):
        directory.mkdir(parents=True)
    (viz_dir / "text_metrics.json").write_text(
        json.dumps(
            [
                {"work_id": "current", "has_text": True},
                {"work_id": "second", "has_text": True},
                {"work_id": "missing", "has_text": True},
                {"work_id": "filtered", "has_text": True},
                {"work_id": "image_only", "has_text": False},
            ]
        )
    )
    for work_id, text in {
        "current": "vision fire morning",
        "second": "vision shadow morning",
        "stale": "prophet flame shadow",
        "filtered": "the and with",
        "image_only": "old cached transcription",
    }.items():
        (text_dir / f"{work_id}.txt").write_text(text)
        (analysis_dir / f"{work_id}_text_analysis.json").write_text(
            json.dumps({"sentiment": {"sentiment": work_id}})
        )
        (analysis_dir / f"{work_id}_ontological_analysis.json").write_text(
            json.dumps({"entities": [{"text": work_id, "label": "PERSON"}]})
        )
    result = build_nlp_diagnostics(tmp_path)
    assert result["embedding"]["work_count"] == 2
    assert result["membership"]["embedded_work_ids"] == ["current", "second"]
    assert result["membership"]["excluded_cached_text_ids"] == ["image_only", "stale"]
    assert result["membership"]["missing_text_file_ids"] == ["missing"]
    assert result["membership"]["empty_or_filtered_text_ids"] == ["filtered"]
    assert len(result["membership"]["text_sha256"]["current"]) == 64
    assert result["entities"]["artifact_count"] == 3
    assert result["text_analysis"]["sentiment_counts"] == {
        "current": 1,
        "filtered": 1,
        "second": 1,
    }


def test_nlp_diagnostics_without_saved_membership_does_not_scan_cache(tmp_path):
    text_dir = tmp_path / "blake_data" / "texts"
    text_dir.mkdir(parents=True)
    (text_dir / "stale.txt").write_text("vision fire morning")
    result = build_nlp_diagnostics(tmp_path)
    assert result["embedding"]["work_count"] == 0
    assert result["membership"]["excluded_cached_text_ids"] == ["stale"]


def test_nlp_membership_requires_boolean_modality_and_preserves_legacy_rows(tmp_path):
    text_dir = tmp_path / "blake_data/texts"
    viz_dir = tmp_path / "analysis_output/visualizations"
    text_dir.mkdir(parents=True)
    viz_dir.mkdir(parents=True)
    rows = [
        {"work_id": "current", "has_text": True},
        {"work_id": "legacy"},
        {"work_id": "string_false", "has_text": "false"},
        {"work_id": "integer_one", "has_text": 1},
        {"work_id": "null_flag", "has_text": None},
    ]
    (viz_dir / "text_metrics.json").write_text(json.dumps(rows))
    for row in rows:
        (text_dir / f"{row['work_id']}.txt").write_text("vision fire morning")
    result = build_nlp_diagnostics(tmp_path)
    assert result["membership"]["text_work_ids"] == ["current", "legacy"]
    assert result["membership"]["excluded_cached_text_ids"] == [
        "integer_one",
        "null_flag",
        "string_false",
    ]
    assert result["embedding"]["work_count"] == 2
