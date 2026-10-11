"""Dictionary-management workflow without wx.

``DictionaryManagementPresenter`` owns the list of dictionary names and the
add, delete, rename, import and export flows. It talks to the user only through
a ``DictionaryManagementView`` (implemented by ``dialog.DictionaryManagementDialog``)
and builds every user-facing string with ``_`` at call time.
"""

from __future__ import annotations

import csv
from collections.abc import Callable
from pathlib import Path
from typing import Protocol

from dictionaries.actions import is_default_dictionary
from dictionaries.manager import (
	DictionaryImportSourceError,
	create_dictionary,
	delete_dictionary,
	dictionary_path_for_name,
	ensure_default_dictionary,
	export_dictionary,
	import_dictionary,
	list_dictionary_names,
)
from dictionaries.name_prompt import prompt_dictionary_name_until_success, rename_dictionary_after_name_prompt
from dictionaries.read_problems import describe_dictionary_read_error
from i18n import _
from translation.dictionary_state import (
	plan_dictionary_state_after_add,
	plan_dictionary_state_after_delete,
	plan_dictionary_state_after_rename,
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

	def delete(self, view: DictionaryManagementView, name: str) -> str | None:
		if is_default_dictionary(name):
			view.show_info(_("The default dictionary cannot be deleted."))
			return None
		if not view.confirm(
			_('Do you want to delete dictionary "{name}"?').format(name=name),
			_("Confirm Delete Dictionary"),
		):
			return None

		previous_names = list(self._dictionary_names)
		active_name = self._get_active_name()
		try:
			delete_dictionary(self._dictionary_dir, name)
		except OSError as exc:
			view.show_error(_("Failed to delete dictionary: {error}").format(error=exc))
			return None
		self.refresh(name)
		update = plan_dictionary_state_after_delete(active_name, name, previous_names)
		if update.active_selected_name != active_name:
			self._set_active_name(update.active_selected_name)
		return update.management_selected_name

	def rename(self, view: DictionaryManagementView, name: str) -> str | None:
		if is_default_dictionary(name):
			return None
		try:
			path = self._prompt_name_until_success(
				view,
				_("Rename Dictionary"),
				name,
				lambda dictionary_name: rename_dictionary_after_name_prompt(
					self._dictionary_dir,
					name,
					dictionary_name,
				),
			)
		except ValueError as exc:
			view.show_info(str(exc))
			return None
		except OSError as exc:
			view.show_error(_("Failed to save dictionary: {error}").format(error=exc))
			return None
		if path is None:
			return None

		active_name = self._get_active_name()
		self.refresh(path.stem)
		update = plan_dictionary_state_after_rename(active_name, name, path.stem, self._dictionary_names)
		if update.active_selected_name != active_name:
			self._set_active_name(update.active_selected_name)
		return update.management_selected_name

	def import_from_file(self, view: DictionaryManagementView) -> str | None:
		source_path = view.choose_import_path(_("Import Dictionary"))
		if source_path is None:
			return None
		try:
			path = self._prompt_name_until_success(
				view,
				_("Add Dictionary"),
				source_path.stem,
				lambda dictionary_name: import_dictionary(self._dictionary_dir, source_path, dictionary_name),
			)
		except (UnicodeDecodeError, csv.Error) as exc:
			# F-6 (D9): before ValueError, which UnicodeDecodeError also is. Nothing was copied.
			view.show_error(_("Failed to import dictionary: {error}").format(error=describe_dictionary_read_error(exc)))
			return None
		except DictionaryImportSourceError as exc:
			# F-11 (D11): the source is held by another program or cannot be read; F-6's reason.
			view.show_error(_("Failed to import dictionary: {error}").format(error=describe_dictionary_read_error(exc.error)))
			return None
		except ValueError:
			view.show_error(_("Imported file must contain text, braille, and type headers."))
			return None
		except OSError as exc:
			view.show_error(_("Failed to import dictionary: {error}").format(error=exc))
			return None
		if path is None:
			return None
		return self._selection_after_add(path.stem)

	def export_to_file(self, view: DictionaryManagementView, name: str) -> None:
		if not self._dictionary_names:
			return None
		destination_path = view.choose_export_path(_("Export Dictionary"), f"{name}.csv")
		if destination_path is None:
			return None
		try:
			export_dictionary(self._dictionary_dir, name, destination_path)
		except OSError as exc:
			view.show_error(_("Failed to export dictionary: {error}").format(error=exc))
		return None

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
