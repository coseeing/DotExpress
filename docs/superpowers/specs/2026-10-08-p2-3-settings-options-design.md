# Settings Option Source (P2-3) Design

## Goal

Give every settings option list one definition. Today the values, labels, order, ranges and table fields of the settings are written out separately in `settings/dialogs.py`, `settings/translation.py`, `settings/view.py` and `gui.py`, and the math table choices are hard-coded although `conversion/math_braille_codes.py` already defines them. This is roadmap task P2-3 in `storage/refactor.md` (section 6.3), covering finding O-3 and the `if key == "math"` dispatch named under P-4. It also settles two review follow-ups: whether to keep the `_(table.displayName)` call in `settings/dialogs.py` (P0 review M-5, P1 review P2 item 3), and what P2-3 does about the `__tables.py` localedir bug.

Concretely:

- New module `client/settings/options.py`. It imports only `N_` from `i18n` and `conversion.math_braille_codes`, and holds frozen option descriptors (value plus label msgid), the two integer ranges, the five translation-table fields, and four small lookup helpers.
- `settings/translation.py`, `settings/view.py`, `settings/dialogs.py` and `gui.py` read from it. Their own tuples (`SUPPORTED_OUTPUT_MODES`, `VIEW_SCHEME_KEYS`, `BRAILLE_FONT_KEYS`, `_OUTPUT_MODES`, `_VIEW_SCHEME_OPTIONS`, `_BRAILLE_FONT_OPTIONS`, `CHOICE_SPECS`), the min/max constants, the hard-coded `UEB`/`Nemeth` list and the `{"default", "math"}` sets are removed.
- Option labels become `N_()` msgids, translated with `_()` when the control is built. The msgids stay identical.
- Persisted defaults stay in `config.py`. New invariant tests check that they are among the option values.
- `_(table.displayName)` stays. It is what makes source runs show translated table names, and it has no effect in packaged runs (decision D6).

This refactor keeps behavior the same. Every choice label, choice order, selected index, saved value, normalization result, spin range and editor color stays the same in zh_TW and in an untranslated run. No msgid changes (353, same set). The golden fixtures `client/tests/fixtures/translation_golden.json` (sha256 `e67d95a1ae001d928b657f16468494d0e98beeea5a6425283090b34030211ccd`) and `client/tests/fixtures/dictionary_entries_trace.json` (sha256 `f493da52376c8eac32a50c33b7f11870451360bed4bf26c1db339ccd2c66c2cf`) do not change.

