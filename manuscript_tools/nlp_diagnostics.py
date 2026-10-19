from __future__ import annotations

import hashlib
import json
import math
import re
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

_TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z'-]{2,}")
_STOPWORDS = {
    "about",
    "after",
    "again",
    "against",
    "all",
    "also",
    "among",
    "and",
    "another",
    "any",
    "are",
    "because",
    "been",
    "before",
    "being",
    "but",
    "can",
    "could",
    "did",
    "does",
    "for",
    "from",
    "had",
    "has",
    "have",
    "her",
    "him",
    "his",
    "into",
    "its",
    "may",
    "more",
    "not",
    "now",
    "one",
    "only",
    "our",
    "out",
    "over",
    "shall",
    "she",
    "should",
    "such",
    "than",
    "that",
    "the",
    "their",
    "them",
    "then",
    "there",
    "these",
    "they",
    "this",
    "thou",
    "thy",
    "through",
    "was",
    "were",
    "what",
    "when",
    "where",
    "which",
    "who",
    "will",
    "with",
    "would",
    "you",
    "your",
}


def build_nlp_diagnostics(project_root: Path | str) -> dict[str, Any]:
    root = Path(project_root)
    membership_path = root / "analysis_output/visualizations/text_metrics.json"
    raw = membership_path.read_bytes() if membership_path.exists() else None
    text_metrics = json.loads(raw) if raw is not None else []
    if not isinstance(text_metrics, list) or any(not isinstance(row, dict) or not isinstance(row.get("work_id"), str) or not row["work_id"] for row in text_metrics):
        raise ValueError("Saved text metrics require identified work rows")
    if len({row["work_id"] for row in text_metrics}) != len(text_metrics):
        raise ValueError("Duplicate saved text work identity")
    title_by_id = {
        str(row.get("work_id")): str(row.get("title") or row.get("work_id"))
        for row in text_metrics
        if row.get("work_id")
    }
    # The saved run owns membership. Local caches can outlive that run.
    text_work_ids = {
        str(row["work_id"])
        for row in text_metrics
        if row.get("work_id") and row.get("has_text", True) is True
    }
    text_dir = root / "blake_data" / "texts"
    texts = _load_texts(text_dir, title_by_id, text_work_ids)
    loaded_ids = {doc["work_id"] for doc in texts}
    cached_ids = {path.stem for path in text_dir.glob("*.txt")}
    analysis_dir = root / "blake_data" / "analysis"

    return {
        "schema_version": "1.2",
        "generated_at": datetime.now().isoformat(),
        "sources": {
            "membership": "analysis_output/visualizations/text_metrics.json",
            "texts": "blake_data/texts/*.txt (saved-run text IDs only)",
            "text_analysis": "blake_data/analysis/*_text_analysis.json",
            "ontology": "blake_data/analysis/*_ontological_analysis.json",
        },
        "membership": {
            "source_sha256": hashlib.sha256(raw).hexdigest() if raw is not None else None,
            "legacy_modality_ids": sorted(row["work_id"] for row in text_metrics if "has_text" not in row),
            "invalid_modality_ids": sorted(row["work_id"] for row in text_metrics if "has_text" in row and type(row["has_text"]) is not bool),
            "text_work_ids": sorted(text_work_ids),
            "embedded_work_ids": sorted(loaded_ids),
            "excluded_cached_text_ids": sorted(cached_ids - text_work_ids),
            "missing_text_file_ids": sorted(text_work_ids - cached_ids),
            "empty_or_filtered_text_ids": sorted(
                (text_work_ids & cached_ids) - loaded_ids
            ),
            "text_sha256": {
                doc["work_id"]: hashlib.sha256(doc["text"].encode("utf-8")).hexdigest()
                for doc in texts
            },
        },
        "embedding": _build_tfidf_embedding(texts),
        "entities": _entity_summary(analysis_dir, text_work_ids),
        "text_analysis": _text_analysis_summary(analysis_dir, text_work_ids),
    }


def save_nlp_diagnostics(
    project_root: Path | str,
    diagnostics: dict[str, Any] | None = None,
) -> Path:
    root = Path(project_root)
    diagnostics = diagnostics or build_nlp_diagnostics(root)
    path = root / "analysis_output" / "data" / "nlp_diagnostics.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(diagnostics, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return path


