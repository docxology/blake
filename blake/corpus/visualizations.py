from __future__ import annotations

from collections import Counter
import html
import json
import math
from pathlib import Path
import re
from typing import Any, Dict, List, Optional

from ..models import BlakeWork
from ..version import version_info
from .models import CorpusManifest
from .network import build_theme_entity_network
from .result_errors import component_errors

_TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z'\\-]*")
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
    "between",
    "both",
    "but",
    "bentley",
    "can",
    "could",
    "did",
    "does",
    "erdman",
    "every",
    "for",
    "from",
    "had",
    "has",
    "have",
    "her",
    "him",
    "his",
    "how",
    "into",
    "its",
    "like",
    "may",
    "more",
    "most",
    "not",
    "now",
    "off",
    "one",
    "only",
    "our",
    "out",
    "over",
    "own",
    "page",
    "pages",
    "same",
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
    "those",
    "through",
    "upon",
    "was",
    "were",
    "what",
    "when",
    "where",
    "which",
    "while",
    "who",
    "will",
    "with",
    "would",
    "you",
    "your",
}


def _language_tokens(text: str) -> List[str]:
    tokens: List[str] = []
    for match in _TOKEN_RE.finditer(text.lower().replace("\u2019", "'")):
        token = match.group(0).strip("'-")
        if len(token) > 1:
            tokens.append(token)
    return tokens


def _lexical_tokens(tokens: List[str]) -> List[str]:
    return [token for token in tokens if len(token) > 2 and token not in _STOPWORDS]


def _bigram_counts(tokens: List[str]) -> Counter[str]:
    return Counter(
        f"{left} {right}" for left, right in zip(tokens, tokens[1:]) if left != right
    )


def _top_bigrams(tokens: List[str], limit: int = 8) -> List[Dict[str, Any]]:
    counts = _bigram_counts(tokens)
    return [
        {"phrase": phrase, "count": count}
        for phrase, count in counts.most_common(limit)
    ]


def _authority_tier(work: BlakeWork) -> str:
    analysis = work.metadata.analysis_results or {}
    tier = analysis.get("source_authority_tier")
    if tier:
        return str(tier)
    source_value = getattr(work.metadata.source, "value", work.metadata.source)
    if str(source_value) == "blake_archive":
        return "archive_primary"
    if analysis.get("validated_fallback_text"):
        return "fallback_text_validated"
    return "corroborating_or_legacy"


def _image_depth_payload(work: BlakeWork) -> Dict[str, Any]:
    analysis = work.metadata.analysis_results or {}
    depth = analysis.get("image_depth")
    return dict(depth) if isinstance(depth, dict) else {}


def _pct(part: int | float, total: int | float) -> float:
    return round((float(part) / float(total) * 100.0), 1) if total else 0.0


def _numeric_summary(values: List[int | float]) -> Dict[str, int | float]:
    clean = sorted(float(value) for value in values)
    if not clean:
        return {
            "n": 0,
            "min": 0,
            "median": 0,
            "q1": 0,
            "q3": 0,
            "iqr": 0,
            "mean": 0,
            "max": 0,
        }
    count = len(clean)
    midpoint = count // 2
    median = (
        clean[midpoint] if count % 2 else (clean[midpoint - 1] + clean[midpoint]) / 2
    )

    def percentile(position: float) -> float:
        if count == 1:
            return clean[0]
        index = (count - 1) * position
        lower = math.floor(index)
        upper = math.ceil(index)
        if lower == upper:
            return clean[int(index)]
        return clean[lower] + (clean[upper] - clean[lower]) * (index - lower)

    q1 = percentile(0.25)
    q3 = percentile(0.75)
    return {
        "n": count,
        "min": round(clean[0], 3),
        "median": round(median, 3),
        "q1": round(q1, 3),
        "q3": round(q3, 3),
        "iqr": round(q3 - q1, 3),
        "mean": round(sum(clean) / count, 3),
        "max": round(clean[-1], 3),
    }


def _counter_rows(
    counter: Counter[str], *, total: int | None = None
) -> List[Dict[str, Any]]:
    denominator = int(total if total is not None else sum(counter.values()))
    return [
        {"label": label, "count": int(count), "share_pct": _pct(count, denominator)}
        for label, count in counter.most_common()
    ]


