from __future__ import annotations

import json
import math
import sqlite3
import textwrap
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from datetime import datetime
from pathlib import Path
from typing import Any, Literal

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.axes import Axes  # noqa: E402
from matplotlib.container import BarContainer  # noqa: E402
from matplotlib.figure import Figure  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402
from PIL import Image, ImageDraw, ImageFont, ImageOps  # noqa: E402

from manuscript_tools.core_architecture import (  # noqa: E402
    CORE_FIGURE_BRIEF,
    core_figure_statistics,
    fig_core_profile_ownership,
)
from manuscript_tools.method_types import (  # noqa: E402
    CategoryCoverage,
    authority_label,
    local_image_count,
)
from manuscript_tools.nlp_diagnostics import (  # noqa: E402
    build_nlp_diagnostics,
)

BG = "#fcfaf4"
INK = "#20242a"
MUTED = "#5f625d"
GRID = "#d8d2c4"
PALETTE = {
    "blue": "#0072B2",
    "gold": "#E69F00",
    "red": "#D55E00",
    "green": "#009E73",
    "violet": "#7A4FA3",
    "slate": "#34495E",
    "gray": "#8A8F8A",
    "cream": "#fcfaf4",
    "tan": "#D9C9A8",
    "pale": "#F7F2E8",
}
STATUS_COLORS = {
    "present": PALETTE["green"],
    "partial": PALETTE["gold"],
    "missing": PALETTE["red"],
    "unverified": PALETTE["blue"],
    "duplicate": PALETTE["violet"],
}
STATISTICAL_FIELDS = {
    "statistical_question",
    "data_shape",
    "statistical_method",
    "missingness_or_scope",
    "statistical_check",
}
BRIEF_FIELDS = {
    "story_job",
    "data_sources",
    "claim",
    "encoding",
    "caveat",
    "static_mobile_fallback",
    "qa_check",
    "accessibility_summary",
} | STATISTICAL_FIELDS


def _brief(
    story_job: str,
    data_sources: list[str],
    claim: str,
    encoding: str,
    caveat: str,
    accessibility_summary: str,
    static_mobile_fallback: str = "Single static PNG with direct labels and high-contrast colors.",
    qa_check: str = "Confirm labels remain legible in PDF and mobile web screenshots.",
) -> dict[str, Any]:
    return {
        "story_job": story_job,
        "data_sources": data_sources,
        "claim": claim,
        "encoding": encoding,
        "caveat": caveat,
        "static_mobile_fallback": static_mobile_fallback,
        "qa_check": qa_check,
        "accessibility_summary": accessibility_summary,
    }


FIGURE_BRIEFS: dict[str, dict[str, Any]] = {
    "coverage_status": _brief(
        "Show the gap between represented targets and fully evidenced targets.",
        ["reports/source_coverage.json"],
        "Most targets are represented locally, but complete required evidence remains partial.",
        "Status bars encode target counts with count and percentage labels.",
        "Work-level denominator only; copy/object-level completeness is out of scope.",
        "Status categories use distinct hues plus printed counts and percentages.",
    ),
    "category_coverage": _brief(
        "Locate remaining coverage work by target category.",
        ["visualizations/target_coverage_matrix.json"],
        "Remaining gaps cluster by category rather than by one global missing bucket.",
        "Horizontal stacked bars encode status counts within each target category.",
        "Categories are ledger groupings, not literary or editorial period claims.",
        "Stacked segments retain a legend and category labels for screen-reader alt text.",
    ),
    "corpus_modalities": _brief(
        "Separate text, image, joint, and metadata-only local evidence.",
        ["visualizations/text_metrics.json", "visualizations/text_image_linkage.json"],
        "Local evidence is multimodal but imbalanced across works.",
        "Bars encode local work counts by evidence modality.",
        "A local image record is not a complete Archive facsimile mirror.",
        "Each modality bar is directly labeled by position and legend-free text.",
    ),
    "source_audit": _brief(
        "Record which source endpoints answered during this bounded audit.",
        ["data/source_audit.json"],
        "Source availability is a saved run artifact, not an assumed condition.",
        "Endpoint rows use availability color and printed HTTP/no-response status.",
        "Endpoint status can drift after the run date.",
        "Color is paired with printed status text inside each row.",
    ),
    "chronology": _brief(
        "Show how dated local records distribute across work types.",
        ["visualizations/chronology.json"],
        "The current corpus spans multiple dated work types but remains source-bound.",
        "Scatter positions encode year and work type; color encodes acquisition source.",
        "Dates are normalized work metadata, not object-specific production histories.",
        "Axis labels expose date/type encoding without relying on color alone.",
    ),
    "word_counts": _brief(
        "Identify the largest text-bearing works driving text-scale metrics.",
        ["visualizations/text_metrics.json"],
        "A small set of long text-bearing works dominates total word volume.",
        "Horizontal bars encode word counts for the largest local texts.",
        "Excludes works without local text evidence.",
        "Direct numeric labels make the ranking readable in grayscale.",
    ),
    "vocab_richness": _brief(
        "Compare lexical richness against text length.",
        ["visualizations/text_metrics.json"],
        "Vocabulary richness varies across local text lengths and should be read as diagnostic.",
        "Scatter x encodes log word count; y encodes type-token ratio; color flags length bands.",
        "Type-token ratio is length-sensitive and not a final stylistic conclusion.",
        "Important points are annotated; axes state the transformations.",
    ),
    "lexical_signature": _brief(
        "Summarize the most frequent filtered terms and adjacent phrases.",
        ["visualizations/lexical_signature.json"],
        "The text-bearing subset has a reproducible Blake-specific lexical signature.",
        "Side-by-side horizontal bars encode term and phrase counts.",
        "Stopword filtering and text availability shape the signature.",
        "Direct labels and split panels keep terms readable in static output.",
    ),
    "nlp_embedding_pca": _brief(
        "Show whether text-bearing works form visible lexical neighborhoods.",
        ["data/nlp_diagnostics.json", "visualizations/text_metrics.json"],
        "The covariance PCA map diagnoses the text subset, not the complete oeuvre.",
        "Point position encodes TF-IDF latent axes; size and color encode text length.",
        "Only works with local text evidence enter the embedding.",
        "Legend, axis variance, and selected labels explain the visual encoding.",
    ),
    "text_image_density": _brief(
        "Inspect joint text/image density for local text-bearing works.",
        ["visualizations/text_metrics.json", "visualizations/text_image_linkage.json"],
        "Cross-modal inspection is bounded to works that have local text evidence.",
        "X encodes log word count, y image associations, color lexical density, size distinct terms.",
        "This is not plate-level or copy-level visual completeness.",
        "Axis labels, colorbar, and annotations describe all encodings.",
    ),
    "theme_network": _brief(
        "Summarize the most frequent themes in the work-theme graph.",
        ["visualizations/theme_entity_network.json"],
        "Theme links provide a regenerable corpus diagnostic over acquired works.",
        "Horizontal bars encode counts of work-theme links by theme.",
        "Theme extraction is a computational view, not an interpretive edition.",
        "Direct bar labels keep the ranking readable without interaction.",
    ),
    "text_image_linkage": _brief(
        "Rank local records by linked image evidence.",
        ["visualizations/text_image_linkage.json"],
        "Image evidence is concentrated in particular local records.",
        "Horizontal bars encode linked image counts; color marks whether text is also present.",
        "Linked image counts are local records, not all Archive objects.",
        "Printed counts and color categories support static and grayscale review.",
    ),
    "evidence_gaps": _brief(
        "Name the failure modes behind incomplete target coverage.",
        ["visualizations/target_coverage_matrix.json"],
        "Missing expected text is the dominant remaining evidence problem.",
        "Horizontal bars encode counted gap-note categories.",
        "Gap-note categories are generated from ledger notes and should guide review, not replace it.",
        "Direct count labels avoid relying on bar area alone.",
    ),
    "pipeline_dag": _brief(
        "Show the run phases that produced the manuscript artifacts.",
        ["visualizations/pipeline_architecture.json", "pipeline_summary.json"],
        "The publication artifacts come from a reproducible pipeline that separates generated phases from reused local evidence.",
        "Phase cards encode the current-run action, evidence/artifact count, and a source note.",
        "Reuse and not-rerun states describe the validation command, not absent acquisition or absent analysis evidence.",
        "Each phase prints action and evidence labels so color is not the only signal.",
    ),
    "all_acquired_images_mosaic": _brief(
        "Show the visual breadth of every acquired image file with a valid local path.",
        ["blake_data/metadata/metadata.db", "blake_data/images/"],
        "The image supplement is built from local files, not from remote or generated art.",
        "A thumbnail mosaic encodes one valid local image file per tile with short work identifiers.",
        "Some metadata image records point to missing local paths; those records are excluded from the file mosaic.",
        "The mosaic uses visible tile labels so each thumbnail remains inspectable without hover.",
        qa_check="Confirm thumbnails load from local files and labels remain readable in PDF/web output.",
    ),
    "work_area_image_mosaics": _brief(
        "Group acquired image files by ledger work area.",
        [
            "blake_data/metadata/metadata.db",
            "visualizations/target_coverage_matrix.json",
        ],
        "The acquired image files are concentrated by work category rather than evenly distributed.",
        "Small multiples group thumbnail tiles under category headings.",
        "Category labels are ledger areas, not interpretive period labels.",
        "Each category heading prints the local file count, and thumbnails retain work ids.",
        qa_check="Confirm category headings and thumbnail labels do not collide after PDF scaling.",
    ),
    "work_evidence_profile_grid": _brief(
        "Give one compact visual profile for every target-ledger work.",
        [
            "visualizations/target_coverage_matrix.json",
            "visualizations/text_metrics.json",
            "visualizations/text_image_linkage.json",
        ],
        "The work-level supplement keeps text, image, and coverage status visible for every target.",
        "Tiles encode target status by color, text availability by T mark, and linked image count by I count.",
        "Text and image flags describe only the first matched source/copy record, not all copies of a target.",
        "Every tile carries redundant text labels for status, text, and image evidence.",
        qa_check="Confirm the grid has one tile per target and no text overflow in PDF/mobile screenshots.",
    ),
    "image_depth_by_work": _brief(
        "Show which works now have deep Archive object-image acquisition.",
        ["visualizations/image_depth.json"],
        "Image evidence is measured as object-depth coverage, not only binary image presence.",
        "Horizontal paired bars encode expected/resolved Archive objects and downloaded local image files.",
        "Only discoverable Archive object metadata is counted; non-Archive catalog records remain out of scope.",
        "Bars use direct labels and redundant source notes so the figure remains readable in static PDF/web output.",
        qa_check="Confirm high-image works show tens of objects and labels do not overlap after PDF scaling.",
    ),
    "image_depth_by_area": _brief(
        "Summarize Archive image-depth acquisition by ledger work area.",
        ["visualizations/image_depth.json"],
        "Image-depth completeness varies by work area and source metadata shape.",
        "Grouped bars encode resolved Archive objects and downloaded image files by target-ledger category.",
        "Category totals aggregate local records; they are not object-level Blake oeuvre totals.",
        "Category labels, numeric bar labels, and a legend make the grouped comparison accessible.",
        qa_check="Confirm grouped bars fit mobile width and every category denominator is visible.",
    ),
    "source_authority_tiers": _brief(
        "Separate Archive-primary, validated fallback, and corroborating/unclassified evidence.",
        ["visualizations/source_authority_tiers.json", "corpus_manifest.json"],
        "The manuscript distinguishes material authority tiers instead of flattening all sources.",
        "Bars encode local work counts by recorded source-authority tier.",
        "Authority tier is a provenance label for this run, not a judgment about literary importance.",
        "Each tier is directly labeled and counted so color is not required for interpretation.",
        qa_check="Confirm every local work has a non-empty authority tier in the manifest and registry.",
    ),
}

