from __future__ import annotations

from dataclasses import dataclass

GENERAL_INITIALS = set([
    "ㄅ", "ㄆ", "ㄇ", "ㄈ",
    "ㄉ", "ㄊ", "ㄋ", "ㄌ",
    "ㄍ", "ㄎ", "ㄏ",
    "ㄐ", "ㄑ", "ㄒ",
])
SPECIAL_INITIALS = set([
    "ㄓ", "ㄔ", "ㄕ", "ㄖ",
    "ㄗ", "ㄘ", "ㄙ",
])
INITIALS = GENERAL_INITIALS | SPECIAL_INITIALS

FINALS_1 = set([
    "ㄚ", "ㄛ", "ㄜ", "ㄝ",
    "ㄞ", "ㄟ", "ㄠ", "ㄡ",
    "ㄢ", "ㄣ", "ㄤ", "ㄥ",
    "ㄦ", "ㄧ", "ㄨ", "ㄩ",
])

FINALS_2 = set([
    "ㄧㄚ", "ㄧㄛ", "ㄧㄝ", "ㄧㄞ", "ㄧㄠ", "ㄧㄡ", "ㄧㄢ", "ㄧㄣ", "ㄧㄤ", "ㄧㄥ",
    "ㄨㄚ", "ㄨㄛ", "ㄨㄞ", "ㄨㄟ", "ㄨㄢ", "ㄨㄣ", "ㄨㄤ", "ㄨㄥ",
    "ㄩㄝ", "ㄩㄢ", "ㄩㄣ", "ㄩㄥ",
])

TONES = set([" ", "ˊ", "ˇ", "ˋ", "˙"])


@dataclass(frozen=True)
class ParseError(ValueError):
    message: str
    index: int
    snippet: str

    def __str__(self) -> str:
        return f"{self.message} (index={self.index}, around={self.snippet!r})"


def _context(s: str, i: int, radius: int = 8) -> str:
    lo = max(0, i - radius)
    hi = min(len(s), i + radius)
    return s[lo:hi]


def _insert_er_for_special_initials(s: str) -> str:
    out = []
    n = len(s)
    i = 0
    while i < n:
        ch = s[i]
        if ch in SPECIAL_INITIALS:
            if i + 1 < n and s[i + 1] in TONES:
                out.append(ch)
                out.append("ㄦ")
                i += 1
                continue
        out.append(ch)
        i += 1
    return "".join(out)


def parse_zhuyin_sequence(seq: str) -> list[str]:
    if not isinstance(seq, str):
        raise TypeError("seq must be a str")

    for idx, ch in enumerate(seq):
        if ch.isspace() and ch != " ":
            raise ParseError("只允許使用半形空白作為一聲；不允許其他空白字元", idx, _context(seq, idx))

    s = _insert_er_for_special_initials(seq)

    res: list[str] = []
    i = 0
    n = len(s)

    while i < n:
        start = i

        if s[i] in TONES:
            raise ParseError("音節不能以聲調開頭", i, _context(s, i))

        if s[i] in INITIALS:
            i += 1

        if i + 1 < n and s[i:i + 2] in FINALS_2:
            i += 2
        elif i < n and s[i] in FINALS_1:
            i += 1
        else:
            raise ParseError("缺少或不合法的韻母", i, _context(s, i))

        if i >= n:
            raise ParseError("缺少聲調（若是一聲，必須有空白）", i, _context(s, i))
        if s[i] not in TONES:
            raise ParseError("缺少或不合法的聲調（若是一聲，必須有空白）", i, _context(s, i))
        i += 1

        res.append(s[start:i])

    return res


def normalize_zhuyin_sequence(seq: str) -> str:
    return parse_zhuyin_sequence(seq)
