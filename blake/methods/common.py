# Copyright (c) 2026 Daniel Ari Friedman
"""Shared primitives without application decisions or source acquisition imports."""

from enum import Enum
from typing import Annotated, ClassVar

from pydantic import BaseModel, ConfigDict, Field
from typing_extensions import override

Digest = Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")]


class FrozenModel(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, extra="forbid")


class ResearchError(Exception):
    """A projection or research-method boundary failed with a stable code."""

    def __init__(self, code: str, detail: str) -> None:
        self.code: str = code
        self.detail: str = detail
        super().__init__(f"{code}: {detail}")


class EvidenceError(ValueError):
    """A run or authored annotation violates a named evidence boundary."""

    def __init__(self, code: str, detail: str) -> None:
        self.code: str = code
        self.detail: str = detail
        super().__init__(f"{code}: {detail}")


class StringEnum(str, Enum):
    """String-valued enums with the same string behavior on Python 3.9 and later."""

    @override
    def __str__(self) -> str:
        return str.__str__(self)


class Plane(StringEnum):
    READING = "reading"
    ERDMAN = "erdman"
    XML = "xml"


class Role(StringEnum):
    PRIMARY = "primary"
    EDITORIAL = "editorial"
    UNVERIFIED = "unverified"
