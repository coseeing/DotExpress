"""Whether a script can be used and, if not, why, in words the user can act on (F-18 D7).

The twin of ``dictionaries.read_problems``: an error reading the file is classified as a
dictionary's (F-6), with the plain-text advice for a file that is not UTF-8; a file that can
be read can still be not valid, when it does not compile or its ``main`` breaks the
signature rule (F-18 D5). Nothing here imports wx, and nothing runs the script.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from conversion.preprocessing.user_script import read_script_source, validate_script
from dictionaries.read_problems import DictionaryReadProblem, classify_dictionary_read_error
from i18n import _
from log import get_logger


class ScriptStatus(Enum):
	READY = "ready"
	UNREADABLE = "unreadable"
	NOT_VALID = "not_valid"


@dataclass(frozen=True)
class ScriptCheck:
	status: ScriptStatus = ScriptStatus.READY
	error: Exception | None = None  # None while the script is ready


def read_script_status(path: Path) -> ScriptCheck:
	"""Read and check the script at ``path``; an error reading it is logged, invalid code is not."""
	try:
		source = read_script_source(path)
	except Exception as error:
		log_script_read_error(path, error)
		return ScriptCheck(ScriptStatus.UNREADABLE, error)
	try:
		validate_script(source, filename=str(path))
	except Exception as error:
		# The user's code, not an error of DotExpress.
		return ScriptCheck(ScriptStatus.NOT_VALID, error)
	return ScriptCheck()


def describe_script_problem(error: Exception) -> str:
	"""Why the script cannot be used, as one or more full sentences."""
	problem = classify_dictionary_read_error(error)
	if problem is DictionaryReadProblem.NOT_UTF8:
		return _("The file is not saved as UTF-8 text. Save it again as UTF-8, for example with Save As in Notepad.")
	if isinstance(error, SyntaxError):
		return str(error)
	if isinstance(error, ValueError):
		# A msgid of the signature rule (F-18 D5).
		return _(str(error))
	if problem is DictionaryReadProblem.CANNOT_OPEN:
		return _(
			"The file cannot be opened. It may be in use by another program, or you may not have "
			"permission to read it. Close the other program and try again."
		)
	if isinstance(error, OSError):
		return _("The file cannot be read: {error}").format(error=error)
	return str(error)


def describe_unreadable_script(name: str, error: Exception) -> str:
	"""A headline naming the script, a blank line, then the reason."""
	headline = _('Script "{name}" cannot be read.').format(name=name)
	return f"{headline}\n\n{describe_script_problem(error)}"


def log_script_read_error(path: Path, error: Exception) -> None:
	"""One line for an error that comes from the file; a traceback for anything else."""
	# Bound here, not at import, as in dictionaries.read_problems (F-6 review M-6).
	logger = get_logger("dotexpress.gui", "gui.log")
	if isinstance(error, (UnicodeDecodeError, OSError)):
		logger.error('Cannot read script "%s": %s: %s', Path(path).name, type(error).__name__, error)
	else:
		logger.error('Unexpected error while reading script "%s"', Path(path).name, exc_info=error)
