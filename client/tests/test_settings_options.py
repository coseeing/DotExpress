"""Tests of the settings option source (``settings.options``, P2-3).

``settings.options`` is imported here at module level, outside any stub scope,
so the descriptor classes are the same objects for every test module.
"""

from __future__ import annotations

import ast
import dataclasses
import unittest
from pathlib import Path

import config
from conversion import math_braille_codes
from settings.options import (
    BRAILLE_FONT_DEFAULT,
    BRAILLE_FONT_OPTIONS,
    BRAILLE_FONT_SIMBRAILLE,
    CONVERSION_WIDTH_RANGE,
    OUTPUT_MODE_ASCII,
    OUTPUT_MODE_OPTIONS,
    OUTPUT_MODE_UNICODE,
    TRANSLATION_TABLE_FIELDS,
    VIEW_FONT_SIZE_RANGE,
    VIEW_SCHEME_DARK,
    VIEW_SCHEME_LIGHT,
    VIEW_SCHEME_OPTIONS,
    IntRange,
    SettingOption,
    TranslationTableField,
    ViewSchemeOption,
    normalize_option_value,
    option_index,
    option_value_at,
    option_values,
)

CLIENT_ROOT = Path(__file__).resolve().parents[1]


def _module_tree(relative_path: str) -> ast.Module:
    path = CLIENT_ROOT / relative_path
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


class OptionListsTest(unittest.TestCase):
    def test_output_modes(self) -> None:
        self.assertEqual((OUTPUT_MODE_UNICODE, OUTPUT_MODE_ASCII), ("unicode", "ascii"))
        self.assertEqual(
            OUTPUT_MODE_OPTIONS,
            (SettingOption("unicode", "Unicode"), SettingOption("ascii", "ASCII")),
        )

    def test_view_schemes_carry_their_editor_colours(self) -> None:
        self.assertEqual((VIEW_SCHEME_LIGHT, VIEW_SCHEME_DARK), ("light", "dark"))
        self.assertEqual(
            VIEW_SCHEME_OPTIONS,
            (
                ViewSchemeOption("light", "Light", (255, 255, 255), (0, 0, 0)),
                ViewSchemeOption("dark", "Dark", (0, 0, 0), (255, 255, 255)),
            ),
        )
        for option in VIEW_SCHEME_OPTIONS:
            self.assertIsInstance(option, SettingOption)

    def test_braille_fonts(self) -> None:
        self.assertEqual((BRAILLE_FONT_DEFAULT, BRAILLE_FONT_SIMBRAILLE), ("default", "simbraille"))
        self.assertEqual(
            BRAILLE_FONT_OPTIONS,
            (SettingOption("default", "Default"), SettingOption("simbraille", "SimBraille")),
        )

    def test_integer_ranges(self) -> None:
        self.assertEqual(CONVERSION_WIDTH_RANGE, IntRange(10, 200))
        self.assertEqual(VIEW_FONT_SIZE_RANGE, IntRange(8, 48))

    def test_translation_table_fields(self) -> None:
        self.assertEqual(
            TRANSLATION_TABLE_FIELDS,
            (
                TranslationTableField("default", "Default Translation Table", None, True),
                TranslationTableField("en", "English Translation Table", "en", False),
                TranslationTableField("zh", "Chinese Translation Table", "zh", False),
                TranslationTableField("ja", "Japanese Translation Table", "ja", False),
                TranslationTableField("math", "Math Translation Table", None, True, ("UEB", "Nemeth")),
            ),
        )

    def test_lists_are_tuples_of_frozen_descriptors(self) -> None:
        for options in (OUTPUT_MODE_OPTIONS, VIEW_SCHEME_OPTIONS, BRAILLE_FONT_OPTIONS, TRANSLATION_TABLE_FIELDS):
            with self.subTest(first=options[0]):
                self.assertIs(type(options), tuple)
                with self.assertRaises(dataclasses.FrozenInstanceError):
                    options[0].label = "changed"
        with self.assertRaises(dataclasses.FrozenInstanceError):
            CONVERSION_WIDTH_RANGE.minimum = 0
        self.assertEqual(len({*OUTPUT_MODE_OPTIONS, *VIEW_SCHEME_OPTIONS, *BRAILLE_FONT_OPTIONS}), 6)


