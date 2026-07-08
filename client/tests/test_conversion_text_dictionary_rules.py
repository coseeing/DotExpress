import csv
from pathlib import Path

from conversion.text.dictionary_rules import (
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


def test_apply_dictionary_longer_source_strings_win_over_shorter_overlaps(tmp_path) -> None:
    dictionary_path = tmp_path / "dictionary.csv"
    bopomofo_path = tmp_path / "bopomofo.csv"

    with dictionary_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["text", "braille", "type"])
        writer.writeheader()
        writer.writerow({"text": "abc", "braille": "short", "type": ""})
        writer.writerow({"text": "abcd", "braille": "long", "type": ""})

    with bopomofo_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["Bopomofo", "Braille"])
        writer.writeheader()

    result = apply_dictionary(
        "abcd",
        dictionary_path=dictionary_path,
        bopomofo_path=bopomofo_path,
        processing=lambda text: text,
    )

    assert split_bracket_segments(result["replacement"]) == [
        {"text": "long", "atomic": True},
    ]


def test_apply_dictionary_bopomofo_branch_calls_processing_and_maps_output(tmp_path) -> None:
    dictionary_path = tmp_path / "dictionary.csv"
    bopomofo_path = tmp_path / "bopomofo.csv"
    processed: list[str] = []

    with dictionary_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["text", "braille", "type"])
        writer.writeheader()
        writer.writerow({"text": "肚子", "braille": "ㄉㄨˋ", "type": "Bopomofo"})

    with bopomofo_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["Bopomofo", "Braille"])
        writer.writeheader()
        writer.writerow({"Bopomofo": "ㄉㄨˋ", "Braille": "⠙⠨"})

    def processing(text: str) -> str:
        processed.append(text)
        return text

    result = apply_dictionary(
        "肚子",
        dictionary_path=dictionary_path,
        bopomofo_path=bopomofo_path,
        processing=processing,
    )

    assert processed == ["ㄉㄨˋ"]
    assert split_bracket_segments(result["replacement"]) == [
        {"text": "⠙⠨", "atomic": True},
    ]


def test_apply_dictionary_collapses_length_mismatch_to_one_segment(tmp_path) -> None:
    dictionary_path = tmp_path / "dictionary.csv"
    bopomofo_path = tmp_path / "bopomofo.csv"

    with dictionary_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["text", "braille", "type"])
        writer.writeheader()
        writer.writerow({"text": "音樂", "braille": "abc", "type": ""})

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
        {"text": "音樂", "atomic": True},
    ]
    assert split_bracket_segments(result["replacement"]) == [
        {"text": "abc", "atomic": True},
    ]


def test_split_bracket_segments_treats_unclosed_marker_as_text() -> None:
    assert split_bracket_segments(r"\[abc") == [
        {"text": r"\[abc", "atomic": False},
    ]
