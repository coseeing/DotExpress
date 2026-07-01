from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class AlignmentItem:
	raw_index: int
	raw_char: str
	braille_start: int
	braille_end: int
	braille_text: str
	is_space: bool
	is_newline: bool


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


def build_dual_view_model(translation_results: Iterable[object]) -> DualViewModel:
	segments: list[AlignmentSegment] = []

	for result in translation_results:
		raw_tokens = list(result.raw)
		braille = list(result.braille)
		raw_to_braille_pos = list(result.raw_to_braille_pos)

		if len(raw_to_braille_pos) != len(raw_tokens):
			raise ValueError("raw_to_braille_pos must contain one entry per raw token")

		items: list[AlignmentItem] = []
		raw_index = 0
		for token_index, raw_token in enumerate(raw_tokens):
			start = raw_to_braille_pos[token_index]
			end = _token_braille_end(raw_to_braille_pos, token_index, len(braille))

			if start < 0 or end < start or end > len(braille):
				raise ValueError("invalid raw-to-braille alignment range")

			raw_text = str(raw_token)
			for character_index, raw_char in enumerate(raw_text):
				character_start = start if character_index == 0 else end
				items.append(
					AlignmentItem(
						raw_index=raw_index,
						raw_char=raw_char,
						braille_start=character_start,
						braille_end=end,
						braille_text="".join(braille[character_start:end]),
						is_space=raw_char.isspace() and raw_char != "\n",
						is_newline=raw_char == "\n",
					)
				)
				raw_index += 1

		segments.append(
			AlignmentSegment(
				source_text="".join(str(token) for token in raw_tokens),
				braille_text="".join(braille),
				items=tuple(items),
			)
		)

	return DualViewModel(tuple(segments))
