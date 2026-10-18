"""What Script Management may do with the selected script, and how a script is named (F-18)."""

from dataclasses import dataclass

from i18n import _
from text_scripts.manager import NO_PROCESSING_DISPLAY_NAME, is_no_processing_script


@dataclass(frozen=True)
class ScriptActionAvailability:
	edit: bool
	delete: bool
	rename: bool
	export: bool


def get_script_action_availability(script_names: list[str], selected_name: str) -> ScriptActionAvailability:
	"""No Processing can only be exported; any other script can be edited, renamed, deleted and exported (F-18 D7)."""
	has_selection = bool(script_names)
	can_modify = has_selection and not is_no_processing_script(selected_name)
	return ScriptActionAvailability(
		edit=can_modify,
		delete=can_modify,
		rename=can_modify,
		export=has_selection,
	)


def script_display_name(name: str) -> str:
	"""「不處理」 for No Processing, else the name (F-18 D-D)."""
	return _(NO_PROCESSING_DISPLAY_NAME) if is_no_processing_script(name) else name
