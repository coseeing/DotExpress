import csv
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Iterable, TypedDict


DICTIONARY_MARKER_OPEN = r"\["
DICTIONARY_MARKER_CLOSE = r"\]"
DICTIONARY_MARKER_JOIN = f"{DICTIONARY_MARKER_CLOSE}{DICTIONARY_MARKER_OPEN}"
DICTIONARY_MARKER_PATTERN = re.compile(
    rf"{re.escape(DICTIONARY_MARKER_OPEN)}|{re.escape(DICTIONARY_MARKER_CLOSE)}"
)


class BracketSegment(TypedDict):
    text: str
    atomic: bool


@dataclass
class _TrieNode:
    children: dict[str, "_TrieNode"] = field(default_factory=dict)
    target: str | None = None


def _replace_with_trie(text: str, replacements: Iterable[tuple[str, str]]) -> str:
    """Replace source text using left-to-right, longest-prefix matching.

    The trie is built from dictionary sources and only the original input is
    scanned. Emitted targets are never re-scanned, so replacement rules cannot
    cascade into one another.
    """
    root = _TrieNode()
    for source, target in replacements:
        if not source:
            continue

        node = root
        for char in source:
            child = node.children.get(char)
            if child is None:
                child = _TrieNode()
                node.children[char] = child
            node = child
        # Match the existing replacement order: the first duplicate source wins.
        if node.target is None:
            node.target = target

    result: list[str] = []
    index = 0
    while index < len(text):
        node = root
        cursor = index
        longest_target: str | None = None
        longest_end = index

        while cursor < len(text) and text[cursor] in node.children:
            node = node.children[text[cursor]]
            cursor += 1
            if node.target is not None:
                longest_target = node.target
                longest_end = cursor

        if longest_target is None:
            result.append(text[index])
            index += 1
        else:
            result.append(longest_target)
            index = longest_end

    return "".join(result)


def _wrap_atomic_parts(parts: list[str]) -> str:
    return (
        DICTIONARY_MARKER_OPEN
        + DICTIONARY_MARKER_JOIN.join(parts)
        + DICTIONARY_MARKER_CLOSE
    )


def _align_source_and_replacement_parts(source: str, replacement_parts: list[str]) -> tuple[list[str], list[str]]:
    if len(source) == len(replacement_parts):
        return list(source), replacement_parts
    return [source], ["".join(replacement_parts)]


def mapping(
    text: str,
    replacements: Iterable[tuple[str, str]],
    *,
    marker: bool = False,
) -> str:
    if not marker:
        return _replace_with_trie(text, replacements)

    # Keep pre-existing atomic segments intact, while applying the same trie to
    # every non-atomic segment. Materialize the iterable because each segment
    # needs the full rule set.
    rules = list(replacements)
    result: list[str] = []
    for segment in split_bracket_segments(text):
        if segment["atomic"]:
            result.append(f"{DICTIONARY_MARKER_OPEN}{segment['text']}{DICTIONARY_MARKER_CLOSE}")
        else:
            result.append(_replace_with_trie(segment["text"], rules))
    return "".join(result)


def translate__mapping_string(
    text: str,
    dictionary_path: Path | str,
    *,
    from_field: str,
    to_field: str,
) -> str:
    """
    支援多字元對多字元的字串對照轉換。
    """
    dictionary_path = Path(dictionary_path)
    if not dictionary_path.exists():
        return text

    with dictionary_path.open("r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            raise ValueError("CSV must contain header row.")
        if not {from_field, to_field}.issubset(reader.fieldnames):
            raise ValueError(f"CSV must contain columns: {from_field}, {to_field}")

        replacements: list[tuple[str, str]] = []
        for row in reader:
            source = (row.get(from_field) or "")
            target = (row.get(to_field) or "")
            if not source:
                continue
            replacements.append((source, target))

    return mapping(text, replacements)


def apply_dictionary(
    text: str,
    dictionary_path: Path | str,
    bopomofo_path: Path | str,
    processing: Callable[[str], str],
) -> dict[str, str]:
    """
    支援不同類型字典的轉換。
    """
    dictionary_path = Path(dictionary_path)
    if not dictionary_path.exists():
        return {
            "raw": text,
            "replacement": text,
        }

    with bopomofo_path.open("r", newline="", encoding="utf-8") as f_b:
        reader = csv.DictReader(f_b)
        if reader.fieldnames is None:
            raise ValueError("CSV must contain header row.")
        if not {"Bopomofo", "Braille"}.issubset(reader.fieldnames):
            raise ValueError("CSV must contain columns: Bopomofo, Braille")

        replacements_bopomofo: list[tuple[str, str]] = []
        for row in reader:
            source = (row.get("Bopomofo") or "")
            target = (row.get("Braille") or "")
            if not source:
                continue
            replacements_bopomofo.append((source, target))

    with dictionary_path.open("r", newline="", encoding="utf-8") as f_d:
        reader = csv.DictReader(f_d)
        if reader.fieldnames is None:
            raise ValueError("CSV must contain header row.")
        if not {"text", "braille", "type"}.issubset(reader.fieldnames):
            raise ValueError("CSV must contain columns: text, braille, type")

        raws: list[tuple[str, str]] = []
        replacements: list[tuple[str, str]] = []
        for row in reader:
            source = (row.get("text") or "")
            target = (row.get("braille") or "")
            if not source:
                continue

            type_ = (row.get("type") or "")
            if type_ == "Bopomofo":
                try:
                    target = processing(target)
                except Exception:
                    pass
                if isinstance(target, str):
                    target_parts = [target]
                else:
                    target_parts = list(target)
                replacement_parts = [mapping(part, replacements_bopomofo) for part in target_parts]
            else:
                replacement_parts = target.split("@")

            raw_parts, replacement_parts = _align_source_and_replacement_parts(source, replacement_parts)
            raws.append((source, _wrap_atomic_parts(raw_parts)))
            replacements.append((source, _wrap_atomic_parts(replacement_parts)))

    # Both outputs are derived from the same original text. The trie therefore
    # gives them identical dictionary-match boundaries without relying on marker
    # wrapping to prevent a second replacement pass.
    raw = mapping(text, raws)
    replacement = mapping(text, replacements)

    return {
        "raw": raw,
        "replacement": replacement,
    }


def split_bracket_segments(text: str) -> list[BracketSegment]:
    """
    Split text into normal segments and bracketed segments.
    - Normal segment: (segment, False)
    - Bracketed segment (content inside outermost markers): (segment, True)
    This supports multiple bracket groups and nested brackets.
    """
    segments: list[BracketSegment] = []
    last = 0
    depth = 0
    open_start: int | None = None

    for match in DICTIONARY_MARKER_PATTERN.finditer(text):
        ch = match.group()
        idx = match.start()

        if ch == DICTIONARY_MARKER_OPEN:
            if depth == 0:
                if idx > last:
                    segments.append({
                        "text": text[last:idx],
                        "atomic": False,
                    })
                open_start = idx
            depth += 1
        else:
            if depth > 0:
                depth -= 1
                if depth == 0 and open_start is not None:
                    segments.append({
                        "text": text[open_start + len(DICTIONARY_MARKER_OPEN):idx],
                        "atomic": True,
                    })
                    last = match.end()
                    open_start = None

    if depth > 0 and open_start is not None:
        segments.append({
            "text": text[open_start:],
            "atomic": False,
        })
    elif last < len(text):
        segments.append({
            "text": text[last:],
            "atomic": False,
        })

    return segments
