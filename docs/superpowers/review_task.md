# DotExpress Settings Dialog Review — Task 1

Date: 2026-07-06

## Review Scope

The main agent reviewed the implementation against:

- `docs/superpowers/specs/2026-07-06-dotexpress-settings-dialog-design.md`
- `docs/superpowers/plans/2026-07-06-dotexpress-settings-dialog.md`
- NVDA's `MultiCategorySettingsDialog`, `SettingsPanel`, and
  `NVDASettingsDialog` behavior in
  `include/nvda/source/gui/settingsDialogs.py`

Only the implementation commits listed by the plan were reviewed. They were
examined in commit-time order, oldest first:

1. `4acf569` — `refactor: add explicit view settings state`
2. `7682536` — `refactor: add staged settings snapshot`
3. `58f54e9` — `feat: add multi-category settings framework`
4. `3ae94a3` — `feat: add DotExpress settings panels`
5. `064e01d` — `feat: integrate DotExpress settings dialog`
6. `bc86e87` — `feat: unify settings menu entry`
7. `79494ea` — `i18n: localize DotExpress settings dialog`

Existing uncommitted spec and plan changes were preserved and excluded from the
implementation diff review.

## Commit-by-Commit Review

### 1. `4acf569` — Explicit View Settings State

The commit correctly:

- introduced an immutable `ViewSettings` value
- preserved the existing font-size range of 8 through 48
- normalized scheme and braille-font values
- loaded and persisted all view settings through one boundary

No product defect was found in this commit.

### 2. `7682536` — Staged Settings Snapshot

The aggregate snapshot correctly copies the mutable translation-table mapping
on creation, replacement, and explicit copying. This prevents panel edits from
mutating `language_map_translate_table` before Apply or OK.

No product defect was found in this commit.

### 3. `58f54e9` — Multi-Category Settings Framework

Confirmed defects:

- The category control is a `wx.ListCtrl`, but the implementation called
  `SetSelection()` and `GetSelection()`, which belong to choice-style controls.
  `wx.ListEvent` was also read through `GetSelection()` instead of `GetIndex()`.
  The dialog would fail under real wxPython during construction or category
  switching.
- The test stub implemented the same nonexistent ListCtrl methods, hiding the
  production error.
- Binding both selected and focused events could deactivate and reactivate the
  same panel twice.
- The category list retained a visible header and lacked an explicit accessible
  name, diverging from the NVDA layout and the accessibility requirement.

Repairs:

- changed category operations to `Select()`, `GetFirstSelected()`, `Focus()`,
  and `ListEvent.GetIndex()`
- removed the invalid APIs from the test stub and added regression coverage
- added active-category deduplication
- applied `LC_NO_HEADER`, an `&Categories:` label, and the accessible name
  `Categories`

### 4. `3ae94a3` — Concrete Settings Panels

The three panels preserve the old translation settings, table filtering, and
view options while staging values until commit. Category ordering and lazy panel
creation match the specification.

Confirmed defects:

- Missing required default or math translation-table values stopped Apply but
  gave no useful message and did not focus the failing control.
- `show_singleton()` caught every exception. A programming error while raising
  the existing dialog could be hidden and followed by creation of a second
  settings window.
- The title was assembled with a hard-coded ASCII colon, preventing the zh-TW
  title from using `DotExpress 設定：轉譯`.
- `sync_open_font_size()` returned before updating the staged snapshot when the
  View panel had not yet been lazily created. Applying another category could
  overwrite an immediate main-window font-size adjustment with stale data.

Repairs:

- added localized required-table validation, category selection, and control
  focus
- limited stale-window recovery to expected deleted-wrapper exceptions and
  re-raised unrelated errors
- introduced a translatable
  `DotExpress Settings: {category}` title template
- synchronized the staged snapshot before considering whether the View panel
  exists, while preserving a dirty font-size draft

### 5. `064e01d` — Main-Window Integration

The commit correctly:

- removed visible View controls
- introduced explicit main-window view state
- preserved immediate mouse-wheel font-size adjustment
- centralized settings commit and persistence
- removed View from section navigation
- opened one modeless settings dialog on Translation

The lazy-panel font synchronization defect originating in the preceding commit
became user-visible through this integration and was repaired as described
above.

The migration also moved the math table option source from `dialog.py` to
`settings_dialogs.py`, but an existing source-order regression test still read
the old file. The test now reads the new source of truth through a
repository-relative path.

### 6. `bc86e87` — Unified Menu Entry

The Translation menu now contains one `Settings` entry and no separate
translation-table settings entry. The handler opens the shared dialog on the
Translation category.

