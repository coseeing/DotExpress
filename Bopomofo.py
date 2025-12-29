from __future__ import annotations

from dataclasses import dataclass

# ====== 定義 ======

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

# 一聲用「空白」表示
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
    """
    規則 1：
    特殊聲母 7 個(ㄓ ㄔ ㄕ ㄖ ㄗ ㄘ ㄙ)若「後面沒有韻母而直接接聲調」，
    就在韻母與聲調中間補 ㄦ：
      ㄔ  -> ㄔㄦ
      ㄖˋ -> ㄖㄦˋ
    （空白代表一聲）
    """
    out = []
    n = len(s)
    i = 0
    while i < n:
        ch = s[i]
        if ch in SPECIAL_INITIALS:
            # 若下一個字元是聲調（含空白），就補 ㄦ
            if i + 1 < n and s[i + 1] in TONES:
                out.append(ch)
                out.append("ㄦ")
                i += 1
                continue
        out.append(ch)
        i += 1
    return "".join(out)


def parse_zhuyin_sequence(seq: str) -> list[str]:
    """
    輸入：一連串注音符號（包含「空白」作為一聲）
    輸出：若合法，回傳以「字(音節)」為單位的 list[str]
          若非法，raise ValueError

    合法音節：
      聲母(選) + 韻母(必) + 聲調(必)
    """
    if not isinstance(seq, str):
        raise TypeError("seq must be a str")

    # 不接受 tab/newline 等其他空白，避免把它們誤當一聲
    for idx, ch in enumerate(seq):
        if ch.isspace() and ch != " ":
            raise ParseError("只允許使用半形空白作為一聲；不允許其他空白字元", idx, _context(seq, idx))

    # Step 1：補 ㄦ
    s = _insert_er_for_special_initials(seq)

    res: list[str] = []
    i = 0
    n = len(s)

    while i < n:
        start = i

        # 音節不能以聲調開頭
        if s[i] in TONES:
            raise ParseError("音節不能以聲調開頭", i, _context(s, i))

        # 2-1) 聲母(選)
        if s[i] in INITIALS:
            i += 1

        # 2-2) 韻母(必)：優先吃雙韻母（2 字元），再吃單韻母（1 字元）
        if i + 1 < n and s[i:i + 2] in FINALS_2:
            i += 2
        elif i < n and s[i] in FINALS_1:
            i += 1
        else:
            raise ParseError("缺少或不合法的韻母", i, _context(s, i))

        # 2-3) 聲調(必)
        if i >= n:
            raise ParseError("缺少聲調（若是一聲，必須有空白）", i, _context(s, i))
        if s[i] not in TONES:
            raise ParseError("缺少或不合法的聲調（若是一聲，必須有空白）", i, _context(s, i))
        i += 1

        res.append(s[start:i])

    return res


def normalize_zhuyin_sequence(seq: str) -> str:
    """
    驗證並正規化注音序列：
    - 補齊特殊聲母的 ㄦ
    - 確保每個音節符合 聲母+韻母+聲調
    """
    return "".join(parse_zhuyin_sequence(seq))


if __name__ == "__main__":
    print(parse_zhuyin_sequence("ㄒㄧㄡ ㄒㄧˊ"))  # ["ㄒㄧㄡ ", "ㄒㄧˊ"]
    try:
        parse_zhuyin_sequence("ㄖㄖ")
    except ValueError as e:
        print("Expected error:", e)
    print(parse_zhuyin_sequence("ㄖ ㄖ "))       # ["ㄖ ", "ㄖ "]
    print(parse_zhuyin_sequence("ㄖˋ"))          # 會先補成 "ㄖㄦˋ" 再解析 -> ["ㄖㄦˋ"]
    print(normalize_zhuyin_sequence("ㄖ ㄖ "))
