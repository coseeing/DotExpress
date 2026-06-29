from __future__ import annotations

from collections.abc import Callable
from typing import TypeVar

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
