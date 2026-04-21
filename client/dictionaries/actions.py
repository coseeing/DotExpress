from dataclasses import dataclass

from dictionaries.manager import (
	DEFAULT_DICTIONARY_NAME,
	choose_selection_after_delete,
	resolve_selected_dictionary,
)


@dataclass(frozen=True)
class DictionaryActionAvailability:
	edit: bool
	delete: bool
	rename: bool
	export: bool


def is_default_dictionary(name: str) -> bool:
	return name.casefold() == DEFAULT_DICTIONARY_NAME.casefold()


def get_action_availability(dictionary_names: list[str], selected_name: str) -> DictionaryActionAvailability:
	has_selection = bool(dictionary_names)
	can_modify = has_selection and not is_default_dictionary(selected_name)
	return DictionaryActionAvailability(
		edit=has_selection,
		delete=can_modify,
		rename=can_modify,
		export=has_selection,
	)


def resolve_dictionary_selection(names: list[str], preferred_name: str | None) -> str:
	return resolve_selected_dictionary(names, preferred_name)


def plan_dictionary_delete(names: list[str], selected_name: str) -> str:
	if is_default_dictionary(selected_name):
		raise ValueError("The default dictionary cannot be deleted.")
	return choose_selection_after_delete(names, selected_name)
