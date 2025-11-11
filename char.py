from typing import Dict, List, Set, Iterable

from languageDetection.blocks import BLOCKS, BLOCK_RSHIFT

# ---- 基礎：由字元求其 Unicode Block 名稱 ----
def codepoint_block(cp: int) -> str | None:
    """給定 code point 回傳所屬 BLOCK 名稱（或 None）。"""
    idx = cp >> BLOCK_RSHIFT
    if 0 <= idx < len(BLOCKS):
        return BLOCKS[idx]
    return None

def char_block(ch: str) -> str | None:
    """給定單一字元回傳所屬 BLOCK 名稱（或 None）。"""
    if not ch:
        return None
    return codepoint_block(ord(ch))

# ---- 建立語系對應的 block 名稱集合 ----
def build_language_blocks(availableLanguagesBase: Iterable[str]) -> Dict[str, List[str]]:
    """
    依 availableLanguagesBase（如 {'ja','zh','ko'}）建立語系 -> 應涵蓋的 Unicode Block 名稱清單。
    只加入「有出現在 availableLanguagesBase」的語系。
    """
    available = set(availableLanguagesBase)
    languageBlocks: Dict[str, List[str]] = {lang: [] for lang in available}

    # ja：日文 ─ Hiragana / Katakana / Katakana Phonetic Extensions 在你的 BLOCKS 都標為 "Kana"
    if "ja" in available:
        languageBlocks["ja"].extend([
            "Kana",              # Hiragana / Katakana / Katakana Phonetic Extensions（皆標 "Kana"）
            "Kana Supplement",   # U+1B000–U+1B0FF
        ])

    # zh：中文 ─ 注音相關
    if "zh" in available:
        languageBlocks["zh"].extend([
            "Bopomofo",
            "Bopomofo Extended",
        ])

    # ko：韓文
    if "ko" in available:
        languageBlocks["ko"].extend([
            "Hangul Syllables",
            "Hangul Jamo",
            "Hangul Compatibility Jamo",
            "Hangul Jamo Extended-A",
            "Hangul Jamo Extended-B",
        ])

    # CJK 三語共同：漢字與周邊
    CJK = {"ja", "zh", "ko"}
    for l in (available & CJK):
        languageBlocks[l].extend([
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

    return languageBlocks

# ---- 判斷工具：給語系與字元，看是否屬於該語系涵蓋的區塊 ----
def language_has_char(lang: str, ch: str, languageBlocks: Dict[str, List[str]]) -> bool:
    """檢查 ch 的區塊是否在 languageBlocks[lang] 之內。"""
    blk = char_block(ch)
    if blk is None:
        return False
    blocks = languageBlocks.get(lang)
    if not blocks:
        return False
    return blk in blocks

# ----（可選）一次判斷多字元 ----
def language_has_any(lang: str, text: str, languageBlocks: Dict[str, List[str]]) -> bool:
    """文字中只要有任一字元屬於該語系涵蓋區塊就回 True。"""
    blocks = set(languageBlocks.get(lang, []))
    if not blocks:
        return False
    for ch in text:
        blk = char_block(ch)
        if blk in blocks:
            return True
    return False

def language_has_all(lang: str, text: str, languageBlocks: Dict[str, List[str]]) -> bool:
    """文字中所有字元皆需屬於該語系涵蓋區塊才回 True（通常較嚴格，實務較少用）。"""
    blocks = set(languageBlocks.get(lang, []))
    if not blocks:
        return False
    for ch in text:
        blk = char_block(ch)
        if blk not in blocks:
            return False
    return True


if __name__ == '__main__':
	lang_blocks = build_language_blocks({"ja", "zh", "ko"})

	print(language_has_char("ja", "あ", lang_blocks))   # True（Kana）
	print(language_has_char("zh", "ㄅ", lang_blocks))   # True（Bopomofo）
	print(language_has_char("ko", "한", lang_blocks))   # True（Hangul Syllables）
	print(language_has_char("zh", "。", lang_blocks))   # True（CJK Symbols and Punctuation）
	print(language_has_char("zh", "Ａ", lang_blocks))   # True（Halfwidth and Fullwidth Forms）