class OptionHelpersTest(unittest.TestCase):
    def test_option_values_keep_the_visible_order(self) -> None:
        self.assertEqual(option_values(OUTPUT_MODE_OPTIONS), ("unicode", "ascii"))
        self.assertEqual(option_values(VIEW_SCHEME_OPTIONS), ("light", "dark"))
        self.assertEqual(option_values(BRAILLE_FONT_OPTIONS), ("default", "simbraille"))
        self.assertEqual(option_values(()), ())

    def test_normalize_keeps_members_and_replaces_anything_else_with_the_default(self) -> None:
        for value in ("default", "simbraille"):
            with self.subTest(value=value):
                self.assertEqual(normalize_option_value(BRAILLE_FONT_OPTIONS, value, "simbraille"), value)
        for value in ("", "SimBraille", "serif", None):
            with self.subTest(value=value):
                self.assertEqual(normalize_option_value(BRAILLE_FONT_OPTIONS, value, "simbraille"), "simbraille")
        self.assertEqual(normalize_option_value((), "light", "dark"), "dark")

    def test_option_index_finds_the_first_equal_value_or_zero(self) -> None:
        self.assertEqual(option_index(VIEW_SCHEME_OPTIONS, "light"), 0)
        self.assertEqual(option_index(VIEW_SCHEME_OPTIONS, "dark"), 1)
        for value in ("Dark", "", "sepia", None):
            with self.subTest(value=value):
                self.assertEqual(option_index(VIEW_SCHEME_OPTIONS, value), 0)
        repeated = (SettingOption("a", "A"), SettingOption("b", "B"), SettingOption("b", "B again"))
        self.assertEqual(option_index(repeated, "b"), 1)
        self.assertEqual(option_index((), "a"), 0)

    def test_option_value_at_maps_out_of_range_indexes_to_the_first_option(self) -> None:
        # KNOWN QUIRK (P2-3 spec, K1): the first option, not the config default.
        self.assertEqual(option_value_at(BRAILLE_FONT_OPTIONS, 0), "default")
        self.assertEqual(option_value_at(BRAILLE_FONT_OPTIONS, 1), "simbraille")
        for index in (-1, -2, 2, 99):
            with self.subTest(index=index):
                self.assertEqual(option_value_at(BRAILLE_FONT_OPTIONS, index), "default")

    def test_int_range_clamps_at_both_ends(self) -> None:
        cases = ((-5, 10), (9, 10), (10, 10), (40, 40), (200, 200), (201, 200))
        for value, expected in cases:
            with self.subTest(value=value):
                self.assertEqual(CONVERSION_WIDTH_RANGE.clamp(value), expected)
        self.assertEqual(IntRange(8, 48).clamp(7), 8)
        self.assertEqual(IntRange(8, 48).clamp(49), 48)


class ConfigDefaultsInvariantTest(unittest.TestCase):
    """The persisted defaults stay in config (P2-3 spec D3) and must be valid options."""

    def test_choice_defaults_are_option_values(self) -> None:
        self.assertIn(config.DEFAULT_OUTPUT_MODE, option_values(OUTPUT_MODE_OPTIONS))
        self.assertIn(config.DEFAULT_VIEW_SCHEME, option_values(VIEW_SCHEME_OPTIONS))
        self.assertIn(config.DEFAULT_BRAILLE_FONT, option_values(BRAILLE_FONT_OPTIONS))

    def test_integer_defaults_are_inside_their_ranges(self) -> None:
        self.assertEqual(CONVERSION_WIDTH_RANGE.clamp(config.DEFAULT_CONVERSION_WIDTH), config.DEFAULT_CONVERSION_WIDTH)
        self.assertEqual(VIEW_FONT_SIZE_RANGE.clamp(config.DEFAULT_VIEW_FONT_SIZE), config.DEFAULT_VIEW_FONT_SIZE)

    def test_table_fields_match_the_default_translation_tables(self) -> None:
        self.assertEqual(
            tuple(field.key for field in TRANSLATION_TABLE_FIELDS),
            tuple(config.DEFAULT_TRANSLATION_TABLES),
        )
        self.assertEqual({field.key for field in TRANSLATION_TABLE_FIELDS if field.required}, {"default", "math"})
        self.assertEqual([field.key for field in TRANSLATION_TABLE_FIELDS if field.fixed_choices is not None], ["math"])

    def test_math_choices_and_default_come_from_the_leaf_module(self) -> None:
        math_field = TRANSLATION_TABLE_FIELDS[-1]
        self.assertIs(math_field.fixed_choices, math_braille_codes.MATH_BRAILLE_TABLES)
        self.assertEqual(config.DEFAULT_TRANSLATION_TABLES["math"], math_braille_codes.DEFAULT_MATH_BRAILLE_TABLE)
        self.assertIn(math_braille_codes.DEFAULT_MATH_BRAILLE_TABLE, math_field.fixed_choices)

    def test_config_names_the_math_default_instead_of_repeating_it(self) -> None:
        tables = next(
            node.value
            for node in _module_tree("config.py").body
            if isinstance(node, ast.Assign)
            and [target.id for target in node.targets] == ["DEFAULT_TRANSLATION_TABLES"]
        )
        values = dict(zip((key.value for key in tables.keys), tables.values))
        self.assertIsInstance(values["math"], ast.Name)
        self.assertEqual(values["math"].id, "DEFAULT_MATH_BRAILLE_TABLE")


