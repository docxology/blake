"""Tests for blake.viz.generate_visualizations (moved from scripts/generate_visualizations.py)."""

from blake.viz.generate_visualizations import (
    generate_all_visualizations,
    load_corpus,
)

BODIES = [
    "The lamb and the child rejoice in innocence.\nJoy joy!\n",
    "Heaven and hell argue over fire and water.\nThe angel dreams of urizen!\n",
    "Los builds jerusalem with hammer and vision.\nAlbion wakes?\n",
]


def test_load_corpus_computes_lexical_statistics(tmp_path):
    (tmp_path / "songs_sample.txt").write_text(BODIES[0], encoding="utf-8")

    works = load_corpus(tmp_path)

    assert len(works) == 1
    work = works[0]
    assert work["name"] == "songs_sample"
    assert work["title"] == "Songs Sample"
    assert work["words"] == 12
    assert work["lines"] == 3
    assert work["sentences"] == 3
    assert work["words"] == 10
    assert work["unique_words"] == 8

def test_generate_all_visualizations_writes_all_figures(tmp_path):
    texts = tmp_path / "texts"
    texts.mkdir()
    for stem, body in zip(["a_work", "b_work", "c_work"], BODIES):
        (texts / f"{stem}.txt").write_text(body, encoding="utf-8")
    out = tmp_path / "visualizations"

    generate_all_visualizations(texts, out)

    expected = [
        "text/vocabulary_analysis.png",
        "text/word_frequency_analysis.png",
        "text/readability_analysis.png",
        "temporal/temporal_analysis.png",
        "network/network_analysis.png",
        "comparative/comparative_analysis.png",
        "image/image_analysis.png",
    ]
    for relpath in expected:
        assert (out / relpath).is_file(), relpath
