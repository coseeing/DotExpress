"""Why a dictionary file cannot be read, in words the user can act on (F-6).

Nothing here imports wx. The reasons are built with ``_`` at call time; they never
mention an encoding by name, so a file in any encoding other than UTF-8 gets the
same advice (DotExpress does not guess encodings).
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from dictionaries.entries import load_dictionary_entries
from i18n import _
from log import get_logger

logger = get_logger("dotexpress.gui", "gui.log")


class DictionaryReadProblem(Enum):
	NOT_UTF8 = "not_utf8"
	# In use by another program, or no permission to read it: opening the file for
	# reading reports both as the same PermissionError on Windows.
	CANNOT_OPEN = "cannot_open"
	INVALID_CSV = "invalid_csv"
	OTHER = "other"


def classify_dictionary_read_error(error: Exception) -> DictionaryReadProblem:
	# UnicodeDecodeError first: it is also a ValueError.
	if isinstance(error, UnicodeDecodeError):
		return DictionaryReadProblem.NOT_UTF8
	if isinstance(error, PermissionError):
		return DictionaryReadProblem.CANNOT_OPEN
	if isinstance(error, csv.Error):
		return DictionaryReadProblem.INVALID_CSV
	return DictionaryReadProblem.OTHER


def describe_dictionary_read_error(error: Exception) -> str:
	"""The reason, as one or more full sentences."""
	problem = classify_dictionary_read_error(error)
	if problem is DictionaryReadProblem.NOT_UTF8:
		return _(
			'The file is not saved as UTF-8. Save it again in the "CSV UTF-8 (Comma delimited)" format, '
			"for example with Save As in Excel."
		)
	if problem is DictionaryReadProblem.CANNOT_OPEN:
		return _(
			"The file cannot be opened. It may be in use by another program, or you may not have "
			"permission to read it. Close the other program and try again."
		)
	if problem is DictionaryReadProblem.INVALID_CSV:
		return _(
			"The file is not a valid CSV file. Check for a quotation mark that is not closed. Details: {error}"
		).format(error=error)
	return _("The file cannot be read: {error}").format(error=error)


def describe_unreadable_dictionary(name: str, error: Exception) -> str:
	"""A headline naming the dictionary, a blank line, then the reason."""
	headline = _('Dictionary "{name}" cannot be read.').format(name=name)
	return f"{headline}\n\n{describe_dictionary_read_error(error)}"


def log_dictionary_read_error(path: Path, error: Exception) -> None:
	"""One line for an error that comes from the file; a traceback for anything else."""
	if isinstance(error, (UnicodeDecodeError, csv.Error, OSError)):
		logger.error('Cannot read dictionary "%s": %s: %s', Path(path).name, type(error).__name__, error)
	else:
		logger.error('Unexpected error while reading dictionary "%s"', Path(path).name, exc_info=error)


@dataclass(frozen=True)
class DictionaryCount:
	entries: int = 0
	error: Exception | None = None  # None: the file could be read


def read_dictionary_count(path: Path) -> DictionaryCount:
	"""The number of entries the editor shows, or why the file cannot be read (logged)."""
	try:
		return DictionaryCount(len(load_dictionary_entries(path)))
	except Exception as error:
		log_dictionary_read_error(path, error)
		return DictionaryCount(error=error)