def _read_json(path: Path, *, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def _load_texts(
    text_dir: Path, title_by_id: dict[str, str], work_ids: set[str]
) -> list[dict[str, Any]]:
    texts: list[dict[str, Any]] = []
    if not text_dir.exists():
        return texts
    for path in sorted(text_dir.glob("*.txt")):
        if path.stem not in work_ids:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        tokens = _tokenize(text)
        if not tokens:
            continue
        work_id = path.stem
        texts.append(
            {
                "work_id": work_id,
                "title": title_by_id.get(work_id, work_id),
                "text": text,
                "tokens": tokens,
                "word_count": len(tokens),
            }
        )
    return texts


def _tokenize(text: str) -> list[str]:
    return [
        token.lower().strip("'")
        for token in _TOKEN_RE.findall(text)
        if token.lower().strip("'") not in _STOPWORDS
    ]


def _build_tfidf_embedding(texts: list[dict[str, Any]]) -> dict[str, Any]:
    docs = [doc for doc in texts if doc.get("tokens")]
    if len(docs) < 2:
        return {
            "method": "tfidf_lsa_pca",
            "work_count": len(docs),
            "feature_count": 0,
            "variance_pc1": 0.0,
            "variance_pc2": 0.0,
            "points": [],
            "top_terms_pc1": [],
            "top_terms_pc2": [],
        }

    doc_counts = [Counter(doc["tokens"]) for doc in docs]
    document_frequency: Counter[str] = Counter()
    corpus_frequency: Counter[str] = Counter()
    for counts in doc_counts:
        corpus_frequency.update(counts)
        document_frequency.update(counts.keys())

    shared_terms = [
        term
        for term, _count in corpus_frequency.most_common()
        if document_frequency[term] >= 2
    ]
    if len(shared_terms) < 3:
        shared_terms = [term for term, _count in corpus_frequency.most_common()]
    terms = shared_terms[:120]
    if len(terms) < 2:
        return {
            "method": "tfidf_lsa_pca",
            "work_count": len(docs),
            "feature_count": len(terms),
            "variance_pc1": 0.0,
            "variance_pc2": 0.0,
            "points": [],
            "top_terms_pc1": terms,
            "top_terms_pc2": [],
        }

    idf = {
        term: math.log((1 + len(docs)) / (1 + document_frequency[term])) + 1
        for term in terms
    }
    vectors: list[list[float]] = []
    for counts in doc_counts:
        total = sum(counts.values()) or 1
        vector = [(counts.get(term, 0) / total) * idf[term] for term in terms]
        norm = math.sqrt(sum(value * value for value in vector)) or 1.0
        vectors.append([value / norm for value in vector])

    means = [
        sum(row[index] for row in vectors) / len(vectors) for index in range(len(terms))
    ]
    centered = [
        [value - means[index] for index, value in enumerate(row)] for row in vectors
    ]
    trace = _covariance_trace(centered)
    pc1 = _power_component(centered, [])
    lambda1 = _eigenvalue(centered, pc1)
    pc2 = _power_component(centered, [pc1])
    lambda2 = _eigenvalue(centered, pc2)

    points = []
    for doc, row in zip(docs, centered):
        points.append(
            {
                "work_id": doc["work_id"],
                "title": doc["title"],
                "word_count": doc["word_count"],
                "pc1": sum(value * weight for value, weight in zip(row, pc1)),
                "pc2": sum(value * weight for value, weight in zip(row, pc2)),
            }
        )

    return {
        "method": "tfidf_lsa_pca",
        "work_count": len(docs),
        "feature_count": len(terms),
        "variance_pc1": lambda1 / trace if trace > 0 else 0.0,
        "variance_pc2": lambda2 / trace if trace > 0 else 0.0,
        "points": points,
        "top_terms_pc1": _top_terms(terms, pc1),
        "top_terms_pc2": _top_terms(terms, pc2),
    }


def _covariance_trace(centered: list[list[float]]) -> float:
    if len(centered) < 2:
        return 0.0
    denominator = len(centered) - 1
    return sum(sum(value * value for value in row) for row in centered) / denominator


def _covariance_matvec(centered: list[list[float]], vector: list[float]) -> list[float]:
    if not centered:
        return [0.0 for _ in vector]
    denominator = max(len(centered) - 1, 1)
    result = [0.0 for _ in vector]
    for row in centered:
        projection = sum(value * weight for value, weight in zip(row, vector))
        for index, value in enumerate(row):
            result[index] += value * projection
    return [value / denominator for value in result]


def _power_component(
    centered: list[list[float]],
    orthogonal_to: list[list[float]],
    *,
    iterations: int = 80,
) -> list[float]:
    dimension = len(centered[0]) if centered else 0
    if dimension == 0:
        return []
    vector = [math.sin(index + 1.0) for index in range(dimension)]
    vector = _normalise(vector)
    for _ in range(iterations):
        updated = _covariance_matvec(centered, vector)
        for basis in orthogonal_to:
            dot = sum(value * weight for value, weight in zip(updated, basis))
            updated = [value - dot * weight for value, weight in zip(updated, basis)]
        vector = _normalise(updated)
    return vector


def _normalise(vector: list[float]) -> list[float]:
    norm = math.sqrt(sum(value * value for value in vector))
    if norm == 0:
        dimension = len(vector) or 1
        return [1.0 / math.sqrt(dimension) for _ in range(dimension)]
    return [value / norm for value in vector]


def _eigenvalue(centered: list[list[float]], vector: list[float]) -> float:
    if not vector:
        return 0.0
    transformed = _covariance_matvec(centered, vector)
    return max(sum(value * weight for value, weight in zip(vector, transformed)), 0.0)


def _top_terms(
    terms: list[str], component: list[float], *, limit: int = 8
) -> list[str]:
    ranked = sorted(
        zip(terms, component),
        key=lambda item: abs(item[1]),
        reverse=True,
    )
    return [term for term, _weight in ranked[:limit]]


def _entity_summary(analysis_dir: Path, work_ids: set[str]) -> dict[str, Any]:
    artifacts = sorted(
        path
        for path in analysis_dir.glob("*_ontological_analysis.json")
        if path.name.removesuffix("_ontological_analysis.json") in work_ids
    )
    entity_mentions: Counter[str] = Counter()
    label_counts: Counter[str] = Counter()
    works_with_entities = 0
    for path in artifacts:
        payload = _read_json(path, default={})
        ontology = (payload.get("results") or {}).get(
            "ontological_analysis"
        ) or payload.get("ontological_analysis")
        if not isinstance(ontology, dict):
            ontology = payload
        entities = ontology.get("entities") or []
        filtered = []
        for entity in entities:
            text = _normalise_entity(entity.get("text"))
            if not text:
                continue
            mentions = int(entity.get("mention_count") or 1)
            label = str(entity.get("label") or entity.get("type") or "UNLABELED")
            entity_mentions[text] += mentions
            label_counts[label] += mentions
            filtered.append(text)
        if filtered:
            works_with_entities += 1

    return {
        "artifact_count": len(artifacts),
        "works_with_entities": works_with_entities,
        "mention_count": sum(entity_mentions.values()),
        "distinct_entity_count": len(entity_mentions),
        "label_counts": dict(label_counts.most_common()),
        "top_entities": [
            {"text": text, "mentions": count}
            for text, count in entity_mentions.most_common(12)
        ],
    }


def _normalise_entity(value: object) -> str:
    text = " ".join(str(value or "").split())
    if not text or not any(character.isalpha() for character in text):
        return ""
    if len(text) > 64:
        return text[:61].rstrip() + "..."
    return text


def _text_analysis_summary(analysis_dir: Path, work_ids: set[str]) -> dict[str, Any]:
    artifacts = sorted(
        path
        for path in analysis_dir.glob("*_text_analysis.json")
        if path.name.removesuffix("_text_analysis.json") in work_ids
    )
    sentiment_counts: Counter[str] = Counter()
    flesch_scores: list[float] = []
    topic_count = 0
    for path in artifacts:
        payload = _read_json(path, default={})
        sentiment = (payload.get("sentiment") or {}).get("sentiment")
        if sentiment:
            sentiment_counts[str(sentiment).lower()] += 1
        readability = payload.get("readability") or {}
        if readability.get("flesch_reading_ease") is not None:
            flesch_scores.append(float(readability["flesch_reading_ease"]))
        topics = payload.get("topics") or {}
        topic_count += int(topics.get("n_topics") or len(topics.get("topics") or []))

    return {
        "artifact_count": len(artifacts),
        "sentiment_counts": dict(sentiment_counts),
        "mean_flesch_reading_ease": (
            sum(flesch_scores) / len(flesch_scores) if flesch_scores else 0.0
        ),
        "topic_model_count": topic_count,
    }


def validate_membership(diagnostics: dict[str, Any], *, publication: bool = False, coverage_count: int | None = None) -> dict[str, int]:
    """Reconcile eligible, loaded, missing and filtered work sets explicitly."""
    membership = diagnostics["membership"]
    names = ("text_work_ids", "embedded_work_ids", "missing_text_file_ids", "empty_or_filtered_text_ids", "excluded_cached_text_ids")
    groups = {}
    for name in names:
        values = membership[name]
        if not isinstance(values, list) or any(not isinstance(v, str) or not v for v in values) or len(values) != len(set(values)):
            raise ValueError("Invalid or duplicate diagnostic work identity")
        groups[name] = set(values)
    allowed, loaded, missing, filtered, excluded = (groups[name] for name in names)
    if loaded & missing or loaded & filtered or missing & filtered or allowed != loaded | missing | filtered or excluded & allowed:
        raise ValueError("NLP denominator sets do not reconcile")
    if coverage_count is not None and coverage_count != len(allowed):
        raise ValueError("Coverage count differs from saved text membership")
    if diagnostics["embedding"]["work_count"] != len(loaded):
        raise ValueError("Embedding count differs from its identified work set")
    if publication and (not membership.get("source_sha256") or membership.get("legacy_modality_ids") or membership.get("invalid_modality_ids")):
        raise ValueError("Publication requires hash-bound saved membership with explicit boolean modality")
    return {"saved": len(allowed), "embedded": len(loaded), "missing": len(missing), "filtered": len(filtered), "excluded": len(excluded)}
