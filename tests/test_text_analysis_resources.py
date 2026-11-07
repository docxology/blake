"""Exercise text analysis with the NLTK package but no local corpora."""
import asyncio

import pytest

from blake.analysis import text_analysis


def test_missing_nltk_data_uses_offline_fallbacks(monkeypatch):
    nltk = pytest.importorskip("nltk")

    def unexpected_download(*args, **kwargs):
        pytest.fail("analysis construction tried to download NLTK data")

    def missing(*args, **kwargs):
        raise LookupError("test resource is absent")

    class MissingStopwords:
        words = staticmethod(missing)

    monkeypatch.setattr(nltk, "download", unexpected_download)
    monkeypatch.setattr(text_analysis, "SPACY_AVAILABLE", False)
    monkeypatch.setattr(text_analysis, "SentimentIntensityAnalyzer", missing)
    monkeypatch.setattr(text_analysis, "sent_tokenize", missing)
    monkeypatch.setattr(text_analysis, "stopwords", MissingStopwords())
    analyzer = text_analysis.TextAnalyzer()
    text = "Words recur. Words return!"
    stats = asyncio.run(analyzer._analyze_basic_stats(text))
    style = asyncio.run(analyzer._analyze_style(text))
    concordance = asyncio.run(analyzer._analyze_concordance(text))
    assert stats["sentence_count"] == 2
    assert style["avg_sentence_length"] == 2
    assert concordance["keywords"] == [{"word": "words", "count": 2, "frequency": 0.5}]
    assert asyncio.run(analyzer._analyze_sentiment(text)) == {
        "error": "Local NLTK VADER data is unavailable"
    }


def test_sentence_analysis_uses_an_installed_nltk_tokenizer(monkeypatch):
    pytest.importorskip("nltk")
    monkeypatch.setattr(text_analysis, "sent_tokenize", lambda text: [text])
    assert text_analysis.TextAnalyzer._split_sentences("Dr. Blake.") == ["Dr. Blake."]
