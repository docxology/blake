"""Source-bound retrieval-profile ownership diagram."""

import textwrap
from pathlib import Path

from manuscript_tools.core_architecture import build_core_architecture


def fig_core_profile_ownership(analysis_output: Path, out_dir: Path) -> Path:
    """Draw a code-only figure; analysis_output is intentionally not consumed."""
    import matplotlib.pyplot as plt
    from matplotlib.patches import FancyBboxPatch

    evidence = build_core_architecture(Path(__file__).resolve().parents[1])
    out_dir.mkdir(parents=True, exist_ok=True)
    fig, axes = plt.subplots(
        2, 1, figsize=(11, 9), gridspec_kw={"height_ratios": (1.35, 1)}
    )
    fig.patch.set_facecolor("#fcfaf4")
    for ax in axes:
        ax.set_axis_off()
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
    axes[0].set_title("Named retrieval contracts", loc="left", fontsize=15)
    for i, profile in enumerate(evidence.profiles):
        y = 0.95 - i * 0.31
        axes[0].text(
            0.01,
            y,
            profile.semantics.profile.value,
            va="top",
            fontsize=10.5,
            weight="bold",
            color="#0072B2",
        )
        text = "\n".join(
            textwrap.wrap(
                profile.semantics.normalization + ". " + profile.semantics.boundaries,
                width=106,
            )
        )
        axes[0].text(0.01, y - 0.065, text, va="top", fontsize=10, linespacing=1.5)
        axes[0].text(
            0.01,
            y - 0.21,
            profile.entrypoint,
            va="top",
            fontsize=9,
            family="monospace",
            color="#5f625d",
        )
    axes[1].set_title(
        "Responsibility stays explicit at each boundary", loc="left", fontsize=15
    )
    for i, owner in enumerate(evidence.responsibilities):
        y = 0.91 - i * 0.23
        axes[1].add_patch(
            FancyBboxPatch(
                (0.005, y - 0.17),
                0.99,
                0.18,
                boxstyle="round,pad=0.005",
                facecolor="#f0ece2",
                edgecolor="#d8d2c4",
            )
        )
        axes[1].text(
            0.025, y - 0.035, owner.owner, va="top", fontsize=10.5, weight="bold"
        )
        axes[1].text(0.025, y - 0.105, owner.responsibility, va="top", fontsize=10)
    fig.text(
        0.03,
        0.022,
        "Source-code diagnostic only; analytical producer and saved corpus epoch "
        "remain separate.",
        fontsize=10,
        color="#5f625d",
    )
    fig.tight_layout(rect=(0.01, 0.05, 0.99, 0.99), h_pad=2)
    path = out_dir / "core_profile_ownership.png"
    try:
        fig.savefig(path, dpi=190, facecolor=fig.get_facecolor())
        fig.savefig(path.with_suffix(".svg"), facecolor=fig.get_facecolor())
    finally:
        plt.close(fig)
    path.with_suffix(".json").write_text(
        evidence.model_dump_json(indent=2) + "\n", encoding="utf-8"
    )
    return path
