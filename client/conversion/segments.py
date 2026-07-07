def _append_text_segment(segments: list[dict[str, str]], text: str) -> None:
    if not text:
        return
    if segments and segments[-1]["type"] == "text":
        segments[-1]["text"] += text
    else:
        segments.append({"type": "text", "text": text})


def parse_inline_math_segments(text: str) -> list[dict[str, str]]:
    segments: list[dict[str, str]] = []
    current: list[str] = []
    in_math = False

    for index, char in enumerate(text):
        is_escaped_dollar = char == "$" and index > 0 and text[index - 1] == "\\"
        if char == "$" and not is_escaped_dollar:
            if in_math:
                segments.append({"type": "math", "text": "".join(current)})
                current = []
                in_math = False
            else:
                _append_text_segment(segments, "".join(current))
                current = []
                in_math = True
            continue
        current.append(char)

    if in_math:
        _append_text_segment(segments, "$" + "".join(current))
    else:
        _append_text_segment(segments, "".join(current))

    return segments


def segment_needs_boundary_space(left_segment: dict[str, str], right_segment: dict[str, str]) -> bool:
    if left_segment["type"] != "math" and right_segment["type"] != "math":
        return False
    left_text = left_segment["text"]
    right_text = right_segment["text"]
    return bool(
        left_text
        and right_text
        and not left_text[-1].isspace()
        and not right_text[0].isspace()
    )
