from __future__ import annotations

from typing import Dict, List, Iterable

from languageDetection.blocks import BLOCKS, BLOCK_RSHIFT


def codepoint_block(cp: int) -> str | None:
    idx = cp >> BLOCK_RSHIFT
    if 0 <= idx < len(BLOCKS):
        return BLOCKS[idx]
    return None


def char_block(ch: str) -> str | None:
    if not ch:
        return None
    return codepoint_block(ord(ch))


def build_language_blocks(available_languages_base: Iterable[str]) -> Dict[str, List[str]]:
    available = set(available_languages_base)
    language_blocks: Dict[str, List[str]] = {lang: [] for lang in available}

    if "ja" in available:
        language_blocks["ja"].extend([
            "Kana",
            "Kana Supplement",
        ])

    if "zh" in available:
        language_blocks["zh"].extend([
            "Bopomofo",
            "Bopomofo Extended",
        ])

    if "ko" in available:
        language_blocks["ko"].extend([
            "Hangul Syllables",
            "Hangul Jamo",
            "Hangul Compatibility Jamo",
            "Hangul Jamo Extended-A",
            "Hangul Jamo Extended-B",
        ])

    cjk = {"ja", "zh", "ko"}
    for language in available & cjk:
        language_blocks[language].extend([
            "CJK Symbols and Punctuation",
            "CJK Unified Ideographs",
            "CJK Unified Ideographs Extension A",
            "CJK Unified Ideographs Extension B",
            "CJK Unified Ideographs Extension C",
            "CJK Unified Ideographs Extension D",
            "CJK Compatibility Ideographs",
            "CJK Compatibility Ideographs Supplement",
            "Halfwidth and Fullwidth Forms",
        ])

    return language_blocks


def language_has_char(lang: str, ch: str, language_blocks: Dict[str, List[str]]) -> bool:
    blk = char_block(ch)
    if blk is None:
        return False
    blocks = language_blocks.get(lang)
    if not blocks:
        return False
    return blk in blocks


def language_has_any(lang: str, text: str, language_blocks: Dict[str, List[str]]) -> bool:
    blocks = set(language_blocks.get(lang, []))
    if not blocks:
        return False
    for ch in text:
        blk = char_block(ch)
        if blk in blocks:
            return True
    return False


def language_has_all(lang: str, text: str, language_blocks: Dict[str, List[str]]) -> bool:
    blocks = set(language_blocks.get(lang, []))
    if not blocks:
        return False
    for ch in text:
        blk = char_block(ch)
        if blk not in blocks:
            return False
    return True
