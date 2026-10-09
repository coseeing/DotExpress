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


def _build_trie(replacements: Iterable[tuple[str, str]]) -> _TrieNode:
    """Build the match trie for (source, target) rules; empty sources are skipped."""
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
    return root


def _scan_trie(text: str, root: _TrieNode) -> str:
    """Replace source text using left-to-right, longest-prefix matching.

    Only the original input is scanned. Emitted targets are never re-scanned,
    so replacement rules cannot cascade into one another. The trie is only
    read, never changed, so one trie can serve many scans.
    """
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


def _replace_with_trie(text: str, replacements: Iterable[tuple[str, str]]) -> str:
    return _scan_trie(text, _build_trie(replacements))


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


@dataclass(frozen=True)
class LoadedDictionaryRules:
    """Parsed dictionary rules with their match tries, read once and applied many times.

    Immutable: the rule tuples never change and the private tries are built once,
    in __post_init__, and only read afterwards.
    """

    raw_rules: tuple[tuple[str, str], ...] = ()
    replacement_rules: tuple[tuple[str, str], ...] = ()
    _raw_trie: _TrieNode = field(init=False, repr=False, compare=False)
    _replacement_trie: _TrieNode = field(init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "_raw_trie", _build_trie(self.raw_rules))
        object.__setattr__(self, "_replacement_trie", _build_trie(self.replacement_rules))

    @classmethod
    def from_paths(
        cls,
        dictionary_path: Path | str,
        bopomofo_path: Path | str,
        *,
        processing: Callable[[str], str],
    ) -> "LoadedDictionaryRules":
        """Read the dictionary and Bopomofo rule files.

        A missing dictionary gives empty rules without opening the Bopomofo file.
        A leading UTF-8 BOM is ignored.
        """
        dictionary_path = Path(dictionary_path)
        if not dictionary_path.exists():
            return cls()

        with Path(bopomofo_path).open("r", newline="", encoding="utf-8-sig") as f_b:
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
        bopomofo_trie = _build_trie(replacements_bopomofo)

        with dictionary_path.open("r", newline="", encoding="utf-8-sig") as f_d:
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
                    replacement_parts = [_scan_trie(part, bopomofo_trie) for part in target_parts]
                else:
                    replacement_parts = target.split("@")

                raw_parts, replacement_parts = _align_source_and_replacement_parts(source, replacement_parts)
                raws.append((source, _wrap_atomic_parts(raw_parts)))
                replacements.append((source, _wrap_atomic_parts(replacement_parts)))

        return cls(tuple(raws), tuple(replacements))

    def apply(self, text: str) -> dict[str, str]:
        """Return the raw and replacement text; reads no file and builds no trie."""
        if not self.raw_rules and not self.replacement_rules:
            return {
                "raw": text,
                "replacement": text,
            }
        # Both outputs are derived from the same original text. The trie therefore
        # gives them identical dictionary-match boundaries without relying on marker
        # wrapping to prevent a second replacement pass.
        return {
            "raw": _scan_trie(text, self._raw_trie),
            "replacement": _scan_trie(text, self._replacement_trie),
        }


class DictionaryRulesLoader:
    """Loads one conversion's dictionary rules on first use and keeps them for that conversion.

    Creating a loader reads nothing. A failed load is not kept, so the next
    load() reads the files again. Not thread-safe: one loader serves one
    conversion on one worker thread, and nothing is cached across conversions.
    """

    def __init__(
        self,
        dictionary_path: Path | str,
        bopomofo_path: Path | str,
        *,
        processing: Callable[[str], str],
    ) -> None:
        self._dictionary_path = dictionary_path
        self._bopomofo_path = bopomofo_path
        self._processing = processing
        self._rules: LoadedDictionaryRules | None = None

    def load(self) -> LoadedDictionaryRules:
        if self._rules is None:
            self._rules = LoadedDictionaryRules.from_paths(
                self._dictionary_path,
                self._bopomofo_path,
                processing=self._processing,
            )
        return self._rules


def apply_dictionary(
    text: str,
    dictionary_path: Path | str,
    bopomofo_path: Path | str,
    processing: Callable[[str], str],
) -> dict[str, str]:
    """
    支援不同類型字典的轉換。
    """
    return LoadedDictionaryRules.from_paths(
        dictionary_path,
        bopomofo_path,
        processing=processing,
    ).apply(text)


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
