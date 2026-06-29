#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import html
import re
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable

import requests
from bs4 import BeautifulSoup

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

from blake.metadata import MetadataManager  # noqa: E402
from blake.models import (
    BlakeMetadata,
    BlakeWork,
    LicenseType,
    SourceType,
    WorkType,
)  # noqa: E402

WIKISOURCE_API = "https://en.wikisource.org/w/api.php"
USER_AGENT = "BlakeAnalysisPlatform/1.0 (Academic Research)"


@dataclass(frozen=True)
class TextTarget:
    work_id: str
    title: str
    work_type: WorkType
    creation_year: int
    source_page: str
    page_sequence: tuple[str, ...] = ()
    raw_source: bool = False

    @property
    def source_url(self) -> str:
        return f"https://en.wikisource.org/wiki/{self.source_page.replace(' ', '_')}"


POETICAL_BASE = (
    "Poetical sketches by William Blake now first reprinted from the original "
    "edition of 1783"
)

TARGETS: tuple[TextTarget, ...] = (
    TextTarget(
        work_id="poetical-sketches",
        title="Poetical Sketches",
        work_type=WorkType.POEM,
        creation_year=1783,
        source_page=POETICAL_BASE,
        page_sequence=(
            "To Spring",
            "To Summer",
            "To Autumn",
            "To Winter",
            "To the Evening Star",
            "To Morning",
            "Fair Eleanor",
            "Gwin, King of Norway",
            "An Imitation of Spenser",
            "Blind-man's Buff",
            "King Edward the Third",
            "Prologue intended for a dramatic piece of King Edward the Fourth",
            "Prologue to King John",
            "A War Song",
            "The Couch of Death",
            "Contemplation",
            "Samson",
            "To the Muses",
            "Fresh from the dewy hill",
            "How sweet I roam'd from field to field",
            "I love the jocund dance",
            "Memory, hither come",
            "Mad Song",
            "Love and harmony combine",
            "My silks and fine array",
            "When early morn walks forth",
        ),
    ),
    TextTarget(
        work_id="everlasting-gospel",
        title="The Everlasting Gospel",
        work_type=WorkType.POEM,
        creation_year=1818,
        source_page="The Everlasting Gospel (complete)",
        raw_source=True,
    ),
)


def _session() -> requests.Session:
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})
    return session


def _get_with_retries(
    session: requests.Session,
    url: str,
    *,
    params: dict[str, str] | None = None,
) -> requests.Response:
    for attempt in range(6):
        response = session.get(url, params=params, timeout=30)
        if response.status_code != 429:
            response.raise_for_status()
            return response
        retry_after = response.headers.get("retry-after")
        delay = (
            float(retry_after)
            if retry_after and retry_after.isdigit()
            else 1.5 * (attempt + 1)
        )
        time.sleep(delay)
    response.raise_for_status()
    return response


def _clean_lines(lines: Iterable[str]) -> str:
    cleaned: list[str] = []
    previous_blank = False
    for line in lines:
        line = html.unescape(line).replace("\u200b", "").replace("\xa0", " ")
        line = re.sub(r"\s+", " ", line).strip()
        if not line:
            if cleaned and not previous_blank:
                cleaned.append("")
            previous_blank = True
            continue
        if line in {"↑", "←", "→"}:
            continue
        cleaned.append(line)
        previous_blank = False
    return "\n".join(cleaned).strip()


def _wiki_link_text(match: re.Match[str]) -> str:
    target = match.group(1)
    return target.split("|")[-1]


def clean_raw_wikitext(raw: str) -> str:
    text = re.sub(r"<!--.*?-->", "", raw, flags=re.DOTALL)
    text = re.sub(r"\{\{header\b.*?\n\}\}", "", text, flags=re.DOTALL)
    text = re.sub(r"\{\{poem-on\|([^}]*)\}\}", r"\n[\1]\n", text)
    text = re.sub(r"\{\{[^{}\n]*\}\}", "", text)
    text = text.replace("__TOC__", "")
    text = re.sub(r"<h[1-6][^>]*>(.*?)</h[1-6]>", r"\n\1\n", text, flags=re.DOTALL)
    text = re.sub(r"</?(poem|br|p|div|span)[^>]*>", "\n", text)
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"\[\[([^][]+)\]\]", _wiki_link_text, text)
    text = re.sub(r"\[(https?://\S+)\s+([^\]]+)\]", r"\2", text)
    text = re.sub(r"\[https?://[^\]]+\]", "", text)
    return _clean_lines(text.splitlines())


