"""Store imported text without trusting identifiers or external source paths."""

import hashlib
import os
from pathlib import Path
import tempfile


def store_imported_text(data_dir: Path, text: str) -> Path:
    payload = text.encode("utf-8")
    path = (
        data_dir
        / "texts"
        / ("imported-" + hashlib.sha256(payload).hexdigest() + ".txt")
    )
    if any(part.is_symlink() for part in (path, *path.parents)):
        raise ValueError("Imported text storage must not contain a symlink")
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_bytes() != payload:
            raise ValueError("Existing imported text does not match its content hash")
        return path
    # Publish complete bytes exclusively; never replace a prior destination file.
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            dir=path.parent, prefix=".import-", delete=False
        ) as stream:
            temporary = Path(stream.name)
            stream.write(payload)
        os.link(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink()
    return path
