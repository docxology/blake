"""Readable, data-derived figure for support geometry and indexed multiplicity."""

from __future__ import annotations

import io
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Final, Literal

from blake.methods.common import EvidenceError, FrozenModel
from blake.methods.intervals import Interval
from blake.methods.storage import digest, publish_bytes
from manuscript_tools.interval_illustration import (
    IntervalIllustration,
    build_interval_illustration,
)

if TYPE_CHECKING:
    from matplotlib.axes import Axes
    from matplotlib.figure import Figure

_BG: Final = "#fcfaf4"
_INK: Final = "#20242a"
_BLUE: Final = "#0072B2"
_GREEN: Final = "#006B54"
_FORMATS: Final[tuple[Literal["png", "svg", "pdf"], ...]] = ("png", "svg", "pdf")
_FORMAT_METADATA: Final = (
    ("png", {"Software": "Blake interval mathematical illustration"}),
    ("svg", {"Date": None}),
    ("pdf", {"CreationDate": None, "ModDate": None}),
)
_NAME: Final = "core_interval_support"


@dataclass(frozen=True)  # noqa: SLOTS_OK -- Preserve the project's Python 3.9 runtime.
class SupportRow:
    label: str
    intervals: tuple[Interval, ...]
    color: str


class IntervalFigureReceipt(FrozenModel):
    schema_version: Literal["1"] = "1"
    illustration: IntervalIllustration
    outputs: dict[str, str]
    scope: str = (
        "Mathematical figure bytes; native and independent acceptance are separate"
    )


INTERVAL_FIGURE_BRIEF: Final = {
    "story_job": "Distinguish support geometry from indexed record multiplicity.",
    "data_sources": ["blake/methods/intervals.py", "core_interval_support.json"],
    "claim": ("Support, threshold support and indexed pairs count different things."),
    "encoding": "Labelled records, canonical supports and threshold rows.",
    "caveat": "Mathematical integer-coordinate example; no corpus measurement.",
    "static_mobile_fallback": "Static labelled PNG with vector SVG/PDF and bound JSON.",
    "qa_check": ("Check labels, open ends, empty support and separate pair counts."),
    "accessibility_summary": (
        "Indexed records include a duplicate, adjacency and empty support; "
        "support and record multiplicity are displayed separately."
    ),
    "statistical_question": "What changes when interval records duplicate or touch?",
    "data_shape": "Mathematical records, mask and canonical API outputs.",
    "statistical_method": "Exact interval API; no estimation or literary inference.",
    "missingness_or_scope": (
        "No corpus data, application clocks, source grouping or eligibility policy."
    ),
    "statistical_check": "Real API refusals and source-byte checks.",
}


def _draw_support(axis: Axes, rows: Sequence[SupportRow]) -> None:
    """Draw half-open supports without using color as the sole record identifier."""
    for y, row in enumerate(rows):
        for span in row.intervals:
            if span.start == span.end:
                axis.plot(span.start, y, marker="x", color=_INK, markersize=7)
                axis.text(span.start + 0.15, y, "empty", va="center", fontsize=10)
            else:
                axis.broken_barh(
                    [(span.start, span.end - span.start)],
                    (y - 0.23, 0.46),
                    facecolors=row.color,
                    edgecolors=_INK,
                    linewidth=0.65,
                    zorder=3,
                )
                axis.plot(span.start, y, marker="o", color=_INK, markersize=4, zorder=4)
                axis.plot(
                    span.end,
                    y,
                    marker="o",
                    markerfacecolor=_BG,
                    markeredgecolor=_INK,
                    markersize=4,
                    zorder=4,
                )
                axis.text(
                    (span.start + span.end) / 2,
                    y,
                    f"[{span.start},{span.end})",
                    ha="center",
                    va="center",
                    color="white",
                    fontsize=10,
                    zorder=5,
                )
    axis.set_yticks(
        list(range(len(rows))), labels=[row.label for row in rows], fontsize=10.5
    )
    axis.set_ylim(len(rows) - 0.5, -0.5)
    axis.grid(axis="x", color="#d8d2c4", linewidth=0.6, zorder=0)
    axis.spines[["top", "right", "left"]].set_visible(False)
    axis.tick_params(axis="y", length=0)
    axis.set_facecolor(_BG)