def _parse_rendered_html(rendered_html: str) -> str:
    soup = BeautifulSoup(rendered_html, "html.parser")
    container = soup.select_one(".prp-pages-output") or soup
    for node in container.select(".ws-noexport, .noprint, style, script, sup, table"):
        node.decompose()
    for br in container.find_all("br"):
        br.replace_with("\n")
    return _clean_lines(container.get_text("\n").splitlines())


def fetch_rendered_page(session: requests.Session, page: str) -> str:
    response = _get_with_retries(
        session,
        WIKISOURCE_API,
        params={
            "action": "parse",
            "format": "json",
            "formatversion": "2",
            "page": page,
            "prop": "text",
        },
    )
    payload = response.json()
    rendered = payload.get("parse", {}).get("text")
    if not rendered:
        raise RuntimeError(f"Wikisource parse returned no text for {page!r}")
    return _parse_rendered_html(str(rendered))


def fetch_raw_page(session: requests.Session, page: str) -> str:
    response = _get_with_retries(
        session,
        f"https://en.wikisource.org/wiki/{page.replace(' ', '_')}",
        params={"action": "raw"},
    )
    return clean_raw_wikitext(response.text)


def fetch_target_text(session: requests.Session, target: TextTarget) -> str:
    if target.raw_source:
        text = fetch_raw_page(session, target.source_page)
    else:
        sections = []
        for section in target.page_sequence:
            page = f"{target.source_page}/{section}"
            sections.append(fetch_rendered_page(session, page))
            time.sleep(0.35)
        text = "\n\n".join(sections)
    if len(text.split()) < 100:
        raise RuntimeError(
            f"Fetched text for {target.work_id!r} is unexpectedly short."
        )
    return text


async def save_target(data_dir: Path, target: TextTarget, text: str) -> BlakeWork:
    texts_dir = data_dir / "texts"
    texts_dir.mkdir(parents=True, exist_ok=True)
    text_path = texts_dir / f"{target.work_id}.txt"
    text_path.write_text(text, encoding="utf-8")

    metadata = BlakeMetadata(
        id=target.work_id,
        title=target.title,
        author="William Blake",
        work_type=target.work_type,
        creation_date=datetime(target.creation_year, 1, 1),
        source=SourceType.WIKIMEDIA,
        source_id=target.source_page,
        source_url=target.source_url,
        api_source="wikisource",
        license_type=LicenseType.PUBLIC_DOMAIN,
        attribution="Wikisource contributors; text by William Blake",
        usage_terms="Public-domain Wikisource transcription used as fallback text evidence.",
        file_path=text_path,
        file_size=len(text.encode("utf-8")),
        mime_type="text/plain",
    )
    work = BlakeWork(
        id=target.work_id,
        metadata=metadata,
        text_content=text,
        text_versions=[
            {
                "source": "Wikisource",
                "source_url": target.source_url,
                "kind": "fallback_text_transcription",
            }
        ],
    )
    manager = MetadataManager(data_dir)
    await manager.save_work(work)
    return work


async def acquire_missing_texts(data_dir: Path) -> list[BlakeWork]:
    session = _session()
    saved: list[BlakeWork] = []
    for target in TARGETS:
        text = fetch_target_text(session, target)
        saved.append(await save_target(data_dir, target, text))
    return saved


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Acquire Wikisource fallback text for missing Blake targets."
    )
    parser.add_argument(
        "--data-dir",
        default=str(_PROJECT_ROOT / "blake_data"),
        help="Blake data directory containing metadata/ and texts/.",
    )
    args = parser.parse_args()

    works = asyncio.run(acquire_missing_texts(Path(args.data_dir)))
    for work in works:
        words = len((work.text_content or "").split())
        print(f"{work.id}: saved {words} words from {work.metadata.source_url}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
