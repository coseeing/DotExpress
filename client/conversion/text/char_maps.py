import csv
from pathlib import Path


def _load_char_mapping(
    dictionary_path: Path | str,
    *,
    from_field: str,
    to_field: str,
) -> dict[int, str | None]:
    dictionary_path = Path(dictionary_path)
    mapping: dict[int, str | None] = {}

    with dictionary_path.open("r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            raise ValueError("CSV must contain header row.")
        if not {from_field, to_field}.issubset(reader.fieldnames):
            raise ValueError(f"CSV must contain columns: {from_field}, {to_field}")

        for row in reader:
            source_char = row.get(from_field) or ""
            target_char = row.get(to_field)

            if len(source_char) != 1:
                continue

            mapping[ord(source_char)] = None if not target_char else target_char

    return mapping


def map_characters(
    text: str,
    dictionary_path: Path | str,
    *,
    from_field: str,
    to_field: str,
) -> str:
    return text.translate(
        _load_char_mapping(
            dictionary_path,
            from_field=from_field,
            to_field=to_field,
        )
    )


def translate__mapping_char(
    text: str,
    dictionary_path: Path | str,
    *,
    from_field: str,
    to_field: str,
) -> str:
    return map_characters(
        text,
        dictionary_path,
        from_field=from_field,
        to_field=to_field,
    )


def preprocess_bopomofo_characters(text: str, dictionary_path: Path | str) -> str:
    return map_characters(
        text,
        dictionary_path,
        from_field="Bopomofo",
        to_field="Braille",
    )


def map_braille_to_ascii(text: str, dictionary_path: Path | str) -> str:
    return map_characters(
        text,
        dictionary_path,
        from_field="Braille",
        to_field="Ascii",
    )