def _save_artifacts(figure: Figure, out_dir: Path) -> None:
    """Publish each real image exclusively; the final receipt follows all artifacts."""
    for kind, metadata in _FORMAT_METADATA:
        with io.BytesIO() as stream:
            figure.savefig(
                stream, format=kind, dpi=190, facecolor=_BG, metadata=metadata
            )
            publish_bytes(out_dir / (_NAME + "." + kind), stream.getvalue())


def fig_interval_support(_analysis_output: Path, out_dir: Path) -> Path:
    """Generate only this code-derived illustration; consume no saved analysis root."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    root = Path(__file__).resolve().parents[1]
    evidence = build_interval_illustration(root)
    if any(p.is_symlink() for p in (out_dir, *out_dir.parents)):
        raise EvidenceError("interval_figure_symlink", str(out_dir))
    if any(
        p.exists() or p.is_symlink()
        for p in (out_dir / (_NAME + "." + ext) for ext in (*_FORMATS, "json"))
    ):
        raise EvidenceError("interval_figure_occupied", str(out_dir))
    out_dir.mkdir(parents=True, exist_ok=True)
    with plt.rc_context(
        {"font.family": "DejaVu Sans", "font.size": 11, "svg.hashsalt": _NAME}
    ):
        figure, axes = plt.subplots(
            3,
            1,
            figsize=(7.2, 8.8),
            sharex=True,
            gridspec_kw={"height_ratios": (1.35, 1.2, 0.7)},
        )
        figure.patch.set_facecolor(_BG)
        maximum = max(p.end for p in (*evidence.records, *evidence.mask))
        for axis in axes:
            axis.set_xlim(0, maximum + 1)
            axis.set_xticks(list(range(maximum + 2)))
        _draw_support(
            axes[0],
            tuple(
                SupportRow(f"I{i + 1}", (span,), _BLUE)
                for i, span in enumerate(evidence.records)
            ),
        )
        axes[0].set_title(
            "A  Indexed records: duplicate support stays separate",
            loc="left",
            fontsize=11.5,
        )
        _draw_support(
            axes[1],
            (
                SupportRow("Union U", evidence.union, _BLUE),
                SupportRow("Mask M", evidence.mask, _GREEN),
                SupportRow(r"$U \cap M$", evidence.intersection, _GREEN),
                SupportRow(r"$U \setminus M$", evidence.difference, _BLUE),
            ),
        )
        axes[1].set_title(
            "B  Set geometry: adjacency joins the union", loc="left", fontsize=11.5
        )
        _draw_support(
            axes[2],
            (
                SupportRow("Depth >= 2", evidence.depth_two, _BLUE),
                SupportRow("Depth >= 3", evidence.depth_three, _BLUE),
            ),
        )
        axes[2].set_title(
            "C  Multiplicity: overlapping record indices", loc="left", fontsize=11.5
        )
        axes[2].set_xlabel("Arbitrary integer coordinate units", fontsize=11)
        pairs = ", ".join(f"I{i}/I{j}" for i, j in evidence.pair_indices)
        figure.suptitle(
            "One support, several records", x=0.04, ha="left", fontsize=18, color=_INK
        )
        figure.text(
            0.04,
            0.93,
            "Mathematical illustration; no corpus or application observations",
            fontsize=10,
        )
        figure.text(
            0.04,
            0.10,
            f"Union length = {evidence.union_length}; "
            f"summed record lengths = {evidence.summed_record_length}.",
            fontsize=10.5,
        )
        figure.text(
            0.04,
            0.07,
            f"Strictly overlapping pairs = {evidence.strict_pairs}: {pairs}.",
            fontsize=10.5,
        )
        figure.text(
            0.04,
            0.035,
            "Open circles mark excluded ends; touching alone creates no pair.",
            fontsize=10,
        )
        figure.subplots_adjust(
            left=0.23, right=0.97, top=0.86, bottom=0.19, hspace=0.43
        )
        try:
            _save_artifacts(figure, out_dir)
        finally:
            plt.close(figure)
    if evidence.source_bindings != build_interval_illustration(root).source_bindings:
        raise EvidenceError(
            "interval_illustration_source_changed", "No completion after changed source"
        )
    receipt = IntervalFigureReceipt(
        illustration=evidence,
        outputs={
            _NAME + "." + ext: digest(out_dir / (_NAME + "." + ext)) for ext in _FORMATS
        },
    )
    publish_bytes(
        out_dir / (_NAME + ".json"), (receipt.model_dump_json(indent=2) + "\n").encode()
    )
    return out_dir / (_NAME + ".png")
