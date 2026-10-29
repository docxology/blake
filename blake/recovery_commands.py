"""Click entry points for corpus recovery, verification and offline restoration."""

from __future__ import annotations

import json
import tarfile
import zipfile
from pathlib import Path

import click


from .recovery_models import ARCHIVE_COMMIT
from .recovery_pipeline import recover_corpus, recovery_summary
from .recovery_integrity import verify_recovery
from .recovery_registration import register_recovery


@click.group()
def main() -> None:
    """Recover and verify complete available Blake source collections locally."""


@main.command("recover")
@click.option(
    "--data-dir",
    type=click.Path(path_type=Path),
    default="blake_data",
    show_default=True,
)
@click.option("--commit", default=ARCHIVE_COMMIT, show_default=True)
@click.option(
    "--offline", is_flag=True, help="Rebuild exclusively from retained source bytes."
)
@click.option(
    "--images/--no-images",
    default=True,
    help="Attempt every identified image; retain explicit failures for retry.",
)
@click.option(
    "--image-workers", type=click.IntRange(1, 8), default=6, show_default=True
)
@click.option(
    "--full",
    is_flag=True,
    help="Also retain the live catalogues and complete Erdman source edition.",
)
def recover_command(
    data_dir: Path,
    commit: str,
    offline: bool,
    images: bool,
    image_workers: int,
    full: bool,
) -> None:
    """Retain all source copies, complete Erdman text, a search index, and receipts."""
    try:
        manifest = recover_corpus(
            data_dir,
            commit=commit,
            offline=offline,
            images=images,
            image_workers=image_workers,
            full=full,
        )
    except (OSError, ValueError, tarfile.TarError, zipfile.BadZipFile) as exc:
        raise click.ClickException(str(exc)) from exc
    click.echo(recovery_summary(manifest))


@main.command("verify")
@click.option(
    "--data-dir",
    type=click.Path(path_type=Path),
    default="blake_data",
    show_default=True,
)
def verify_command(data_dir: Path) -> None:
    """Verify every recovered file against its saved SHA-256 receipt, offline."""
    try:
        manifest = verify_recovery(data_dir)
    except (OSError, ValueError) as exc:
        raise click.ClickException(str(exc)) from exc
    click.echo(recovery_summary(manifest))


@main.command("register")
@click.option(
    "--data-dir",
    type=click.Path(path_type=Path),
    default="blake_data",
    show_default=True,
)
def register_command(data_dir: Path) -> None:
    """Make recovered source documents available through BlakeCorpus and the pipeline."""
    try:
        count = register_recovery(data_dir)
    except (OSError, ValueError) as exc:
        raise click.ClickException(str(exc)) from exc
    click.echo(json.dumps({"registered_documents": count}))


@main.command("backup")
@click.option(
    "--data-dir",
    type=click.Path(path_type=Path),
    default="blake_data",
    show_default=True,
)
@click.option("--destination", type=click.Path(path_type=Path))
def backup_command(data_dir: Path, destination: Path | None) -> None:
    """Create a verified, self-contained local corpus bundle and checksum receipt."""
    from .recovery_backup import backup_recovery

    try:
        bundle = backup_recovery(data_dir, destination)
    except (OSError, ValueError, tarfile.TarError) as exc:
        raise click.ClickException(str(exc)) from exc
    click.echo(json.dumps({"backup": str(bundle), "receipt": str(bundle) + ".json"}))


@main.command("verify-backup")
@click.argument("bundle", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("--sha256", "expected_sha256")
def verify_backup_command(bundle: Path, expected_sha256: str | None) -> None:
    """Verify the bundle checksum, member hashes, and exact inventory offline."""
    from .recovery_backup import verify_backup

    try:
        manifest = verify_backup(bundle, expected_sha256=expected_sha256)
    except (OSError, ValueError, tarfile.TarError) as exc:
        raise click.ClickException(str(exc)) from exc
    click.echo(recovery_summary(manifest))


@main.command("restore")
@click.argument("bundle", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("--data-dir", type=click.Path(path_type=Path), required=True)
@click.option("--sha256", "expected_sha256")
def restore_command(bundle: Path, data_dir: Path, expected_sha256: str | None) -> None:
    """Restore offline, preserving every conflicting local file in quarantine."""
    from .recovery_backup import restore_backup

    try:
        result = restore_backup(bundle, data_dir, expected_sha256=expected_sha256)
    except (OSError, ValueError, tarfile.TarError) as exc:
        raise click.ClickException(str(exc)) from exc
    click.echo(result.model_dump_json(indent=2))


@main.command("restore-drill")
@click.argument("bundle", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("--destination", type=click.Path(path_type=Path), required=True)
def restore_drill_command(bundle: Path, destination: Path) -> None:
    """Verify offline restoration and deliberate corruption repair on a fresh copy."""
    from .recovery_backup import restore_drill

    try:
        result = restore_drill(bundle, destination)
    except (OSError, ValueError, tarfile.TarError) as exc:
        raise click.ClickException(str(exc)) from exc
    click.echo(result.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
