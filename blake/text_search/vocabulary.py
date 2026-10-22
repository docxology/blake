"""Explicit inflections and editorial navigation; never aliases presented as quotations."""

from pathlib import Path
from typing import Final

from pydantic import TypeAdapter

from .models import Concept

GROUPS: Final = (
    ("state", "states"), ("nation", "nations"), ("generation", "generations"),
    ("emanation", "emanations"), ("individual", "individuals"),
    ("identity", "identities"), ("contrary", "contraries"),
    ("negation", "negations"), ("vision", "visions"),
    ("fourfold", "four-fold", "four fold"),
    ("federation", "federations", "federal", "federalism"),
)


def variants(term: str) -> tuple[str, ...]:
    return next((group for group in GROUPS if term.casefold() in group), (term,))


def concepts() -> dict[str, Concept]:
    data = Path(__file__).with_name("concepts.json").read_text(encoding="utf-8")
    return TypeAdapter(dict[str, Concept]).validate_json(data)
