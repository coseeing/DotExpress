import ast
import csv
import sys
import tempfile
import unittest
from contextlib import nullcontext
from pathlib import Path
from unittest.mock import patch

from dictionaries import read_problems
from dictionaries.read_problems import (
	DictionaryCount,
	DictionaryReadProblem,
	classify_dictionary_read_error,
	describe_dictionary_read_error,
	describe_unreadable_dictionary,
	read_dictionary_count,
)
from tests.file_log_isolation import isolate_file_logs
from tests.unreadable_dictionary_files import (
	BIG5,
	FIELD_LIMIT,
	LATE_BIG5,
	READABLE,
	UTF16,
	big5_decode_error,
)
from tests.windows_file_handles import hold_open

LOGGER = "dotexpress.gui"
NOT_UTF8 = (
	'The file is not saved as UTF-8. Save it again in the "CSV UTF-8 (Comma delimited)" format, '
	"for example with Save As in Excel."
)
CANNOT_OPEN = (
	"The file cannot be opened. It may be in use by another program, or you may not have "
	"permission to read it. Close the other program and try again."
)
INVALID_CSV = "The file is not a valid CSV file. Check for a quotation mark that is not closed. Details: {error}"
OTHER = "The file cannot be read: {error}"


def setUpModule():
	unittest.addModuleCleanup(isolate_file_logs(LOGGER))


class DictionaryReadProblemTestCase(unittest.TestCase):
	def setUp(self):
		temp_dir = tempfile.TemporaryDirectory()
		self.addCleanup(temp_dir.cleanup)
		self.root = Path(temp_dir.name)

	def write(self, name, data):
		path = self.root / f"{name}.csv"
		path.write_bytes(data)
		return path


class DescribeTest(DictionaryReadProblemTestCase):
	def test_classifies_each_error(self):
		cases = (
			("Big5 file", big5_decode_error(), DictionaryReadProblem.NOT_UTF8),
			("in use or denied", PermissionError(13, "Permission denied"), DictionaryReadProblem.CANNOT_OPEN),
			("csv error", csv.Error("field larger than field limit (131072)"), DictionaryReadProblem.INVALID_CSV),
			("missing", FileNotFoundError(2, "No such file or directory"), DictionaryReadProblem.OTHER),
			("other OSError", OSError(22, "Invalid argument"), DictionaryReadProblem.OTHER),
			("other ValueError", ValueError("injected"), DictionaryReadProblem.OTHER),
			("anything else", RuntimeError("injected"), DictionaryReadProblem.OTHER),
		)
		for label, error, expected in cases:
			with self.subTest(label):
				self.assertIs(classify_dictionary_read_error(error), expected)

	def test_describes_each_problem(self):
		# Compared through the module's own _, so the test holds before and after the catalog step.
		csv_error = csv.Error("field larger than field limit (131072)")
		other_error = OSError(22, "Invalid argument")
		cases = (
			("not UTF-8", big5_decode_error(), read_problems._(NOT_UTF8)),
			("cannot open", PermissionError(13, "Permission denied"), read_problems._(CANNOT_OPEN)),
			("invalid CSV", csv_error, read_problems._(INVALID_CSV).format(error=csv_error)),
			("other", other_error, read_problems._(OTHER).format(error=other_error)),
		)
		for label, error, expected in cases:
			with self.subTest(label):
				self.assertEqual(describe_dictionary_read_error(error), expected)

	def test_unreadable_dictionary_message_has_headline_and_reason(self):
		error = big5_decode_error()

		message = describe_unreadable_dictionary("big5", error)

		headline = read_problems._('Dictionary "{name}" cannot be read.').format(name="big5")
		self.assertEqual(message, headline + "\n\n" + read_problems._(NOT_UTF8))


class ReadDictionaryCountTest(DictionaryReadProblemTestCase):
	def test_count_of_readable_and_missing_files(self):
		bopomofo_rows = (
			"text,braille,type\r\n"
			"Alpha,a,General\r\n"
			",b,General\r\n"
			"Beta,not bopomofo,Bopomofo\r\n"
		).encode("utf-8")
		cases = (
			("UTF-8", "plain", READABLE, 1),
			("UTF-8 with BOM", "bom", b"\xef\xbb\xbf" + READABLE, 1),
			("hidden rows are not counted (F-4)", "hidden", bopomofo_rows, 1),
			("missing file", "missing", None, 0),
		)
		for label, name, data, entries in cases:
			with self.subTest(label):
				path = self.write(name, data) if data is not None else self.root / f"{name}.csv"
				with self.assertNoLogs(LOGGER):
					count = read_dictionary_count(path)
				self.assertEqual(count, DictionaryCount(entries))
				self.assertIsNone(count.error)

	def test_count_of_unreadable_file_returns_the_error_and_logs_one_line(self):
		cases = (
			("Big5", BIG5, None, UnicodeDecodeError),
			("Big5 after 17 KB of ASCII rows", LATE_BIG5, None, UnicodeDecodeError),
			("UTF-16", UTF16, None, UnicodeDecodeError),
			("field over the CSV limit", FIELD_LIMIT, None, csv.Error),
			("in use or denied", READABLE, PermissionError(13, "Permission denied"), PermissionError),
			("other OSError", READABLE, OSError(22, "Invalid argument"), OSError),
		)
		for label, data, injected, error_type in cases:
			with self.subTest(label):
				path = self.write("broken", data)
				replaced = nullcontext() if injected is None else patch.object(read_problems, "load_dictionary_entries", side_effect=injected)
				with replaced, self.assertLogs(LOGGER, level="ERROR") as logs:
					count = read_dictionary_count(path)

				self.assertEqual(count.entries, 0)
				self.assertIs(type(count.error), error_type)
				self.assertEqual(
					[record.getMessage() for record in logs.records],
					[f'Cannot read dictionary "broken.csv": {error_type.__name__}: {count.error}'],
				)
				self.assertIsNone(logs.records[0].exc_info)

	def test_unexpected_error_is_logged_with_traceback(self):
		path = self.write("alpha", READABLE)
		error = RuntimeError("injected")

		with patch.object(read_problems, "load_dictionary_entries", side_effect=error):
			with self.assertLogs(LOGGER, level="ERROR") as logs:
				count = read_dictionary_count(path)

		self.assertEqual(count, DictionaryCount(error=error))
		self.assertEqual([record.getMessage() for record in logs.records], ['Unexpected error while reading dictionary "alpha.csv"'])
		self.assertIs(logs.records[0].exc_info[1], error)

	@unittest.skipUnless(sys.platform == "win32", "Windows file sharing")
	def test_file_held_open_without_sharing_cannot_be_opened(self):
		path = self.write("alpha", READABLE)
		hold_open(self, path, 0)

		with self.assertLogs(LOGGER, level="ERROR"):
			count = read_dictionary_count(path)

		self.assertIsInstance(count.error, PermissionError)
		self.assertIs(classify_dictionary_read_error(count.error), DictionaryReadProblem.CANNOT_OPEN)


class ReadProblemsModuleTest(unittest.TestCase):
	def test_module_does_not_import_wx(self):
		tree = ast.parse(Path(read_problems.__file__).read_text(encoding="utf-8"))
		imported = set()
		for node in ast.walk(tree):
			if isinstance(node, ast.Import):
				imported.update(alias.name.split(".")[0] for alias in node.names)
			elif isinstance(node, ast.ImportFrom) and node.module:
				imported.add(node.module.split(".")[0])

		self.assertNotIn("wx", imported)


if __name__ == "__main__":
	unittest.main()
