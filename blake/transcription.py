"""Primary-text extraction without overlapping containers or editorial annotations."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import Final

OMITTED: Final = frozenset({"note", "interp", "figDesc", "fw", "del"})
BLOCKS: Final = frozenset({"l", "p", "ab", "head"})


@dataclass(frozen=True)  # Python 3.9 supports the project's existing runtime contract.
class TranscribedBlock:
    """A source block; locator is absent when the edition supplies none."""

    locator: str | None
    text: str


def _tag(element: ET.Element) -> str:
    return element.tag.rsplit("}", 1)[-1]


def _reading(element: ET.Element) -> str:
    if _tag(element) in OMITTED:
        return ""
    children = list(element)
    if _tag(element) == "choice":
        for preferred in ("orig", "sic", "abbr"):
            selected = next((child for child in children if _tag(child) == preferred), None)
            if selected is not None:
                return _reading(selected)
        message = "TEI choice lacks an original reading; edition review required"
        raise ValueError(message)
    parts = [element.text or ""]
    for child in children:
        parts.append(_reading(child))
        parts.append(child.tail or "")
    return "".join(parts)


def extract_primary_blocks(xml: str) -> tuple[TranscribedBlock, ...]:
    """Read BAD phystext or TEI body once, preserving source block identifiers.

    Original readings of TEI choice are selected; alternate/corrected readings stay
    in the source XML. This is a reading layer, not a full diplomatic apparatus.
    """
    root = ET.fromstring(xml)
    containers = [element for element in root.iter() if _tag(element) == "phystext"]
    if not containers:
        containers = [element for element in root.iter() if _tag(element) == "body"]
    result = []

    def visit(element: ET.Element) -> None:
        if _tag(element) in OMITTED:
            return
        descendants = [child for child in element.iter() if child is not element and _tag(child) in BLOCKS]
        if _tag(element) in BLOCKS and not descendants:
            text = _reading(element).strip()
            if text:
                result.append(TranscribedBlock(element.get("n") or element.get("{http://www.w3.org/XML/1998/namespace}id"), text))
            return
        for child in element:
            visit(child)

    for container in containers:
        visit(container)
    return tuple(result)


def extract_primary_text(xml: str) -> str | None:
    blocks = extract_primary_blocks(xml)
    return "\n".join(block.text for block in blocks) or None
