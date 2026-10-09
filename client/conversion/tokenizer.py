"""How source characters are grouped into tokens.

Pure functions over token lists and position maps; TranslationResult
(conversion.alignment) applies the spans they return to its four lists.
"""
import string
from types import MappingProxyType

from languageDetection.unicode_blocks import (
    build_language_blocks,
    language_has_all,
)


LEFT_PUNCT_HALF = frozenset("([{")
RIGHT_PUNCT_HALF = frozenset(")]}")
MIDDLE_SENTENCE_PUNCT_HALF = frozenset(",;:%")
END_SENTENCE_PUNCT_HALF = frozenset(".!?")

LEFT_PUNCT_FULL = frozenset("‘“「『〈《【〔〖（")
RIGHT_PUNCT_FULL = frozenset("’”」』〉》】〕〗）")
MIDDLE_SENTENCE_PUNCT_FULL = frozenset("，；：、％")
END_SENTENCE_PUNCT_FULL = frozenset("。！？")

LEFT_PUNCT = LEFT_PUNCT_HALF | LEFT_PUNCT_FULL
RIGHT_PUNCT = RIGHT_PUNCT_HALF | RIGHT_PUNCT_FULL
MIDDLE_SENTENCE_PUNCT = MIDDLE_SENTENCE_PUNCT_HALF | MIDDLE_SENTENCE_PUNCT_FULL
END_SENTENCE_PUNCT = END_SENTENCE_PUNCT_HALF | END_SENTENCE_PUNCT_FULL

CJK_LANGUAGE_BLOCKS = MappingProxyType({
    language: tuple(blocks)
    for language, blocks in build_language_blocks(("ja", "zh", "ko")).items()
})

# ---- ASCII 英數集合（可合併成詞）----
ASCII_ALNUM = frozenset(string.ascii_letters + string.digits)
# 會併到「前一個字母 token」的尾隨標點（避免出現在行首）
TRAIL_PUNCT = RIGHT_PUNCT | MIDDLE_SENTENCE_PUNCT | END_SENTENCE_PUNCT
# 會併到「後一個字母 token」的開頭標點（避免出現在行尾）
LEAD_PUNCT = LEFT_PUNCT | frozenset("—")


def is_cjk_word_char(ch: str, lang_blocks) -> bool:
    """CJK/kana/Bopomofo/Hangul letters: one token each, but they can take punctuation."""
    if not lang_blocks:
        return False
    for _lang in ("ja", "zh", "ko"):
        if language_has_all(_lang, ch, lang_blocks):
            return True
    return False


def contracted_token_spans(raw_to_braille_pos) -> list[tuple[int, int]]:
    """Spans of adjacent source characters that share one braille-cell start."""
    token_spans: list[tuple[int, int]] = []
    start = 0
    while start < len(raw_to_braille_pos):
        end = start + 1
        while (
            end < len(raw_to_braille_pos)
            and raw_to_braille_pos[end] == raw_to_braille_pos[start]
        ):
            end += 1
        token_spans.append((start, end))
        start = end
    return token_spans


