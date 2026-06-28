from __future__ import annotations

from dataclasses import dataclass

from dictionaries.actions import plan_dictionary_delete, resolve_dictionary_selection


@dataclass(frozen=True)
class DictionaryStateUpdate:
	management_selected_name: str
	active_selected_name: str


def resolve_management_selection(dictionary_names: list[str], preferred_name: str | None) -> str:
	return resolve_dictionary_selection(dictionary_names, preferred_name)


def plan_dictionary_state_after_add(
	active_name: str,
	dictionary_names: list[str],
	added_name: str,
) -> DictionaryStateUpdate:
	return DictionaryStateUpdate(
		management_selected_name=resolve_management_selection(dictionary_names, added_name),
		active_selected_name=resolve_dictionary_selection(dictionary_names, active_name),
	)


def plan_dictionary_state_after_rename(
	active_name: str,
	previous_name: str,
	new_name: str,
	dictionary_names: list[str],
) -> DictionaryStateUpdate:
	next_active_name = new_name if active_name == previous_name else active_name
	return DictionaryStateUpdate(
		management_selected_name=resolve_management_selection(dictionary_names, new_name),
		active_selected_name=resolve_dictionary_selection(dictionary_names, next_active_name),
	)


def plan_dictionary_state_after_delete(
	active_name: str,
	deleted_name: str,
	dictionary_names_before_delete: list[str],
) -> DictionaryStateUpdate:
	remaining_names = [name for name in dictionary_names_before_delete if name != deleted_name]
	if active_name == deleted_name:
		next_active_name = plan_dictionary_delete(dictionary_names_before_delete, deleted_name)
	else:
		next_active_name = active_name
	return DictionaryStateUpdate(
		management_selected_name=resolve_management_selection(remaining_names, deleted_name),
		active_selected_name=resolve_dictionary_selection(remaining_names, next_active_name),
	)