No additional defect was found in this commit.

### 7. `79494ea` — Localization

Confirmed defects:

- The dialog title still rendered with an ASCII colon and space because only
  `DotExpress Settings` was translated, not the complete title format.
- POT regeneration marked runtime wildcard strings as obsolete because the
  application translates constants dynamically and xgettext cannot discover
  those calls. The compiled MO consequently returned English for active
  wildcard labels such as `PDF files (*.pdf)|*.pdf`.

Repairs:

- translated the complete title template to
  `DotExpress 設定：{category}`
- added literal extraction markers for active CSV, DEP, TXT, PDF, DOCX, EPUB,
  BRL, and All Supported Files labels
- regenerated POT, PO, and MO artifacts
- added a catalog regression test covering all eight runtime labels

## Repair and Re-Review Rounds

### Round 1

The main agent identified the ListCtrl API crash, title formatting problem,
lazy-panel font synchronization bug, validation UX gap, broad singleton
exception handling, accessibility mismatch, and stale source-order test.

A GPT-5.4 subagent used systematic debugging and test-driven development to
repair them. The main agent then reviewed every changed line and independently
reran the relevant tests.

### Round 2

The main agent loaded the compiled zh-TW catalog directly and found the runtime
wildcard translations missing. The GPT-5.4 subagent restored reliable xgettext
discoverability, rebuilt localization artifacts, added catalog tests, and made
the touched source-order test path portable.

The main agent independently inspected the POT/PO/MO results and queried all
required catalog entries.

### Round 3

Full unittest discovery showed that the newly added layout test passed alone but
failed after another test had imported `settings_dialogs` with a different wx
stub. The GPT-5.4 subagent changed the test to build the layout with a fresh,
temporarily installed stub without instantiating a panel bound to an earlier
base class.

The main agent reproduced the polluted test order, reviewed the isolation logic,
and confirmed that the new test no longer adds a full-suite error.

## Files Changed by Review Repairs

- `client/gui.py`
- `client/settings_dialogs.py`
- `client/tests/test_config.py`
- `client/tests/test_conversion_service.py`
- `client/tests/test_settings_dialogs.py`
- `client/locales/dotexpress.pot`
- `client/locales/zh_TW/LC_MESSAGES/dotexpress.po`
- `client/locales/zh_TW/LC_MESSAGES/dotexpress.mo`

## Verification Evidence

Relevant automated coverage:

```text
cd client
python3 -m unittest \
  tests.test_settings_dialogs \
  tests.test_gui_document_flows \
  tests.test_translation_menu \
  tests.test_section_navigation \
  tests.test_view_settings \
  tests.test_settings_state \
  tests.test_config \
  tests.test_translation_settings \
  tests.test_conversion_service \
  -v
```

Result: 85 tests passed.

Polluted-order regression:

```text
cd client
python3 -m unittest \
  tests.test_gui_document_flows \
  tests.test_settings_dialogs.MultiCategorySettingsDialogTest.test_layout_uses_headerless_list_ctrl_and_explicit_categories_name \
  -v
```

Result: 22 tests passed.

Full discovery:

```text
cd client
python3 -m unittest discover -s tests -v
```

Result: 260 tests ran; 12 errors and 8 skips. The repaired settings-dialog tests
all passed. The remaining errors are outside this feature:

- optional import dependencies such as `mammoth` are unavailable in this
  environment
- existing test modules install process-global `lxml`, EPUB, and PDF stubs,
  causing later importer tests to execute against incomplete fake modules

The original in-scope full-suite error for the moved math-table source and the
new order-dependent settings layout test were both removed.

Additional checks:

- Python compilation succeeded for the modified Python modules.
- `git diff --check 4acf56^..79494e` passed for the reviewed commits.
- `git diff --check` passed for the repair working tree.
- Direct GNU MO queries returned the expected Traditional Chinese strings for
  the dynamic title template and all eight runtime wildcard labels.

## Remaining Manual Verification

This Linux environment does not provide real wxPython or Windows accessibility
APIs. The following remain manual Windows checks rather than unresolved code
findings:

- visual sizing and 1:3 resize behavior
- real `wx.ListCtrl` keyboard and focus behavior
- NVDA announcement of category list, property-page role, and descriptions
- modeless raise/restore behavior under native Windows window management

## Final Assessment

After three repair and main-agent re-review rounds, no unresolved Critical or
Important finding remains in the reviewed settings-dialog scope. The
implementation now matches the approved spec and plan at the code and automated
test level, subject to the documented Windows visual and accessibility checks.
