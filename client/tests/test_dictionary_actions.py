import unittest

from dictionaries.actions import (
    DictionaryActionAvailability,
    get_action_availability,
    plan_dictionary_delete,
    resolve_dictionary_selection,
)
from dictionaries.manager import DEFAULT_DICTIONARY_NAME


class DictionaryActionsTest(unittest.TestCase):
    def test_get_action_availability_disables_selection_actions_when_empty(self) -> None:
        self.assertEqual(
            get_action_availability([], DEFAULT_DICTIONARY_NAME),
            DictionaryActionAvailability(edit=False, delete=False, rename=False, export=False),
        )

    def test_get_action_availability_protects_default_dictionary(self) -> None:
        self.assertEqual(
            get_action_availability([DEFAULT_DICTIONARY_NAME, "math"], DEFAULT_DICTIONARY_NAME),
            DictionaryActionAvailability(edit=True, delete=False, rename=False, export=True),
        )

    def test_get_action_availability_allows_mutable_dictionary_actions(self) -> None:
        self.assertEqual(
            get_action_availability([DEFAULT_DICTIONARY_NAME, "math"], "math"),
            DictionaryActionAvailability(edit=True, delete=True, rename=True, export=True),
        )

    def test_resolve_dictionary_selection_uses_saved_value_or_default(self) -> None:
        names = [DEFAULT_DICTIONARY_NAME, "math"]

        self.assertEqual(resolve_dictionary_selection(names, "math"), "math")
        self.assertEqual(resolve_dictionary_selection(names, "missing"), DEFAULT_DICTIONARY_NAME)

    def test_plan_dictionary_delete_rejects_default_dictionary(self) -> None:
        with self.assertRaises(ValueError):
            plan_dictionary_delete([DEFAULT_DICTIONARY_NAME, "math"], DEFAULT_DICTIONARY_NAME)

    def test_plan_dictionary_delete_returns_preferred_selection(self) -> None:
        self.assertEqual(
            plan_dictionary_delete([DEFAULT_DICTIONARY_NAME, "math", "zoo"], "math"),
            DEFAULT_DICTIONARY_NAME,
        )


if __name__ == "__main__":
    unittest.main()
