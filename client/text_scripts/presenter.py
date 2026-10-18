"""Script-management workflow without wx (F-18).

``ScriptManagementPresenter`` owns the list of script names and the add, edit, delete,
rename, import and export flows, the twin of
``dictionaries.presenter.DictionaryManagementPresenter``. It talks to the user only
through a ``ScriptManagementView`` (implemented by ``dialog.ScriptManagementDialog``)
and builds every user-facing string with ``_`` at call time.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Protocol, TypeVar

from conversion.preprocessing.user_script import (
	NO_PROCESSING_SCRIPT,
	NO_PROCESSING_SCRIPT_NAME,
	SCRIPT_SUFFIX,
	read_script_source,
	save_script,
)
from dictionaries.name_prompt import prompt_dictionary_name_until_success
from i18n import _
from text_scripts.manager import (
	ScriptImportSourceError,
	check_import_suffix,
	create_script,
	delete_script,
	ensure_no_processing_script,
	export_script,
	import_script,
	is_no_processing_script,
	list_script_names,
	normalize_script_name,
	rename_script,
	resolve_selected_script,
	script_exists,
	script_path_for_name,
)
from text_scripts.read_problems import describe_script_problem, describe_unreadable_script

SaveScript = Callable[[str], None]
_T = TypeVar("_T")


class ScriptManagementView(Protocol):
	def prompt_script_name(self, title: str, initial_name: str) -> str | None: ...

	def edit_script(self, title: str, source: str, save: SaveScript) -> None:
		"""Show the editor until it is closed; ``save`` raises ``OSError``, ``SyntaxError`` or ``ValueError``."""
		...

	def show_info(self, message: str) -> None: ...

	def show_error(self, message: str) -> None: ...

	def confirm(self, message: str, caption: str) -> bool: ...

	def choose_import_path(self, title: str) -> Path | None: ...

	def choose_export_path(self, title: str, default_file: str) -> Path | None: ...


class ScriptManagementActions(Protocol):
	@property
	def script_names(self) -> list[str]: ...

	def script_path(self, name: str) -> Path: ...

	def add(self, view: ScriptManagementView) -> str | None: ...

	def edit(self, view: ScriptManagementView, name: str) -> str | None: ...

	def delete(self, view: ScriptManagementView, name: str) -> str | None: ...

	def rename(self, view: ScriptManagementView, name: str) -> str | None: ...

	def import_from_file(self, view: ScriptManagementView) -> str | None: ...

	def export_to_file(self, view: ScriptManagementView, name: str) -> None: ...


class ScriptManagementPresenter:
	"""Satisfies ``ScriptManagementActions``; the only owner of the script name list.

	Each flow returns the name to select in the list afterwards, or ``None`` to leave the
	list as it is. Only Rename and Delete change the active script (F-18 D3).
	"""

	def __init__(
		self,
		script_dir: Path,
		*,
		get_active_name: Callable[[], str],
		set_active_name: Callable[[str], None],
	) -> None:
		self._script_dir = Path(script_dir)
		self._get_active_name = get_active_name
		self._set_active_name = set_active_name
		self._script_names: list[str] = []

	@property
	def script_dir(self) -> Path:
		return self._script_dir

	@property
	def script_names(self) -> list[str]:
		return list(self._script_names)

	def refresh(self, preferred_name: str | None = None) -> str:
		"""Read the folder again (No Processing is written again if missing or altered); the name to select."""
		ensure_no_processing_script(self._script_dir)
		self._script_names = list_script_names(self._script_dir)
		return resolve_selected_script(self._script_names, preferred_name)

	def script_path(self, name: str) -> Path:
		return script_path_for_name(name, self._script_dir)

	def add(self, view: ScriptManagementView) -> str | None:
		"""A name, then the editor with the template; nothing is written before a save (F-18 D8.1)."""
		try:
			name = self._prompt_name_until_success(view, _("Add Script"), "", self._new_name)
		except ValueError as exc:
			view.show_info(str(exc))
			return None
		if name is None:
			return None
		created = False

		def save(source: str) -> None:
			nonlocal created
			if created:
				save_script(self.script_path(name), source)
				return
			try:
				create_script(self._script_dir, name, source)
			except FileExistsError as error:
				# Another program wrote a file of that name while the editor was open.
				raise FileExistsError(_('Script "{name}" already exists.').format(name=name)) from error
			created = True

		view.edit_script(name, NO_PROCESSING_SCRIPT, save)
		if not created:
			return None
		self.refresh(name)
		return name

	def edit(self, view: ScriptManagementView, name: str) -> str | None:
		"""Read the file again and open the editor; an invalid script opens too (F-18 D8.2).

		A file that cannot be read is explained, not logged: the returned name makes the list
		read every script again, which logs it once (F-18 review M-3).
		"""
		if is_no_processing_script(name):
			return None
		path = self.script_path(name)
		try:
			source = read_script_source(path)
		except Exception as error:
			view.show_error(describe_unreadable_script(name, error))
			return name
		view.edit_script(name, source, lambda text: save_script(path, text))
		return name

	def delete(self, view: ScriptManagementView, name: str) -> str | None:
		if is_no_processing_script(name):
			return None
		if not view.confirm(
			_('Do you want to delete script "{name}"?').format(name=name),
			_("Confirm Delete Script"),
		):
			return None
		previous_names = list(self._script_names)
		active_name = self._get_active_name()
		try:
			delete_script(self._script_dir, name)
		except OSError as exc:
			view.show_error(_("Failed to delete script: {error}").format(error=exc))
			return None
		if active_name == name:
			# Not the neighbour, as for dictionaries: that would start running another script (F-18 O5).
			self._set_active_name(NO_PROCESSING_SCRIPT_NAME)
		index = previous_names.index(name) if name in previous_names else 0
		return self.refresh(previous_names[index - 1] if index > 0 else None)

	def rename(self, view: ScriptManagementView, name: str) -> str | None:
		if is_no_processing_script(name):
			return None
		try:
			path = self._prompt_name_until_success(view, _("Rename Script"), name, lambda new_name: self._rename(name, new_name))
		except ValueError as exc:
			view.show_info(str(exc))
			return None
		except OSError as exc:
			view.show_error(_("Failed to save script: {error}").format(error=exc))
			return None
		if path is None:
			return None
		if self._get_active_name() == name and path.stem != name:
			self._set_active_name(path.stem)
		return self.refresh(path.stem)

	def import_from_file(self, view: ScriptManagementView) -> str | None:
		source_path = view.choose_import_path(_("Import Script"))
		if source_path is None:
			return None
		try:
			# Refused before the name box; import_script checks it again (F-18 review M-2).
			check_import_suffix(source_path)
			path = self._prompt_name_until_success(
				view,
				_("Add Script"),
				source_path.stem,
				lambda script_name: import_script(self._script_dir, source_path, script_name),
			)
		except ScriptImportSourceError as exc:
			view.show_error(self._import_failed(exc.error))
			return None
		except (SyntaxError, ValueError) as exc:
			# Not UTF-8, a msgid of the signature rule or of the suffix check (F-18 D8.5).
			view.show_error(self._import_failed(exc))
			return None
		except OSError as exc:
			view.show_error(_("Failed to import script: {error}").format(error=exc))
			return None
		if path is None:
			return None
		return self.refresh(path.stem)

	def export_to_file(self, view: ScriptManagementView, name: str) -> None:
		if not self._script_names:
			return None
		destination_path = view.choose_export_path(_("Export Script"), f"{name}{SCRIPT_SUFFIX}")
		if destination_path is None:
			return None
		try:
			export_script(self._script_dir, name, destination_path)
		except OSError as exc:
			view.show_error(_("Failed to export script: {error}").format(error=exc))
		return None

	def _new_name(self, name: str) -> str:
		"""The name of a new script; ``FileExistsError`` asks for another one."""
		normalized = normalize_script_name(name)
		if script_exists(self._script_dir, normalized):
			raise FileExistsError(normalized)
		return normalized

	def _rename(self, name: str, new_name: str) -> Path:
		if name.strip() == new_name.strip():
			return self.script_path(name.strip())
		return rename_script(self._script_dir, name, new_name)

	@staticmethod
	def _import_failed(error: Exception) -> str:
		return _("Failed to import script: {error}").format(error=describe_script_problem(error))

	def _prompt_name_until_success(
		self,
		view: ScriptManagementView,
		title: str,
		initial_name: str,
		submit: Callable[[str], _T],
	) -> _T | None:
		return prompt_dictionary_name_until_success(
			initial_name,
			prompt_name=lambda current_name: view.prompt_script_name(title, current_name),
			on_submit=submit,
			on_duplicate=lambda script_name: view.show_error(
				_('Script "{name}" already exists.').format(name=script_name.strip())
			),
		)
