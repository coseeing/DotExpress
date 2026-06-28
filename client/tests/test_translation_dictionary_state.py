import unittest

from translation.dictionary_state import (
	resolve_active_dictionary_after_add,
	resolve_active_dictionary_after_delete,
	resolve_active_dictionary_after_rename,
	resolve_management_selection,
)


class TranslationDictionaryStateTest(unittest.TestCase):
	def test_management_selection_uses_preferred_name_when_available(self) -> None:
		self.assertEqual(
			resolve_management_selection(["default", "math"], "math"),
			"math",
		)

	def test_management_selection_falls_back_when_preferred_missing(self) -> None:
		self.assertEqual(
			resolve_management_selection(["default", "math"], "missing"),
			"default",
		)

	def test_add_keeps_active_dictionary_unchanged(self) -> None:
		self.assertEqual(
			resolve_active_dictionary_after_add("default", ["default", "math"]),
			"default",
		)

	def test_rename_updates_active_dictionary_only_when_renamed_dictionary_was_active(self) -> None:
		self.assertEqual(
			resolve_active_dictionary_after_rename("math", "math", "science", ["default", "science"]),
			"science",
		)
		self.assertEqual(
			resolve_active_dictionary_after_rename("default", "math", "science", ["default", "science"]),
			"default",
		)

	def test_delete_keeps_active_dictionary_when_other_dictionary_is_removed(self) -> None:
		self.assertEqual(
			resolve_active_dictionary_after_delete("default", "math", ["default", "math", "science"]),
			"default",
		)

	def test_delete_falls_back_when_active_dictionary_is_removed(self) -> None:
		self.assertEqual(
			resolve_active_dictionary_after_delete("math", "math", ["default", "math", "science"]),
			"default",
		)


if __name__ == "__main__":
	unittest.main()