def word_token_spans(units, lang_blocks=CJK_LANGUAGE_BLOCKS) -> list[tuple[int, int]]:
    """Spans of word-level tokens over units (see TranslationResult.bind_word_tokens).

    The token text of a span (start, end) is always "".join(units[start:end]).
    """
    chars = units  # list[str]（每元素一字元）
    n_chars = len(chars)

    # ---- Pass 1：產生基礎 tokens ----
    # 規則：
    #   - 連續 ASCII 英數 → 合併為一個 token
    #   - CJK/假名/注音/韓文 → 單字一 token（不合併）
    #   - 其他（空白/標點/符號…）→ 單字一 token
    #   - '\n' → 獨立 token
    tokens: list[str] = []
    token_char_spans: list[tuple[int, int]] = []  # (char_start, char_end_exclusive)

    i = 0
    while i < n_chars:
        ch = chars[i]
        if ch == "\n":
            tokens.append("\n")
            token_char_spans.append((i, i + 1))
            i += 1
            continue

        if ch in ASCII_ALNUM:
            j = i + 1
            while j < n_chars and chars[j] in ASCII_ALNUM:
                j += 1
            tokens.append("".join(chars[i:j]))
            token_char_spans.append((i, j))
            i = j
            continue

        if is_cjk_word_char(ch, lang_blocks):
            tokens.append(ch)
            token_char_spans.append((i, i + 1))
            i += 1
            continue

        # 其他：空白/標點/符號等，單字元 token
        tokens.append(ch)
        token_char_spans.append((i, i + 1))
        i += 1

    # ---- 定義「字母 token」：可被尾隨/開頭標點綁定的 token ----
    #   A) 含任一 ASCII_ALNUM 的 ASCII 詞
    #   B) 長度為 1 且為 CJK 字母字元
    def is_word_token(tok: str) -> bool:
        if any(c in ASCII_ALNUM for c in tok):
            return True
        return len(tok) == 1 and is_cjk_word_char(tok, lang_blocks)

    # ---- Pass 2：尾隨標點鏈併入前一個字母 token ----
    merged_tokens: list[str] = []
    merged_spans: list[tuple[int, int]] = []
    t = 0
    while t < len(tokens):
        tok = tokens[t]
        span_start, span_end = token_char_spans[t]

        if is_word_token(tok):
            u = t
            trailing_text = ""
            trailing_end = span_end
            # 貪婪吸收連續尾隨標點
            while (
                u + 1 < len(tokens)
                and len(tokens[u + 1]) == 1
                and tokens[u + 1] in TRAIL_PUNCT
            ):
                u += 1
                trailing_text += tokens[u]
                trailing_end = token_char_spans[u][1]
            if trailing_text:
                tok = tok + trailing_text
                span_end = trailing_end
                t = u  # 跳過吃掉的尾隨標點

        merged_tokens.append(tok)
        merged_spans.append((span_start, span_end))
        t += 1

    tokens = merged_tokens
    token_char_spans = merged_spans

    # ---- Pass 3：開頭標點鏈併到下一個字母 token ----
    # 不與 '\n' 或空白（含全形空白等 .isspace()）綁定
    merged_tokens2: list[str] = []
    merged_spans2: list[tuple[int, int]] = []
    t = 0
    while t < len(tokens):
        tok = tokens[t]
        span_start, span_end = token_char_spans[t]

        if len(tok) == 1 and tok in LEAD_PUNCT and t + 1 < len(tokens):
            u = t
            lead_text = tok
            lead_start = span_start
            lead_end = span_end

            # 收集連續的開頭標點
            while (
                u + 1 < len(tokens)
                and len(tokens[u + 1]) == 1
                and tokens[u + 1] in LEAD_PUNCT
            ):
                u += 1
                lead_text += tokens[u]
                lead_end = token_char_spans[u][1]

            # 嘗試與下一個可綁定的「字母 token」合併
            if u + 1 < len(tokens):
                next_tok = tokens[u + 1]
                if next_tok != "\n" and not (len(next_tok) == 1 and next_tok.isspace()):
                    if is_word_token(next_tok):
                        merged_tokens2.append(lead_text + next_tok)
                        merged_spans2.append((lead_start, token_char_spans[u + 1][1]))
                        t = u + 2
                        continue

            # 無法綁定則保留開頭標點鏈
            merged_tokens2.append(lead_text)
            merged_spans2.append((lead_start, lead_end))
            t = u + 1
            continue

        # 其他情況原樣輸出
        merged_tokens2.append(tok)
        merged_spans2.append((span_start, span_end))
        t += 1

    return merged_spans2


def iter_separator_positions(tokens):
    """Yield each index i (1 <= i < len(tokens)) before which a separator space goes:
    tokens[i - 1] ends with a closing and tokens[i] starts with an opening mark."""
    for i in range(1, len(tokens)):
        prev_tok = tokens[i - 1]
        curr_tok = tokens[i]
        # 防禦：空字串不處理
        if prev_tok and curr_tok and prev_tok[-1] in RIGHT_PUNCT and curr_tok[0] in LEFT_PUNCT:
            yield i