FIGURE_STATISTICAL_BRIEFS: dict[str, dict[str, str]] = {
    "coverage_status": {
        "statistical_question": "How many target-ledger entries have complete, partial, missing, unverified, or duplicate local evidence?",
        "data_shape": "One row per target-ledger entry summarized into status counts.",
        "statistical_method": "Descriptive status census with per-status denominator percentages.",
        "missingness_or_scope": "Target-level denominator only; copy, object, plate, and public-release rights completeness are excluded.",
        "statistical_check": "Status counts must sum to the reported target total and every bar label must include count and percent.",
    },
    "category_coverage": {
        "statistical_question": "Which target categories contribute the most unresolved target evidence?",
        "data_shape": "One target-ledger row per work, grouped by ledger category and status.",
        "statistical_method": "Grouped descriptive counts and unresolved shares within each category.",
        "missingness_or_scope": "Ledger categories are acquisition/work-area groups, not literary-period strata.",
        "statistical_check": "Each stacked row must expose its denominator and unresolved count.",
    },
    "corpus_modalities": {
        "statistical_question": "How many local records have text, images, both modalities, or metadata only?",
        "data_shape": "One local work row from text metrics joined to one local work row from image linkage.",
        "statistical_method": "Descriptive cross-tabulation of binary text and binary image availability.",
        "missingness_or_scope": "Local image presence does not imply Archive object or copy completeness.",
        "statistical_check": "Modality counts must sum to the union of text and image linkage work ids.",
    },
    "source_audit": {
        "statistical_question": "Which configured source endpoints answered during the saved audit run?",
        "data_shape": "One checked endpoint row with ok and HTTP/no-response status fields.",
        "statistical_method": "Endpoint availability count and ok-share for the run artifact.",
        "missingness_or_scope": "Endpoint availability can drift after the saved run timestamp.",
        "statistical_check": "Every endpoint row must print a status rather than relying on color alone.",
    },
    "chronology": {
        "statistical_question": "What dated work types are represented in the acquired local corpus?",
        "data_shape": "One acquired work row with normalized date, work type, and source.",
        "statistical_method": "Descriptive dated-work count, date span, and work-type/source counts.",
        "missingness_or_scope": "Dates are normalized work metadata, not object-specific production histories.",
        "statistical_check": "Undated rows are excluded from the scatter denominator and reported in statistics.",
    },
    "word_counts": {
        "statistical_question": "Which text-bearing works dominate the corpus word denominator?",
        "data_shape": "One local text-bearing work row with word count and lexical metrics.",
        "statistical_method": "Ranked descriptive counts plus top-work share of total words.",
        "missingness_or_scope": "Works without local text evidence are excluded from text-scale summaries.",
        "statistical_check": "Top-bar total and total word denominator must be regenerated from text_metrics.json.",
    },
    "vocab_richness": {
        "statistical_question": "How does type-token ratio vary with text length in the text-bearing subset?",
        "data_shape": "One local text-bearing work row with word count and type-token ratio.",
        "statistical_method": "Descriptive scatter using log word count, median/IQR summaries, and length-band counts.",
        "missingness_or_scope": "Type-token ratio is length-sensitive; short texts can inflate richness.",
        "statistical_check": "Length-band counts and median/IQR must be present in registry statistics.",
    },
    "lexical_signature": {
        "statistical_question": "Which filtered terms and adjacent phrases dominate the text-bearing subset?",
        "data_shape": "Corpus-level token-frequency artifact plus per-work text diagnostics.",
        "statistical_method": "Stopword-filtered frequency counts, document frequency, and top-term share.",
        "missingness_or_scope": "Tokenization, stopword filtering, and missing text evidence shape the result.",
        "statistical_check": "Top terms must include both count and document-frequency evidence.",
    },
    "nlp_embedding_pca": {
        "statistical_question": "What descriptive lexical neighborhoods appear among text-bearing works?",
        "data_shape": "One point per text-bearing work projected from TF-IDF features into two axes.",
        "statistical_method": "Centered row-normalized TF-IDF covariance PCA with variance and top-axis terms.",
        "missingness_or_scope": "Only text-bearing local records enter; no inferential literary clustering is claimed.",
        "statistical_check": "Registry statistics must include n, feature count, variance, and top terms for both axes.",
    },
    "text_image_density": {
        "statistical_question": "How do local word count and linked image count co-occur for text-bearing works?",
        "data_shape": "One text-bearing local work row joined to linked image counts.",
        "statistical_method": "Descriptive cross-modal scatter with zero-image mass and Pearson correlation as local diagnostics.",
        "missingness_or_scope": "Correlation is descriptive for this run only; object/copy completeness is out of scope.",
        "statistical_check": "Zero-image count and correlation denominator must be visible in statistics.",
    },
    "theme_network": {
        "statistical_question": "Which generated themes occur most often in the work-theme graph?",
        "data_shape": "Serialized graph nodes and work-theme edges.",
        "statistical_method": "Descriptive edge counts by theme node.",
        "missingness_or_scope": "Theme extraction is computational and diagnostic, not an editorial taxonomy.",
        "statistical_check": "Theme counts must be derived from graph edges rather than hand-written labels.",
    },
    "text_image_linkage": {
        "statistical_question": "Which local records concentrate linked image evidence?",
        "data_shape": "One local work row with text flag, image count, and linked image records.",
        "statistical_method": "Ranked descriptive image counts and top-work share of image associations.",
        "missingness_or_scope": "Linked images are local records, not all Archive objects or copies.",
        "statistical_check": "Image-rich bars must preserve local count labels and text-presence category.",
    },
    "evidence_gaps": {
        "statistical_question": "What failure modes explain incomplete target coverage?",
        "data_shape": "Target-ledger rows with status and generated evidence notes.",
        "statistical_method": "Rule-based descriptive counts over gap-note categories.",
        "missingness_or_scope": "Gap-note categories guide follow-up review and do not replace source inspection.",
        "statistical_check": "Counts must be regenerated from target coverage notes and status fields.",
    },
    "pipeline_dag": {
        "statistical_question": "Which pipeline phases produced the saved manuscript artifacts?",
        "data_shape": "One pipeline phase node joined to saved run phase status, item count, artifacts, and local evidence counts.",
        "statistical_method": "Descriptive phase classification into generated, reused, and not-rerun current-command states.",
        "missingness_or_scope": "Reuse and not-rerun labels describe the saved validation command, not the absence of prior acquisition or descriptive diagnostics.",
        "statistical_check": "Every phase card must include a printed action and evidence label.",
    },
    "all_acquired_images_mosaic": {
        "statistical_question": "How many acquired image metadata rows have valid local file paths?",
        "data_shape": "One metadata image row per local database image record, filtered to existing file paths for thumbnails.",
        "statistical_method": "Descriptive valid-path count and missing-path exclusion count.",
        "missingness_or_scope": "Provider-supplied thumbnails remain subject to the distribution rights gate.",
        "statistical_check": "The mosaic count must equal the valid local file count used to build tiles.",
    },
    "work_area_image_mosaics": {
        "statistical_question": "How are valid local image files distributed by ledger work area?",
        "data_shape": "Valid local image file rows grouped by matched target category.",
        "statistical_method": "Category counts and category share of valid local image files.",
        "missingness_or_scope": "Ledger work areas are not interpretive periods and rights review remains separate.",
        "statistical_check": "Category totals must sum to the valid local image-file denominator.",
    },
    "work_evidence_profile_grid": {
        "statistical_question": "What target-level evidence profile exists for each ledger entry?",
        "data_shape": "One tile per target-ledger row with status, text flag, and linked image count.",
        "statistical_method": "Descriptive census of status counts, text availability, and image availability.",
        "missingness_or_scope": "One tile per target; text and image fields use only its first matched source/copy record. Unmatched targets have no text and zero image associations.",
        "statistical_check": "Tile count must equal target_total and status counts must sum to tile count.",
    },
    "image_depth_by_work": {
        "statistical_question": "Which local records have the deepest resolved/downloaded Archive object evidence?",
        "data_shape": "One local work row with expected, resolved, downloaded, local-image, and failure counts.",
        "statistical_method": "Ranked descriptive resolved/downloaded counts and completion ratio.",
        "missingness_or_scope": "Counts cover discoverable Archive object metadata only.",
        "statistical_check": "Each row label must expose downloaded versus resolved object counts.",
    },
    "image_depth_by_area": {
        "statistical_question": "How do resolved/downloaded Archive object counts aggregate by work area?",
        "data_shape": "Image-depth rows grouped by target-ledger category.",
        "statistical_method": "Grouped descriptive totals and downloaded/resolved completion percentage.",
        "missingness_or_scope": "Category totals are local-run aggregates, not Blake oeuvre object totals.",
        "statistical_check": "Resolved and downloaded totals must be shown for every plotted category.",
    },
    "source_authority_tiers": {
        "statistical_question": "What provenance authority tier is recorded for each local work?",
        "data_shape": "One local work row summarized by source-authority tier.",
        "statistical_method": "Descriptive tier counts and tier percentages.",
        "missingness_or_scope": "Authority tier is run provenance metadata, not a literary importance ranking.",
        "statistical_check": "Tier counts must sum to the local work denominator.",
    },
}

for _figure_name, _fields in FIGURE_STATISTICAL_BRIEFS.items():
    FIGURE_BRIEFS[_figure_name].update(_fields)
FIGURE_BRIEFS["core_profile_ownership"] = dict(CORE_FIGURE_BRIEF)


def _read(ao: Path, rel: str) -> Any:
    return json.loads((ao / rel).read_text(encoding="utf-8"))


def _read_optional(ao: Path, rel: str, default: Any) -> Any:
    path = ao / rel
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def _pct(part: int | float, total: int | float) -> float:
    return round((float(part) / float(total) * 100.0), 1) if total else 0.0


def _summary(values: Sequence[int | float]) -> dict[str, int | float]:
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


def _pearson(xs: Sequence[int | float], ys: Sequence[int | float]) -> float:
    pairs = [(float(x), float(y)) for x, y in zip(xs, ys)]
    if len(pairs) < 2:
        return 0.0
    x_mean = sum(x for x, _ in pairs) / len(pairs)
    y_mean = sum(y for _, y in pairs) / len(pairs)
    numerator = sum((x - x_mean) * (y - y_mean) for x, y in pairs)
    x_denom = math.sqrt(sum((x - x_mean) ** 2 for x, _ in pairs))
    y_denom = math.sqrt(sum((y - y_mean) ** 2 for _, y in pairs))
    if not x_denom or not y_denom:
        return 0.0
    return round(numerator / (x_denom * y_denom), 3)


def _counter_rows(
    counter: Counter[str], *, total: int | None = None
) -> list[dict[str, Any]]:
    denominator = int(total if total is not None else sum(counter.values()))
    return [
        {"label": label, "count": int(count), "share_pct": _pct(count, denominator)}
        for label, count in counter.most_common()
    ]


def _configure() -> None:
    plt.rcParams.update(
        {
            "figure.facecolor": BG,
            "axes.facecolor": BG,
            "axes.edgecolor": GRID,
            "axes.labelcolor": INK,
            "axes.titlecolor": INK,
            "xtick.color": MUTED,
            "ytick.color": MUTED,
            "font.size": 11.5,
            "axes.titlesize": 14.5,
            "axes.titleweight": "bold",
            "axes.labelsize": 11,
            "legend.fontsize": 10.5,
            "xtick.labelsize": 10.5,
            "ytick.labelsize": 10.5,
            "font.family": "DejaVu Sans",
            "axes.linewidth": 0.8,
            "figure.autolayout": False,
        }
    )


def _style(ax: Axes, *, grid_axis: Literal["x", "y", "both", ""] = "y") -> None:
    ax.set_facecolor(BG)
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    for spine in ("left", "bottom"):
        ax.spines[spine].set_color(GRID)
    if grid_axis:
        ax.grid(axis=grid_axis, color=GRID, linewidth=0.8, alpha=0.78)
    ax.set_axisbelow(True)


def _save(fig: Figure, out_dir: Path, name: str) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{name}.png"
    fig.savefig(path, dpi=190, bbox_inches="tight", facecolor=BG)
    plt.close(fig)
    return path


def _short(title: str, limit: int = 34) -> str:
    title = " ".join(str(title).split())
    return title if len(title) <= limit else title[: limit - 1].rstrip() + "..."


