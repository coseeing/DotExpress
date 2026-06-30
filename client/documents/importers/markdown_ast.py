from __future__ import annotations

from dataclasses import dataclass
from typing import TypeAlias


@dataclass(frozen=True)
class Heading:
    level: int
    text: str

    def __post_init__(self) -> None:
        if not 1 <= self.level <= 6:
            raise ValueError("Heading level must be between 1 and 6.")


@dataclass(frozen=True)
class Paragraph:
    text: str


@dataclass(frozen=True)
class HorizontalRule:
    pass


@dataclass(frozen=True)
class ListItem:
    blocks: tuple[Block, ...]


@dataclass(frozen=True)
class ListBlock:
    ordered: bool
    items: tuple[ListItem, ...]


@dataclass(frozen=True)
class BlockQuote:
    blocks: tuple[Block, ...]


@dataclass(frozen=True)
class Table:
    headers: tuple[str, ...]
    rows: tuple[tuple[str, ...], ...]

    def __post_init__(self) -> None:
        width = len(self.headers)
        if any(len(row) != width for row in self.rows):
            raise ValueError("Table rows must have the same number of columns as headers.")


Block: TypeAlias = Heading | Paragraph | ListBlock | BlockQuote | HorizontalRule | Table


@dataclass(frozen=True)
class DocumentAst:
    blocks: tuple[Block, ...]
