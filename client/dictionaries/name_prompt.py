from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import TypeVar

from dictionaries.manager import dictionary_path_for_name, rename_dictionary

DictionaryNamePrompt = Callable[[str], str | None]

T = TypeVar("T")


def prompt_dictionary_name_until_success(
	initial_name: str,
	*,
	prompt_name: DictionaryNamePrompt,
	on_submit: Callable[[str], T],
	on_duplicate: Callable[[str], None],
) -> T | None:
	current_name = initial_name
	while True:
		dictionary_name = prompt_name(current_name)
		if dictionary_name is None:
			return None
		try:
			return on_submit(dictionary_name)
		except FileExistsError:
			on_duplicate(dictionary_name)
			current_name = dictionary_name


def rename_dictionary_after_name_prompt(
	dictionary_dir: Path | None,
	source_name: str,
	new_name: str,
) -> Path:
	source_normalized = source_name.strip()
	new_normalized = new_name.strip()
	if source_normalized.casefold() == new_normalized.casefold():
		return dictionary_path_for_name(source_normalized, dictionary_dir)
	return rename_dictionary(dictionary_dir, source_normalized, new_normalized)
