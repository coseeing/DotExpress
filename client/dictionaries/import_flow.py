from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from dictionaries.manager import import_dictionary

DictionaryNamePrompt = Callable[[str], str | None]


def import_dictionary_after_name_prompt(
    dictionary_dir: Path | None,
    source_path: Path | str,
    *,
    prompt_name: DictionaryNamePrompt,
) -> Path | None:
    source = Path(source_path)
    dictionary_name = prompt_name(source.stem)
    if dictionary_name is None:
        return None
    return import_dictionary(dictionary_dir, source, dictionary_name)