def _wrapped(title: str, width: int = 22) -> str:
    return "\n".join(
        textwrap.wrap(str(title), width=width, break_long_words=False)
    ) or str(title)


def _title_with_subtitle(
    ax: Axes, title: str, subtitle: str, *, pad: int = 18
) -> None:
    ax.set_title(title, pad=pad)
    ax.text(
        0,
        1.015,
        subtitle,
        transform=ax.transAxes,
        ha="left",
        va="bottom",
        fontsize=9.8,
        color=MUTED,
    )


def _note(
    ax: Axes,
    text: str,
    *,
    xy: tuple[float, float] = (0.01, 0.02),
    fontsize: float = 9.6,
) -> None:
    ax.text(
        xy[0],
        xy[1],
        text,
        transform=ax.transAxes,
        ha="left",
        va="bottom",
        fontsize=fontsize,
        color=MUTED,
        bbox={"facecolor": BG, "edgecolor": GRID, "alpha": 0.94, "pad": 3.0},
    )


def _pil_font(size: int, *, bold: bool = False) -> ImageFont.ImageFont | ImageFont.FreeTypeFont:
    candidates = [
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold else "",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/Library/Fonts/Arial.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for candidate in candidates:
        if candidate and Path(candidate).exists():
            try:
                return ImageFont.truetype(candidate, size=size)
            except Exception:
                continue
    return ImageFont.load_default()


def _text_size(
    draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont | ImageFont.FreeTypeFont
) -> tuple[float, float]:
    bbox = draw.textbbox((0, 0), text, font=font)
    return bbox[2] - bbox[0], bbox[3] - bbox[1]


def _draw_wrapped(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int],
    text: str,
    font: ImageFont.ImageFont | ImageFont.FreeTypeFont,
    fill: str,
    width: int,
    *,
    max_lines: int = 2,
    line_gap: int = 2,
) -> None:
    avg = max(_text_size(draw, "M", font)[0], 1)
    chars = max(int(width / avg), 4)
    lines = textwrap.wrap(str(text), width=chars, break_long_words=False)[:max_lines]
    for index, line in enumerate(lines):
        draw.text(
            (
                xy[0],
                xy[1] + index * (
                    (font.size if isinstance(font, ImageFont.FreeTypeFont)
                     else _text_size(draw, "M", font)[1]) + line_gap
                ),
            ),
            line, fill=fill, font=font
        )


def _valid_image_records(root: Path, ao: Path) -> list[dict[str, Any]]:
    db_path = root / "blake_data" / "metadata" / "metadata.db"
    if not db_path.exists():
        return []
    target_rows = _read_optional(ao, "visualizations/target_coverage_matrix.json", [])
    category_by_id = {
        row.get("target_id"): str(row.get("category", "uncategorized")).replace(
            "_", " "
        )
        for row in target_rows
    }
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    records: list[dict[str, Any]] = []
    try:
        rows = conn.execute(
            """
            SELECT w.id AS work_id, w.title, w.work_type, i.id AS image_id, i.file_path
            FROM works w
            JOIN images i ON i.metadata_id = w.id
            ORDER BY lower(COALESCE(w.title, w.id)), i.id
            """
        ).fetchall()
    finally:
        conn.close()
    for row in rows:
        path = Path(row["file_path"])
        if not path.is_absolute():
            path = root / path
        if not path.exists():
            continue
        records.append(
            {
                "work_id": row["work_id"],
                "title": row["title"] or row["work_id"],
                "work_type": str(row["work_type"] or "").replace("_", " "),
                "category": category_by_id.get(
                    row["work_id"],
                    str(row["work_type"] or "uncategorized").replace("_", " "),
                ),
                "image_id": row["image_id"],
                "path": path,
            }
        )
    return records


def _thumbnail(path: Path, size: tuple[int, int]) -> Image.Image:
    bg_rgb = "#f6efe2"
    with Image.open(path) as image:
        image = ImageOps.exif_transpose(image).convert("RGB")
        image.thumbnail(size, Image.Resampling.LANCZOS)
        tile = Image.new("RGB", size, bg_rgb)
        x = (size[0] - image.width) // 2
        y = (size[1] - image.height) // 2
        tile.paste(image, (x, y))
        return tile


def _save_pil(image: Image.Image, out_dir: Path, name: str) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{name}.png"
    image.save(path)
    return path


def _work_profiles(ao: Path) -> list[dict[str, Any]]:
    targets = _read(ao, "visualizations/target_coverage_matrix.json")
    text_rows = _read(ao, "visualizations/text_metrics.json")
    link_rows = _read(ao, "visualizations/text_image_linkage.json")
    text_by_id = {row.get("work_id"): bool(row.get("has_text")) for row in text_rows}
    images_by_id = {
        row.get("work_id"): int(row.get("image_count", 0)) for row in link_rows
    }
    profiles: list[dict[str, Any]] = []
    for row in targets:
        matched = list(row.get("matched_work_ids") or [])
        work_id = matched[0] if matched else row.get("target_id")
        profiles.append(
            {
                "target_id": row.get("target_id"),
                "work_id": work_id,
                "title": row.get("title") or work_id,
                "category": str(row.get("category", "uncategorized")).replace("_", " "),
                "status": row.get("status") or "unknown",
                "has_text": text_by_id.get(work_id, False),
                "image_count": images_by_id.get(work_id, 0),
            }
        )
    return sorted(profiles, key=lambda item: (item["category"], item["title"]))


def _pipeline_phase_records(ao: Path) -> list[dict[str, Any]]:
    arch = _read_optional(ao, "visualizations/pipeline_architecture.json", {"nodes": []})
    summary = _read_optional(ao, "pipeline_summary.json", {})
    corpus_stats = _read_optional(ao, "reports/statistics.json", {})
    manifest = _read_optional(ao, "corpus_manifest.json", {})
    text_rows = _read_optional(ao, "visualizations/text_metrics.json", [])
    image_depth = _read_optional(ao, "visualizations/image_depth.json", [])
    phases = summary.get("phases", []) if isinstance(summary, dict) else []
    by_name = {str(phase.get("name")): phase for phase in phases}
    total_works = int(corpus_stats.get("total_works") or manifest.get("work_count") or 0)
    total_images = int(corpus_stats.get("total_images") or 0)
    target_total = int(manifest.get("target_total") or 0)
    nodes = arch.get("nodes", []) if isinstance(arch, dict) else []

    def _count_artifacts(phase: dict[str, Any]) -> int:
        artifacts = phase.get("artifacts") or {}
        return len(artifacts) if isinstance(artifacts, dict) else 0

    records: list[dict[str, Any]] = []
    for node in nodes:
        name = str(node.get("id") or node.get("label") or "")
        label = str(node.get("label") or name.replace("_", " ").title())
        phase = by_name.get(name, {})
        raw_status = str(phase.get("status") or "not run")
        items = int(phase.get("items_processed") or 0)
        artifact_count = _count_artifacts(phase)
        action = "generated this run"
        action_class = "generated"
        evidence = f"{items:,} item{'s' if items != 1 else ''}"
        note = str(phase.get("message") or "").replace("_", " ")

        if name == "discovery":
            evidence = f"{items:,} source records"
            note = "saved discovery status; see phase flag"
        elif name == "acquisition" and raw_status == "skipped":
            action = "reused local corpus"
            action_class = "reused"
            evidence = f"{total_works:,} records; {total_images:,} image associations"
            note = "no live re-fetch"
        elif name == "metadata":
            evidence = f"{target_total:,} targets; {total_works:,} records"
            note = "manifest regenerated"
        elif name == "analysis" and raw_status == "skipped":
            action = "deep analyzer not rerun"
            action_class = "not rerun"
            evidence = f"{len(text_rows):,} text rows; {len(image_depth):,} image-depth rows"
            note = "diagnostics generated downstream"
        elif name == "analysis":
            evidence = f"{items:,} records analyzed"
            note = "analysis artifacts regenerated"
        elif name == "visualizations":
            evidence = f"{artifact_count:,} visualization artifacts"
            note = "metrics and charts regenerated"
        elif name == "export":
            export_count = artifact_count or items
            evidence = f"{export_count:,} export artifact{'s' if export_count != 1 else ''}"
            note = "JSON export regenerated"
        elif name == "reports":
            evidence = f"{artifact_count:,} report artifacts"
            note = "manuscript inputs regenerated"

        if raw_status not in {"completed", "skipped"}:
            action = raw_status.replace("_", " ")
            action_class = "other"
        if raw_status == "skipped" and name not in {"acquisition", "analysis"}:
            action = "not run"
            action_class = "not rerun"

        records.append(
            {
                "name": name,
                "label": label,
                "raw_status": raw_status,
                "action": action,
                "action_class": action_class,
                "items_processed": items,
                "artifact_count": artifact_count,
                "evidence": evidence,
                "note": note,
            }
        )
    return records


