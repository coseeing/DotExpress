"""The one definition of every settings option list (P2-3).

Each list is a tuple of frozen descriptors in the order the settings dialog
shows them. ``value`` is what config.json stores. ``label`` is a msgid marked
with ``N_``; whoever shows it translates it with ``_()``. Math table choices
are proper names, shown as is, and come from ``conversion.math_braille_codes``.

The persisted defaults (``DEFAULT_*``) stay in ``config``: ``config`` cannot
import this module, because importing ``settings.options`` runs
``settings/__init__``, which imports ``settings.translation``, which imports
from ``config`` (an import cycle). Tests check that every default is one of
the values here.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from conversion.math_braille_codes import MATH_BRAILLE_TABLES
from i18n import N_

RGB = tuple[int, int, int]


@dataclass(frozen=True)
class SettingOption:
    value: str
    """The value persisted in config.json."""
    label: str
    """The msgid shown for the value; translate it with ``_()`` when shown."""


@dataclass(frozen=True)
class ViewSchemeOption(SettingOption):
    background: RGB
    foreground: RGB


@dataclass(frozen=True)
class IntRange:
    minimum: int
    maximum: int

    def clamp(self, value: int) -> int:
        return max(self.minimum, min(self.maximum, value))


@dataclass(frozen=True)
class TranslationTableField:
    key: str
    """The key in the translation_tables setting."""
    label: str
    """The msgid of the row label."""
    file_prefix: str | None
    """Keep the tables whose lower-cased file name starts with it; None keeps every output table."""
    required: bool
    """No "None selected" entry, and a value must be chosen before Apply."""
    fixed_choices: tuple[str, ...] | None = None
    """Choices shown as is, untranslated, instead of the braille tables."""


OUTPUT_MODE_UNICODE = "unicode"
OUTPUT_MODE_ASCII = "ascii"
VIEW_SCHEME_LIGHT = "light"
VIEW_SCHEME_DARK = "dark"
BRAILLE_FONT_DEFAULT = "default"
BRAILLE_FONT_SIMBRAILLE = "simbraille"

OUTPUT_MODE_OPTIONS = (
    SettingOption(OUTPUT_MODE_UNICODE, N_("Unicode")),
    SettingOption(OUTPUT_MODE_ASCII, N_("ASCII")),
)
VIEW_SCHEME_OPTIONS = (
    ViewSchemeOption(VIEW_SCHEME_LIGHT, N_("Light"), (255, 255, 255), (0, 0, 0)),
    ViewSchemeOption(VIEW_SCHEME_DARK, N_("Dark"), (0, 0, 0), (255, 255, 255)),
)
BRAILLE_FONT_OPTIONS = (
    SettingOption(BRAILLE_FONT_DEFAULT, N_("Default")),
    SettingOption(BRAILLE_FONT_SIMBRAILLE, N_("SimBraille")),
)
CONVERSION_WIDTH_RANGE = IntRange(10, 200)
VIEW_FONT_SIZE_RANGE = IntRange(8, 48)
TRANSLATION_TABLE_FIELDS = (
    TranslationTableField("default", N_("Default Translation Table"), None, True),
    TranslationTableField("en", N_("English Translation Table"), "en", False),
    TranslationTableField("zh", N_("Chinese Translation Table"), "zh", False),
    TranslationTableField("ja", N_("Japanese Translation Table"), "ja", False),
    TranslationTableField("math", N_("Math Translation Table"), None, True, MATH_BRAILLE_TABLES),
)


def option_values(options: Sequence[SettingOption]) -> tuple[str, ...]:
    return tuple(option.value for option in options)


def normalize_option_value(options: Sequence[SettingOption], value: str, default: str) -> str:
    """Return ``value`` when it is one of the option values, else ``default``."""
    if value in option_values(options):
        return value
    return default


def option_index(options: Sequence[SettingOption], value: str) -> int:
    """Return the index of the first option with ``value``, or 0 when there is none."""
    for index, option in enumerate(options):
        if option.value == value:
            return index
    return 0


def option_value_at(options: Sequence[SettingOption], index: int) -> str:
    """Return the value at ``index``; the first option's value when ``index`` is out of range."""
    if index < 0 or index >= len(options):
        return options[0].value
    return options[index].value
