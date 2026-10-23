"""Bounded image recovery with explicit source URLs, resolutions and failures."""

from __future__ import annotations

import io
import logging
import re
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import quote


from .recovery_models import (
    RecoveryError,
    FileReceipt,
    CopyRecord,
    ImageRecovery,
    RecoveryManifest,
)
from .recovery_io import _digest, _safe_path, fetch_file, _retain

logger = logging.getLogger(__name__)


def recover_images(
    root: Path,
    copies: list[CopyRecord],
    *,
    offline: bool,
    enabled: bool,
    image_base_url: str = "https://blakearchive.org",
    workers: int = 1,
    max_consecutive_failures: int | None = 3,
) -> tuple[ImageRecovery, list[FileReceipt]]:
    """Recover all identified images, stopping after repeated provider failures.

    A provider outage is recorded once with explicit unattempted membership,
    instead of hammering thousands of known-unavailable endpoints. Reruns retry
    missing images and validate cached images by actually decoding them.
    """
    from PIL import Image

    def validate_image(data: bytes) -> None:
        with Image.open(io.BytesIO(data)) as image:
            image.load()

    if not 1 <= workers <= 8:
        raise RecoveryError("Image worker count must be between 1 and 8")
    objects = sorted({obj for copy in copies for obj in copy.object_ids})
    files: list[FileReceipt] = []
    failures: list[str] = []
    unattempted: list[str] = []
    consecutive_failures = 0
    known_receipts: dict[str, FileReceipt] = {}
    if (root / "manifest.json").is_file():
        previous = RecoveryManifest.model_validate_json(
            (root / "manifest.json").read_bytes()
        )
        known_receipts = {receipt.path: receipt for receipt in previous.files}
    for object_id in objects:
        if not re.fullmatch(r"[A-Za-z0-9_.+-]+", object_id):
            raise RecoveryError(f"Unsafe Archive object identity: {object_id}")

    def fetch_object(object_id: str) -> tuple[FileReceipt | None, str]:
        errors = []
        spellings = tuple(dict.fromkeys((object_id.casefold(), object_id)))
        for dpi in (300, 100):
            relative = f"images/{object_id}.{dpi}.jpg"
            path = _safe_path(root, relative)
            known = known_receipts.get(relative)
            candidates = tuple(
                f"{image_base_url}/images/{quote(spelling, safe='._-')}.{dpi}.jpg"
                for spelling in spellings
            )
            if path.exists() and known is not None and known.source_url is not None:
                candidates = (known.source_url,)
            for url in candidates:
                try:
                    data = fetch_file(
                        url,
                        path,
                        offline=offline or not enabled,
                        validate=validate_image,
                    )
                    if known is not None and known.sha256 != _digest(data):
                        raise RecoveryError(
                            f"Cached image checksum differs: {relative}"
                        )
                    return _retain(root, relative, data, url), ""
                except (RecoveryError, OSError, Image.DecompressionBombError) as exc:
                    errors.append(str(exc))
        return None, f"{object_id}: {'; '.join(errors)}"

    with ThreadPoolExecutor(max_workers=workers) as pool:
        batch_size = (
            max(1, len(objects)) if max_consecutive_failures is None else workers
        )
        for start in range(0, len(objects), batch_size):
            batch = []
            for object_id in objects[start : start + batch_size]:
                cached = any(
                    _safe_path(root, f"images/{object_id}.{dpi}.jpg").exists()
                    for dpi in (300, 100)
                )
                paused = (
                    max_consecutive_failures is not None
                    and consecutive_failures >= max_consecutive_failures
                )
                if not cached and (not enabled or offline or paused):
                    unattempted.append(object_id)
                else:
                    batch.append(object_id)
            for receipt, error in pool.map(fetch_object, batch):
                if receipt is not None:
                    files.append(receipt)
                    consecutive_failures = 0
                else:
                    consecutive_failures += 1
                    failures.append(error)
                processed = len(files) + len(failures) + len(unattempted)
                if processed % 60 == 0 or processed == len(objects):
                    logger.info(
                        "Image recovery %s/%s: saved=%s failed=%s unattempted=%s",
                        processed,
                        len(objects),
                        len(files),
                        len(failures),
                        len(unattempted),
                    )
    return ImageRecovery(
        status="complete" if len(files) == len(objects) else "incomplete",
        expected=len(objects),
        downloaded=len(files),
        failures=tuple(failures),
        unattempted=tuple(unattempted),
        resolution_counts=dict(
            Counter(receipt.path.rsplit(".", 2)[1] for receipt in files)
        ),
        lower_resolution_ids=tuple(
            sorted(
                receipt.path[len("images/") : -len(".100.jpg")]
                for receipt in files
                if receipt.path.endswith(".100.jpg")
            )
        ),
    ), files
