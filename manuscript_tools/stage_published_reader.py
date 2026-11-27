"""Stage the deposited Blake paper for a pinned Template reader build."""

import argparse
import csv
import hashlib
import json
import os
import re
import sys
from pathlib import Path
from zipfile import ZipFile

ARCHIVE_NAME = "Blake-0.5.0-reproduction.zip"
NUMBER = re.compile(
    r"(?<![A-Za-z0-9_@.-])-?(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?%?(?!(?:[A-Za-z0-9_-]|\.\d))"
)
TOKEN = re.compile(r"\{\{[A-Z][A-Z0-9_]*\}\}")
ASSET_TARGET = re.compile(r"(?P<open>\]\(|\b(?:href|src)=\")\.\./\.\./output/")


def stage(root: Path, archive: Path, pin: str, template: Path) -> None:
    """Verify the public archive and hydrate the canonical body with deposited values."""
    sys.path.insert(0, str(template.resolve()))
    from infrastructure.rendering.manuscript_injection import substitute_manuscript_text

    delivery = json.loads((root / "publication-verification-20261103.json").read_bytes())
    record = delivery["assets"][ARCHIVE_NAME]
    output = root / "output"
    if output.exists():
        raise FileExistsError(output)

    with archive.open("rb") as stream:
        actual = hashlib.file_digest(stream, "sha256").hexdigest()
        if actual != pin or actual != record["sha256"]:
            raise ValueError("Archive does not match the caller pin and public release receipt")
        if os.fstat(stream.fileno()).st_size != record["bytes"]:
            raise ValueError("Archive size differs from the public release receipt")
        with ZipFile(stream) as package:
            manifest_name = "bundle-manifest.json"
            manifest = json.loads(package.read(manifest_name))["members"]
            if sorted(package.namelist()) != sorted([*manifest, manifest_name]):
                raise ValueError("ZIP members differ from manifest")
            for name, expected in manifest.items():
                member = package.read(name)
                if len(member) != expected["size"] or (
                    hashlib.sha256(member).hexdigest() != expected["sha256"]
                ):
                    raise ValueError(f"ZIP member differs from manifest: {name}")
            preparation = json.loads(package.read("paper/prepared-publication.json"))
            variables = json.loads(package.read("paper/manuscript_variables.json"))
            body = {}
            for name in preparation["source_order"]:
                path = root / "docs/manuscript" / name
                source = path.read_bytes()
                if source != package.read(f"paper/docs/manuscript/{name}"):
                    raise ValueError(f"Current manuscript section differs from deposit: {name}")
                resolved, missing = substitute_manuscript_text(source.decode("utf-8"), variables)
                if missing or TOKEN.search(resolved):
                    raise ValueError(f"Unresolved manuscript tokens in {name}: {missing}")
                body[name] = ASSET_TARGET.sub(r"\g<open>../", resolved)

            config = package.read("paper/docs/manuscript/config.yaml")
            for name in ("config.yaml", "preamble.md", "references.bib", "web.css"):
                if (root / "docs/manuscript" / name).read_bytes() != package.read(
                    f"paper/docs/manuscript/{name}"
                ):
                    raise ValueError(f"Current manuscript support differs from deposit: {name}")

            manuscript = output / "manuscript"
            manuscript.mkdir(parents=True)
            for name, text in body.items():
                (manuscript / name).write_text(text, encoding="utf-8")
            (manuscript / "config.yaml").write_bytes(b"# Generated manuscript ordering\n" + config)
            for name in ("preamble.md", "references.bib"):
                (manuscript / name).write_bytes(package.read(f"paper/docs/manuscript/{name}"))
            for name in manifest:
                if name.startswith(("paper/output/figures/", "paper/output/cover/")):
                    path = root / name.removeprefix("paper/")
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_bytes(package.read(name))

            data = output / "data"
            data.mkdir()
            (data / "manuscript_variables.json").write_bytes(
                package.read("paper/manuscript_variables.json")
            )

    # Use hydrated deposited values for text parity, without regenerating analysis.
    with (data / "retained-reader-values.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(("value", "source"))
        for name, text in body.items():
            writer.writerows((value, name) for value in sorted(set(NUMBER.findall(text))))
    print(f"Verified {len(manifest)} archive members and hydrated {len(body)} canonical sections.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--archive-sha256", required=True)
    parser.add_argument("--template-root", type=Path, required=True)
    args = parser.parse_args()
    stage(Path(__file__).resolve().parents[1], args.archive, args.archive_sha256, args.template_root)
