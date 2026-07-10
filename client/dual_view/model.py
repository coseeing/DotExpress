from dataclasses import dataclass
from typing import Callable, Iterable

from conversion.math_service import latex_to_mathml


@dataclass(frozen=True)
class DualViewSegment:
    result: object
    source_kind: str


@dataclass(frozen=True)
class AlignmentItem:
	raw_index: int
	raw_text: str
	braille_start: int
	braille_end: int
	braille_text: str
	is_space: bool
	is_newline: bool
	source_kind: str
	source_html: str | None


@dataclass(frozen=True)
class AlignmentSegment:
	source_text: str
	braille_text: str
	items: tuple[AlignmentItem, ...]


@dataclass(frozen=True)
class DualViewModel:
	segments: tuple[AlignmentSegment, ...]


def _token_braille_end(raw_to_braille_pos: list[int], token_index: int, braille_length: int) -> int:
	if token_index + 1 < len(raw_to_braille_pos):
		return raw_to_braille_pos[token_index + 1]
	return braille_length


def build_dual_view_model(segments: Iterable[DualViewSegment], *, mathml_converter: Callable[[str], str] = latex_to_mathml) -> DualViewModel:
	result_segments: list[AlignmentSegment] = []

	for segment in segments:
		if segment.source_kind not in {"text", "math"}:
			raise ValueError("source_kind must be 'text' or 'math'")

		result = segment.result
		raw_tokens = list(result.raw)
		braille = list(result.braille)
		raw_to_braille_pos = list(result.raw_to_braille_pos)

		if len(raw_to_braille_pos) != len(raw_tokens):
			raise ValueError("raw_to_braille_pos must contain one entry per raw token")

		items: list[AlignmentItem] = []
		for token_index, raw_token in enumerate(raw_tokens):
			start = raw_to_braille_pos[token_index]
			end = _token_braille_end(raw_to_braille_pos, token_index, len(braille))

			if start < 0 or end < start or end > len(braille):
				raise ValueError("invalid raw-to-braille alignment range")

			raw_text = str(raw_token)
			items.append(
				AlignmentItem(
					raw_index=token_index,
					raw_text=raw_text,
					braille_start=start,
					braille_end=end,
					braille_text="".join(braille[start:end]),
					is_space=(raw_text == " "),
					is_newline=(raw_text == "\n"),
					source_kind=segment.source_kind,
					source_html=mathml_converter(raw_text) if segment.source_kind == "math" else None,
				)
			)

		result_segments.append(
			AlignmentSegment(
				source_text="".join(str(token) for token in raw_tokens),
				braille_text="".join(braille),
				items=tuple(items),
			)
		)

	return DualViewModel(tuple(result_segments))
