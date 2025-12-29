import csv
from pathlib import Path
from typing import Callable


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

	# 依據來源字串長度由長到短排序，避免較短的匹配先行替換造成重疊問題。
	replacements.sort(key=lambda item: len(item[0]), reverse=True)

	result = text
	for source, target in replacements:
		result = result.replace(source, target)
	return result


def apply_dictionary(
	text: str,
	dictionary_path: Path | str,
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
		return text

	with dictionary_path.open("r", newline="", encoding="utf-8") as f:
		reader = csv.DictReader(f)
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

			replacements.append((source, target))

	# 依據來源字串長度由長到短排序，避免較短的匹配先行替換造成重疊問題。
	replacements.sort(key=lambda item: len(item[0]), reverse=True)

	result = text
	for source, target in replacements:
		result = result.replace(source, target)
	return result