class CorpusVisualizationBuilder:
    def __init__(self, output_dir: Path):
        self.output_dir = Path(output_dir)
        self.visualization_dir = self.output_dir / "visualizations"
        self.visualization_dir.mkdir(parents=True, exist_ok=True)

    def generate(
        self,
        works: List[BlakeWork],
        manifest: CorpusManifest,
        *,
        profile: str = "core",
        available_visualizations: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        available_visualizations = available_visualizations or []
        datasets = self._build_datasets(works, manifest)
        artifacts: Dict[str, str] = {}

        inventory_path = self.visualization_dir / "visualization_inventory.json"
        self._write_json(inventory_path, available_visualizations)
        artifacts["visualization_inventory"] = str(inventory_path)

        if profile == "inventory":
            summary = {
                "status": "completed",
                "profile": profile,
                "works_available": len(works),
                "available_visualizations": available_visualizations,
                "datasets": [],
                "artifacts": artifacts,
                "visualizations_generated": 0,
            }
            self._write_json(
                self.visualization_dir / "visualization_summary.json", summary
            )
            return summary

        dataset_artifacts = self._write_datasets(datasets)
        artifacts.update(dataset_artifacts)

        coverage_png = self._render_coverage_chart(manifest)
        if coverage_png:
            artifacts["coverage_chart_png"] = str(coverage_png)

        html_path = self._write_workbench_html(datasets, manifest, profile)
        artifacts["corpus_workbench_html"] = str(html_path)

        summary = {
            "status": "completed",
            "profile": profile,
            "works_available": len(works),
            "target_profile": manifest.target_profile,
            "coverage_status": manifest.coverage_status,
            "coverage_counts": manifest.coverage_counts,
            "dataset_statistics": datasets.get("dataset_statistics", {}),
            "available_visualizations": available_visualizations,
            "datasets": sorted(datasets.keys()),
            "artifacts": artifacts,
            "visualizations_generated": len(artifacts),
        }
        summary_path = self.visualization_dir / "visualization_summary.json"
        self._write_json(summary_path, summary)
        summary["artifacts"]["visualization_summary"] = str(summary_path)
        self._write_json(summary_path, summary)
        return summary

    def _build_datasets(
        self, works: List[BlakeWork], manifest: CorpusManifest
    ) -> Dict[str, Any]:
        datasets = {
            "target_coverage_matrix": [
                record.model_dump(mode="json") for record in manifest.target_records
            ],
            "chronology": self._chronology(works),
            "source_provenance_coverage": self._source_provenance(works, manifest),
            "text_metrics": self._text_metrics(works),
            "lexical_signature": self._lexical_signature(works),
            "image_metrics": self._image_metrics(works),
            "image_depth": self._image_depth(works, manifest),
            "source_authority_tiers": self._source_authority_tiers(works),
            "theme_entity_network": self._theme_entity_network(works),
            "text_image_linkage": self._text_image_linkage(works),
            "work_gallery_index": self._work_gallery(works),
            "pipeline_architecture": self._pipeline_architecture(),
            "source_health": self._source_health(),
        }
        datasets["dataset_statistics"] = self._dataset_statistics(datasets, manifest)
        return datasets

    def _dataset_statistics(
        self, datasets: Dict[str, Any], manifest: CorpusManifest
    ) -> Dict[str, Any]:
        coverage_rows = datasets.get("target_coverage_matrix") or []
        text_rows = datasets.get("text_metrics") or []
        text_bearing = [row for row in text_rows if row.get("has_text")]
        linkage_rows = datasets.get("text_image_linkage") or []
        image_depth_rows = datasets.get("image_depth") or []
        authority_rows = datasets.get("source_authority_tiers") or []
        source_health = datasets.get("source_health") or {}

        coverage_counts = Counter(
            str(row.get("status") or "unknown") for row in coverage_rows
        )
        unresolved_statuses = {"partial", "missing", "unverified", "duplicate"}
        unresolved = sum(coverage_counts.get(status, 0) for status in unresolved_statuses)
        represented = sum(
            coverage_counts.get(state, 0) for state in ("present", "partial", "duplicate")
        )
        category_unresolved: Counter[str] = Counter()
        for row in coverage_rows:
            if str(row.get("status") or "") in unresolved_statuses:
                category_unresolved[
                    str(row.get("category") or "uncategorized").replace("_", " ")
                ] += 1

        word_counts = [int(row.get("word_count") or 0) for row in text_bearing]
        lexical_density = [float(row.get("lexical_density") or 0.0) for row in text_bearing]
        signature = datasets.get("lexical_signature") or {}
        image_counts = [int(row.get("image_count") or 0) for row in linkage_rows]

        resolved_counts = [
            int(row.get("resolved_object_count") or 0) for row in image_depth_rows
        ]
        downloaded_counts = [
            int(
                row.get("local_image_count")
                if row.get("local_image_count") is not None
                else row.get("downloaded_image_count") or 0
            )
            for row in image_depth_rows
        ]
        depth_status_counts = Counter(
            str(row.get("image_depth_status") or "unrecorded") for row in image_depth_rows
        )
        failure_total = sum(int(row.get("failure_count") or 0) for row in image_depth_rows)
        authority_counts = Counter(
            {
                str(row.get("authority_tier") or "unrecorded"): int(
                    row.get("work_count") or 0
                )
                for row in authority_rows
            }
        )
        authority_total = sum(authority_counts.values()) or len(linkage_rows)

        return {
            "schema_version": "1.0",
            "scope_note": (
                "Descriptive local-run statistics over a target-aware partial corpus; "
                "no confidence intervals or population-level inference are implied."
            ),
            "coverage": {
                "target_total": manifest.target_total,
                "present": int(coverage_counts.get("present", 0)),
                "represented": int(represented),
                "represented_pct": _pct(represented, manifest.target_total),
                "unresolved": int(unresolved),
                "unresolved_pct": _pct(unresolved, manifest.target_total),
                "status_counts": _counter_rows(
                    coverage_counts, total=manifest.target_total
                ),
                "category_unresolved": _counter_rows(category_unresolved, total=unresolved),
            },
            "text": {
                "local_work_total": len(text_rows),
                "text_work_count": len(text_bearing),
                "text_work_pct": _pct(len(text_bearing), len(text_rows)),
                "total_words": int(sum(word_counts)),
                "word_count_summary": _numeric_summary(word_counts),
                "lexical_density_summary": _numeric_summary(lexical_density),
                "lexical_token_count": int(signature.get("lexical_token_count") or 0),
                "distinct_terms": int(signature.get("distinct_terms") or 0),
                "top_terms": list(signature.get("top_terms") or [])[:10],
            },
            "images": {
                "local_work_total": len(linkage_rows),
                "works_with_images": sum(1 for value in image_counts if value > 0),
                "zero_image_works": sum(1 for value in image_counts if value == 0),
                "linked_image_total": int(sum(image_counts)),
                "image_count_summary": _numeric_summary(image_counts),
            },
            "image_depth": {
                "work_count": len(image_depth_rows),
                "resolved_object_total": int(sum(resolved_counts)),
                "downloaded_image_total": int(sum(downloaded_counts)),
                "downloaded_vs_resolved_pct": _pct(
                    sum(downloaded_counts), sum(resolved_counts)
                ),
                "status_counts": _counter_rows(
                    depth_status_counts, total=len(image_depth_rows)
                ),
                "failure_total": int(failure_total),
                "resolved_summary": _numeric_summary(resolved_counts),
                "downloaded_summary": _numeric_summary(downloaded_counts),
            },
            "source_authority": {
                "local_work_total": int(authority_total),
                "tier_counts": _counter_rows(authority_counts, total=authority_total),
            },
            "missingness": {
                "unresolved_targets": int(unresolved),
                "missing_targets": int(coverage_counts.get("missing", 0)),
                "partial_targets": int(coverage_counts.get("partial", 0)),
                "zero_image_works": sum(1 for value in image_counts if value == 0),
                "text_missing_works": len(text_rows) - len(text_bearing),
                "image_depth_failures": int(failure_total),
            },
            "source_health": self._source_health_statistics(source_health),
        }

    def _source_health(self) -> Dict[str, Any]:
        path = self.output_dir / "data" / "source_audit.json"
        if not path.exists():
            return {
                "provider_discovery": {"providers": [], "failure_count": 0},
                "archive_metadata_enrichment": {},
                "checked_urls": [],
                "missing_evidence_summary": {},
                "acquisition_review": {},
                "analysis_summary": {},
            }
        try:
            audit = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return {
                "provider_discovery": {"providers": [], "failure_count": 0},
                "archive_metadata_enrichment": {},
                "checked_urls": [],
                "missing_evidence_summary": {},
                "acquisition_review": {},
                "analysis_summary": {},
                "error": "source audit could not be read",
            }
        live = audit.get("live") or {}
        review_path = self.output_dir / "data" / "evidence_acquisition_review.json"
        analysis_path = self.output_dir / "analysis" / "analysis_summary.json"
        analysis_summary = self._read_optional_json(analysis_path, {})
        results = self._read_optional_json(
            self.output_dir / "analysis/analysis_results.json", None
        )
        nested_count = (
            len(component_errors(results))
            if isinstance(results, list)
            and analysis_summary.get("analysis_results_current") is True
            else None
        )
        return {
            "provider_discovery": audit.get("provider_discovery") or {},
            "archive_metadata_enrichment": (
                audit.get("metadata_enrichment_report")
                or live.get("archive_metadata_enrichment")
                or {}
            ),
            "checked_urls": live.get("checked_urls") or [],
            "missing_evidence_summary": audit.get("missing_evidence_summary") or {},
            "acquisition_review": self._read_optional_json(review_path, {}),
            "analysis_summary": analysis_summary,
            "nested_component_error_count": nested_count,
        }

    def _source_health_statistics(self, source_health: Dict[str, Any]) -> Dict[str, Any]:
        provider_discovery = source_health.get("provider_discovery") or {}
        providers = provider_discovery.get("providers") or []
        provider_failures = [
            row for row in providers if str(row.get("status") or "") != "completed"
        ]
        archive_report = source_health.get("archive_metadata_enrichment") or {}
        checked_urls = source_health.get("checked_urls") or []
        missing_summary = source_health.get("missing_evidence_summary") or {}
        acquisition_review = source_health.get("acquisition_review") or {}
        analysis_summary = source_health.get("analysis_summary") or {}
        review_candidates = [
            candidate
            for target_review in acquisition_review.get("target_reviews", [])
            for candidate in target_review.get("candidates", [])
        ]
        manual_candidates = [
            candidate
            for candidate in review_candidates
            if str(candidate.get("lead_status") or "") == "manual_review"
            or str(candidate.get("action_taken") or "").startswith("manual_review:")
            or str(candidate.get("status") or "") == "manual_review"
        ]
        analysis_errors = (
            analysis_summary.get("error_ledger") or analysis_summary.get("errors") or []
        )
        ok_urls = sum(1 for row in checked_urls if row.get("ok"))
        return {
            "provider_count": int(
                provider_discovery.get("provider_count") or len(providers)
            ),
            "provider_failure_count": int(
                provider_discovery.get("failure_count") or len(provider_failures)
            ),
            "provider_record_count": int(provider_discovery.get("record_count") or 0),
            "provider_failures": provider_failures,
            "checked_urls": len(checked_urls),
            "ok_urls": ok_urls,
            "ok_url_pct": _pct(ok_urls, len(checked_urls)),
            "archive_metadata_status": str(archive_report.get("status") or "unknown"),
            "archive_metadata_attempted": int(archive_report.get("attempted") or 0),
            "archive_metadata_succeeded": int(archive_report.get("succeeded") or 0),
            "archive_metadata_failed": int(archive_report.get("failed") or 0),
            "archive_metadata_skipped_after_budget": int(
                archive_report.get("skipped_after_budget") or 0
            ),
            "archive_metadata_disabled_reason": archive_report.get("disabled_reason"),
            "archive_metadata_fallback_source": archive_report.get("fallback_source_used"),
            "missing_evidence_targets": int(missing_summary.get("target_count") or 0),
            "missing_evidence_candidates": int(missing_summary.get("candidate_count") or 0),
            "acquisition_review_schema_version": str(
                acquisition_review.get("schema_version") or "unavailable"
            ),
            "acquisition_review_unresolved_targets": int(
                acquisition_review.get("unresolved_target_count") or 0
            ),
            "acquisition_review_candidate_count": int(
                acquisition_review.get("candidate_count") or len(review_candidates)
            ),
            "manual_review_candidate_count": len(manual_candidates),
            "analysis_status": str(analysis_summary.get("status") or "unknown"),
            "analysis_results_current": bool(
                analysis_summary.get("analysis_results_current")
            ),
            "analysis_works_analyzed": int(analysis_summary.get("works_analyzed") or 0),
            "analysis_works_total": int(analysis_summary.get("works_total") or 0),
            "analysis_error_count": int(
                analysis_summary.get("error_count", len(analysis_errors))
            ),
            "analysis_nested_error_count": source_health.get(
                "nested_component_error_count"
            ),
        }

    def _read_optional_json(self, path: Path, default: Any) -> Any:
        if not path.exists():
            return default
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return default

    def _write_datasets(self, datasets: Dict[str, Any]) -> Dict[str, str]:
        artifacts = {}
        for name, data in datasets.items():
            path = self.visualization_dir / f"{name}.json"
            self._write_json(path, data)
            artifacts[name] = str(path)
        return artifacts

    def _render_coverage_chart(self, manifest: CorpusManifest) -> Optional[Path]:
        try:
            import matplotlib

            matplotlib.use("Agg")
            import matplotlib.pyplot as plt
        except Exception:
            return None

        counts = {
            key: manifest.coverage_counts.get(key, 0)
            for key in ["present", "partial", "unverified", "missing", "duplicate"]
        }
        path = self.visualization_dir / "target_coverage_matrix.png"
        fig, ax = plt.subplots(figsize=(8, 4.5))
        colors = ["#009E73", "#E69F00", "#0072B2", "#8A8F8A", "#D55E00"]
        ax.bar(list(counts.keys()), list(counts.values()), color=colors)
        ax.set_title("Blake Corpus Target Coverage")
        ax.set_ylabel("Target entries")
        ax.set_xlabel("Coverage status")
        ax.spines[["top", "right"]].set_visible(False)
        for index, value in enumerate(counts.values()):
            ax.text(index, value + 0.05, str(value), ha="center", va="bottom")
        fig.tight_layout()
        fig.savefig(path, dpi=144)
        plt.close(fig)
        return path

    def _write_workbench_html(
        self,
        datasets: Dict[str, Any],
        manifest: CorpusManifest,
        profile: str,
    ) -> Path:
        stats = datasets.get("dataset_statistics") or {}
        coverage_stats = stats.get("coverage") or {}
        text_stats = stats.get("text") or {}
        image_stats = stats.get("images") or {}
        depth_stats = stats.get("image_depth") or {}
        authority_stats = stats.get("source_authority") or {}
        source_stats = stats.get("source_health") or {}

        def esc(value: Any) -> str:
            return html.escape("" if value is None else str(value))

        def fmt(value: Any) -> str:
            if isinstance(value, float):
                return f"{value:,.1f}"
            if isinstance(value, int):
                return f"{value:,}"
            return esc(value)

        def stat_card(label: str, value: Any, note: str = "") -> str:
            return (
                '<div class="stat">'
                f"<span>{esc(label)}</span>"
                f"<strong>{fmt(value)}</strong>"
                f"<small>{esc(note)}</small>"
                "</div>"
            )

        def chip(label: Any) -> str:
            value = "" if label is None else str(label)
            css = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-") or "unknown"
            return f'<span class="chip chip-{esc(css)}">{esc(value.replace("_", " "))}</span>'

        def bar_cell(value: int | float, total: int | float, label: str = "") -> str:
            pct = _pct(value, total)
            text = label or f"{fmt(value)} ({pct:.1f}%)"
            return (
                '<div class="barcell">'
                f'<span style="width:{max(0.0, min(pct, 100.0)):.1f}%"></span>'
                f"<strong>{esc(text)}</strong>"
                "</div>"
            )

        def image_count_value(row: Dict[str, Any]) -> int:
            return int(
                row.get("local_image_count") or row.get("downloaded_image_count") or 0
            )

        def depth_row_html(row: Dict[str, Any]) -> str:
            downloaded = image_count_value(row)
            resolved = int(row.get("resolved_object_count") or 0)
            return (
                "<tr>"
                f"<td>{esc(row.get('title') or row.get('work_id'))}</td>"
                f"<td>{esc(str(row.get('category') or '').replace('_', ' '))}</td>"
                f"<td>{chip(row.get('image_depth_status') or 'unrecorded')}</td>"
                f"<td>{bar_cell(downloaded, depth_denominator, f'{downloaded:,}/{resolved:,}')}</td>"
                f"<td>{fmt(int(row.get('failure_count') or 0))}</td>"
                "</tr>"
            )

        category_rows = "\n".join(
            "<tr>"
            f"<td>{esc(row.get('label'))}</td>"
            f"<td>{bar_cell(int(row.get('count') or 0), int(coverage_stats.get('unresolved') or 0))}</td>"
            "</tr>"
            for row in coverage_stats.get("category_unresolved", [])[:12]
        )
        authority_rows = "\n".join(
            "<tr>"
            f"<td>{chip(row.get('label'))}</td>"
            f"<td>{bar_cell(int(row.get('count') or 0), int(authority_stats.get('local_work_total') or 0))}</td>"
            "</tr>"
            for row in authority_stats.get("tier_counts", [])
        )
        provider_rows = "\n".join(
            "<tr>"
            f"<td>{esc(row.get('provider'))}</td>"
            f"<td>{chip(row.get('status') or 'unknown')}</td>"
            f"<td>{fmt(int(row.get('record_count') or 0))}</td>"
            f"<td>{esc(row.get('error') or '')}</td>"
            "</tr>"
            for row in (datasets.get("source_health") or {})
            .get("provider_discovery", {})
            .get("providers", [])
        )
        depth_denominator = max(
            [image_count_value(row) for row in datasets.get("image_depth", [])] + [1]
        )
        depth_rows = "\n".join(
            depth_row_html(row)
            for row in sorted(
                datasets.get("image_depth", []),
                key=image_count_value,
                reverse=True,
            )[:24]
        )
        coverage_rows = "\n".join(
            "<tr>"
            f"<td>{esc(row.get('target_id'))}</td>"
            f"<td>{esc(row.get('title'))}</td>"
            f"<td>{esc(str(row.get('category') or '').replace('_', ' '))}</td>"
            f"<td>{chip(row.get('status'))}</td>"
            f"<td>{esc(', '.join(row.get('matched_work_ids') or []))}</td>"
            f"<td>{esc('; '.join(row.get('notes') or []))}</td>"
            "</tr>"
            for row in datasets["target_coverage_matrix"]
        )
        work_rows = "\n".join(
            "<tr>"
            f"<td>{esc(row.get('id'))}</td>"
            f"<td>{esc(row.get('title'))}</td>"
            f"<td>{esc(row.get('work_type'))}</td>"
            f"<td>{esc(row.get('date'))}</td>"
            f"<td>{chip(row.get('source_authority_tier'))}</td>"
            f"<td>{chip(row.get('image_depth_status') or 'unrecorded')}</td>"
            f"<td>{fmt(int(row.get('image_count') or 0))}</td>"
            "</tr>"
            for row in datasets["work_gallery_index"]
        )
        signature = datasets.get("lexical_signature") or {}
        lexical_rows = "\n".join(
            "<tr>"
            f"<td>{esc(row.get('term'))}</td>"
            f"<td>{bar_cell(int(row.get('count') or 0), int(signature.get('lexical_token_count') or 0))}</td>"
            f"<td>{fmt(int(row.get('document_frequency') or 0))}</td>"
            "</tr>"
            for row in (signature.get("top_terms") or [])[:14]
        )
        phrase_rows = "\n".join(
            "<tr>"
            f"<td>{esc(row.get('phrase'))}</td>"
            f"<td>{fmt(int(row.get('count') or 0))}</td>"
            "</tr>"
            for row in (signature.get("top_bigrams") or [])[:10]
        )
        payload = json.dumps(datasets, ensure_ascii=False).replace("</", "<\\/")
        software = version_info()
        document = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Blake Corpus Workbench</title>
  <meta name="blake-version" content="{esc(software['package_version'])}">
  <meta name="blake-methods-profile" content="{esc(software['methods_profile'])}">
  <meta name="blake-dashboard-schema" content="{esc(software['dashboard_schema_version'])}">
  <style>
    :root {{ color-scheme: light; --ink:#20242a; --muted:#5f625d; --line:#d8d2c4; --bg:#fcfaf4; --panel:#f7f2e8; --green:#009E73; --gold:#E69F00; --red:#D55E00; --blue:#0072B2; --violet:#7A4FA3; --slate:#34495E; }}
    * {{ box-sizing: border-box; }}
    body {{ font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; margin: 0; color: var(--ink); background: var(--bg); }}
    header {{ padding: 18px 24px; background: var(--slate); color: white; }}
    header h1 {{ margin: 0 0 4px; font-size: 24px; letter-spacing: 0; }}
    header p {{ margin: 0; color: #e5e2da; }}
    main {{ display: grid; grid-template-columns: minmax(260px, 360px) minmax(0, 1fr); gap: 18px; padding: 18px 24px 28px; }}
    aside, section {{ background: var(--panel); border: 1px solid var(--line); border-radius: 6px; padding: 14px; min-width: 0; }}
    section {{ margin-bottom: 16px; }}
    h2 {{ margin: 0 0 10px; font-size: 16px; }}
    h3 {{ margin: 16px 0 8px; font-size: 14px; }}
    p.note {{ margin: 0 0 12px; color: var(--muted); font-size: 13px; line-height: 1.45; }}
    .statgrid {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px; }}
    .stat {{ border: 1px solid var(--line); border-radius: 6px; padding: 8px; background: #fffdf8; min-height: 78px; }}
    .stat span {{ display: block; color: var(--muted); font-size: 12px; }}
    .stat strong {{ display: block; margin-top: 2px; font-size: 21px; }}
    .stat small {{ display: block; margin-top: 3px; color: var(--muted); font-size: 11px; line-height: 1.25; }}
    .tablewrap {{ overflow-x: auto; max-width: 100%; border: 1px solid var(--line); border-radius: 6px; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 13px; min-width: 620px; }}
    th, td {{ border-bottom: 1px solid #e7dece; padding: 7px 8px; text-align: left; vertical-align: middle; }}
    th {{ background: #eee5d5; color: var(--ink); font-size: 12px; text-transform: uppercase; }}
    tr:last-child td {{ border-bottom: 0; }}
    .chip {{ display: inline-block; min-width: 64px; border-radius: 999px; padding: 2px 8px; font-size: 12px; text-align: center; border: 1px solid var(--line); background: #fffdf8; color: var(--ink); }}
    .chip-present, .chip-complete, .chip-archive-primary {{ background: #e2f2ec; border-color: #75c3aa; color: #005b43; }}
    .chip-partial, .chip-corroborating-or-legacy {{ background: #fff0cc; border-color: #d59b18; color: #5b3b00; }}
    .chip-missing, .chip-failed {{ background: #f7ded2; border-color: #d55e00; color: #752700; }}
    .chip-fallback-text-validated, .chip-unverified {{ background: #dceef8; border-color: #0072b2; color: #004c78; }}
    .barcell {{ position: relative; min-width: 130px; height: 24px; border-radius: 4px; background: #fffdf8; overflow: hidden; border: 1px solid #e7dece; }}
    .barcell span {{ position: absolute; inset: 0 auto 0 0; background: #b9ddd2; }}
    .barcell strong {{ position: relative; display: block; padding: 3px 6px; font-size: 12px; color: var(--ink); }}
    .stack {{ display: grid; gap: 16px; min-width: 0; }}
    @media (max-width: 860px) {{ main {{ grid-template-columns: 1fr; padding: 12px; }} header {{ padding: 16px; }} .statgrid {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }} table {{ font-size: 12px; min-width: 560px; }} }}
    @media (max-width: 520px) {{ .statgrid {{ grid-template-columns: 1fr; }} header h1 {{ font-size: 20px; }} }}
  </style>
</head>
<body>
  <header>
    <h1>Blake Corpus Workbench</h1>
    <p>Software: {esc(software['package_version'])}. Methods: {esc(software['methods_profile'])}. Dashboard schema: {esc(software['dashboard_schema_version'])}.</p>
    <p>Profile: {esc(profile)}. Target: {esc(manifest.target_profile)}. Coverage: {esc(manifest.coverage_status)}. Run: {esc(manifest.run_id)}.</p>
    <p>Records are source/copy records. Image associations can reuse physical files. Represented targets include present, partial and duplicate matches; unresolved states include every non-present target. Saved discovery observations do not refresh provider health during offline reuse.</p>
  </header>
  <main>
    <aside>
      <h2>Dataset Statistics</h2>
      <p class="note">Descriptive local-run statistics for a target-aware partial corpus. These are census/run diagnostics, not confidence intervals.</p>
      <div class="statgrid">
        {stat_card("Target entries", coverage_stats.get("target_total", manifest.target_total), f"{coverage_stats.get('represented_pct', 0):.1f}% represented")}
        {stat_card("Unresolved targets", coverage_stats.get("unresolved", 0), f"{coverage_stats.get('unresolved_pct', 0):.1f}% of target ledger")}
        {stat_card("Text records", text_stats.get("text_work_count", 0), f"{text_stats.get('text_work_pct', 0):.1f}% of local records")}
        {stat_card("Total words", text_stats.get("total_words", 0), "local text-bearing records")}
        {stat_card("Image associations", image_stats.get("linked_image_total", 0), f"{image_stats.get('works_with_images', 0)} image-bearing records")}
        {stat_card("Image depth", depth_stats.get("downloaded_image_total", 0), f"{depth_stats.get('downloaded_vs_resolved_pct', 0):.1f}% downloaded/resolved")}
        {stat_card("Analysis current", "yes" if source_stats.get("analysis_results_current") else "no", f"{source_stats.get('analysis_works_analyzed', 0):,}/{source_stats.get('analysis_works_total', 0):,} records; {source_stats.get('analysis_error_count', 0)} top-level errors")}
        {stat_card("Nested component errors", source_stats.get("analysis_nested_error_count") if source_stats.get("analysis_nested_error_count") is not None else "unavailable", "Explicit nested result fields; separate from top-level completion")}
        {stat_card("Review candidates", source_stats.get("acquisition_review_candidate_count", 0), f"{source_stats.get('manual_review_candidate_count', 0)} manual-review leads")}
        {stat_card("Non-completed discovery observations", source_stats.get("provider_failure_count", 0), f"{source_stats.get('provider_count', 0)} saved provider observations")}
        {stat_card("Archive metadata", f"{source_stats.get('archive_metadata_succeeded', 0)}/{source_stats.get('archive_metadata_attempted', 0)}", source_stats.get("archive_metadata_status", "unknown"))}
      </div>
      <h3>Unresolved By Category</h3>
      <div class="tablewrap"><table>
        <thead><tr><th>Category</th><th>Unresolved share</th></tr></thead>
        <tbody>{category_rows}</tbody>
      </table></div>
      <h3>Authority Tiers</h3>
      <div class="tablewrap"><table>
        <thead><tr><th>Tier</th><th>Record share</th></tr></thead>
        <tbody>{authority_rows}</tbody>
      </table></div>
      <h3>Source Discovery Health</h3>
      <p class="note">Archive work records are built from the target ledger and GitHub XML inventory; live Archive API metadata is opportunistic enrichment.</p>
      <div class="tablewrap"><table>
        <thead><tr><th>Provider</th><th>Status</th><th>Records</th><th>Error</th></tr></thead>
        <tbody>{provider_rows}</tbody>
      </table></div>
    </aside>
    <div class="stack">
      <section>
        <h2>Lexical Signature</h2>
        <p class="note">Top terms include corpus counts and document frequency. Stopword filtering and local text availability shape these rankings.</p>
        <div class="tablewrap"><table>
          <thead><tr><th>Term</th><th>Lexical-token share</th><th>Documents</th></tr></thead>
          <tbody>{lexical_rows}</tbody>
        </table></div>
        <h3>Frequent Phrases</h3>
        <div class="tablewrap"><table>
          <thead><tr><th>Phrase</th><th>Count</th></tr></thead>
          <tbody>{phrase_rows}</tbody>
        </table></div>
      </section>
      <section>
        <h2>Image Depth</h2>
        <p class="note">Downloaded/resolved ratios are local Archive object-depth diagnostics. Rights review remains separate from acquisition success.</p>
        <div class="tablewrap"><table>
          <thead><tr><th>Source/copy record</th><th>Category</th><th>Status</th><th>Downloaded / resolved</th><th>Failures</th></tr></thead>
          <tbody>{depth_rows}</tbody>
        </table></div>
      </section>
      <section>
        <h2>Target Coverage Matrix</h2>
        <div class="tablewrap"><table>
          <thead><tr><th>ID</th><th>Title</th><th>Category</th><th>Status</th><th>Local record IDs</th><th>Notes</th></tr></thead>
          <tbody>{coverage_rows}</tbody>
        </table></div>
      </section>
      <section>
        <h2>Local Record Gallery</h2>
        <div class="tablewrap"><table>
          <thead><tr><th>ID</th><th>Title</th><th>Type</th><th>Date</th><th>Authority</th><th>Image depth</th><th>Image associations</th></tr></thead>
          <tbody>{work_rows}</tbody>
        </table></div>
      </section>
    </div>
  </main>
  <script id="blake-corpus-data" type="application/json">{payload}</script>
</body>
</html>
"""
        path = self.visualization_dir / "corpus_workbench.html"
        path.write_text(document, encoding="utf-8")
        return path

    def _chronology(self, works: List[BlakeWork]) -> List[Dict[str, Any]]:
        rows = []
        for work in works:
            date_value = work.metadata.creation_date or work.metadata.publication_date
            rows.append(
                {
                    "id": work.id,
                    "title": work.metadata.title,
                    "date": date_value.isoformat() if date_value else None,
                    "work_type": str(work.metadata.work_type),
                    "source": str(work.metadata.source),
                }
            )
        return sorted(rows, key=lambda row: row["date"] or "9999")

    def _source_provenance(
        self, works: List[BlakeWork], manifest: CorpusManifest
    ) -> Dict[str, Any]:
        return {
            "source_coverage": manifest.source_coverage,
            "coverage_counts": manifest.coverage_counts,
            "provenance": [
                {
                    "id": work.id,
                    "title": work.metadata.title,
                    "source": str(work.metadata.source),
                    "source_id": work.metadata.source_id,
                    "source_url": work.metadata.source_url,
                    "license_type": str(work.metadata.license_type),
                    "api_source": work.metadata.api_source,
                    "attribution": work.metadata.attribution,
                }
                for work in works
            ],
        }

    def _text_metrics(self, works: List[BlakeWork]) -> List[Dict[str, Any]]:
        rows = []
        for work in works:
            text = work.text_content or ""
            words = _language_tokens(text)
            lexical = _lexical_tokens(words)
            unique_words = set(words)
            lexical_counts = Counter(lexical)
            rows.append(
                {
                    "work_id": work.id,
                    "title": work.metadata.title,
                    "has_text": bool(text),
                    "word_count": len(words),
                    "unique_words": len(unique_words),
                    "vocabulary_richness": (
                        len(unique_words) / len(words) if words else 0.0
                    ),
                    "lexical_token_count": len(lexical),
                    "distinct_lexical_terms": len(lexical_counts),
                    "lexical_density": len(lexical) / len(words) if words else 0.0,
                    "average_token_length": (
                        sum(len(token) for token in words) / len(words)
                        if words
                        else 0.0
                    ),
                    "top_terms": [
                        {"term": term, "count": count}
                        for term, count in lexical_counts.most_common(8)
                    ],
                    "top_bigrams": _top_bigrams(lexical, limit=6),
                }
            )
        return rows

    def _lexical_signature(self, works: List[BlakeWork]) -> Dict[str, Any]:
        rows: List[Dict[str, Any]] = []
        corpus_terms: Counter[str] = Counter()
        corpus_bigrams: Counter[str] = Counter()
        document_frequency: Counter[str] = Counter()

        for work in works:
            words = _language_tokens(work.text_content or "")
            lexical = _lexical_tokens(words)
            if not words:
                continue
            term_counts = Counter(lexical)
            bigram_counts = _bigram_counts(lexical)
            corpus_terms.update(term_counts)
            corpus_bigrams.update(bigram_counts)
            document_frequency.update(term_counts.keys())
            rows.append(
                {
                    "work_id": work.id,
                    "title": work.metadata.title,
                    "word_count": len(words),
                    "lexical_token_count": len(lexical),
                    "distinct_terms": len(term_counts),
                    "lexical_density": len(lexical) / len(words),
                    "image_count": len(work.images),
                    "themes": work.metadata.themes,
                    "top_terms": [
                        {"term": term, "count": count}
                        for term, count in term_counts.most_common(8)
                    ],
                    "top_bigrams": _top_bigrams(lexical, limit=6),
                }
            )

        doc_count = len(rows)
        for row in rows:
            term_counts = Counter(
                {item["term"]: int(item["count"]) for item in row.get("top_terms", [])}
            )
            total = int(row.get("lexical_token_count") or 1)
            scored = []
            for term, count in term_counts.items():
                idf = math.log((1 + doc_count) / (1 + document_frequency[term])) + 1
                scored.append(
                    {
                        "term": term,
                        "count": count,
                        "score": round((count / total) * idf, 6),
                    }
                )
            row["distinctive_terms"] = sorted(
                scored, key=lambda item: item["score"], reverse=True
            )[:6]

        lexical_token_count = sum(int(row["lexical_token_count"]) for row in rows)
        density_values = [float(row["lexical_density"]) for row in rows]
        return {
            "schema_version": "1.0",
            "method": "regex_token_frequency_stopword_filtered",
            "work_count": len(works),
            "text_work_count": doc_count,
            "token_count": sum(int(row["word_count"]) for row in rows),
            "lexical_token_count": lexical_token_count,
            "distinct_terms": len(corpus_terms),
            "mean_lexical_density": (
                sum(density_values) / len(density_values) if density_values else 0.0
            ),
            "top_terms": [
                {
                    "term": term,
                    "count": count,
                    "document_frequency": document_frequency[term],
                }
                for term, count in corpus_terms.most_common(30)
            ],
            "top_bigrams": [
                {"phrase": phrase, "count": count}
                for phrase, count in corpus_bigrams.most_common(24)
            ],
            "works": sorted(
                rows,
                key=lambda row: (
                    -int(row["lexical_token_count"]),
                    str(row["title"]).lower(),
                ),
            ),
        }

    def _image_metrics(self, works: List[BlakeWork]) -> List[Dict[str, Any]]:
        rows = []
        for work in works:
            for image in work.images:
                rows.append(
                    {
                        "work_id": work.id,
                        "image_id": image.id,
                        "title": image.title,
                        "width": image.width,
                        "height": image.height,
                        "dpi": image.dpi,
                        "source_url": image.original_url,
                        "dominant_colors": image.dominant_colors,
                        "plate_number": image.plate_number,
                    }
                )
        return rows

    def _theme_entity_network(self, works: List[BlakeWork]) -> Dict[str, Any]:
        return build_theme_entity_network(works)

    def _text_image_linkage(self, works: List[BlakeWork]) -> List[Dict[str, Any]]:
        return [
            {
                "work_id": work.id,
                "title": work.metadata.title,
                "has_text": bool(work.text_content),
                "image_count": len(work.images),
                "source_authority_tier": _authority_tier(work),
                "image_depth_status": _image_depth_payload(work).get(
                    "image_depth_status"
                ),
                "linked_images": [
                    {
                        "image_id": image.id,
                        "title": image.title,
                        "related_text_id": image.related_text_id,
                        "plate_number": image.plate_number,
                    }
                    for image in work.images
                ],
            }
            for work in works
        ]

    def _image_depth(
        self, works: List[BlakeWork], manifest: CorpusManifest
    ) -> List[Dict[str, Any]]:
        target_by_work = {
            work_id: record
            for record in manifest.target_records
            for work_id in record.matched_work_ids
        }
        rows = []
        for work in works:
            depth = _image_depth_payload(work)
            target_record = target_by_work.get(work.id)
            expected = depth.get("expected_object_count")
            resolved = depth.get("resolved_object_count")
            downloaded = depth.get("downloaded_image_count")
            rows.append(
                {
                    "work_id": work.id,
                    "title": work.metadata.title,
                    "category": (
                        target_record.category
                        if target_record
                        else str(work.metadata.work_type)
                    ),
                    "source": str(work.metadata.source),
                    "source_authority_tier": _authority_tier(work),
                    "image_mode": depth.get("image_mode", "representative"),
                    "preferred_dpi": depth.get("preferred_dpi"),
                    "expected_object_count": expected,
                    "resolved_object_count": resolved,
                    "downloaded_image_count": (
                        downloaded if downloaded is not None else len(work.images)
                    ),
                    "local_image_count": len(work.images),
                    "image_depth_status": depth.get("image_depth_status"),
                    "failure_count": len(depth.get("failures") or []),
                    "failures": list(depth.get("failures") or []),
                }
            )
        return rows

    def _source_authority_tiers(self, works: List[BlakeWork]) -> List[Dict[str, Any]]:
        counts = Counter(_authority_tier(work) for work in works)
        return [
            {"authority_tier": tier, "work_count": count}
            for tier, count in sorted(counts.items())
        ]

    def _work_gallery(self, works: List[BlakeWork]) -> List[Dict[str, Any]]:
        rows = []
        for work in works:
            date_value = work.metadata.creation_date or work.metadata.publication_date
            rows.append(
                {
                    "id": work.id,
                    "title": work.metadata.title,
                    "work_type": str(work.metadata.work_type),
                    "date": date_value.isoformat() if date_value else None,
                    "source": str(work.metadata.source),
                    "source_authority_tier": _authority_tier(work),
                    "image_depth_status": _image_depth_payload(work).get(
                        "image_depth_status"
                    ),
                    "image_count": len(work.images),
                    "text_versions": len(work.text_versions),
                    "themes": work.metadata.themes,
                    "subjects": work.metadata.subjects,
                }
            )
        return rows

    def _pipeline_architecture(self) -> Dict[str, Any]:
        phases = [
            "discovery",
            "acquisition",
            "metadata",
            "analysis",
            "visualizations",
            "export",
            "reports",
        ]
        return {
            "nodes": [
                {"id": phase, "label": phase.title(), "type": "phase"}
                for phase in phases
            ],
            "edges": [
                {
                    "source": phases[index],
                    "target": phases[index + 1],
                    "relationship": "feeds",
                }
                for index in range(len(phases) - 1)
            ],
        }

    def _write_json(self, path: Path, data: Any) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(data, indent=2, ensure_ascii=False, default=str),
            encoding="utf-8",
        )
        return path
