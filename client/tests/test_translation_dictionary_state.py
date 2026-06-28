import unittest

from translation.dictionary_state import (
	DictionaryStateUpdate,
	plan_dictionary_state_after_add,
	plan_dictionary_state_after_delete,
	plan_dictionary_state_after_rename,
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

	def test_add_keeps_active_dictionary_unchanged_and_selects_added_dictionary_in_management(self) -> None:
		self.assertEqual(
			plan_dictionary_state_after_add("default", ["default", "math"], "math"),
			DictionaryStateUpdate(
				management_selected_name="math",
				active_selected_name="default",
			),
		)

	def test_rename_updates_active_dictionary_only_when_renamed_dictionary_was_active(self) -> None:
		self.assertEqual(
			plan_dictionary_state_after_rename("math", "math", "science", ["default", "science"]),
			DictionaryStateUpdate(
				management_selected_name="science",
				active_selected_name="science",
			),
		)
		self.assertEqual(
			plan_dictionary_state_after_rename("default", "math", "science", ["default", "science"]),
			DictionaryStateUpdate(
				management_selected_name="science",
				active_selected_name="default",
			),
		)

	def test_delete_keeps_active_dictionary_when_other_dictionary_is_removed(self) -> None:
		self.assertEqual(
			plan_dictionary_state_after_delete("default", "math", ["default", "math", "science"]),
			DictionaryStateUpdate(
				management_selected_name="default",
				active_selected_name="default",
			),
		)

	def test_delete_falls_back_when_active_dictionary_is_removed(self) -> None:
		self.assertEqual(
			plan_dictionary_state_after_delete("math", "math", ["default", "math", "science"]),
			DictionaryStateUpdate(
				management_selected_name="default",
				active_selected_name="default",
			),
		)


if __name__ == "__main__":
	unittest.main()