def compute_figure_statistics(
    analysis_output: Path | str, figure_name: str
) -> dict[str, Any]:
    if figure_name == "core_profile_ownership":
        return dict(core_figure_statistics())
    ao = Path(analysis_output)
    target_rows = _read_optional(ao, "visualizations/target_coverage_matrix.json", [])
    text_rows = _read_optional(ao, "visualizations/text_metrics.json", [])
    link_rows = _read_optional(ao, "visualizations/text_image_linkage.json", [])
    image_depth = _read_optional(ao, "visualizations/image_depth.json", [])
    source_coverage = _read_optional(ao, "reports/source_coverage.json", {})
    corpus_stats = _read_optional(ao, "reports/statistics.json", {})
    total_works = int(
        corpus_stats.get("total_works") or len(link_rows) or len(text_rows)
    )
    text_bearing = [row for row in text_rows if row.get("has_text")]
    images_by_id = {
        row.get("work_id"): int(row.get("image_count") or 0) for row in link_rows
    }

    if figure_name == "coverage_status":
        counts = Counter(source_coverage.get("coverage_counts") or {})
        total = int(counts.get("total") or sum(counts.values()))
        ordered = Counter(
            {
                status: int(counts.get(status) or 0)
                for status in (
                    "present",
                    "partial",
                    "missing",
                    "unverified",
                    "duplicate",
                )
            }
        )
        open_total = sum(
            ordered[status]
            for status in ("partial", "missing", "unverified", "duplicate")
        )
        return {
            "target_total": total,
            "status_counts": _counter_rows(ordered, total=total),
            "represented_targets": int(ordered["present"] + ordered["partial"]),
            "represented_pct": _pct(ordered["present"] + ordered["partial"], total),
            "complete_targets": int(ordered["present"]),
            "complete_pct": _pct(ordered["present"], total),
            "open_targets": int(open_total),
            "open_pct": _pct(open_total, total),
        }

    if figure_name == "category_coverage":
        by_category: dict[str, Counter[str]] = defaultdict(Counter)
        for row in target_rows:
            category = str(row.get("category") or "uncategorized").replace("_", " ")
            by_category[category][str(row.get("status") or "unknown")] += 1
        categories: list[CategoryCoverage] = []
        for category, counts in by_category.items():
            total = sum(counts.values())
            open_count = sum(
                counts.get(status, 0)
                for status in ("partial", "missing", "unverified", "duplicate")
            )
            categories.append(
                {
                    "category": category,
                    "target_total": int(total),
                    "open_targets": int(open_count),
                    "open_pct": _pct(open_count, total),
                    "status_counts": dict(sorted(counts.items())),
                }
            )
        categories = sorted(
            categories,
            key=lambda row: (
                -row["open_targets"],
                -row["target_total"],
                row["category"],
            ),
        )
        return {
            "target_total": len(target_rows),
            "category_count": len(categories),
            "categories": categories,
            "largest_open_category": dict(categories[0]) if categories else {},
        }

    if figure_name == "corpus_modalities":
        text_by_id = {
            row.get("work_id"): bool(row.get("has_text")) for row in text_rows
        }
        image_by_id = {work_id: count > 0 for work_id, count in images_by_id.items()}
        work_ids = sorted(set(text_by_id) | set(image_by_id))
        counts = Counter(
            (
                "text + image"
                if text_by_id.get(work_id) and image_by_id.get(work_id)
                else (
                    "text only"
                    if text_by_id.get(work_id)
                    else "image only" if image_by_id.get(work_id) else "metadata only"
                )
            )
            for work_id in work_ids
        )
        return {
            "local_work_total": len(work_ids),
            "modality_counts": _counter_rows(counts, total=len(work_ids)),
            "text_work_count": sum(1 for value in text_by_id.values() if value),
            "image_work_count": sum(1 for value in image_by_id.values() if value),
        }

    if figure_name == "source_audit":
        audit = _read_optional(ao, "data/source_audit.json", {})
        review = _read_optional(ao, "data/evidence_acquisition_review.json", {})
        analysis_summary = _read_optional(ao, "analysis/analysis_summary.json", {})
        checked = (audit.get("live") or {}).get("checked_urls") or []
        provider_discovery = audit.get("provider_discovery") or {}
        provider_rows = provider_discovery.get("providers") or []
        provider_failures = [
            row for row in provider_rows if str(row.get("status") or "") != "completed"
        ]
        archive_metadata = (
            audit.get("metadata_enrichment_report")
            or (audit.get("live") or {}).get("archive_metadata_enrichment")
            or {}
        )
        review_candidates = [
            candidate
            for target_review in review.get("target_reviews", [])
            for candidate in target_review.get("candidates", [])
        ]
        manual_candidates = [
            candidate
            for candidate in review_candidates
            if str(candidate.get("lead_status") or "") == "manual_review"
            or str(candidate.get("action_taken") or "").startswith("manual_review:")
            or str(candidate.get("status") or "") == "manual_review"
        ]
        ok_count = sum(1 for row in checked if row.get("ok"))
        status_counts = Counter(
            str(row.get("status") or "no response") for row in checked
        )
        return {
            "checked_endpoints": len(checked),
            "ok_endpoints": ok_count,
            "ok_pct": _pct(ok_count, len(checked)),
            "status_counts": _counter_rows(status_counts, total=len(checked)),
            "live_enabled": bool((audit.get("live") or {}).get("enabled")),
            "provider_count": int(
                provider_discovery.get("provider_count") or len(provider_rows)
            ),
            "provider_failure_count": int(
                provider_discovery.get("failure_count") or len(provider_failures)
            ),
            "provider_record_count": int(provider_discovery.get("record_count") or 0),
            "archive_metadata_status": str(
                archive_metadata.get("status") or "unknown"
            ),
            "archive_metadata_attempted": int(archive_metadata.get("attempted") or 0),
            "archive_metadata_succeeded": int(archive_metadata.get("succeeded") or 0),
            "archive_metadata_failed": int(archive_metadata.get("failed") or 0),
            "archive_metadata_skipped_after_budget": int(
                archive_metadata.get("skipped_after_budget") or 0
            ),
            "archive_metadata_fallback_source": str(
                archive_metadata.get("fallback_source_used")
                or "target ledger + GitHub XML inventory"
            ),
            "acquisition_review_schema_version": str(
                review.get("schema_version") or "unavailable"
            ),
            "acquisition_review_unresolved_targets": int(
                review.get("unresolved_target_count") or 0
            ),
            "acquisition_review_candidate_count": int(
                review.get("candidate_count") or len(review_candidates)
            ),
            "manual_review_candidate_count": len(manual_candidates),
            "analysis_status": str(analysis_summary.get("status") or "unknown"),
            "analysis_results_current": bool(
                analysis_summary.get("analysis_results_current")
            ),
            "analysis_works_analyzed": int(analysis_summary.get("works_analyzed") or 0),
            "analysis_works_total": int(analysis_summary.get("works_total") or 0),
        }

    if figure_name == "chronology":
        rows = _read_optional(ao, "visualizations/chronology.json", [])
        dated = [row for row in rows if row.get("date")]
        years = [int(str(row["date"])[:4]) for row in dated]
        return {
            "work_total": len(rows),
            "dated_works": len(dated),
            "undated_works": len(rows) - len(dated),
            "earliest_year": min(years) if years else 0,
            "latest_year": max(years) if years else 0,
            "span_years": (max(years) - min(years)) if years else 0,
            "work_type_counts": _counter_rows(
                Counter(
                    str(row.get("work_type") or "unknown").replace("_", " ")
                    for row in dated
                ),
                total=len(dated),
            ),
        }

    if figure_name == "word_counts":
        word_counts = [int(row.get("word_count") or 0) for row in text_bearing]
        total_words = sum(word_counts)
        top_rows = sorted(
            text_bearing, key=lambda row: int(row.get("word_count") or 0), reverse=True
        )[:12]
        top_words = sum(int(row.get("word_count") or 0) for row in top_rows)
        return {
            "text_work_count": len(text_bearing),
            "total_words": total_words,
            "top_12_words": top_words,
            "top_12_share_pct": _pct(top_words, total_words),
            "word_count_summary": _summary(word_counts),
            "largest_work": (
                {
                    "work_id": str(top_rows[0].get("work_id") or ""),
                    "title": str(top_rows[0].get("title") or ""),
                    "word_count": int(top_rows[0].get("word_count") or 0),
                    "share_pct": _pct(
                        int(top_rows[0].get("word_count") or 0), total_words
                    ),
                }
                if top_rows
                else {}
            ),
        }

    if figure_name == "vocab_richness":
        word_counts = [int(row.get("word_count") or 0) for row in text_bearing]
        richness = [
            float(row.get("vocabulary_richness") or 0.0) for row in text_bearing
        ]
        short_count = sum(1 for value in word_counts if value < 1000)
        return {
            "text_work_count": len(text_bearing),
            "short_text_count_under_1000_words": short_count,
            "long_text_count_1000_plus_words": len(text_bearing) - short_count,
            "word_count_summary": _summary(word_counts),
            "type_token_ratio_summary": _summary(richness),
            "pearson_log_words_vs_ttr": _pearson(
                [math.log10(max(value, 1)) for value in word_counts], richness
            ),
        }

    if figure_name == "lexical_signature":
        signature = _read_optional(ao, "visualizations/lexical_signature.json", {})
        top_terms = list(signature.get("top_terms") or [])
        top_bigrams = list(signature.get("top_bigrams") or [])
        lexical_tokens = int(signature.get("lexical_token_count") or 0)
        top_term = top_terms[0] if top_terms else {}
        return {
            "text_work_count": int(signature.get("text_work_count") or 0),
            "total_words": int(signature.get("token_count") or 0),
            "lexical_token_count": lexical_tokens,
            "distinct_terms": int(signature.get("distinct_terms") or 0),
            "top_term": str(top_term.get("term") or ""),
            "top_term_count": int(top_term.get("count") or 0),
            "top_term_document_frequency": int(top_term.get("document_frequency") or 0),
            "top_term_share_pct": _pct(int(top_term.get("count") or 0), lexical_tokens),
            "top_bigram": str(
                (top_bigrams[0] if top_bigrams else {}).get("phrase") or ""
            ),
        }

    if figure_name == "nlp_embedding_pca":
        diagnostics = _read_optional(ao, "data/nlp_diagnostics.json", {})
        embedding = diagnostics.get("embedding") or {}
        pc1 = float(embedding.get("variance_pc1") or 0.0)
        pc2 = float(embedding.get("variance_pc2") or 0.0)
        return {
            "work_count": int(embedding.get("work_count") or 0),
            "feature_count": int(embedding.get("feature_count") or 0),
            "variance_pc1_pct": round(pc1 * 100, 2),
            "variance_pc2_pct": round(pc2 * 100, 2),
            "variance_total_pct": round((pc1 + pc2) * 100, 2),
            "top_terms_pc1": list(embedding.get("top_terms_pc1") or [])[:8],
            "top_terms_pc2": list(embedding.get("top_terms_pc2") or [])[:8],
        }

    if figure_name == "text_image_density":
        word_counts = [int(row.get("word_count") or 0) for row in text_bearing]
        image_counts = [images_by_id.get(row.get("work_id"), 0) for row in text_bearing]
        zero_count = sum(1 for value in image_counts if value == 0)
        return {
            "text_work_count": len(text_bearing),
            "zero_image_text_works": zero_count,
            "zero_image_text_work_pct": _pct(zero_count, len(text_bearing)),
            "text_works_with_images": len(text_bearing) - zero_count,
            "image_count_summary": _summary(image_counts),
            "pearson_log_words_vs_images": _pearson(
                [math.log10(max(value, 1)) for value in word_counts], image_counts
            ),
        }

    if figure_name == "theme_network":
        graph = _read_optional(ao, "visualizations/theme_entity_network.json", {})
        nodes = {node.get("id"): node for node in graph.get("nodes", [])}
        theme_counts: Counter[str] = Counter()
        for edge in graph.get("edges", []):
            node = nodes.get(edge.get("target"), {})
            if node.get("type") == "theme":
                theme_counts[str(node.get("label") or edge.get("target"))] += 1
        return {
            "node_count": len(graph.get("nodes", [])),
            "edge_count": len(graph.get("edges", [])),
            "theme_count": len(theme_counts),
            "top_themes": _counter_rows(theme_counts),
        }

    if figure_name == "text_image_linkage":
        image_counts = [int(row.get("image_count") or 0) for row in link_rows]
        total_images = sum(image_counts)
        top_rows = sorted(
            link_rows, key=lambda row: int(row.get("image_count") or 0), reverse=True
        )[:12]
        top_images = sum(int(row.get("image_count") or 0) for row in top_rows)
        zero_image = sum(1 for value in image_counts if value == 0)
        return {
            "local_work_total": len(link_rows),
            "linked_image_total": total_images,
            "works_with_images": len(link_rows) - zero_image,
            "zero_image_works": zero_image,
            "top_12_image_count": top_images,
            "top_12_image_share_pct": _pct(top_images, total_images),
            "image_count_summary": _summary(image_counts),
        }

    if figure_name == "evidence_gaps":
        audit = _read_optional(ao, "data/source_audit.json", {})
        review = _read_optional(ao, "data/evidence_acquisition_review.json", {})
        review_candidates = [
            candidate
            for target_review in review.get("target_reviews", [])
            for candidate in target_review.get("candidates", [])
        ]
        manual_candidates = [
            candidate
            for candidate in review_candidates
            if str(candidate.get("lead_status") or "") == "manual_review"
            or str(candidate.get("action_taken") or "").startswith("manual_review:")
            or str(candidate.get("status") or "") == "manual_review"
        ]
        counts = Counter()
        for row in target_rows:
            status = row.get("status")
            notes = row.get("notes") or []
            if status == "missing":
                counts["no local work"] += 1
            for note in notes:
                lowered = str(note).lower()
                if "text" in lowered:
                    counts["missing expected text"] += 1
                if "image" in lowered:
                    counts["missing expected image"] += 1
            if status not in {"present", "missing"} and not notes:
                counts[f"{status} evidence"] += 1
        return {
            "target_total": len(target_rows),
            "gap_note_total": int(sum(counts.values())),
            "gap_categories": _counter_rows(counts),
            "missing_evidence_targets": int(
                (audit.get("missing_evidence_summary") or {}).get("target_count") or 0
            ),
            "missing_evidence_candidates": int(
                (audit.get("missing_evidence_summary") or {}).get("candidate_count")
                or 0
            ),
            "acquisition_review_unresolved_targets": int(
                review.get("unresolved_target_count") or 0
            ),
            "acquisition_review_candidate_count": int(
                review.get("candidate_count") or len(review_candidates)
            ),
            "review_candidate_count": len(review_candidates),
            "manual_review_candidate_count": len(manual_candidates),
        }

    if figure_name == "pipeline_dag":
        records = _pipeline_phase_records(ao)
        status_counts = Counter(record["raw_status"] for record in records)
        action_counts = Counter(record["action_class"] for record in records)
        return {
            "phase_count": len(records),
            "status_counts": _counter_rows(status_counts, total=len(records)),
            "action_counts": _counter_rows(action_counts, total=len(records)),
            "completed_phases": int(status_counts.get("completed") or 0),
            "reused_or_not_rerun_phases": int(
                action_counts.get("reused", 0) + action_counts.get("not rerun", 0)
            ),
            "phase_records": records,
        }

    if figure_name in {"all_acquired_images_mosaic", "work_area_image_mosaics"}:
        records = _valid_image_records(ao.parent, ao)
        reported_images = int(corpus_stats.get("total_images") or len(records))
        category_counts = Counter(
            str(record.get("category") or "uncategorized") for record in records
        )
        return {
            "reported_local_images": reported_images,
            "valid_local_image_paths": len(records),
            "excluded_missing_or_unreadable_paths": max(
                reported_images - len(records), 0
            ),
            "valid_path_pct_of_reported_images": _pct(len(records), reported_images),
            "category_count": len(category_counts),
            "category_counts": _counter_rows(category_counts, total=len(records)),
        }

    if figure_name == "work_evidence_profile_grid":
        profiles = _work_profiles(ao)
        status_counts = Counter(str(profile["status"]) for profile in profiles)
        text_count = sum(1 for profile in profiles if profile["has_text"])
        image_count = sum(1 for profile in profiles if int(profile["image_count"]) > 0)
        return {
            "target_total": len(profiles),
            "status_counts": _counter_rows(status_counts, total=len(profiles)),
            "text_targets": text_count,
            "text_target_pct": _pct(text_count, len(profiles)),
            "image_targets": image_count,
            "image_target_pct": _pct(image_count, len(profiles)),
            "category_count": len({profile["category"] for profile in profiles}),
        }

    if figure_name in {"image_depth_by_work", "image_depth_by_area"}:
        resolved = [int(row.get("resolved_object_count") or 0) for row in image_depth]
        downloaded = [
            int(
                row.get("local_image_count")
                if row.get("local_image_count") is not None
                else row.get("downloaded_image_count") or 0
            )
            for row in image_depth
        ]
        status_counts = Counter(
            str(row.get("image_depth_status") or "unrecorded") for row in image_depth
        )
        failure_total = sum(int(row.get("failure_count") or 0) for row in image_depth)
        category_counts = Counter(
            str(row.get("category") or "uncategorized").replace("_", " ")
            for row in image_depth
        )
        total_resolved = sum(resolved)
        total_downloaded = sum(downloaded)
        return {
            "image_depth_work_count": len(image_depth),
            "resolved_object_total": total_resolved,
            "downloaded_image_total": total_downloaded,
            "downloaded_vs_resolved_pct": _pct(total_downloaded, total_resolved),
            "failure_total": failure_total,
            "status_counts": _counter_rows(status_counts, total=len(image_depth)),
            "category_counts": _counter_rows(category_counts, total=len(image_depth)),
            "resolved_summary": _summary(resolved),
            "downloaded_summary": _summary(downloaded),
        }

    if figure_name == "source_authority_tiers":
        rows = _read_optional(ao, "visualizations/source_authority_tiers.json", [])
        counts = Counter(
            {
                str(row.get("authority_tier") or "unrecorded"): int(
                    row.get("work_count") or 0
                )
                for row in rows
            }
        )
        total = sum(counts.values()) or total_works
        return {
            "local_work_total": total,
            "tier_count": len(counts),
            "tier_counts": _counter_rows(counts, total=total),
        }

    return {
        "artifact_status": "unrecognized_figure",
        "available_target_rows": len(target_rows),
    }


