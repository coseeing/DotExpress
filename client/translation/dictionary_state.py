from __future__ import annotations

from dictionaries.actions import plan_dictionary_delete, resolve_dictionary_selection


def resolve_management_selection(dictionary_names: list[str], preferred_name: str | None) -> str:
	return resolve_dictionary_selection(dictionary_names, preferred_name)


def resolve_active_dictionary_after_add(active_name: str, dictionary_names: list[str]) -> str:
	return resolve_dictionary_selection(dictionary_names, active_name)


def resolve_active_dictionary_after_rename(
	active_name: str,
	previous_name: str,
	new_name: str,
	dictionary_names: list[str],
) -> str:
	if active_name == previous_name:
		return resolve_dictionary_selection(dictionary_names, new_name)
	return resolve_dictionary_selection(dictionary_names, active_name)


def resolve_active_dictionary_after_delete(
	active_name: str,
	deleted_name: str,
	dictionary_names_before_delete: list[str],
) -> str:
	if active_name != deleted_name:
		return resolve_dictionary_selection(dictionary_names_before_delete, active_name)
	preferred_name = plan_dictionary_delete(dictionary_names_before_delete, deleted_name)
	remaining_names = [name for name in dictionary_names_before_delete if name != deleted_name]
	return resolve_dictionary_selection(remaining_names, preferred_name)
