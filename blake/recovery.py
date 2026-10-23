"""Compatibility API and CLI for retained-source corpus recovery."""

from .recovery_models import (
    ARCHIVE_COMMIT,
    ERDMAN_URL,
    RIGHTS,
    MAX_MEMBER_BYTES,
    RecoveryError,
    RecoveryModel,
    FileReceipt,
    CopyRecord,
    ErdmanPage,
    ImageRecovery,
    CatalogRecovery,
    RecoveryManifest,
)
from .recovery_io import (
    _digest,
    _safe_path,
    _atomic_write,
    fetch_file,
    _retain,
    _derive,
    retain_recipe,
    unpack_snapshot,
    _work_sources,
)
from .recovery_text import _primary_ids, extract_archive, extract_erdman
from .recovery_images import recover_images
from .recovery_integrity import verify_recovery, _verify_recovery_contract
from .recovery_registration import register_recovery
from .recovery_pipeline import recover_corpus, recovery_summary
from .recovery_commands import (
    main,
    recover_command,
    verify_command,
    register_command,
    backup_command,
    verify_backup_command,
    restore_command,
    restore_drill_command,
)

__all__ = [
    "ARCHIVE_COMMIT",
    "ERDMAN_URL",
    "RIGHTS",
    "MAX_MEMBER_BYTES",
    "RecoveryError",
    "RecoveryModel",
    "FileReceipt",
    "CopyRecord",
    "ErdmanPage",
    "ImageRecovery",
    "CatalogRecovery",
    "RecoveryManifest",
    "_digest",
    "_safe_path",
    "_atomic_write",
    "fetch_file",
    "_retain",
    "_derive",
    "retain_recipe",
    "unpack_snapshot",
    "_work_sources",
    "_primary_ids",
    "extract_archive",
    "extract_erdman",
    "recover_images",
    "verify_recovery",
    "_verify_recovery_contract",
    "register_recovery",
    "recover_corpus",
    "recovery_summary",
    "main",
    "recover_command",
    "verify_command",
    "register_command",
    "backup_command",
    "verify_backup_command",
    "restore_command",
    "restore_drill_command",
]

if __name__ == "__main__":
    main()
