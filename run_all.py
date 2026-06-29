#!/usr/bin/env python3

import argparse
import asyncio
import logging
import os
import subprocess
import sys
from pathlib import Path


def _check_and_bootstrap():
    try:
        import blake  # noqa: F401
        return True
    except ImportError:
        if os.environ.get("UV_RUN_ACTIVE"):
            print("ERROR: Dependencies still missing even under uv. Run: uv sync")
            sys.exit(1)
        print("Dependencies not found. Bootstrapping via uv...")
        os.environ["UV_RUN_ACTIVE"] = "1"
        result = subprocess.run(
            ["uv", "run", "python", __file__] + sys.argv[1:],
            cwd=Path(__file__).parent,
        )
        sys.exit(result.returncode)


_check_and_bootstrap()

from blake.corpus import BlakeCorpus, CorpusConfig  # noqa: E402


def parse_max_images(value: str) -> int | None:
    text = value.strip().lower()
    if text in {"none", "all", "unlimited"}:
        return None
    parsed = int(text)
    if parsed < 1:
        raise argparse.ArgumentTypeError("use a positive integer or 'none'")
    return parsed


def configure_logging(output_dir: Path) -> None:
    logs_dir = output_dir / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(logs_dir / "run_all.log", mode="w"),
        ],
        force=True,
    )


def parse_args():
    parser = argparse.ArgumentParser(
        description="Blake Corpus Pipeline - reproducible corpus workflow"
    )
    parser.add_argument("--quick", "-q", action="store_true", help="Use existing data and skip live acquisition")
    parser.add_argument("--skip-download", action="store_true", help="Skip acquisition")
    parser.add_argument("--skip-analysis", action="store_true", help="Skip analysis")
    parser.add_argument("--skip-viz", action="store_true", help="Skip visualization inventory/rendering")
    parser.add_argument("--skip-export", action="store_true", help="Skip export phase")
    parser.add_argument("--skip-reports", action="store_true", help="Skip report generation")
    parser.add_argument("--data-dir", type=str, default="blake_data", help="Raw/local cache directory")
    parser.add_argument("--output-dir", type=str, default="analysis_output", help="Pipeline output directory")
    parser.add_argument("--target-profile", default="canonical", help="Corpus target ledger profile")
    parser.add_argument("--fixture-mode", choices=["auto", "always", "never"], default="auto", help="Quick-mode fixture behavior")
    parser.add_argument("--viz-profile", choices=["inventory", "core", "full"], default="core", help="Visualization artifact profile")
    parser.add_argument("--archive-scope", choices=["target-ledger", "archive-inventory"], default="archive-inventory", help="Blake Archive discovery scope")
    parser.add_argument("--image-mode", choices=["representative", "archive-all"], default="archive-all", help="Image acquisition depth for Blake Archive works")
    parser.add_argument("--image-dpi", type=int, default=300, help="Preferred image DPI for Archive image acquisition")
    parser.add_argument("--max-images-per-work", type=parse_max_images, default=None, help="Maximum Archive images per work; use 'none' for all discoverable objects")
    parser.add_argument(
        "--format",
        dest="export_formats",
        action="append",
        choices=["json", "csv", "pdf", "html", "markdown", "md", "parquet"],
        help="Export format; can be passed multiple times",
    )
    return parser.parse_args()


async def main(args):
    output_dir = Path(args.output_dir)
    configure_logging(output_dir)

    config = CorpusConfig(
        data_dir=Path(args.data_dir),
        output_dir=output_dir,
        quick=args.quick,
        skip_download=args.skip_download,
        skip_analysis=args.skip_analysis,
        skip_visualizations=args.skip_viz,
        skip_export=args.skip_export,
        skip_reports=args.skip_reports,
        target_profile=args.target_profile,
        fixture_mode=args.fixture_mode,
        viz_profile=args.viz_profile,
        archive_scope=args.archive_scope,
        image_mode=args.image_mode,
        image_dpi=args.image_dpi,
        max_images_per_work=args.max_images_per_work,
        export_formats=args.export_formats or ["json"],
    )
    corpus = BlakeCorpus(config.data_dir, output_dir=config.output_dir)
    summary = await corpus.run(config)
    logging.getLogger(__name__).info("Pipeline completed with status %s", summary.status)
    return summary.model_dump(mode="json")


if __name__ == "__main__":
    asyncio.run(main(parse_args()))