def fig_coverage_status(ao: Path, out_dir: Path) -> Path:
    data = _read(ao, "reports/source_coverage.json")
    counts = data["coverage_counts"]
    order = ["present", "partial", "missing", "unverified", "duplicate"]
    labels = [status for status in order if status in counts]
    values = [int(counts[status]) for status in labels]
    total = int(counts.get("total", sum(values))) or 1
    present = int(counts.get("present", 0))
    open_total = sum(
        int(counts.get(status, 0))
        for status in ("partial", "missing", "unverified", "duplicate")
    )

    fig, ax = plt.subplots(figsize=(8.6, 5.0))
    _style(ax)
    bars = ax.bar(
        labels,
        values,
        color=[STATUS_COLORS.get(label, PALETTE["gray"]) for label in labels],
    )
    for bar, value in zip(bars, values):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            value + total * 0.012,
            f"{value}\n{value / total * 100:.1f}%",
            ha="center",
            va="bottom",
            fontsize=10.8,
            color=INK,
            weight="bold",
        )
    ax.set_ylabel("target entries")
    ax.set_ylim(0, max(values + [1]) * 1.18)
    _title_with_subtitle(
        ax,
        f"{present} of {total} targets fully evidenced",
        f"{open_total} open targets ({open_total / total * 100:.1f}%) remain partial, missing, unverified, or duplicate.",
    )
    return _save(fig, out_dir, "coverage_status")


def fig_category_coverage(ao: Path, out_dir: Path) -> Path:
    rows = _read(ao, "visualizations/target_coverage_matrix.json")
    by_category: dict[str, Counter[str]] = defaultdict(Counter)
    for row in rows:
        by_category[row.get("category", "uncategorized").replace("_", " ")][
            row.get("status", "")
        ] += 1

    categories = sorted(
        by_category,
        key=lambda cat: (
            -sum(
                by_category[cat].get(status, 0)
                for status in ("partial", "missing", "unverified", "duplicate")
            ),
            -sum(by_category[cat].values()),
            cat,
        ),
    )
    fig, ax = plt.subplots(figsize=(9.8, max(5.2, len(categories) * 0.48)))
    _style(ax, grid_axis="x")
    left = [0] * len(categories)
    totals = [sum(by_category[category].values()) for category in categories]
    open_counts = [
        sum(
            by_category[category].get(status, 0)
            for status in ("partial", "missing", "unverified", "duplicate")
        )
        for category in categories
    ]
    max_total = max(totals + [1])
    for status in ["present", "partial", "missing", "unverified", "duplicate"]:
        values = [by_category[category].get(status, 0) for category in categories]
        left_before = list(left)
        bars = ax.barh(
            categories,
            values,
            left=left,
            color=STATUS_COLORS.get(status, PALETTE["gray"]),
            label=status,
            height=0.7,
        )
        for bar, value, start in zip(bars, values, left_before):
            if value <= 0:
                continue
            if value >= max(2, max_total * 0.045):
                ax.text(
                    start + value / 2,
                    bar.get_y() + bar.get_height() / 2,
                    str(value),
                    ha="center",
                    va="center",
                    fontsize=9.5,
                    color=BG if status in {"present", "partial", "missing"} else INK,
                    weight="bold",
                )
        left = [base + value for base, value in zip(left, values)]
    for index, (total, open_count) in enumerate(zip(totals, open_counts)):
        ax.text(
            total + max_total * 0.015,
            index,
            f"{open_count} open / {total}",
            va="center",
            fontsize=9.8,
            color=MUTED,
        )
    ax.set_xlabel("target entries")
    ax.set_xlim(0, max_total * 1.42)
    _title_with_subtitle(
        ax,
        "Target evidence states by ledger category",
        "Each row prints unresolved targets over the category denominator.",
    )
    ax.legend(frameon=False, ncol=5, loc="lower right", bbox_to_anchor=(1.0, -0.16))
    return _save(fig, out_dir, "category_coverage")


def fig_corpus_modalities(ao: Path, out_dir: Path) -> Path:
    text_rows = _read(ao, "visualizations/text_metrics.json")
    link_rows = _read(ao, "visualizations/text_image_linkage.json")
    text_by_id = {row.get("work_id"): bool(row.get("has_text")) for row in text_rows}
    image_by_id = {
        row.get("work_id"): int(row.get("image_count", 0)) > 0 for row in link_rows
    }
    work_ids = sorted(set(text_by_id) | set(image_by_id))
    counts = Counter(
        (
            "text + image"
            if text_by_id.get(work_id) and image_by_id.get(work_id)
            else (
                "text only"
                if text_by_id.get(work_id)
                else "image only" if image_by_id.get(work_id) else "metadata only"
            )
        )
        for work_id in work_ids
    )
    labels = ["text + image", "text only", "image only", "metadata only"]
    values = [counts.get(label, 0) for label in labels]
    colors = [PALETTE["green"], PALETTE["blue"], PALETTE["gold"], PALETTE["gray"]]

    fig, ax = plt.subplots(figsize=(8.2, 4.8))
    _style(ax)
    bars = ax.bar(labels, values, color=colors)
    for bar, value in zip(bars, values):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            value + 0.7,
            str(value),
            ha="center",
            va="bottom",
        )
    ax.set_ylabel("local records")
    _title_with_subtitle(
        ax,
        "Local work records separate text, image, joint, and metadata evidence",
        "Counts are local records; image presence is not object- or copy-complete coverage.",
    )
    return _save(fig, out_dir, "corpus_modalities")


def fig_source_audit(ao: Path, out_dir: Path) -> Path:
    audit = _read_optional(ao, "data/source_audit.json", {})
    review = _read_optional(ao, "data/evidence_acquisition_review.json", {})
    analysis_summary = _read_optional(ao, "analysis/analysis_summary.json", {})
    checked = (audit.get("live") or {}).get("checked_urls") or []
    provider_discovery = audit.get("provider_discovery") or {}
    archive_metadata = (
        audit.get("metadata_enrichment_report")
        or (audit.get("live") or {}).get("archive_metadata_enrichment")
        or {}
    )
    labels = [_wrapped(row.get("label", ""), width=22) for row in checked]
    statuses = [row.get("status") for row in checked]
    values = [1 for _ in checked]
    colors = [PALETTE["green"] if row.get("ok") else PALETTE["red"] for row in checked]

    fig, ax = plt.subplots(figsize=(10.0, max(5.2, len(labels) * 0.45)))
    _style(ax, grid_axis="")
    ax.barh(labels, values, color=colors, height=0.68)
    for index, status in enumerate(statuses):
        label = str(status) if status is not None else "no response"
        ax.text(
            0.52,
            index,
            label,
            va="center",
            ha="center",
            color=BG,
            fontsize=10.5,
            weight="bold",
        )
    ax.set_xlim(0, 1.05)
    ax.set_xticks([])
    ok_count = sum(1 for row in checked if row.get("ok"))
    provider_failures = int(provider_discovery.get("failure_count") or 0)
    attempted = int(archive_metadata.get("attempted") or 0)
    succeeded = int(archive_metadata.get("succeeded") or 0)
    metadata_status = str(archive_metadata.get("status") or "unknown")
    analysis_current = "current" if analysis_summary.get("analysis_results_current") else "stale"
    _title_with_subtitle(
        ax,
        f"Source audit recorded {ok_count}/{len(checked)} endpoint checks OK",
        f"Provider warnings {provider_failures}; Archive metadata {succeeded}/{attempted} {metadata_status}; analysis {analysis_current}.",
    )
    fallback = archive_metadata.get("fallback_source_used")
    review_candidates = int(review.get("candidate_count") or 0)
    manual_candidates = sum(
        1
        for target_review in review.get("target_reviews", [])
        for candidate in target_review.get("candidates", [])
        if str(candidate.get("lead_status") or "") == "manual_review"
        or str(candidate.get("action_taken") or "").startswith("manual_review:")
        or str(candidate.get("status") or "") == "manual_review"
    )
    notes = []
    if fallback:
        notes.append(f"Archive records fall back to {fallback}.")
    if review_candidates:
        notes.append(
            f"Evidence review lists {review_candidates} candidates, including {manual_candidates} manual-review leads."
        )
    if notes:
        ax.text(
            0,
            -0.9,
            " ".join(notes),
            color=MUTED,
            fontsize=9.4,
            ha="left",
            va="top",
        )
    return _save(fig, out_dir, "source_audit")


def fig_chronology(ao: Path, out_dir: Path) -> Path:
    rows = [
        row for row in _read(ao, "visualizations/chronology.json") if row.get("date")
    ]
    work_types = sorted(
        {row.get("work_type", "unknown").replace("_", " ") for row in rows}
    )
    y_by_type = {label: index for index, label in enumerate(work_types)}

    fig, ax = plt.subplots(figsize=(8.6, max(4.2, len(work_types) * 0.42)))
    _style(ax, grid_axis="x")
    for index, row in enumerate(rows):
        year = int(str(row["date"])[:4])
        label = row.get("work_type", "unknown").replace("_", " ")
        jitter = ((index % 5) - 2) * 0.045
        ax.scatter(
            year,
            y_by_type[label] + jitter,
            s=44,
            color=(
                PALETTE["blue"]
                if row.get("source") == "blake_archive"
                else PALETTE["violet"]
            ),
            edgecolors=BG,
            linewidth=0.6,
            alpha=0.9,
        )
    ax.set_yticks(list(y_by_type.values()))
    ax.set_yticklabels(work_types)
    ax.set_xlabel("year")
    ax.set_title("Chronology of acquired local records")
    return _save(fig, out_dir, "chronology")


