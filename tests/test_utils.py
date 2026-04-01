import csv

from utils import (
	DICTIONARY_MARKER_CLOSE,
	DICTIONARY_MARKER_OPEN,
	apply_dictionary,
	mapping,
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
