import csv

import pytest

from conversion.text.char_maps import translate__mapping_char


def test_translate_mapping_char_maps_single_char_rows(tmp_path) -> None:
    dictionary_path = tmp_path / "mapping.csv"

    with dictionary_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["source", "target"])
        writer.writeheader()
        writer.writerow({"source": "a", "target": "x"})
        writer.writerow({"source": "b", "target": "y"})

    assert translate__mapping_char(
        "abc",
        dictionary_path=dictionary_path,
        from_field="source",
        to_field="target",
    ) == "xyc"


def test_translate_mapping_char_ignores_multi_char_sources(tmp_path) -> None:
    dictionary_path = tmp_path / "mapping.csv"

    with dictionary_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["source", "target"])
        writer.writeheader()
        writer.writerow({"source": "ab", "target": "x"})
        writer.writerow({"source": "c", "target": "z"})

    assert translate__mapping_char(
        "abc",
        dictionary_path=dictionary_path,
        from_field="source",
        to_field="target",
    ) == "abz"


def test_translate_mapping_char_deletes_char_when_target_is_empty(tmp_path) -> None:
    dictionary_path = tmp_path / "mapping.csv"

    with dictionary_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["source", "target"])
        writer.writeheader()
        writer.writerow({"source": "b", "target": ""})

    assert translate__mapping_char(
        "abc",
        dictionary_path=dictionary_path,
        from_field="source",
        to_field="target",
    ) == "ac"


def test_translate_mapping_char_requires_header_row(tmp_path) -> None:
    dictionary_path = tmp_path / "mapping.csv"
    dictionary_path.write_text("", encoding="utf-8")

    with pytest.raises(ValueError, match="header row"):
        translate__mapping_char(
            "abc",
            dictionary_path=dictionary_path,
            from_field="source",
            to_field="target",
        )


def test_translate_mapping_char_requires_requested_columns(tmp_path) -> None:
    dictionary_path = tmp_path / "mapping.csv"

    with dictionary_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["source", "other"])
        writer.writeheader()
        writer.writerow({"source": "a", "other": "x"})

    with pytest.raises(ValueError, match="source, target"):
        translate__mapping_char(
            "abc",
            dictionary_path=dictionary_path,
            from_field="source",
            to_field="target",
        )
