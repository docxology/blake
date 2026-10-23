"""The saved, identified result ledger owns manuscript model summaries."""

import hashlib
import json
from pathlib import Path

import pytest

from manuscript_tools.nlp_diagnostics import build_nlp_diagnostics


def seed_saved_results(root: Path) -> Path:
    texts = root / "blake_data/texts"
    texts.mkdir(parents=True)
    for identity in ("a", "b"):
        (texts / f"{identity}.txt").write_text("vision fire city prophet")
    output = root / "analysis_output"
    (output / "visualizations").mkdir(parents=True)
    (output / "visualizations/text_metrics.json").write_text(
        json.dumps([{"work_id": identity, "has_text": True} for identity in ("a", "b")])
    )
    (output / "analysis").mkdir()
    (output / "analysis/analysis_summary.json").write_text(
        json.dumps({"analysis_results_current": True})
    )
    records = []
    for identity, sentiment in (
        ("a", "positive"),
        ("b", "negative"),
        ("outside", "neutral"),
    ):
        records.append(
            {
                "work_id": identity,
                "results": {
                    "text_analysis": {
                        "sentiment": {"sentiment": sentiment},
                        "readability": {"flesch_reading_ease": 50.0},
                        "topics": {"n_topics": 2},
                    },
                    "ontological_analysis": {
                        "entities": [
                            {"text": "Los", "label": "MYTH", "mention_count": 3}
                        ]
                    },
                },
            }
        )
    path = output / "analysis/analysis_results.json"
    path.write_text(json.dumps(records))
    # Real analyzer filenames contain the title, not just the work identity.
    legacy = root / "blake_data/analysis"
    legacy.mkdir()
    (legacy / "a_alpha_text_analysis.json").write_text(
        json.dumps({"topics": {"n_topics": 99}})
    )
    return path


def test_model_summaries_use_identified_saved_results_and_exclude_other_members(
    tmp_path,
):
    path = seed_saved_results(tmp_path)
    result = build_nlp_diagnostics(tmp_path)
    assert result["entities"]["artifact_count"] == 2
    assert result["entities"]["mention_count"] == 6
    assert result["text_analysis"]["sentiment_counts"] == {"positive": 1, "negative": 1}
    assert result["text_analysis"]["topic_model_count"] == 4
    assert (
        result["sources"]["analysis_results_sha256"]
        == hashlib.sha256(path.read_bytes()).hexdigest()
    )


def test_selected_transcription_symlink_is_refused(tmp_path):
    seed_saved_results(tmp_path)
    path = tmp_path / "blake_data/texts/a.txt"
    outside = tmp_path / "outside.txt"
    path.rename(outside)
    path.symlink_to(outside)
    with pytest.raises(ValueError, match="escapes storage"):
        build_nlp_diagnostics(tmp_path)


@pytest.mark.parametrize(
    "problem", ["duplicate", "missing_member", "not_a_list", "missing_file"]
)
def test_current_saved_results_refuse_invalid_or_missing_identity(tmp_path, problem):
    path = seed_saved_results(tmp_path)
    rows = json.loads(path.read_text())
    if problem == "duplicate":
        rows.append(rows[0])
    elif problem == "missing_member":
        rows = rows[1:]
    elif problem == "not_a_list":
        rows = {"results": rows}
    if problem == "missing_file":
        path.unlink()
    else:
        path.write_text(json.dumps(rows))
    with pytest.raises(ValueError, match="[Ss]aved.*result"):
        build_nlp_diagnostics(tmp_path)