Corrected after planning: the plan `docs/superpowers/plans/2026-10-08-p2-3-settings-options.md` (section "Spec Corrections and Refinements") fixed two facts (step 3 must also move the dialog's two spins; `tests/test_settings_dialogs.py` runs 47 tests) and refined the test plan, the red step of steps 3-5, a few code choices and the test counts; those changes are folded in below.

## Current State (verified 2026-10-08 on `refactor/p2-3-settings-options`, HEAD `f16bfc8`, P0-*, P1-*, P2-1 and P2-2 merged)

Indentation: `settings/*.py`, `config.py`, `tests/test_settings_dialogs.py`, `tests/test_view_settings.py` and `tests/test_translation_settings.py` use 4 spaces. `gui.py` uses tabs.

Baseline: `cd client && $PY -m unittest discover -s tests` gives `Ran 973 tests`, `FAILED (failures=1, skipped=9)`. The failure is the P2-5 case `test_conversion_service ... test_translate_with_language_does_not_duplicate_existing_spaces_around_math`. The focused set `tests.test_settings_dialogs tests.test_translation_settings tests.test_view_settings tests.test_settings_state tests.test_translation_tables tests.test_math_braille_codes` runs 57 tests, all OK. Msgid scan (`$SP/p12/tools/msgid_scan.py client`) reports 353 source msgids. (`$PY` = `$SP/venv/bin/python`, `$SP` = the session scratchpad. The `.pot` still has 4 extra wildcard msgids that P1-2 removed; regenerating it is Windows debt and not part of this task.)

The line numbers in `storage/refactor.md` predate P0-P2-2. These are the current ones.

### Where each option list lives today

| Setting | Values (order = visible order) | Labels (msgid -> zh_TW) | Defined at | Re-derived at |
| --- | --- | --- | --- | --- |
| Output mode ("Braille Type") | `unicode`, `ascii` | "Unicode" -> Unicode, "ASCII" -> ASCII | `settings/dialogs.py:353-356` `_OUTPUT_MODES` (`_()` at import) | `settings/translation.py:20` `SUPPORTED_OUTPUT_MODES`; default `config.py:36` `DEFAULT_OUTPUT_MODE = "unicode"` |
| Width | 10..200 | - | `settings/translation.py:18-19` `MIN/MAX_CONVERSION_WIDTH` | clamp in `translation.py:43-44` and twice in `dialogs.py:394-397, 415-420`; default `config.py:37` = 40 |
| View scheme ("Scheme") | `light`, `dark` | "Light" -> 淺色, "Dark" -> 深色 | `settings/dialogs.py:358-361` `_VIEW_SCHEME_OPTIONS` | `settings/view.py:15` `VIEW_SCHEME_KEYS`; `gui.py:94-103` `VIEW_SCHEMES` (colors keyed by value); default `config.py:39` = `light` |
| Braille font | `default`, `simbraille` | "Default" -> 預設, "SimBraille" -> SimBraille | `settings/dialogs.py:363-366` `_BRAILLE_FONT_OPTIONS` | `settings/view.py:16` `BRAILLE_FONT_KEYS`; literal `"simbraille"` in `gui.py:385`; default `config.py:40` = `simbraille` |
| Font size | 8..48 | - | `settings/view.py:13-14` `VIEW_FONT_SIZE_MIN/MAX` | clamp in `view.py:28` and twice in `dialogs.py:605-608, 639-644`; default `config.py:38` = 12 |
| Translation table fields | `default`, `en`, `zh`, `ja`, `math` | "Default/English/Chinese/Japanese/Math Translation Table" -> 預設/英文/中文/日文/數學轉譯表 | `settings/dialogs.py:471-477` `CHOICE_SPECS` (key, label, file prefix) | `config.py:29-35` `DEFAULT_TRANSLATION_TABLES` (same keys, same order); `{"default", "math"}` at `dialogs.py:489` (no "None selected") and `:517` (required), literal keys in `is_valid` `:509-513` |
| Math table | `UEB`, `Nemeth` (shown as is, untranslated) | - | `settings/dialogs.py:571-577` `_options_for_key("math")` | `conversion/math_braille_codes.py:1-2` (P1-1 leaf; `config.py:8` re-exports); `config.py:34` `"math": "UEB"` literal |

### How the panels use them (`settings/dialogs.py`)

- `TranslationSettingsPanel` (369-462): `wx.Choice(choices=[label ...])` for output mode. `_selected_output_mode` returns `_OUTPUT_MODES[0][0]` for a selection `< 0` or past the end. `_select_output_mode` selects the index of the value, or 0 when the value is unknown. Width spin `min/max/initial` comes from the range, and `initial` and `load_snapshot` clamp by hand.
- `ViewSettingsPanel` (588-686): the same pattern twice (scheme, braille font) and the font-size spin. `on_save` normalizes through `normalize_view_settings`.
- `TranslationTablesPanel` (465-585): one row per `CHOICE_SPECS` entry, in order. Each row has a `StaticText(label)` and a `wx.Choice`. Options are built like this: for `math`, the fixed list `[UEB, Nemeth]` with `display_name == file_name`. Otherwise, `_load_table_options()` returns every `listTables()` table with `output` set, as `TableOption(fileName, _(displayName))`, sorted by `display_name.lower()`. A `None` prefix keeps all of them, and a prefix `p` keeps those whose `file_name.lower().startswith(p)`. Rows other than `default`/`math` get `TableOption("", _("None selected"))` prepended. A row with no options is disabled and gets `NOT_FOUND`. `_select_choice_value` selects the first option with an equal `file_name`, else index 0. `validation_error` returns `_("Please select a value for {field}.").format(field=label)` for the first empty required row. `on_save` writes all five keys.
- Labels are translated once, when `settings.dialogs` is imported (`_()` in module-level tuples and class attributes). `_` is the bound `gettext` of the zh_TW catalog loaded by `i18n` at import. The catalog never changes during a process.

### Normalization and persistence

- `settings/translation.py:37-58`: an unknown output mode becomes `DEFAULT_TRANSLATION_SETTINGS.output_mode` (= `config.DEFAULT_OUTPUT_MODE`), and the width is clamped.
- `settings/view.py:26-35`: font size is clamped, and an unknown scheme or braille font becomes the `config.DEFAULT_*` value.
- `config.py` getters return the stored value when it is a `str` (or a coercible `int`), else the default. They do no membership check. Translation tables are merged over `DEFAULT_TRANSLATION_TABLES` and are never checked against the choices (see quirk K3).
- `settings/state.py` (snapshot) holds no option knowledge and is not changed.

### `_(table.displayName)` and the `__tables.py` localedir (measured)

- `braille/tables/__tables.py` (NVDA-derived, must not be edited) builds its own catalog with `localedir = resource_path("locales")`. Its `resource_path` uses `Path(__file__).parent.parent` = `client/braille`. In a source run `client/braille/locales` does not exist, so `addTable` receives **English** display names. In a frozen run the base is `_MEIPASS`, so it receives **zh_TW** names.
- `settings/dialogs.py:582` then applies `_()` again. A script over all 198 `addTable` calls (196 with `output`) against the real catalog found: 0 untranslated names; 0 names where `_(_(name)) != _(name)`, so the second translation is idempotent; and the dialog's list (translated, then sorted by `.lower()`) is **identical** in both runs. Without the `_()`, a source run would show English names in a different order (first entries "Afrikaans grade 1"... instead of "世界文一級"...).
- `listTables()` sorts by `strxfrm(displayName)`, so its own order differs between runs. The only consumer is this panel, and it re-sorts. M-5 therefore has no visible effect anywhere.
- File-prefix counts among output tables: `en` 10, `zh` 6, `ja` 2.

### Tests touching this area

`tests/test_settings_dialogs.py` (39 test methods, 47 tests run: the 8 methods of the `_SingletonCharacterization` mixin run in both `TextProcessingSingletonTest` and `DotExpressSettingsSingletonTest`; `StubScope(settings_dialog_stubs(), isolate=("settings.dialogs",))`, stub `listTables() -> []`). Two of its tests assign `panel.CHOICE_SPECS` a list of 5 tuples, and several patch `settings.dialogs._` to identity. Also `tests/test_view_settings.py`, `tests/test_translation_settings.py`, `tests/test_settings_state.py`, `tests/test_translation_tables.py`, `tests/test_math_braille_codes.py`, `tests/test_config.py` (pins the `DEFAULT_*` values), and `tests/test_gui_document_flows.py` (`isolate=("gui", "settings.dialogs", "ui.dual_view")`; `_apply_editor_view_settings` is always mocked there, so the colors are untested). `tests/test_i18n.py` asserts that `settings/dialogs.py` imports exactly `{"_"}` from `i18n`, and that "Default", "SimBraille" and "Braille Font" stay extracted.

## Design

### Decision summary

- **D1 Descriptors, not dicts.** Each option is a frozen dataclass `SettingOption(value, label)`. `label` is the msgid. A list is a plain `tuple` in visible order. Immutable and hashable, with no behavior beyond lookup.
- **D2 Labels are msgids, translated at display time.** `options.py` marks labels with `N_()` and never calls `_()`. Consumers call `_(option.label)` where they build a control or a message. This follows the P1-2 pattern (`ui/action_menu.py`, `documents/formats.py`). Production output is the same, because the catalog is fixed for the life of the process. The difference shows only in tests that patch `settings.dialogs._` (see Risks). It keeps `options.py` free of any catalog state and keeps `settings/dialogs.py`'s `i18n` import at `{"_"}`.
- **D3 Defaults stay in `config.py`.** `config` cannot import `settings.options`: that runs `settings/__init__`, which imports `settings.translation`, which imports from the partly initialized `config` (an import cycle). `config` is also the documented owner of persisted defaults (`tests/test_config.py`). Duplication is prevented by invariant tests instead: each `config.DEFAULT_*` must be an option value or inside the range. Normalizers take the default as an argument.
- **D4 Math choices come from the leaf.** `options.py` imports `MATH_BRAILLE_TABLES` from `conversion.math_braille_codes`, not from `config`. The math field's `fixed_choices` **is** that tuple. `config.DEFAULT_TRANSLATION_TABLES["math"]` becomes `DEFAULT_MATH_BRAILLE_TABLE` (same value `"UEB"`). Math choices stay untranslated proper names, so they add no msgids.
- **D5 Table fields replace `CHOICE_SPECS` and the `"math"` dispatch.** A `TranslationTableField(key, label, file_prefix, required, fixed_choices)` row says everything the panel decides per key today. `required=True` means no "None selected" entry, and the field must be set before Apply. That matches the current two `{"default", "math"}` sets exactly. `fixed_choices` replaces `if key == "math"`. Building `TableOption` lists from `listTables()` stays in the dialog, because that is UI assembly over a vendored module.
- **D6 Keep `_(table.displayName)`.** It is not redundant: it is the first-party compensation for the `__tables.py` localedir, and it is idempotent for packaged runs (measured above). A comment at the call says so. A guard test re-checks idempotence over every `__tables.py` name against the real catalog, so a future catalog entry that collides fails loudly. P2-3 does not otherwise touch the M-5 bug: it has no visible effect, and fixing it needs an edit to `__tables.py` (forbidden) or a re-sort wrapper with no consumer. It is recorded as won't-fix-here (follow-up candidate for P2-7, which owns the braille glue).
- **D7 Out-of-range and unknown selection rules are kept exactly.** A selection index that is negative or past the end maps to the **first** option's value, not to the config default. An unknown value selects index 0. Both rules move into two helpers so the six copies collapse to one.
- **D8 Scheme colors live on the scheme descriptor.** `ViewSchemeOption(SettingOption)` adds `background` and `foreground` as RGB `tuple[int, int, int]`, so `options.py` stays wx-free. `gui.VIEW_SCHEMES` keeps its name and shape, built from the descriptors with `wx.Colour(*rgb)`. `_apply_editor_view_settings` is unchanged except that it uses the `BRAILLE_FONT_SIMBRAILLE` constant.
- **D9 Old names are removed, not aliased.** Grep shows `SUPPORTED_OUTPUT_MODES`, `VIEW_SCHEME_KEYS`, `BRAILLE_FONT_KEYS`, `MIN/MAX_CONVERSION_WIDTH` and `VIEW_FONT_SIZE_MIN/MAX` are used only by the modules being changed, and the dialog tuples are private. Keeping aliases would recreate a second source.

### `client/settings/options.py` (4 spaces)

Allowed imports: `__future__`, `collections.abc`, `dataclasses`, `i18n` (only `N_`), `conversion.math_braille_codes`. An AST guard in the new test forbids `wx`, `gui`, `dialog`, `ui`, `config`, `braille`, `settings` (sibling) and any `_` import or `_()` call.

```python
RGB = tuple[int, int, int]

@dataclass(frozen=True)
class SettingOption:
    value: str      # the value persisted in config.json
    label: str      # msgid (N_); translate with _() when shown

@dataclass(frozen=True)
class ViewSchemeOption(SettingOption):
    background: RGB
    foreground: RGB

@dataclass(frozen=True)
class IntRange:
    minimum: int
    maximum: int
    def clamp(self, value: int) -> int  # max(minimum, min(maximum, value))

@dataclass(frozen=True)
class TranslationTableField:
    key: str                                # translation_tables key
    label: str                              # msgid
    file_prefix: str | None                 # None: every output table
    required: bool                          # no "None selected"; must be chosen
    fixed_choices: tuple[str, ...] | None = None   # shown as is, untranslated

OUTPUT_MODE_UNICODE, OUTPUT_MODE_ASCII = "unicode", "ascii"
VIEW_SCHEME_LIGHT, VIEW_SCHEME_DARK = "light", "dark"
BRAILLE_FONT_DEFAULT, BRAILLE_FONT_SIMBRAILLE = "default", "simbraille"

OUTPUT_MODE_OPTIONS = (SettingOption(OUTPUT_MODE_UNICODE, N_("Unicode")),
                       SettingOption(OUTPUT_MODE_ASCII, N_("ASCII")))
VIEW_SCHEME_OPTIONS = (ViewSchemeOption(VIEW_SCHEME_LIGHT, N_("Light"), (255, 255, 255), (0, 0, 0)),
                       ViewSchemeOption(VIEW_SCHEME_DARK, N_("Dark"), (0, 0, 0), (255, 255, 255)))
BRAILLE_FONT_OPTIONS = (SettingOption(BRAILLE_FONT_DEFAULT, N_("Default")),
                        SettingOption(BRAILLE_FONT_SIMBRAILLE, N_("SimBraille")))
CONVERSION_WIDTH_RANGE = IntRange(10, 200)
VIEW_FONT_SIZE_RANGE = IntRange(8, 48)
TRANSLATION_TABLE_FIELDS = (
    TranslationTableField("default", N_("Default Translation Table"), None, True),
    TranslationTableField("en", N_("English Translation Table"), "en", False),
    TranslationTableField("zh", N_("Chinese Translation Table"), "zh", False),
    TranslationTableField("ja", N_("Japanese Translation Table"), "ja", False),
    TranslationTableField("math", N_("Math Translation Table"), None, True, MATH_BRAILLE_TABLES),
)

def option_values(options) -> tuple[str, ...]
def normalize_option_value(options, value, default: str) -> str   # value if a member, else default
def option_index(options, value) -> int                           # first equal value's index, else 0
def option_value_at(options, index: int) -> str                   # options[index].value; options[0].value if index < 0 or >= len
```

The msgids are written literally inside `N_()` so `xgettext --keyword=N_` (already in `scripts/generate-pot.bat`) and the msgid scan extract them. Importing `settings.options` runs `settings/__init__` (and therefore `config`), exactly as importing any settings module does today. `options.py` adds no import of its own beyond the list above. Importing `settings.translation` or `settings.view` now also imports `i18n` (through `options.py`); `i18n` has no side effect beyond loading the bundled catalog, which every GUI process loads anyway.

Small code choices: each field is documented with an attribute docstring, and the module docstring records the D3 import-cycle reason. `option_value_at` keeps the old `index < 0 or index >= len` test; `normalize_option_value` uses `in option_values(options)` (tuple membership, as before); `IntRange.clamp` is the old `max(minimum, min(maximum, value))`.

### Consumers after the change

- `settings/translation.py`: `_normalize_output_mode` -> `normalize_option_value(OUTPUT_MODE_OPTIONS, value, DEFAULT_TRANSLATION_SETTINGS.output_mode)`. `_normalize_width` -> `CONVERSION_WIDTH_RANGE.clamp`. `MIN/MAX_CONVERSION_WIDTH` and `SUPPORTED_OUTPUT_MODES` are removed. Because `settings/dialogs.py` imports the width and font-size constants from `.translation` and `.view`, the same step also switches the dialog's two spins (`min`/`max`/`initial` and both `load_snapshot` clamps, 4 sites) and their imports to `CONVERSION_WIDTH_RANGE`/`VIEW_FONT_SIZE_RANGE`; otherwise `import settings.dialogs` (and with it `gui`) would fail.
- `settings/view.py`: the same with `VIEW_FONT_SIZE_RANGE`, `VIEW_SCHEME_OPTIONS`, `BRAILLE_FONT_OPTIONS` and `config.DEFAULT_*`. The four constants are removed.
- `settings/dialogs.py`: the three option tuples and `CHOICE_SPECS` are removed. Choices are built with `[_(o.label) for o in ...]`. The six `_selected_*`/`_select_*` bodies use `option_value_at`/`option_index`, and the spins use `range.minimum/maximum/clamp` (done in step 3, see above). `TranslationTablesPanel` iterates `TRANSLATION_TABLE_FIELDS` through a class attribute `TABLE_FIELDS = TRANSLATION_TABLE_FIELDS` (tests may override it). Each row's `StaticText` label and the validation message use `_(field.label)`. "None selected" is prepended when `not field.required`. `is_valid`/`validation_error` loop over the required fields in field order (`is_valid` becomes `all(... for field in TABLE_FIELDS if field.required)`: same calls, same short-circuit as `default and math`). `_options_for_key` becomes `_options_for_field(field)`: `fixed_choices` -> `TableOption(v, v)`, else `_options_for_lang(field.file_prefix)` (kept). `_load_table_options`, the `TableOption` dataclass, `_("None selected")`, and `_(table.displayName)` (with a new comment above that list, D6) stay in the dialog.
- `gui.py`: `VIEW_SCHEMES` is built from `VIEW_SCHEME_OPTIONS` (same keys, `{"background": wx.Colour(*bg), "foreground": wx.Colour(*fg)}`). `settings.braille_font == BRAILLE_FONT_SIMBRAILLE`.
- `config.py`: `"math": DEFAULT_MATH_BRAILLE_TABLE` in `DEFAULT_TRANSLATION_TABLES`. Nothing else changes, and `config` imports nothing new.
- Not changed: `settings/state.py`, `settings/translation_tables.py`, `conversion/*` (including `output.py:85` `== "ascii"` and `text/pipeline.py:71` `{"default", "math"}`; see Out of Scope), `main.py`, `dual_view/*`, `braille/*`, `locales/*`, `scripts/*`.

## What Stays Identical

Visible order and labels of every choice (zh_TW: Braille Type `Unicode, ASCII`; Scheme `淺色, 深色`; Braille Font `預設, SimBraille`; table rows `預設轉譯表, 英文轉譯表, 中文轉譯表, 日文轉譯表, 數學轉譯表`; math `UEB, Nemeth`; "未選擇" first in the en/zh/ja rows), the selected index for every stored value, the value saved for every index (including -1 and past-the-end), spin min/max/initial, normalization results, the validation message and focus target, the editor colors, the SimBraille face rule, the saved `config.json` bytes, the msgid set, and the sorted table display names in both source and packaged runs.

## Test Plan

Characterization uses the **real** zh_TW catalog and never patches `settings.dialogs._` (or `gui._`). Under the old code such a patch would leave option labels translated, because they were translated at import time. Under the new code the same patch would show English labels. A test with the patch would therefore record that implementation detail rather than what users see. Where an untranslated label is needed, assert against the msgid and against `i18n._(msgid)`.

### A. Characterization on current code (step 1)

Part A spells values out literally (`"unicode"`, `"淺色"`, `(10, 200)`, ...) plus `i18n._(msgid)` and `config.DEFAULT_*`, never the old tuples, so it is never edited after step 1. Where it lives: items 1-3 and 6 in `tests/test_settings_dialogs.py` (`TranslationPanelOptionsTest`, `ViewPanelOptionsTest`, `TranslationTablesPanelOptionsTest`, `TableDisplayNameGuardTest`); item 4 in `tests/test_translation_settings.py` (`TranslationSettingsNormalizeTest`) and `tests/test_view_settings.py` (`ViewSettingsNormalizeTest`); item 5 in `tests/test_gui_document_flows.py` (`EditorViewSettingsCharacterizationTest`), the only module with the gui stub scope. Part A passes by construction on today's code, so a throwaway mutant runner (not committed) applies 20 one-edit breakages to a copy of `client/` (untranslated output labels, swapped scheme order, unknown value selecting the last option, unset braille font saving the config default, past-the-end scheme raising, width spin max off by one, width reload or font-size initial not clamped, "None selected" also for math, table rows reordered, math choices reversed, table names not re-translated, empty row left enabled, unknown table selecting the last option, math validated first, math dropped from save, width not clamped below, unknown scheme becoming dark, dark foreground off by one, SimBraille face only when registered) and shows each one makes part A fail.

How the panels are observed: the real panel class from `sys.modules["settings.dialogs"]` is built with a `SimpleNamespace` owner, `patch.multiple(module.wx, Choice=RecordingChoice, SpinCtrl=RecordingSpin)` and `patch.object(module, "listTables", ...)`. Rows are read from the layout: the stub `FlexGridSizer` records every `Add`, so the (label, control) pairs come out in order, and the validation focus target is compared with the row's control. Only the public attributes `output_choice`, `width_spin`, `dictionary_choice`, `scheme_choice`, `braille_font_choice`, `font_size_spin` are used (to set a selection); private fields and the field list are never read.

1. Translation panel built for real under the settings stub scope, with the recording `wx.Choice`/`wx.SpinCtrl` above. Assert: output choices `["Unicode", "ASCII"]` (and `== [i18n._("Unicode"), i18n._("ASCII")]`), the initial selection for `unicode`/`ascii`/an unknown value (0/1/0), `on_save` values for selection 0, 1, -1 and 2 (`unicode`, `ascii`, `unicode`, `unicode`), and the width spin min/max/initial for widths 5, 40 and 500.
2. View panel: scheme choices `["淺色", "深色"]`, braille font choices `["預設", "SimBraille"]`, selection for each value and for unknown values. `on_save` maps selection -1 to `light`/`default` (pinned K1: not `simbraille`). Font spin min/max/initial clamped.
3. Tables panel with a stub `listTables` returning fake `BrailleTable`-like objects: some with English names (the source-run path), one already in zh_TW (the packaged path), one with `output=False`, and file names covering the `en`/`zh`/`ja` prefixes, an upper-case file name (`en-GB-g2.ctb`), a `zhcn` prefix (K4) and a non-matching one. Assert: row labels and order, each row's display list (sorted, "未選擇" first only for en/zh/ja, math exactly `UEB, Nemeth`), the English and zh names producing the same zh label, a row with no options being disabled at `NOT_FOUND`, an unknown stored file name selecting index 0 (pinned K2), `on_save` keys and order, and the validation message plus focus for an empty `default`, then for an empty `math`.
4. Normalizers: every value of each list round-trips, unknown values become the `config.DEFAULT_*`, and clamps at both ends.
5. gui scheme colors: `gui.VIEW_SCHEMES` under the gui scope equals `{"light": {background (255,255,255), foreground (0,0,0)}, "dark": inverse}` (the stub `wx.Colour` is a tuple). Because step 5 edits `_apply_editor_view_settings` and the existing tests always mock it, it is characterized too: the font size on both editors, the colours and their call order, the SimBraille face for a registered font / `win32` / neither, and normalization of unknown values.
6. Table display-name guard (kept permanently): AST-parse `braille/tables/__tables.py` without importing it. For every `addTable` name, assert `i18n._(i18n._(name)) == i18n._(name)`, and that the sorted translated list of output tables is the same whether built from English or from translated names.

### B. Options module (step 2; new `tests/test_settings_options.py`, 4 spaces, no wx, no stub scope)

Exact values, msgids and order of each tuple. Descriptors are frozen and the tuples are tuples. Helper behavior (members, unknown, -1, past the end, and the empty option tuple: `option_values(()) == ()`, `option_index((), v) == 0`, `normalize_option_value((), v, d) == d`; the `None` file prefix is covered by part A's default row). `IntRange.clamp`. Invariants: each `config.DEFAULT_OUTPUT_MODE/VIEW_SCHEME/BRAILLE_FONT` is in the corresponding values; `DEFAULT_VIEW_FONT_SIZE`/`DEFAULT_CONVERSION_WIDTH` are inside their range; `tuple(f.key for f in TRANSLATION_TABLE_FIELDS) == tuple(config.DEFAULT_TRANSLATION_TABLES)`; the math field's `fixed_choices is math_braille_codes.MATH_BRAILLE_TABLES`; `config.DEFAULT_TRANSLATION_TABLES["math"] == DEFAULT_MATH_BRAILLE_TABLE`, and an AST check that config spells it as the name `DEFAULT_MATH_BRAILLE_TABLE` (this makes step 2's config switch red first); the required keys are exactly `{"default", "math"}`. Also the AST guard (imports, no `_`), and every label being a literal `N_()` argument. 19 tests in four classes: `OptionListsTest` (6), `OptionHelpersTest` (5), `ConfigDefaultsInvariantTest` (5), `OptionsModuleGuardTest` (3). The module imports `settings.options` at top level, outside any stub scope, so descriptor class identity is stable across scopes. `tests/test_i18n.py` gains `test_settings_options_uses_shared_i18n` (`{"N_"}`), and the `settings/dialogs.py` expectation stays `{"_"}`.

### C. Migration (steps 3-5)

Part A passes unchanged after every step. The only edit to existing tests: the two tests that assign `panel.CHOICE_SPECS` drop that assignment in step 4 (the class default is the same five fields). Part A has no invariant test to switch (the invariants live in part B).

Red step of steps 3-5: each step first appends one guard to `OptionSourceConsumerTest` in `tests/test_settings_options.py` and runs it red. Step 3 (`test_normalizers_define_no_option_lists_or_ranges`): the module-level assignments of `settings/translation.py` are only `DEFAULT_TRANSLATION_SETTINGS` and those of `settings/view.py` are none. Step 4 (`test_settings_panels_define_no_option_lists_or_option_values`): those of `settings/dialogs.py` are only `_DEAD_WINDOW_ERROR_TYPES` and `CommitSettings`, and the class body of `TranslationTablesPanel` assigns only `title`, `panel_description`, `TABLE_FIELDS`. Step 5 (`test_gui_spells_out_no_option_values`) checks only the literals in `gui.py`. All three check that no string literal among the option values (`unicode ascii light dark simbraille UEB Nemeth`, plus the table keys for the dialog) is in the migrated module. The guards are allow-lists, so they never spell a removed name and AC6's first grep (which also covers `client/tests`) stays empty. `"default"` is not checked in `translation.py`, where it is the default dictionary's name.

## Migration Steps (each step one green commit)

1. `test: characterize settings option lists` (part A on the current code).
2. `refactor: add settings option source` (part B. The module is not used yet, except that `config.DEFAULT_TRANSLATION_TABLES["math"]` switches to `DEFAULT_MATH_BRAILLE_TABLE`, a value-identical change).
3. `refactor: normalize settings through option source` (`settings/translation.py`, `settings/view.py`; old constants removed; also the dialog's width and font-size spins and their imports, which use the removed constants; one guard).
4. `refactor: build settings panels from option source` (`settings/dialogs.py`; `CHOICE_SPECS` and `_options_for_key` dispatch removed; D6 comment; the two test edits; one guard).
5. `refactor: derive gui view schemes from option source` (`gui.py`; one guard).

## Acceptance Criteria

1. Roadmap verification on Linux: `cd client && $PY -m unittest tests.test_settings_dialogs tests.test_translation_settings tests.test_view_settings tests.test_settings_options -v` passes (99 tests).
2. Also green: `tests.test_settings_state tests.test_translation_tables tests.test_math_braille_codes tests.test_config tests.test_gui_document_flows tests.test_i18n tests.test_wx_stub tests.test_removed_dead_code tests.test_translation_golden tests.test_dictionary_entries_dialog`.
3. Full suite: 973 + 50 = 1023 tests (step 1: 27, step 2: 20, steps 3-5: 1 each), `failures=1` (P2-5 only), `errors=0`, `skipped=9`. Shuffle harness (`$SP/shuffle_harness.py`) seeds 0-19 give the same single failure for every seed. `test_settings_options`, `test_settings_dialogs` and `test_gui_document_flows` pass alone and in both orders of each pair with `test_settings_options`.
4. Both fixture sha256 values above are unchanged, and `git diff main -- client/tests/fixtures` is empty.
5. Msgid scan: 353, and `--compare` against a list saved from `main` reports `SOURCE == SAVED`. `git diff main --stat -- client/locales scripts client/braille client/conversion client/dual_view client/main.py` is empty.
6. `grep -rnE "SUPPORTED_OUTPUT_MODES|VIEW_SCHEME_KEYS|BRAILLE_FONT_KEYS|_OUTPUT_MODES|_VIEW_SCHEME_OPTIONS|_BRAILLE_FONT_OPTIONS|CHOICE_SPECS|_options_for_key|MIN_CONVERSION_WIDTH|MAX_CONVERSION_WIDTH|VIEW_FONT_SIZE_MIN|VIEW_FONT_SIZE_MAX" client --include=*.py` prints nothing. `grep -rnE '"(unicode|ascii|light|dark|simbraille|UEB|Nemeth)"' client --include=*.py --exclude-dir=tests` prints only `settings/options.py`, `config.py` (`DEFAULT_OUTPUT_MODE`, `DEFAULT_VIEW_SCHEME`, `DEFAULT_BRAILLE_FONT`), `conversion/math_braille_codes.py`, `conversion/output.py` (2), `conversion/presenter.py` (1) and `main.py` (1). In a working tree that has the git-ignored `client/.venv`, both greps need `--exclude-dir=.venv`, or they also list third-party packages.
7. `client/settings/options.py` passes the AST guard, and `tests.test_i18n` passes with the new consumer test.

## Risks

- **Translation timing (D2).** The labels are the same in production, but `patch("settings.dialogs._", identity)` now also turns option and table-field labels into English. The existing tests that use the patch assert only the validation message, which already used the English field label under the patch because the tests injected English `CHOICE_SPECS`. Part A avoids the patch altogether.
- **Import cycle (D3).** Any later move of the defaults into `options.py` with `config` importing it would deadlock at import. A short comment in `options.py` records why the defaults are not there.
- **Stub-scope class identity.** Frozen dataclass `__eq__` requires the same class. Both stub scopes that load `settings.dialogs` use `evict_nothing`, and the new test imports `settings.options` before any scope. Covered by the order pairs and the shuffles.
- **Behavior hidden in helpers (D7).** "Past the end -> first option" and "unknown -> index 0" are easy to "fix" into "-> default". Part A pins them through the panels, and part B pins the helpers.
- **xgettext source references.** Regenerating the `.pot` on Windows moves the `#:` references for these msgids to `settings/options.py`. The msgids are unchanged, so no `.po` edit or `.mo` rebuild is needed.
- **PyInstaller.** `settings/options.py` is reached through static imports from `settings/dialogs.py`, `settings/translation.py`, `settings/view.py` and `gui.py` (read, not run).
- **Real wx.** Everything here is checked with stubs only.

## Known quirks kept (pinned, not fixed)

1. **K1** With no selection (-1) or a selection past the end, the Translation and View panels save the **first** option (`unicode`, `light`, `default`), not the config default (for the braille font, `simbraille`). This cannot happen in practice, because `_select_*` always selects an index.
2. **K2** A stored table file name that is not among the row's options silently selects index 0, and Apply/OK then saves that option. For the `default` row this is the alphabetically first translated table, and for en/zh/ja it is "None selected". For `math` it is `UEB`.
3. **K3** Translation tables are never normalized on load. Any string is accepted, and a math value outside `MATH_BRAILLE_TABLES` reaches conversion, where `conversion/mathcat_adapter.py` falls back to `UEB`.
4. **K4** Prefix filtering is a plain `startswith` on the lower-cased file name (for example, `zh` also matches every `zh-*`/`zhcn*` table).

Pinning tests are marked `# KNOWN QUIRK (P2-3 spec, Kn)`: K1 `ViewPanelOptionsTest.test_save_maps_out_of_range_selections_to_the_first_option` and `OptionHelpersTest.test_option_value_at_maps_out_of_range_indexes_to_the_first_option`; K2 `TranslationTablesPanelOptionsTest.test_unknown_or_missing_file_names_select_the_first_option`; K4 `TranslationTablesPanelOptionsTest.test_each_row_lists_its_tables_sorted_by_translated_name`. K3 has no panel-visible effect beyond K2 and is left to the existing `test_translation_tables`.

## Windows verification debt

- Packaged build, zh_TW, with NVDA: open Settings on each of the three panels and compare a screenshot and the spoken choice lists with `main` (labels, order, initial selection). Switch Scheme and Braille Font and check the editor colors and the SimBraille face. Leave en/zh/ja on "None selected", then Apply. An empty Default row shows the validation message and focuses the row.
- A source run on Windows shows the same translated, sorted table names as the packaged build (D6).
- `scripts\generate-pot.bat`: the msgid set is unchanged, and only the references move.
- PyInstaller includes `settings/options.py`.

## Out of Scope

- Moving the persisted defaults out of `config.py` (D3). Normalizing translation tables on load (K3). Fixing K1, K2 or K4.
- Editing `braille/tables/__tables.py`, or re-sorting `listTables()` (M-5 stays a P2-7 follow-up candidate; no visible effect).
- `conversion/output.py`'s `"ascii"` check and `conversion/text/pipeline.py:71`'s `{"default", "math"}` / key-derived language list. Conversion must not import `settings`. A conversion-side leaf for output modes (like `math_braille_codes`) would be a separate task.
- The dictionary choice (a dynamic list), and `get_settings_snapshot` re-listing dictionaries (P0 review M-8, P2-6).
- `sync_open_font_size` (P2-4). Panel titles and descriptions, which are still translated at import (class attributes).
- `main.py`'s demo `output_mode="unicode"`.
