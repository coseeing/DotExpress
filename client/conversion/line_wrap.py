"""How tokens are laid out on lines of a given width."""
from conversion.tokenizer import END_SENTENCE_PUNCT_FULL, RIGHT_PUNCT_FULL


# A token ending in one of these marks is followed by a separator space when the
# next token is not a space and the token's braille does not already end blank.
SEPARATED_AFTER_PUNCT = RIGHT_PUNCT_FULL | END_SENTENCE_PUNCT_FULL
SPACE_ONLY = frozenset(" ")


def wrap_tokens(tokens, braille, raw_to_braille_pos, width) -> tuple[str, str]:
    """Lay the tokens out on lines of width braille cells.

    Token i owns the cells braille[raw_to_braille_pos[i]:raw_to_braille_pos[i + 1]]
    (the last token owns the rest). Returns (braille text, source text), lines joined
    by "\\n"; every braille line is padded with blank cells to the full width. The
    inputs are only read.
    """
    blank = chr(0x2800)
    width = max(1, int(width or 1))
    current_len = 0

    raw_lines: list[list[str]] = []
    current_raw_parts: list[str] = []

    braille_lines: list[list[str]] = []
    current_braille_parts: list[str] = []

    raw_len = len(tokens)

    # line_start_blank 是為了分辨是原文就在開頭的空白與後續因點字規則需要而插入的空白
    # (line_start_blank tells spaces that start a source line, which are kept, from a
    # space that only starts a wrapped line, which is dropped.)
    line_start_blank = True
    full_line_break = False

    for i, token in enumerate(tokens):
        # Treat explicit newline in source as a hard line break.
        if token == "\n":
            # Pad a partly filled line, or an empty line that a newline started (not
            # the empty line left behind when the previous token filled a line).
            if (current_len < width and current_len > 0) or (current_len == 0 and not full_line_break):
                current_raw_parts.append("")
                current_braille_parts.append(blank * (width - current_len))

            # 不能與上面條件相同，要移除 current_len < width 因為這樣如果單一 token 超過寬度雖然會爆版，但仍能顯示
            # (Not the same condition as above: without current_len < width, a line that
            # one over-long token overflows is still ended here, so the token is shown.)
            if current_len > 0 or (current_len == 0 and not full_line_break):
                raw_lines.append(current_raw_parts)
                braille_lines.append(current_braille_parts)
                current_raw_parts = []
                current_braille_parts = []
                current_len = 0

            line_start_blank = True
            full_line_break = False
            continue
        elif token == " ":
            # A space at the start of a wrapped line is dropped.
            if current_len == 0 and not line_start_blank:
                continue

        if token != " ":
            line_start_blank = False

        full_line_break = False
        start = raw_to_braille_pos[i]
        end = raw_to_braille_pos[i + 1] if i + 1 < raw_len else len(braille)
        seg_len = end - start

        # The token does not fit: pad and end the current line first.
        if current_len + seg_len > width and current_len > 0:
            current_raw_parts.append("")
            current_braille_parts.append(blank * (width - current_len))
            raw_lines.append(current_raw_parts)
            braille_lines.append(current_braille_parts)
            current_raw_parts = []
            current_braille_parts = []
            current_len = 0

        if seg_len:
            current_raw_parts.append(token)
            current_braille_parts.append("".join(braille[start:end]))
            current_len += seg_len

        if current_len < width:
            next_token = tokens[i + 1] if i + 1 < len(tokens) else None
            if (
                token[-1] in SEPARATED_AFTER_PUNCT
                and next_token is not None
                and next_token not in SPACE_ONLY
                and current_braille_parts[-1][-1] != blank
            ):
                current_raw_parts[-1] += " "
                current_braille_parts[-1] += blank
                current_len += len(blank)

        if current_len == width:
            raw_lines.append(current_raw_parts)
            braille_lines.append(current_braille_parts)
            current_raw_parts = []
            current_braille_parts = []
            current_len = 0
            full_line_break = True

    if current_len > 0 or not braille_lines:
        current_raw_parts.append("")
        current_braille_parts.append(blank * (width - current_len))
        raw_lines.append(current_raw_parts)
        braille_lines.append(current_braille_parts)

    braille_lines_str = ["".join(item) for item in braille_lines]
    raw_lines_str = ["".join(item) for item in raw_lines]

    return "\n".join(braille_lines_str), "\n".join(raw_lines_str)