def _record_bars(ax: Axes, rows: list[dict[str, Any]], values: list[int], colors: Any) -> BarContainer:
    """Keep equally titled source/copy records on distinct numeric rows."""
    if len(rows) != len(values) or any(value < 0 for value in values):
        raise ValueError("Record bars require matching nonnegative counts")
    positions = list(range(len(rows)))
    bars = ax.barh(positions, values, color=colors)
    labels = [
        f"{rank}. "
        + _wrapped(_short(row.get("title") or row.get("work_id", ""), 32), width=24)
        for rank, row in enumerate(rows, 1)
    ]
    ax.set_yticks(positions)
    ax.set_yticklabels(labels)
    ax.invert_yaxis()
    ax.set_xlim(0, max(values + [1]) * 1.20)
    return bars


def fig_word_counts(ao: Path, out_dir: Path) -> Path:
    all_rows = [
        row
        for row in _read(ao, "visualizations/text_metrics.json")
        if row.get("has_text")
    ]
    total_words = sum(int(row.get("word_count", 0)) for row in all_rows)
    rows = sorted(
        all_rows, key=lambda row: int(row.get("word_count", 0)), reverse=True
    )[:12]
    words = [int(row.get("word_count", 0)) for row in rows]
    top_share = _pct(sum(words), total_words)

    fig, ax = plt.subplots(figsize=(9.4, max(5.2, len(rows) * 0.52 + 1.2)))
    _style(ax, grid_axis="x")
    bars = _record_bars(ax, rows, words, PALETTE["blue"])
    for bar, value in zip(bars, words):
        ax.text(
            value + max(words) * 0.012,
            bar.get_y() + bar.get_height() / 2,
            f"{value:,}",
            va="center",
        )
    ax.set_xlabel("words")
    _title_with_subtitle(
        ax,
        f"Largest text records: {top_share:.1f}% of {total_words:,} words",
        "Ranked bars distinguish source/copy records with repeated titles.",
    )
    return _save(fig, out_dir, "word_counts")


def fig_vocab_richness(ao: Path, out_dir: Path) -> Path:
    rows = [
        row
        for row in _read(ao, "visualizations/text_metrics.json")
        if row.get("has_text")
    ]
    x = [max(int(row.get("word_count", 0)), 1) for row in rows]
    y = [float(row.get("vocabulary_richness", 0.0)) for row in rows]
    colors = [PALETTE["gold"] if value < 1000 else PALETTE["green"] for value in x]
    richness_summary = _summary(y)
    short_count = sum(1 for value in x if value < 1000)

    fig, ax = plt.subplots(figsize=(8.8, 5.3))
    _style(ax)
    ax.scatter(x, y, s=58, color=colors, edgecolors=BG, linewidth=0.7, alpha=0.9)
    ax.set_xscale("log")
    if x:
        ax.set_xlim(max(min(x) * 0.7, 0.8), max(x) * 2.6)
    ax.set_xlabel("word count (log scale)")
    ax.set_ylabel("type-token ratio")
    _title_with_subtitle(
        ax,
        f"Vocabulary richness is length-sensitive (n={len(rows)})",
        f"Median type-token ratio {richness_summary['median']:.2f}; short records can inflate type-token ratio.",
    )
    ax.text(
        0.02,
        0.03,
        f"{short_count} texts under 1,000 words; short texts can inflate type-token ratio",
        transform=ax.transAxes,
        fontsize=9.4,
        color=MUTED,
        bbox={"facecolor": BG, "edgecolor": GRID, "alpha": 0.92, "pad": 2.5},
    )
    return _save(fig, out_dir, "vocab_richness")


def fig_lexical_signature(ao: Path, out_dir: Path) -> Path:
    signature = _read_optional(ao, "visualizations/lexical_signature.json", {})
    terms = list(signature.get("top_terms") or [])[:16]
    phrases = list(signature.get("top_bigrams") or [])[:8]

    fig, (ax_terms, ax_phrases) = plt.subplots(
        1,
        2,
        figsize=(11.2, max(5.3, len(terms) * 0.34)),
        gridspec_kw={"width_ratios": [1.25, 1]},
    )
    _style(ax_terms, grid_axis="x")
    _style(ax_phrases, grid_axis="x")
    if not terms:
        ax_terms.text(
            0.5, 0.5, "No lexical signature available", ha="center", va="center"
        )
        ax_terms.set_axis_off()
        ax_phrases.set_axis_off()
        ax_terms.set_title("Corpus lexical signature")
        return _save(fig, out_dir, "lexical_signature")

    term_labels = [_wrapped(row.get("term", ""), width=16) for row in terms]
    term_values = [int(row.get("count", 0)) for row in terms]
    lexical_total = int(signature.get("lexical_token_count") or sum(term_values))
    top_share = _pct(term_values[0] if term_values else 0, lexical_total)
    bars = ax_terms.barh(term_labels[::-1], term_values[::-1], color=PALETTE["slate"])
    for bar, value in zip(bars, term_values[::-1]):
        ax_terms.text(
            value + max(term_values) * 0.012,
            bar.get_y() + bar.get_height() / 2,
            str(value),
            va="center",
        )
    ax_terms.set_xlabel("filtered token count")
    _title_with_subtitle(
        ax_terms,
        "Leading lexical terms",
        f"Top term: {top_share:.1f}% of filtered tokens",
    )
    ax_terms.set_xlim(0, max(term_values + [1]) * 1.18)

    phrase_labels = [_wrapped(row.get("phrase", ""), width=18) for row in phrases]
    phrase_values = [int(row.get("count", 0)) for row in phrases]
    ax_phrases.barh(phrase_labels[::-1], phrase_values[::-1], color=PALETTE["violet"])
    ax_phrases.set_xlabel("phrase count")
    _title_with_subtitle(
        ax_phrases,
        "Adjacent-term phrases",
        f"{signature.get('text_work_count', 0)} text records",
    )
    return _save(fig, out_dir, "lexical_signature")


def fig_nlp_embedding_pca(ao: Path, out_dir: Path) -> Path:
    diagnostics = build_nlp_diagnostics(ao.parent)
    embedding = diagnostics.get("embedding", {})
    points = embedding.get("points") or []

    fig, ax = plt.subplots(figsize=(10.2, 6.2))
    _style(ax)
    if not points:
        ax.text(
            0.5, 0.5, "No text embedding points available", ha="center", va="center"
        )
        ax.set_axis_off()
        ax.set_title("No text-bearing works entered the embedding")
        return _save(fig, out_dir, "nlp_embedding_pca")

    max_words = max(int(point.get("word_count", 0)) for point in points) or 1
    sizes = [
        34
        + 130
        * (math.log10(int(point.get("word_count", 0)) + 1) / math.log10(max_words + 1))
        for point in points
    ]
    x = [float(point.get("pc1", 0.0)) for point in points]
    y = [float(point.get("pc2", 0.0)) for point in points]
    colors = [
        PALETTE["blue"] if int(point.get("word_count", 0)) >= 1000 else PALETTE["gold"]
        for point in points
    ]
    ax.scatter(x, y, s=sizes, color=colors, edgecolors=BG, linewidth=0.7, alpha=0.86)
    ax.margins(x=0.08, y=0.12)

    ax.axhline(0, color=GRID, linewidth=0.8)
    ax.axvline(0, color=GRID, linewidth=0.8)
    legend_items = [
        Line2D(
            [0],
            [0],
            marker="o",
            color="none",
            markerfacecolor=PALETTE["blue"],
            markeredgecolor=BG,
            label="1,000+ words",
            markersize=8,
        ),
        Line2D(
            [0],
            [0],
            marker="o",
            color="none",
            markerfacecolor=PALETTE["gold"],
            markeredgecolor=BG,
            label="<1,000 words",
            markersize=8,
        ),
    ]
    ax.legend(handles=legend_items, frameon=False, loc="lower right")
    pc1 = float(embedding.get("variance_pc1", 0.0)) * 100
    pc2 = float(embedding.get("variance_pc2", 0.0)) * 100
    ax.set_xlabel(f"PC1 ({pc1:.1f}% variance)")
    ax.set_ylabel(f"PC2 ({pc2:.1f}% variance)")
    top_pc1 = ", ".join(list(embedding.get("top_terms_pc1") or [])[:4])
    top_pc2 = ", ".join(list(embedding.get("top_terms_pc2") or [])[:4])
    ax.text(
        0.015,
        0.02,
        f"{len(points)} records, {int(embedding.get('feature_count') or 0)} features\n"
        f"PC1 terms: {top_pc1}\nPC2 terms: {top_pc2}",
        transform=ax.transAxes,
        fontsize=9.0,
        color=MUTED,
        bbox={"facecolor": BG, "edgecolor": GRID, "alpha": 0.92, "pad": 2.5},
    )
    _title_with_subtitle(
        ax,
        f"Text-bearing PCA diagnostic: PC1+PC2 explain {pc1 + pc2:.1f}%",
        "Centered TF-IDF covariance projection; points are source/copy records.",
        pad=20,
    )
    return _save(fig, out_dir, "nlp_embedding_pca")


def fig_text_image_density(ao: Path, out_dir: Path) -> Path:
    text_rows = [
        row
        for row in _read(ao, "visualizations/text_metrics.json")
        if row.get("has_text")
    ]
    link_rows = _read(ao, "visualizations/text_image_linkage.json")
    images_by_id = {
        row.get("work_id"): int(row.get("image_count", 0)) for row in link_rows
    }

    fig, ax = plt.subplots(figsize=(9.5, 5.8))
    _style(ax)
    if not text_rows:
        ax.text(0.5, 0.5, "No text-bearing works available", ha="center", va="center")
        ax.set_axis_off()
        ax.set_title("No text-bearing works available for text-image density")
        return _save(fig, out_dir, "text_image_density")

    x = [max(int(row.get("word_count", 0)), 1) for row in text_rows]
    y = [images_by_id.get(row.get("work_id"), 0) for row in text_rows]
    density = [float(row.get("lexical_density", 0.0)) for row in text_rows]
    distinct_terms = [int(row.get("distinct_lexical_terms", 0)) for row in text_rows]
    max_distinct = max(distinct_terms) or 1
    sizes = [42 + 130 * (value / max_distinct) for value in distinct_terms]
    scatter = ax.scatter(
        x,
        y,
        c=density,
        s=sizes,
        cmap="cividis",
        edgecolors=BG,
        linewidth=0.7,
        alpha=0.88,
    )
    ax.set_xscale("log")
    ax.set_xlim(max(min(x) * 0.72, 0.8), max(x) * 2.9)
    max_images = max(y + [1])
    ax.set_ylim(-0.12, max_images * 1.13)
    ax.set_xlabel("word count (log scale)")
    ax.set_ylabel("image associations")
    zero_count = sum(1 for value in y if value == 0)
    correlation = _pearson([math.log10(max(value, 1)) for value in x], y)
    ax.axhline(0, color=GRID, linewidth=1.0, linestyle="--")
    _note(
        ax,
        f"{zero_count} of {len(text_rows)} text records have zero image associations\n"
        f"local Pearson r(log words, images) = {correlation:.2f}",
        xy=(0.02, 0.03),
    )
    _title_with_subtitle(
        ax,
        "Cross-modal density is bounded to text-bearing local records",
        "Bubble size encodes distinct lexical terms; color encodes lexical density.",
    )
    colorbar = fig.colorbar(scatter, ax=ax, fraction=0.042, pad=0.03)
    colorbar.set_label("lexical density")

    return _save(fig, out_dir, "text_image_density")


