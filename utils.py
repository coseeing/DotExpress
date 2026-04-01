import csv
import re
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


def translate__mapping_char(
	text: str,
	dictionary_path: Path | str,
	*,
	from_field: str,
	to_field: str,
) -> str:
	"""
	通用的 CSV 對照字串轉換工具。
	- 若目標欄值為空，視為刪除該字元（對 str.translate 以 None 處理）
	- 只處理單一字元對應；多字元對應會被略過（str.translate 無法處理片語替換）

	Args:
		text: 要轉換的字串
		dictionary_path: 對照表路徑
		from_field: CSV 中來源欄名稱（需為單一字元）
		to_field: CSV 中目標欄名稱

	Returns:
		轉換後的字串
	"""
	dictionary_path = Path(dictionary_path)
	mapping: dict[int, str | None] = {}

	with dictionary_path.open("r", newline="", encoding="utf-8") as f:
		reader = csv.DictReader(f)
		if reader.fieldnames is None:
			raise ValueError("CSV must contain header row.")
		if not {from_field, to_field}.issubset(reader.fieldnames):
			raise ValueError(f"CSV must contain columns: {from_field}, {to_field}")

		for row in reader:
			source_char = (row.get(from_field) or "")
			target_char = row.get(to_field)

			if len(source_char) != 1:
				continue

			value = None if not target_char else target_char
			mapping[ord(source_char)] = value

	return text.translate(mapping)


def mapping(
	text: str,
	replacements: Iterable[tuple[str, str]],
	*,
	marker: bool = False,
) -> str:
	# 依據來源字串長度由長到短排序，避免較短的匹配先行替換造成重疊問題。
	ordered_replacements = sorted(
		replacements,
		key=lambda item: len(item[0]),
		reverse=True,
	)

	result = text
	for source, target in ordered_replacements:
		if not marker:
			result = result.replace(source, target)
			continue

		segments = split_bracket_segments(result)
		tmp = ""
		for segment in segments:
			text = segment["text"]
			if not segment["atomic"]:
				text = text.replace(source, target)
			else:
				text = f"{DICTIONARY_MARKER_OPEN}{text}{DICTIONARY_MARKER_CLOSE}"
			tmp += text
		result = tmp
	return result


def translate__mapping_string(
	text: str,
	dictionary_path: Path | str,
	*,
	from_field: str,
	to_field: str,
) -> str:
	"""
	支援多字元對多字元的字串對照轉換。

	Args:
		text: 要轉換的字串
		dictionary_path: 對照表路徑
		from_field: CSV 中來源欄名稱
		to_field: CSV 中目標欄名稱

	Returns:
		轉換後的字串
	"""
	dictionary_path = Path(dictionary_path)
	if not dictionary_path.exists():
		return text

	with dictionary_path.open("r", newline="", encoding="utf-8") as f:
		reader = csv.DictReader(f)
		if reader.fieldnames is None:
			raise ValueError("CSV must contain header row.")
		if not {from_field, to_field}.issubset(reader.fieldnames):
			raise ValueError(f"CSV must contain columns: {from_field}, {to_field}")

		replacements: list[tuple[str, str]] = []
		for row in reader:
			source = (row.get(from_field) or "")
			target = (row.get(to_field) or "")
			if not source:
				continue
			replacements.append((source, target))

	result = mapping(text, replacements)

	return result


def apply_dictionary(
	text: str,
	dictionary_path: Path | str,
	bopomofo_path: Path | str,
	processing: Callable[[str], str],
) -> str:
	"""
	支援不同類型字典的轉換

	Args:
		text: 要轉換的字串
		dictionary_path: 對照表路徑

	Returns:
		轉換後的字串
	"""
	dictionary_path = Path(dictionary_path)
	if not dictionary_path.exists():
		return {
			"raw": text,
			"replacement": text,
		}

	with bopomofo_path.open("r", newline="", encoding="utf-8") as f_b:
		reader = csv.DictReader(f_b)
		if reader.fieldnames is None:
			raise ValueError("CSV must contain header row.")
		if not {"Bopomofo", "Braille"}.issubset(reader.fieldnames):
			raise ValueError(f"CSV must contain columns: Bopomofo, Braille")

		replacements_bopomofo: list[tuple[str, str]] = []
		for row in reader:
			source = (row.get("Bopomofo") or "")
			target = (row.get("Braille") or "")
			if not source:
				continue
			replacements_bopomofo.append((source, target))

	with dictionary_path.open("r", newline="", encoding="utf-8") as f_d:
		reader = csv.DictReader(f_d)
		if reader.fieldnames is None:
			raise ValueError("CSV must contain header row.")
		if not {"text", "braille", "type"}.issubset(reader.fieldnames):
			raise ValueError(f"CSV must contain columns: text, braille, type")

		raws: list[tuple[str, str]] = []
		for row in reader:
			source = (row.get("text") or "")
			if not source:
				continue

			target = (
				DICTIONARY_MARKER_OPEN
				+ DICTIONARY_MARKER_JOIN.join([i for i in source])
				+ DICTIONARY_MARKER_CLOSE
			)
			raws.append((source, target))

	with dictionary_path.open("r", newline="", encoding="utf-8") as f_d:
		reader = csv.DictReader(f_d)
		if reader.fieldnames is None:
			raise ValueError("CSV must contain header row.")
		if not {"text", "braille", "type"}.issubset(reader.fieldnames):
			raise ValueError(f"CSV must contain columns: text, braille, type")

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
				except Exception as e:
					pass
				target = (
					DICTIONARY_MARKER_OPEN
					+ DICTIONARY_MARKER_JOIN.join(target)
					+ DICTIONARY_MARKER_CLOSE
				)
				target = mapping(target, replacements_bopomofo)
			else:
				target = (
					DICTIONARY_MARKER_OPEN
					+ DICTIONARY_MARKER_JOIN.join(target.split("@"))
					+ DICTIONARY_MARKER_CLOSE
				)
			replacements.append((source, target))

	raw = mapping(text, raws, marker=True)
	replacement = mapping(text, replacements, marker=True)

	return {
		"raw": raw,
		"replacement": replacement,
	}


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