class OptionsModuleGuardTest(unittest.TestCase):
    ALLOWED_IMPORTS = {"__future__", "collections.abc", "dataclasses", "i18n", "conversion.math_braille_codes"}
    LABEL_CONSTRUCTORS = {"SettingOption", "ViewSchemeOption", "TranslationTableField"}

    def test_imports_only_n_and_the_math_leaf(self) -> None:
        tree = _module_tree("settings/options.py")
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                self.assertEqual(node.level, 0, "no relative (settings sibling) imports")
                imported.add(node.module)
                if node.module == "i18n":
                    self.assertEqual([alias.name for alias in node.names], ["N_"])
        self.assertEqual(imported, self.ALLOWED_IMPORTS)
        for root in ("wx", "gui", "dialog", "ui", "config", "braille", "settings"):
            self.assertFalse(any(name == root or name.startswith(root + ".") for name in imported), root)

    def test_never_translates(self) -> None:
        tree = _module_tree("settings/options.py")
        names = {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)}
        self.assertNotIn("_", names)

    def test_every_label_is_a_literal_n_marker(self) -> None:
        labels = []
        for node in ast.walk(_module_tree("settings/options.py")):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in self.LABEL_CONSTRUCTORS:
                label = node.args[1]
                self.assertIsInstance(label, ast.Call)
                self.assertEqual(label.func.id, "N_")
                self.assertIsInstance(label.args[0], ast.Constant)
                labels.append(label.args[0].value)
        expected = [
            option.label
            for options in (OUTPUT_MODE_OPTIONS, VIEW_SCHEME_OPTIONS, BRAILLE_FONT_OPTIONS, TRANSLATION_TABLE_FIELDS)
            for option in options
        ]
        self.assertEqual(sorted(labels), sorted(expected))
        self.assertEqual(len(labels), 11)


# Option values that only settings/options.py (and config's DEFAULT_*) may spell out.
# "default" is left out: it is also the default dictionary's name.
OPTION_VALUE_LITERALS = {"unicode", "ascii", "light", "dark", "simbraille", "UEB", "Nemeth"}


def _assigned_names(body: list[ast.stmt]) -> set[str]:
    names = set()
    for node in body:
        if isinstance(node, ast.Assign):
            targets = node.targets
        elif isinstance(node, ast.AnnAssign):
            targets = [node.target]
        else:
            continue
        names.update(target.id for target in targets if isinstance(target, ast.Name))
    return names


def _string_constants(tree: ast.AST) -> set[str]:
    return {node.value for node in ast.walk(tree) if isinstance(node, ast.Constant) and isinstance(node.value, str)}


class OptionSourceConsumerTest(unittest.TestCase):
    """The consumers keep no option list, range or option value of their own (P2-3 spec D9, AC6)."""

    def test_normalizers_define_no_option_lists_or_ranges(self) -> None:
        for relative_path, expected in (
            ("settings/translation.py", {"DEFAULT_TRANSLATION_SETTINGS"}),
            ("settings/view.py", set()),
        ):
            with self.subTest(module=relative_path):
                tree = _module_tree(relative_path)
                self.assertEqual(_assigned_names(tree.body), expected)
                self.assertEqual(_string_constants(tree) & OPTION_VALUE_LITERALS, set())

    def test_settings_panels_define_no_option_lists_or_option_values(self) -> None:
        tree = _module_tree("settings/dialogs.py")
        self.assertEqual(_assigned_names(tree.body), {"_DEAD_WINDOW_ERROR_TYPES", "CommitSettings"})
        tables_panel = next(
            node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "TranslationTablesPanel"
        )
        self.assertEqual(_assigned_names(tables_panel.body), {"title", "panel_description", "TABLE_FIELDS"})
        table_keys = {field.key for field in TRANSLATION_TABLE_FIELDS}
        self.assertEqual(_string_constants(tree) & (OPTION_VALUE_LITERALS | table_keys), set())


if __name__ == "__main__":
    unittest.main()