def fig_theme_network(ao: Path, out_dir: Path) -> Path:
    data = _read(ao, "visualizations/theme_entity_network.json")
    nodes = {node["id"]: node for node in data.get("nodes", [])}
    theme_counts: Counter[str] = Counter()
    for edge in data.get("edges", []):
        target = edge.get("target")
        node = nodes.get(target, {})
        if node.get("type") == "theme":
            theme_counts[node.get("label", target)] += 1
    common = theme_counts.most_common(16)
    labels = [_wrapped(label, width=18) for label, _ in common]
    values = [count for _, count in common]

    fig, ax = plt.subplots(figsize=(9.2, max(5.0, len(common) * 0.43)))
    _style(ax, grid_axis="x")
    bars = ax.barh(labels[::-1], values[::-1], color=PALETTE["violet"])
    for bar, value in zip(bars, values[::-1]):
        ax.text(
            value + 0.2, bar.get_y() + bar.get_height() / 2, str(value), va="center"
        )
    ax.set_xlabel("record-theme links")
    _title_with_subtitle(
        ax,
        "Most frequent generated themes in the record-theme graph",
        "Counts are computational record-theme links; metadata and model sources are retained.",
    )
    return _save(fig, out_dir, "theme_network")


def fig_text_image_linkage(ao: Path, out_dir: Path) -> Path:
    rows = _read(ao, "visualizations/text_image_linkage.json")
    total_linked_images = sum(int(row.get("image_count", 0)) for row in rows)
    rows = sorted(rows, key=lambda row: int(row.get("image_count", 0)), reverse=True)[
        :12
    ]
    images = [int(row.get("image_count", 0)) for row in rows]
    colors = [
        PALETTE["green"] if row.get("has_text") else PALETTE["gold"] for row in rows
    ]

    fig, ax = plt.subplots(figsize=(9.4, max(5.2, len(rows) * 0.52 + 1.2)))
    _style(ax, grid_axis="x")
    bars = _record_bars(ax, rows, images, colors)
    for bar, value in zip(bars, images):
        ax.text(
            value + max(images + [1]) * 0.012,
            bar.get_y() + bar.get_height() / 2,
            str(value),
            va="center",
        )
    ax.set_xlabel("image associations")
    _title_with_subtitle(
        ax,
        f"Top {len(rows)} records: {sum(images):,}/{total_linked_images:,} image associations",
        "Ranks distinguish source/copy records; associations can reuse files.",
    )
    return _save(fig, out_dir, "text_image_linkage")


def fig_evidence_gaps(ao: Path, out_dir: Path) -> Path:
    rows = _read(ao, "visualizations/target_coverage_matrix.json")
    counts: Counter[str] = Counter()
    for row in rows:
        status = row.get("status")
        notes = row.get("notes") or []
        if status == "missing":
            counts["no local work"] += 1
        for note in notes:
            if "text" in str(note).lower():
                counts["missing expected text"] += 1
            if "image" in str(note).lower():
                counts["missing expected image"] += 1
        if status not in {"present", "missing"} and not notes:
            counts[f"{status} evidence"] += 1
    labels = [label for label, _count in counts.most_common()]
    values = [counts[label] for label in labels]
    if not labels:
        labels = ["none"]
        values = [0]
    color_cycle = [
        PALETTE["red"],
        PALETTE["gold"],
        PALETTE["blue"],
        PALETTE["violet"],
        PALETTE["gray"],
    ]

    fig, ax = plt.subplots(figsize=(9.0, max(4.8, len(labels) * 0.62)))
    _style(ax, grid_axis="x")
    bars = ax.barh(
        labels[::-1],
        values[::-1],
        color=[color_cycle[index % len(color_cycle)] for index in range(len(labels))],
    )
    for bar, value in zip(bars, values[::-1]):
        ax.text(
            value + max(values + [1]) * 0.025,
            bar.get_y() + bar.get_height() / 2,
            str(value),
            ha="left",
            va="center",
        )
    ax.set_xlabel("target entries")
    _title_with_subtitle(
        ax,
        "Open evidence gaps in the target ledger",
        "Gap-note categories guide review and do not replace source inspection.",
    )
    return _save(fig, out_dir, "evidence_gaps")


def _pipeline_strip_label(record: Mapping[str, Any]) -> str:
    action_class = str(record.get("action_class") or "other")
    phase_name = str(record.get("name") or "")
    if phase_name == "acquisition" and action_class == "reused":
        return "REUSED CORPUS"
    if action_class == "generated":
        return "GENERATED"
    if action_class == "not rerun":
        return "NOT RERUN"
    if action_class == "reused":
        return "REUSED"
    return str(record.get("action") or action_class).upper()


def fig_pipeline_dag(ao: Path, out_dir: Path) -> Path:
    records = _pipeline_phase_records(ao)
    generated = sum(1 for record in records if record["action_class"] == "generated")
    reused = sum(1 for record in records if record["action_class"] == "reused")
    not_rerun = sum(1 for record in records if record["action_class"] == "not rerun")
    class_colors = {
        "generated": PALETTE["green"],
        "reused": PALETTE["blue"],
        "not rerun": PALETTE["gold"],
        "other": PALETTE["gray"],
    }
    card_w = 1.85
    gap = 0.28
    card_h = 1.82
    total_w = len(records) * card_w + max(len(records) - 1, 0) * gap

    fig, ax = plt.subplots(figsize=(15.6, 5.5))
    ax.set_facecolor(BG)
    for index, record in enumerate(records):
        x = index * (card_w + gap)
        color = class_colors.get(str(record["action_class"]), PALETTE["gray"])
        strip_label = _pipeline_strip_label(record)
        ax.add_patch(
            Rectangle(
                (x, 0),
                card_w,
                card_h,
                facecolor=PALETTE["pale"],
                edgecolor=INK,
                linewidth=0.8,
                zorder=2,
            )
        )
        ax.add_patch(
            Rectangle(
                (x, card_h - 0.34),
                card_w,
                0.34,
                facecolor=color,
                edgecolor=INK,
                linewidth=0.0,
                zorder=3,
            )
        )
        ax.text(
            x + card_w / 2,
            card_h - 0.17,
            strip_label,
            ha="center",
            va="center",
            fontsize=8.4,
            weight="bold",
            color="white" if record["action_class"] in {"generated", "reused"} else INK,
            zorder=4,
        )
        ax.text(
            x + card_w / 2,
            1.22,
            "\n".join(textwrap.wrap(str(record["label"]), width=17)),
            ha="center",
            va="center",
            fontsize=10.2,
            weight="bold",
            color=INK,
            zorder=4,
            linespacing=0.95,
        )
        ax.text(
            x + card_w / 2,
            0.79,
            "\n".join(textwrap.wrap(str(record["evidence"]), width=18)),
            ha="center",
            va="center",
            fontsize=8.7,
            color=INK,
            zorder=4,
            linespacing=0.95,
        )
        ax.text(
            x + card_w / 2,
            0.34,
            "\n".join(textwrap.wrap(str(record["note"]), width=26)),
            ha="center",
            va="center",
            fontsize=7.8,
            color=MUTED,
            zorder=4,
            linespacing=0.95,
        )
        if index < len(records) - 1:
            ax.annotate(
                "",
                xy=(x + card_w + gap * 0.82, 0.91),
                xytext=(x + card_w + gap * 0.14, 0.91),
                arrowprops=dict(arrowstyle="->", color=MUTED, lw=1.4),
            )

    legend = [("generated this run", class_colors["generated"])]
    if reused:
        legend.append(("reused existing local evidence", class_colors["reused"]))
    if not_rerun:
        legend.append(("not rerun in this validation command", class_colors["not rerun"]))
    for index, (label, color) in enumerate(legend):
        x = 0.15 + index * 3.1
        ax.add_patch(
            Rectangle((x, -0.62), 0.22, 0.22, facecolor=color, edgecolor=INK, linewidth=0.4)
        )
        ax.text(x + 0.31, -0.51, label, ha="left", va="center", fontsize=9.2, color=INK)

    ax.text(
        total_w / 2,
        2.62,
        "Saved corpus workflow: generated phases plus explicit artifact reuse",
        ha="center",
        va="center",
        fontsize=15.0,
        weight="bold",
        color=INK,
    )
    summary_parts = [
        f"{generated} phase{'s' if generated != 1 else ''} generated artifacts in the saved run"
    ]
    if reused:
        summary_parts.append(
            f"{reused} phase{'s' if reused != 1 else ''} reused existing local evidence"
        )
    if not_rerun:
        summary_parts.append(
            f"{not_rerun} phase{'s were' if not_rerun != 1 else ' was'} not rerun"
        )
    ax.text(
        total_w / 2,
        2.34,
        "; ".join(summary_parts) + ".",
        ha="center",
        va="center",
        fontsize=10.0,
        color=MUTED,
    )
    ax.set_xlim(-0.15, total_w + 0.15)
    ax.set_ylim(-0.82, 2.82)
    ax.axis("off")
    return _save(fig, out_dir, "pipeline_dag")


def fig_all_acquired_images_mosaic(ao: Path, out_dir: Path) -> Path:
    records = _valid_image_records(ao.parent, ao)
    tile_w, thumb_h, label_h, gap = 62, 46, 14, 3
    cols = 40
    rows = max(math.ceil(len(records) / cols), 1)
    header_h = 78
    width = cols * tile_w + (cols + 1) * gap
    height = header_h + rows * (thumb_h + label_h + gap) + gap
    image = Image.new("RGB", (width, height), BG)
    draw = ImageDraw.Draw(image)
    title_font = _pil_font(30, bold=True)
    small_font = _pil_font(13)
    label_font = _pil_font(8)
    draw.text(
        (gap, 14),
        f"{len(records)} acquired image files with valid local paths",
        fill=INK,
        font=title_font,
    )
    draw.text(
        (gap, 46),
        "One tile per local file; generated cover art and missing metadata paths are excluded.",
        fill=MUTED,
        font=small_font,
    )
    for index, record in enumerate(records):
        row, col = divmod(index, cols)
        x = gap + col * (tile_w + gap)
        y = header_h + row * (thumb_h + label_h + gap)
        draw.rounded_rectangle(
            (x, y, x + tile_w, y + thumb_h + label_h),
            radius=4,
            fill=PALETTE["pale"],
            outline=GRID,
        )
        thumb = _thumbnail(record["path"], (tile_w - 6, thumb_h - 6))
        image.paste(thumb, (x + 3, y + 3))
        _draw_wrapped(
            draw,
            (x + 3, y + thumb_h + 1),
            str(record["work_id"]),
            label_font,
            INK,
            tile_w - 6,
            max_lines=1,
        )
    return _save_pil(image, out_dir, "all_acquired_images_mosaic")


def fig_work_area_image_mosaics(ao: Path, out_dir: Path) -> Path:
    records = _valid_image_records(ao.parent, ao)
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        grouped[record["category"]].append(record)
    categories = sorted(grouped, key=lambda key: (-len(grouped[key]), key))
    tile_w, thumb_h, label_h, gap = 44, 30, 9, 2
    panel_pad = 5
    cols = 60
    width = cols * tile_w + (cols + 1) * gap + (panel_pad * 2)
    title_h = 56
    panel_header = 16
    panel_heights = []
    for category in categories:
        rows = max(math.ceil(len(grouped[category]) / cols), 1)
        panel_heights.append(panel_header + rows * (thumb_h + label_h + gap) + gap)
    height = title_h + sum(panel_heights) + gap
    image = Image.new("RGB", (width, height), BG)
    draw = ImageDraw.Draw(image)
    title_font = _pil_font(29, bold=True)
    header_font = _pil_font(11, bold=True)
    label_font = _pil_font(5)
    draw.text(
        (gap, 9),
        "Acquired image files grouped by work area",
        fill=INK,
        font=title_font,
    )
    draw.text(
        (gap, 37),
        "Ledger categories orient the image mosaic; counts are local valid files.",
            fill=MUTED,
            font=_pil_font(13),
    )
    y = title_h
    for category, panel_h in zip(categories, panel_heights):
        draw.rounded_rectangle(
            (gap, y, width - gap, y + panel_h - gap),
            radius=5,
            fill=PALETTE["pale"],
            outline=GRID,
        )
        label = f"{category} ({len(grouped[category])} files)"
        draw.text((gap + 7, y + 4), label, fill=INK, font=header_font)
        for index, record in enumerate(grouped[category]):
            row, col = divmod(index, cols)
            x = gap + panel_pad + col * (tile_w + gap)
            tile_y = y + panel_header + row * (thumb_h + label_h + gap)
            thumb = _thumbnail(record["path"], (tile_w - 4, thumb_h - 4))
            draw.rectangle(
                (x, tile_y, x + tile_w, tile_y + thumb_h + label_h),
                fill=BG,
                outline=GRID,
            )
            image.paste(thumb, (x + 2, tile_y + 2))
            _draw_wrapped(
                draw,
                (x + 2, tile_y + thumb_h),
                str(record["work_id"]),
                label_font,
                INK,
                tile_w - 4,
                max_lines=1,
            )
        y += panel_h
    return _save_pil(image, out_dir, "work_area_image_mosaics")


