import unittest
from pathlib import Path
from unittest.mock import patch

from dictionaries.manager import DEFAULT_HEADER, create_dictionary, ensure_default_dictionary
from dictionaries.name_prompt import prompt_dictionary_name_until_success


class DictionaryNamePromptTest(unittest.TestCase):
	def test_reprompts_with_same_name_after_duplicate(self) -> None:
		prompts: list[str] = []
		duplicate_names: list[str] = []
		attempts = iter([
			"duplicate",
			"duplicate",
			"renamed",
		])

		def prompt_name(initial_name: str) -> str | None:
			prompts.append(initial_name)
			return next(attempts)

		def on_submit(dictionary_name: str) -> str:
			if dictionary_name == "duplicate":
				raise FileExistsError("exists")
			return f"saved:{dictionary_name}"

		def on_duplicate(dictionary_name: str) -> None:
			duplicate_names.append(dictionary_name)

		result = prompt_dictionary_name_until_success(
			"",
			prompt_name=prompt_name,
			on_submit=on_submit,
			on_duplicate=on_duplicate,
		)

		self.assertEqual(result, "saved:renamed")
		self.assertEqual(prompts, ["", "duplicate", "duplicate"])
		self.assertEqual(duplicate_names, ["duplicate", "duplicate"])

	def test_cancel_returns_none_without_submitting(self) -> None:
		prompts: list[str] = []
		submitted: list[str] = []

		def prompt_name(initial_name: str) -> str | None:
			prompts.append(initial_name)
			return None

		def on_submit(dictionary_name: str) -> str:
			submitted.append(dictionary_name)
			return f"saved:{dictionary_name}"

		result = prompt_dictionary_name_until_success(
			"prefill",
			prompt_name=prompt_name,
			on_submit=on_submit,
			on_duplicate=lambda _name: None,
		)

		self.assertIsNone(result)
		self.assertEqual(prompts, ["prefill"])
		self.assertEqual(submitted, [])

	def test_same_name_rename_is_a_no_op(self) -> None:
		from tempfile import TemporaryDirectory

		from dictionaries.name_prompt import rename_dictionary_after_name_prompt

		with TemporaryDirectory() as td:
			directory = Path(td)
			ensure_default_dictionary(directory)
			source_path = create_dictionary(directory, "alpha")
			source_path.write_text(",".join(DEFAULT_HEADER) + "\nterm,braille,General\n", encoding="utf-8")
			original_content = source_path.read_text(encoding="utf-8")

			result = rename_dictionary_after_name_prompt(directory, "alpha", "alpha")

			self.assertEqual(result, directory / "alpha.csv")
			self.assertTrue(result.exists())
			self.assertEqual(result.read_text(encoding="utf-8"), original_content)

	def test_case_only_rename_still_renames(self) -> None:
		from tempfile import TemporaryDirectory

		from dictionaries.name_prompt import rename_dictionary_after_name_prompt

		with TemporaryDirectory() as td:
			directory = Path(td)
			ensure_default_dictionary(directory)
			create_dictionary(directory, "alpha")

			result = rename_dictionary_after_name_prompt(directory, "alpha", "Alpha")

			self.assertEqual(result, directory / "Alpha.csv")
			self.assertTrue(result.exists())
			# F-W6, fixed by F-11 (D10). The listing, not exists(): on a case-insensitive file
			# system "alpha.csv" still exists after the rename, as the same file.
			self.assertEqual(sorted(path.name for path in directory.iterdir()), ["Alpha.csv", "default.csv"])

	def test_rename_onto_another_file_under_another_case_is_refused(self) -> None:
		# F-11 (D10): only the same file may be renamed under another case. On a case-sensitive
		# file system "Alpha.csv" can be another dictionary; os.path.samefile tells them apart.
		from tempfile import TemporaryDirectory

		from dictionaries.name_prompt import rename_dictionary_after_name_prompt

		with TemporaryDirectory() as td:
			directory = Path(td)
			ensure_default_dictionary(directory)
			source_path = create_dictionary(directory, "alpha")
			source_path.write_text(",".join(DEFAULT_HEADER) + "\nterm,braille,General\n", encoding="utf-8")
			if not (directory / "Alpha.csv").exists():
				create_dictionary(directory, "Alpha")
			original_content = source_path.read_bytes()

			with patch("os.path.samefile", return_value=False), self.assertRaises(FileExistsError):
				rename_dictionary_after_name_prompt(directory, "alpha", "Alpha")

			self.assertEqual(source_path.read_bytes(), original_content)


if __name__ == "__main__":
	unittest.main()
