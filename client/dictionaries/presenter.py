"""Dictionary-management workflow without wx.

``DictionaryManagementPresenter`` owns the list of dictionary names and the
add, delete, rename, import and export flows. It talks to the user only through
a ``DictionaryManagementView`` (implemented by ``dialog.DictionaryManagementDialog``)
and builds every user-facing string with ``_`` at call time.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Protocol

from dictionaries.manager import (
	create_dictionary,
	dictionary_path_for_name,
	ensure_default_dictionary,
	list_dictionary_names,
)
from dictionaries.name_prompt import prompt_dictionary_name_until_success
from i18n import _
from translation.dictionary_state import (
	plan_dictionary_state_after_add,
	resolve_management_selection,
)


class DictionaryManagementView(Protocol):
	def prompt_dictionary_name(self, title: str, initial_name: str) -> str | None: ...

	def show_info(self, message: str) -> None: ...

	def show_error(self, message: str) -> None: ...

	def confirm(self, message: str, caption: str) -> bool: ...

	def choose_import_path(self, title: str) -> Path | None: ...

	def choose_export_path(self, title: str, default_file: str) -> Path | None: ...


class DictionaryManagementActions(Protocol):
	@property
	def dictionary_names(self) -> list[str]: ...

	def dictionary_path(self, name: str) -> Path: ...

	def add(self, view: DictionaryManagementView) -> str | None: ...

	def delete(self, view: DictionaryManagementView, name: str) -> str | None: ...

	def rename(self, view: DictionaryManagementView, name: str) -> str | None: ...

	def import_from_file(self, view: DictionaryManagementView) -> str | None: ...

	def export_to_file(self, view: DictionaryManagementView, name: str) -> None: ...


class DictionaryManagementPresenter:
	"""Satisfies ``DictionaryManagementActions``; the only owner of the dictionary name list."""

	def __init__(
		self,
		dictionary_dir: Path,
		*,
		get_active_name: Callable[[], str],
		set_active_name: Callable[[str], None],
	) -> None:
		self._dictionary_dir = Path(dictionary_dir)
		self._get_active_name = get_active_name
		self._set_active_name = set_active_name
		self._dictionary_names: list[str] = []

	@property
	def dictionary_dir(self) -> Path:
		return self._dictionary_dir

	@property
	def dictionary_names(self) -> list[str]:
		return list(self._dictionary_names)

	def refresh(self, preferred_name: str | None = None) -> str:
		ensure_default_dictionary(self._dictionary_dir)
		self._dictionary_names = list_dictionary_names(self._dictionary_dir)
		return resolve_management_selection(self._dictionary_names, preferred_name)

	def dictionary_path(self, name: str) -> Path:
		return dictionary_path_for_name(name, self._dictionary_dir)

	def add(self, view: DictionaryManagementView) -> str | None:
		try:
			path = self._prompt_name_until_success(
				view,
				_("Add Dictionary"),
				"",
				lambda dictionary_name: create_dictionary(self._dictionary_dir, dictionary_name),
			)
		except ValueError as exc:
			view.show_info(str(exc))
			return None
		if path is None:
			return None
		return self._selection_after_add(path.stem)

	def _prompt_name_until_success(
		self,
		view: DictionaryManagementView,
		title: str,
		initial_name: str,
		submit: Callable[[str], Path],
	) -> Path | None:
		return prompt_dictionary_name_until_success(
			initial_name,
			prompt_name=lambda current_name: view.prompt_dictionary_name(title, current_name),
			on_submit=submit,
			on_duplicate=lambda dictionary_name: view.show_error(
				_('Dictionary "{name}" already exists.').format(name=dictionary_name.strip())
			),
		)

	def _selection_after_add(self, added_name: str) -> str:
		active_name = self._get_active_name()
		self.refresh(active_name)
		update = plan_dictionary_state_after_add(active_name, self._dictionary_names, added_name)
		return update.management_selected_name