def fig_work_evidence_profile_grid(ao: Path, out_dir: Path) -> Path:
    profiles = _work_profiles(ao)
    status_counts = Counter(profile["status"] for profile in profiles)
    text_count = sum(1 for profile in profiles if profile["has_text"])
    image_count = sum(1 for profile in profiles if int(profile["image_count"]) > 0)
    cols = 6
    tile_w, tile_h, gap = 236, 58, 7
    header_h = 72
    rows = max(math.ceil(len(profiles) / cols), 1)
    width = cols * tile_w + (cols + 1) * gap
    height = header_h + rows * (tile_h + gap) + gap
    image = Image.new("RGB", (width, height), BG)
    draw = ImageDraw.Draw(image)
    title_font = _pil_font(26, bold=True)
    body_font = _pil_font(9)
    body_bold = _pil_font(9, bold=True)
    draw.text(
        (gap, 10),
        f"{len(profiles)} target works as compact evidence profiles",
        fill=INK,
        font=title_font,
    )
    draw.text(
        (gap, 38),
        f"First matched record: {text_count} with text, {image_count} with images; "
        f"{status_counts.get('partial', 0) + status_counts.get('missing', 0)} partial or missing targets.",
        fill=MUTED,
        font=_pil_font(11),
    )
    for index, profile in enumerate(profiles):
        row, col = divmod(index, cols)
        x = gap + col * (tile_w + gap)
        y = header_h + row * (tile_h + gap)
        status = str(profile["status"])
        status_color = STATUS_COLORS.get(status, PALETTE["gray"])
        draw.rounded_rectangle(
            (x, y, x + tile_w, y + tile_h),
            radius=5,
            fill=PALETTE["pale"],
            outline=GRID,
        )
        draw.rounded_rectangle(
            (x, y, x + 8, y + tile_h),
            radius=5,
            fill=status_color,
        )
        _draw_wrapped(
            draw,
            (x + 14, y + 7),
            str(profile["title"]),
            body_bold,
            INK,
            tile_w - 78,
            max_lines=2,
        )
        draw.text(
            (x + 14, y + 43),
            _short(profile["category"], 22),
            fill=MUTED,
            font=body_font,
        )
        badge_x = x + tile_w - 62
        draw.text((badge_x, y + 8), status, fill=status_color, font=body_bold)
        text_flag = "T yes" if profile["has_text"] else "T no"
        draw.text((badge_x, y + 26), text_flag, fill=INK, font=body_font)
        draw.text(
            (badge_x, y + 43),
            f"I {int(profile['image_count'])}",
            fill=INK,
            font=body_font,
        )
    return _save_pil(image, out_dir, "work_evidence_profile_grid")


def fig_image_depth_by_work(ao: Path, out_dir: Path) -> Path:
    rows = _read_optional(ao, "visualizations/image_depth.json", [])

    rows = [row for row in rows if local_image_count(row) > 0]
    rows = sorted(
        rows,
        key=lambda row: (
            local_image_count(row),
            int(row.get("resolved_object_count") or 0),
        ),
        reverse=True,
    )[:24]
    if not rows:
        rows = [
            {
                "title": "No image-depth rows",
                "downloaded_image_count": 0,
                "resolved_object_count": 0,
            }
        ]

    labels = [f"{rank}. " + _short(row.get("title") or row.get("work_id"), 30)
              for rank, row in enumerate(rows, 1)]
    downloaded = [local_image_count(row) for row in rows]
    resolved = [int(row.get("resolved_object_count") or 0) for row in rows]
    total_downloaded = sum(downloaded)
    total_resolved = sum(resolved)
    y = list(range(len(rows)))
    fig, ax = plt.subplots(figsize=(10.4, max(5.2, len(rows) * 0.40)))
    _style(ax, grid_axis="x")
    ax.barh(y, resolved, color=PALETTE["tan"], label="resolved Archive objects", height=0.72)
    ax.barh(
        y,
        downloaded,
        color=PALETTE["green"],
        label="local image associations",
        height=0.42,
    )
    for index, value in enumerate(downloaded):
        resolved_value = resolved[index]
        ax.text(
            max(value, resolved_value) + max(resolved + [1]) * 0.01,
            index,
            f"{value}/{resolved_value}",
            va="center",
            fontsize=9.8,
            color=INK,
        )
    ax.set_yticks(y)
    ax.set_yticklabels(labels)
    ax.invert_yaxis()
    ax.set_xlabel("object candidates / image associations")
    ax.set_xlim(0, max(downloaded + resolved + [1]) * 1.16)
    _title_with_subtitle(
        ax,
        f"Record image depth: {total_downloaded}/{total_resolved} downloaded/resolved",
        "Counts cover discoverable Archive object metadata with valid local image files.",
    )
    ax.legend(frameon=False, loc="lower right")
    return _save(fig, out_dir, "image_depth_by_work")


def fig_image_depth_by_area(ao: Path, out_dir: Path) -> Path:
    rows = _read_optional(ao, "visualizations/image_depth.json", [])
    grouped: dict[str, Counter[str]] = defaultdict(Counter)

    for row in rows:
        category = str(row.get("category") or "uncategorized").replace("_", " ")
        grouped[category]["resolved"] += int(row.get("resolved_object_count") or 0)
        grouped[category]["downloaded"] += local_image_count(row)
        grouped[category]["failures"] += int(row.get("failure_count") or 0)
    categories = sorted(
        grouped,
        key=lambda category: grouped[category]["resolved"],
        reverse=True,
    )
    if not categories:
        categories = ["uncategorized"]
        grouped["uncategorized"] = Counter()
    y = list(range(len(categories)))
    height = 0.34
    fig, ax = plt.subplots(figsize=(10.2, max(5.0, len(categories) * 0.55)))
    _style(ax, grid_axis="x")
    resolved = [grouped[category]["resolved"] for category in categories]
    downloaded = [grouped[category]["downloaded"] for category in categories]
    ax.barh(
        [value - height / 2 for value in y],
        resolved,
        height=height,
        color=PALETTE["tan"],
        label="resolved objects",
    )
    ax.barh(
        [value + height / 2 for value in y],
        downloaded,
        height=height,
        color=PALETTE["green"],
        label="local image associations",
    )
    max_value = max(resolved + downloaded + [1])
    for index, value in enumerate(downloaded):
        resolved_value = resolved[index]
        ax.text(
            max(value, resolved_value) + max_value * 0.01,
            index + height / 2,
            f"{value}/{resolved_value}",
            va="center",
            fontsize=9.8,
            color=INK,
        )
    ax.set_yticks(y)
    ax.set_yticklabels(categories)
    ax.invert_yaxis()
    ax.set_xlabel("Archive object/image count")
    ax.set_xlim(0, max_value * 1.18)
    _title_with_subtitle(
        ax,
        f"Image-depth by area: {sum(downloaded)}/{sum(resolved)} downloaded/resolved",
        "Work areas are ledger categories, not object-level Blake oeuvre totals.",
    )
    ax.legend(frameon=False, loc="lower right")
    return _save(fig, out_dir, "image_depth_by_area")


def fig_source_authority_tiers(ao: Path, out_dir: Path) -> Path:
    rows = _read_optional(ao, "visualizations/source_authority_tiers.json", [])
    if not rows:
        rows = [{"authority_tier": "unrecorded", "work_count": 0}]
    labels = [
        authority_label(str(row.get("authority_tier") or "unrecorded")) for row in rows
    ]
    values = [int(row.get("work_count") or 0) for row in rows]
    fig, ax = plt.subplots(figsize=(8.4, 5.0))
    _style(ax)
    bars = ax.bar(
        range(len(labels)),
        values,
        color=[PALETTE["green"], PALETTE["blue"], PALETTE["gold"], PALETTE["gray"]][
            : len(labels)
        ],
    )
    ax.set_xticks(range(len(labels)), labels)
    max_value = max(values + [1])
    total = sum(values) or 1
    for bar, value in zip(bars, values):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            value + max_value * 0.02,
            f"{value}\n{_pct(value, total):.1f}%",
            ha="center",
            va="bottom",
            fontsize=10.8,
            color=INK,
        )
    ax.set_ylim(0, max_value * 1.28)
    ax.set_ylabel("local records")
    _title_with_subtitle(
        ax,
        "Authority tiers separate Archive and validated fallback evidence",
        "Percentages use the local-record denominator for this saved run.",
        pad=18,
    )
    ax.tick_params(axis="x", rotation=18)
    return _save(fig, out_dir, "source_authority_tiers")


FIGURES = [
    ("core_profile_ownership", fig_core_profile_ownership),
    ("coverage_status", fig_coverage_status),
    ("category_coverage", fig_category_coverage),
    ("corpus_modalities", fig_corpus_modalities),
    ("source_audit", fig_source_audit),
    ("chronology", fig_chronology),
    ("word_counts", fig_word_counts),
    ("vocab_richness", fig_vocab_richness),
    ("lexical_signature", fig_lexical_signature),
    ("nlp_embedding_pca", fig_nlp_embedding_pca),
    ("text_image_density", fig_text_image_density),
    ("theme_network", fig_theme_network),
    ("text_image_linkage", fig_text_image_linkage),
    ("evidence_gaps", fig_evidence_gaps),
    ("pipeline_dag", fig_pipeline_dag),
    ("all_acquired_images_mosaic", fig_all_acquired_images_mosaic),
    ("work_area_image_mosaics", fig_work_area_image_mosaics),
    ("work_evidence_profile_grid", fig_work_evidence_profile_grid),
    ("image_depth_by_work", fig_image_depth_by_work),
    ("image_depth_by_area", fig_image_depth_by_area),
    ("source_authority_tiers", fig_source_authority_tiers),
]


PUBLICATION_OMISSIONS = frozenset(
    {
        "all_acquired_images_mosaic",
        "work_area_image_mosaics",
        "source_audit",
        "chronology",
    }
)


def generate_all_figures(
    project_root: Path | str, *, public_only: bool = False,
    evidence_root: Path | str | None = None,
) -> list[Path]:
    from manuscript_tools.paths import manuscript_roots

    roots = manuscript_roots(project_root, evidence_root)
    ao = roots.analysis
    if not ao.exists():
        raise FileNotFoundError(
            f"analysis_output/ not found at {ao}. Run `run_all.py --quick` first."
        )
    _configure()
    out_dir = roots.output / "figures"
    written: list[Path] = []
    for name, builder in FIGURES:
        if public_only and name in PUBLICATION_OMISSIONS:
            continue
        written.append(builder(ao, out_dir))
    registry = {
        "schema_version": "1.5",
        "scope": "public" if public_only else "local",
        "generated_at": datetime.now().isoformat(),
        "figures": [
            {
                "label": f"fig:{path.stem}",
                "filename": path.name,
                "path": path.name,
                "alt_text": FIGURE_BRIEFS[path.stem]["accessibility_summary"],
                "generated_by": "manuscript_tools.figures",
                "bytes": path.stat().st_size,
                "statistics": compute_figure_statistics(ao, path.stem),
                **FIGURE_BRIEFS[path.stem],
            }
            for path in written
        ],
    }
    (out_dir / "figure_registry.json").write_text(
        json.dumps(registry, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return written
