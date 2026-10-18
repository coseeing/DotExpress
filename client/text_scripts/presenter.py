"""Script-management workflow without wx (F-18).

``ScriptManagementPresenter`` owns the list of script names, the twin of
``dictionaries.presenter.DictionaryManagementPresenter``.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from text_scripts.manager import (
	ensure_no_processing_script,
	list_script_names,
	resolve_selected_script,
	script_path_for_name,
)


class ScriptManagementPresenter:
	"""The only owner of the script name list."""

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
		"""Read the folder again (No Processing is created if missing); the name to select."""
		ensure_no_processing_script(self._script_dir)
		self._script_names = list_script_names(self._script_dir)
		return resolve_selected_script(self._script_names, preferred_name)

	def script_path(self, name: str) -> Path:
		return script_path_for_name(name, self._script_dir)
