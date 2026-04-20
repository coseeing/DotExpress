import csv
from pathlib import Path

from utils import (
	DICTIONARY_MARKER_CLOSE,
	DICTIONARY_MARKER_OPEN,
	apply_dictionary,
	mapping,
	split_bracket_segments,
)


def test_mapping_marker_skips_atomic_segments() -> None:
	text = "abc"
	protected = f"{DICTIONARY_MARKER_OPEN}foo{DICTIONARY_MARKER_CLOSE}"

	result = mapping(
		text,
		[
			("abc", protected),
			("o", "x"),
		],
		marker=True,
	)

	assert result == protected


def test_apply_dictionary_does_not_remap_dictionary_output(tmp_path) -> None:
	dictionary_path = tmp_path / "dictionary.csv"
	bopomofo_path = tmp_path / "bopomofo.csv"

	with dictionary_path.open("w", newline="", encoding="utf-8") as f:
		writer = csv.DictWriter(f, fieldnames=["text", "braille", "type"])
		writer.writeheader()
		writer.writerow({"text": "abc", "braille": "foo", "type": ""})
		writer.writerow({"text": "o", "braille": "bar", "type": ""})

	with bopomofo_path.open("w", newline="", encoding="utf-8") as f:
		writer = csv.DictWriter(f, fieldnames=["Bopomofo", "Braille"])
		writer.writeheader()

	result = apply_dictionary(
		"abc",
		dictionary_path=dictionary_path,
		bopomofo_path=bopomofo_path,
		processing=lambda text: text,
	)

	assert result["raw"] == (
		f"{DICTIONARY_MARKER_OPEN}a{DICTIONARY_MARKER_CLOSE}"
		f"{DICTIONARY_MARKER_OPEN}b{DICTIONARY_MARKER_CLOSE}"
		f"{DICTIONARY_MARKER_OPEN}c{DICTIONARY_MARKER_CLOSE}"
	)
	assert result["replacement"] == f"{DICTIONARY_MARKER_OPEN}foo{DICTIONARY_MARKER_CLOSE}"


def test_apply_dictionary_aligns_bopomofo_multi_char_segments(tmp_path) -> None:
	dictionary_path = tmp_path / "dictionary.csv"

	with dictionary_path.open("w", newline="", encoding="utf-8") as f:
		writer = csv.DictWriter(f, fieldnames=["text", "braille", "type"])
		writer.writeheader()
		writer.writerow({"text": "肚子", "braille": "ㄉㄨˋㄗ˙", "type": "Bopomofo"})

	result = apply_dictionary(
		"肚子",
		dictionary_path=dictionary_path,
		bopomofo_path=Path("data/Bopomofo2Braille.csv"),
		processing=lambda text: text,
	)

	assert split_bracket_segments(result["raw"]) == [
		{"text": "肚", "atomic": True},
		{"text": "子", "atomic": True},
	]
	assert len(split_bracket_segments(result["raw"])) == len(split_bracket_segments(result["replacement"]))


def test_apply_dictionary_aligns_braille_multi_char_segments_with_at_separator(tmp_path) -> None:
	dictionary_path = tmp_path / "dictionary.csv"
	bopomofo_path = tmp_path / "bopomofo.csv"

	with dictionary_path.open("w", newline="", encoding="utf-8") as f:
		writer = csv.DictWriter(f, fieldnames=["text", "braille", "type"])
		writer.writeheader()
		writer.writerow({"text": "音樂", "braille": "abc@de", "type": "Braille"})

	with bopomofo_path.open("w", newline="", encoding="utf-8") as f:
		writer = csv.DictWriter(f, fieldnames=["Bopomofo", "Braille"])
		writer.writeheader()

	result = apply_dictionary(
		"音樂",
		dictionary_path=dictionary_path,
		bopomofo_path=bopomofo_path,
		processing=lambda text: text,
	)

	assert split_bracket_segments(result["raw"]) == [
		{"text": "音", "atomic": True},
		{"text": "樂", "atomic": True},
	]
	assert split_bracket_segments(result["replacement"]) == [
		{"text": "abc", "atomic": True},
		{"text": "de", "atomic": True},
	]
