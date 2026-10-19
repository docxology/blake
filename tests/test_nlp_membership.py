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


def test_denominator_partition_and_source_binding(tmp_path):
    from manuscript_tools.nlp_diagnostics import validate_membership
    import hashlib
    root = tmp_path
    metrics = root / "analysis_output/visualizations/text_metrics.json"
    metrics.parent.mkdir(parents=True)
    text = root / "blake_data/texts"
    text.mkdir(parents=True)
    raw = json.dumps([{"work_id": "loaded", "has_text": True}, {"work_id": "missing", "has_text": True}, {"work_id": "filtered", "has_text": True}]).encode()
    metrics.write_bytes(raw)
    (text / "loaded.txt").write_text("vision morning shadows")
    (text / "filtered.txt").write_text("the and with")
    (text / "stale.txt").write_text("flame shadows")
    result = build_nlp_diagnostics(root)
    assert result["membership"]["source_sha256"] == hashlib.sha256(raw).hexdigest()
    assert validate_membership(result, publication=True) == {"saved": 3, "embedded": 1, "missing": 1, "filtered": 1, "excluded": 1}
    result["embedding"]["work_count"] = 2
    import pytest
    with pytest.raises(ValueError, match="Embedding count"):
        validate_membership(result, publication=True)


def test_duplicate_membership_and_implicit_publication_modality_fail(tmp_path):
    from manuscript_tools.nlp_diagnostics import validate_membership
    import pytest
    path = tmp_path / "analysis_output/visualizations/text_metrics.json"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps([{"work_id": "legacy"}]))
    result = build_nlp_diagnostics(tmp_path)
    assert validate_membership(result)["saved"] == 1
    with pytest.raises(ValueError, match="explicit boolean"):
        validate_membership(result, publication=True)
    path.write_text(json.dumps([{"work_id": "same", "has_text": True}] * 2))
    with pytest.raises(ValueError, match="Duplicate"):
        build_nlp_diagnostics(tmp_path)


def test_publication_rejects_cross_run_coverage_denominator(tmp_path):
    from manuscript_tools.nlp_diagnostics import validate_membership
    import pytest
    path = tmp_path / "analysis_output/visualizations/text_metrics.json"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps([{"work_id": "current", "has_text": True}]))
    result = build_nlp_diagnostics(tmp_path)
    with pytest.raises(ValueError, match="Coverage count"):
        validate_membership(result, publication=True, coverage_count=2)


def test_generated_manuscript_tokens_name_the_partition(tmp_path):
    from manuscript_tools.variables import generate_variables
    path = tmp_path / "analysis_output/visualizations/text_metrics.json"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps([{"work_id": "missing", "has_text": True}]))
    variables = generate_variables(tmp_path, require_analysis_outputs=False)
    assert variables["NLP_SAVED_TEXT_WORKS"] == "1"
    assert variables["NLP_EMBEDDING_WORKS"] == "0"
    assert variables["NLP_MISSING_TEXT_WORKS"] == "1"
    assert len(variables["NLP_MEMBERSHIP_SHA256"]) == 64
