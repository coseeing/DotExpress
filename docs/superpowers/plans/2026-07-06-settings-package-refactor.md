# DotExpress Settings Package Refactor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Consolidate settings models, persistence helpers, staged state, and dialogs under `client/settings/` without changing user-visible behavior.

**Architecture:** Use a flat settings package with pure model/persistence modules at the inner boundary and wx dialogs at the outer boundary. Keep `settings/__init__.py` free of dialog imports so importing `settings.translation`, `settings.translation_tables`, `settings.view`, or `settings.state` never loads wx.

**Tech Stack:** Python 3, wxPython, `dataclasses`, `unittest`, `unittest.mock`

---

## File Structure

- Create `client/settings/__init__.py`: re-export the stable non-UI settings API.
- Move `client/translation/settings.py` to `client/settings/translation.py`: translation model, normalization, and persistence.
- Move `client/view_settings.py` to `client/settings/view.py`: view model, normalization, and persistence.
- Create `client/settings/translation_tables.py`: copied load/save wrappers around `config.py`.
- Move `client/settings_state.py` to `client/settings/state.py`: immutable staged settings snapshot.
- Move `client/settings_dialogs.py` to `client/settings/dialogs.py`: wx dialog framework and settings panels.
- Create `client/tests/test_translation_tables.py`: focused wrapper delegation/copy tests.
- Modify settings and GUI tests: migrate imports, patch targets, and source paths.
- Modify `client/gui.py`: consume the new package and translation-table helpers.
- Modify `client/tests/test_dialog_display.py`: update isolated-import module stubs.
- Delete the four old module paths through `git mv`; no compatibility shims remain.

### Task 1: Move Translation and View Settings Models

**Files:**
- Create: `client/settings/__init__.py`
- Move: `client/translation/settings.py` -> `client/settings/translation.py`
- Move: `client/view_settings.py` -> `client/settings/view.py`
- Modify: `client/settings_state.py`
- Modify: `client/settings_dialogs.py`
- Modify: `client/gui.py`
- Modify: `client/tests/test_translation_settings.py`
- Modify: `client/tests/test_view_settings.py`
- Modify: `client/tests/test_settings_state.py`
- Modify: `client/tests/test_settings_dialogs.py`
- Modify: `client/tests/test_gui_document_flows.py`
- Modify: `client/tests/test_dialog_display.py`

- [ ] **Step 1: Move the model modules**

Run:

```bash
mkdir -p client/settings
git mv client/translation/settings.py client/settings/translation.py
git mv client/view_settings.py client/settings/view.py
```

Expected: both destination files exist and both old paths are absent.

- [ ] **Step 2: Add the package's initial non-UI public surface**

Create `client/settings/__init__.py`:

```python
from .translation import (
    TranslationSettings,
    load_translation_settings,
    normalize_translation_settings,
    save_translation_settings,
)
from .view import (
    ViewSettings,
    load_view_settings,
    normalize_view_settings,
    save_view_settings,
)

__all__ = [
    "TranslationSettings",
    "ViewSettings",
    "load_translation_settings",
    "load_view_settings",
    "normalize_translation_settings",
    "normalize_view_settings",
    "save_translation_settings",
    "save_view_settings",
]
```

- [ ] **Step 3: Migrate application imports**

In `client/settings_state.py`, replace:

```python
from translation.settings import TranslationSettings
from view_settings import ViewSettings
```

with:

```python
from settings.translation import TranslationSettings
from settings.view import ViewSettings
```

In `client/settings_dialogs.py`, replace model imports with:

```python
from settings.translation import (
    MAX_CONVERSION_WIDTH,
    MIN_CONVERSION_WIDTH,
    TranslationSettings,
)
from settings.view import (
    VIEW_FONT_SIZE_MAX,
    VIEW_FONT_SIZE_MIN,
    ViewSettings,
    normalize_view_settings,
)
```

In `client/gui.py`, replace the old translation and view imports with:

```python
from settings.translation import (
    TranslationSettings,
    load_translation_settings,
    normalize_translation_settings,
    save_translation_settings,
)
from settings.view import (
    ViewSettings,
    load_view_settings,
    normalize_view_settings,
    save_view_settings,
)
```

- [ ] **Step 4: Migrate test imports and patch targets**

Use these imports in the corresponding tests:

```python
# client/tests/test_translation_settings.py
from settings.translation import (
    DEFAULT_TRANSLATION_SETTINGS,
    TranslationSettings,
    load_translation_settings,
    save_translation_settings,
)

# client/tests/test_view_settings.py
from settings.view import (
    ViewSettings,
    load_view_settings,
    normalize_view_settings,
    save_view_settings,
)

# client/tests/test_settings_state.py and other mixed settings tests
from settings.translation import TranslationSettings
from settings.view import ViewSettings
```

In `client/tests/test_translation_settings.py`, change every patch target from
`translation.settings.<name>` to `settings.translation.<name>`.

In `client/tests/test_dialog_display.py`, replace `translation.settings` in the
stub-module tuple with both new package paths:

```python
for name in (
    "braille",
    "braille.tables",
    "Bopomofo",
    "dictionaries",
    "dictionaries.actions",
    "dictionaries.manager",
    "documents",
    "documents.workspace",
    "translation",
    "settings",
    "settings.translation",
):
    sys.modules.setdefault(name, _AutoModule(name))
```

- [ ] **Step 5: Verify no old model imports remain**

Run:

```bash
rg -n "translation\.settings|from view_settings|import view_settings" client --glob '*.py'
```

Expected: no matches.

- [ ] **Step 6: Run focused model tests**

Run from `client/`:

```bash
python3 -m unittest tests.test_translation_settings tests.test_view_settings tests.test_settings_state -v
```

Expected: all tests pass.

- [ ] **Step 7: Commit the model moves**

```bash
git add client/settings client/settings_state.py client/settings_dialogs.py client/gui.py client/tests
git commit -m "refactor: move settings models into package"
```

### Task 2: Add Translation-Table Persistence Helpers

**Files:**
- Create: `client/settings/translation_tables.py`
- Create: `client/tests/test_translation_tables.py`
- Modify: `client/settings/__init__.py`
- Modify: `client/gui.py`
- Modify: `client/tests/test_gui_document_flows.py`

- [ ] **Step 1: Write failing wrapper tests**

Create `client/tests/test_translation_tables.py`:

```python
import unittest
from unittest.mock import patch

from settings.translation_tables import (
    load_translation_tables,
    save_translation_tables,
)


class TranslationTablesSettingsTest(unittest.TestCase):
    @patch(
        "settings.translation_tables.get_translation_tables",
        return_value={"default": "zh-tw.ctb", "math": "UEB"},
    )
    def test_load_returns_a_copy(self, get_translation_tables) -> None:
        stored = get_translation_tables.return_value

        loaded = load_translation_tables()
        loaded["default"] = "en-ueb-g1.ctb"

        self.assertEqual(stored["default"], "zh-tw.ctb")

    @patch("settings.translation_tables.set_translation_tables")
    def test_save_persists_a_copy(self, set_translation_tables) -> None:
        tables = {"default": "zh-tw.ctb", "math": "UEB"}

        save_translation_tables(tables)
        persisted = set_translation_tables.call_args.args[0]
        tables["default"] = "en-ueb-g1.ctb"

        self.assertEqual(persisted["default"], "zh-tw.ctb")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the new test to verify it fails**

Run from `client/`:

```bash
python3 -m unittest tests.test_translation_tables -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'settings.translation_tables'`.

- [ ] **Step 3: Implement copied load/save wrappers**

Create `client/settings/translation_tables.py`:

```python
from config import get_translation_tables, set_translation_tables


def load_translation_tables() -> dict[str, str]:
    return dict(get_translation_tables())


def save_translation_tables(tables: dict[str, str]) -> None:
    set_translation_tables(dict(tables))
```

Add these imports and names to `client/settings/__init__.py`:

```python
from .translation_tables import load_translation_tables, save_translation_tables
```

Add `"load_translation_tables"` and `"save_translation_tables"` to `__all__`.

- [ ] **Step 4: Run the wrapper tests**

Run from `client/`:

```bash
python3 -m unittest tests.test_translation_tables -v
```

Expected: 2 tests pass.

- [ ] **Step 5: Switch GUI initialization and save flow to the wrappers**

In `client/gui.py`, remove `get_translation_tables` and
`set_translation_tables` from the `config` import, retain
`DEFAULT_TRANSLATION_TABLES` and `set_selected_dictionary`, and add:

```python
from settings.translation_tables import (
    load_translation_tables,
    save_translation_tables,
)
```

Replace:

```python
language_map_translate_table = get_translation_tables() or DEFAULT_TRANSLATION_TABLES.copy()
```

with:

```python
language_map_translate_table = (
    load_translation_tables() or DEFAULT_TRANSLATION_TABLES.copy()
)
```

Replace:

```python
set_translation_tables(tables)
```

with:

```python
save_translation_tables(tables)
```

In `client/tests/test_gui_document_flows.py`, replace:

```python
patch.object(gui, "set_translation_tables")
```

with:

```python
patch.object(gui, "save_translation_tables")
```

- [ ] **Step 6: Verify direct config calls are gone from GUI**

Run:

```bash
rg -n "get_translation_tables|set_translation_tables" client/gui.py client/tests/test_gui_document_flows.py
```

Expected: no matches.

- [ ] **Step 7: Run focused integration tests**

Run from `client/`:

```bash
python3 -m unittest tests.test_translation_tables tests.test_gui_document_flows -v
```

Expected: all tests pass.

- [ ] **Step 8: Commit the translation-table boundary**

```bash
git add client/settings client/gui.py client/tests/test_translation_tables.py client/tests/test_gui_document_flows.py
git commit -m "refactor: isolate translation table settings"
```

### Task 3: Move Staged Settings State

**Files:**
- Move: `client/settings_state.py` -> `client/settings/state.py`
- Modify: `client/settings/state.py`
- Modify: `client/settings/__init__.py`
- Modify: `client/settings_dialogs.py`
- Modify: `client/gui.py`
- Modify: `client/tests/test_settings_state.py`
- Modify: `client/tests/test_settings_dialogs.py`
- Modify: `client/tests/test_gui_document_flows.py`

- [ ] **Step 1: Move the state module and use relative model imports**

Run:

```bash
git mv client/settings_state.py client/settings/state.py
```

In `client/settings/state.py`, replace:

```python
from settings.translation import TranslationSettings
from settings.view import ViewSettings
```

with:

```python
from .translation import TranslationSettings
from .view import ViewSettings
```

- [ ] **Step 2: Re-export the snapshot**

Add to `client/settings/__init__.py` after the model imports:

```python
from .state import DotExpressSettingsSnapshot
```

Add `"DotExpressSettingsSnapshot"` to `__all__`.

- [ ] **Step 3: Migrate state imports**

In `client/settings_dialogs.py`, use:

```python
from settings.state import DotExpressSettingsSnapshot
```

In `client/gui.py` and the three affected test modules, use:

```python
from settings.state import DotExpressSettingsSnapshot
```

- [ ] **Step 4: Verify no old state imports remain**

Run:

```bash
rg -n "settings_state" client --glob '*.py'
```

Expected: no matches.

- [ ] **Step 5: Run state and dependent dialog tests**

Run from `client/`:

```bash
python3 -m unittest tests.test_settings_state tests.test_settings_dialogs tests.test_gui_document_flows -v
```

Expected: all tests pass.

- [ ] **Step 6: Commit the state move**

```bash
git add client/settings client/settings_dialogs.py client/gui.py client/tests
git commit -m "refactor: move settings state into package"
```

### Task 4: Move the wx Settings Dialogs

**Files:**
- Move: `client/settings_dialogs.py` -> `client/settings/dialogs.py`
- Modify: `client/settings/dialogs.py`
- Modify: `client/gui.py`
- Modify: `client/tests/test_settings_dialogs.py`
- Modify: `client/tests/test_gui_document_flows.py`
- Modify: `client/tests/test_conversion_service.py`

- [ ] **Step 1: Move the dialog module and make internal imports relative**

Run:

```bash
git mv client/settings_dialogs.py client/settings/dialogs.py
```

In `client/settings/dialogs.py`, use:

```python
from .state import DotExpressSettingsSnapshot
from .translation import (
    MAX_CONVERSION_WIDTH,
    MIN_CONVERSION_WIDTH,
    TranslationSettings,
)
from .view import (
    VIEW_FONT_SIZE_MAX,
    VIEW_FONT_SIZE_MIN,
    ViewSettings,
    normalize_view_settings,
)
```

- [ ] **Step 2: Migrate GUI and test imports**

In `client/gui.py`, use:

```python
from settings.dialogs import DotExpressSettingsDialog, TranslationSettingsPanel
```

In `client/tests/test_gui_document_flows.py`, use:

```python
from settings.dialogs import TranslationSettingsPanel
```

In `client/tests/test_settings_dialogs.py`:

- Replace every `from settings_dialogs import ...` with
  `from settings.dialogs import ...`.
- Replace `import settings_dialogs` with
  `from settings import dialogs as settings_dialogs`.
- Replace patch strings beginning with `settings_dialogs.` with
  `settings.dialogs.`.

The module-object patches remain unchanged:

```python
with patch.object(settings_dialogs, "wx", fresh_wx):
    with patch.object(
        settings_dialogs,
        "ScrolledPanel",
        fresh_wx.lib.scrolledpanel.ScrolledPanel,
    ):
        with patch("settings.dialogs._", side_effect=lambda text: text):
            dialog._build_layout()
```

- [ ] **Step 3: Update the source-path assertion**

In `client/tests/test_conversion_service.py`, replace:

```python
source = (
    Path(__file__).resolve().parents[1] / "settings_dialogs.py"
).read_text(encoding="utf-8")
```

with:

```python
source = (
    Path(__file__).resolve().parents[1] / "settings" / "dialogs.py"
).read_text(encoding="utf-8")
```

- [ ] **Step 4: Verify no old dialog imports or paths remain**

Run:

```bash
rg -n "from settings_dialogs|import settings_dialogs|settings_dialogs\.py" client --glob '*.py'
```

Expected: no matches.

- [ ] **Step 5: Run focused dialog and GUI tests**

Run from `client/`:

```bash
python3 -m unittest tests.test_settings_dialogs tests.test_gui_document_flows tests.test_conversion_service -v
```

Expected: all tests pass.

- [ ] **Step 6: Commit the dialog move**

```bash
git add client/settings client/gui.py client/tests
git commit -m "refactor: move settings dialogs into package"
```

### Task 5: Verify Package Boundaries and Full Client Behavior

**Files:**
- Modify only if verification reveals a missed internal import.

- [ ] **Step 1: Verify all legacy paths are absent**

Run:

```bash
test ! -e client/view_settings.py
test ! -e client/settings_state.py
test ! -e client/settings_dialogs.py
test ! -e client/translation/settings.py
rg -n "from view_settings|import view_settings|from settings_state|import settings_state|from settings_dialogs|import settings_dialogs|translation\.settings|settings_dialogs\.py" client --glob '*.py'
```

Expected: all `test` commands exit 0 and `rg` has no matches.

- [ ] **Step 2: Verify the package root does not load wx dialogs**

Run from `client/`:

```bash
python3 -c "import sys, settings; assert 'settings.dialogs' not in sys.modules; assert 'wx' not in sys.modules"
```

Expected: exits 0 with no output.

- [ ] **Step 3: Run every focused settings-related test**

Run from `client/`:

```bash
python3 -m unittest \
  tests.test_view_settings \
  tests.test_translation_settings \
  tests.test_translation_tables \
  tests.test_settings_state \
  tests.test_settings_dialogs \
  tests.test_gui_document_flows \
  tests.test_conversion_service \
  tests.test_dialog_display \
  -v
```

Expected: all tests pass.

- [ ] **Step 4: Run the complete client test suite**

Run from `client/`:

```bash
python3 -m unittest discover -s tests -v
```

Expected: all runnable tests pass; Windows-only liblouis tests may report their existing platform skips.

- [ ] **Step 5: Inspect the final diff**

Run:

```bash
git status --short
git diff --check
git diff --stat
```

Expected: only planned settings-package files and tests are changed, `git diff --check` exits 0, and unrelated pre-existing work remains untouched.

- [ ] **Step 6: Commit any verification-only corrections**

If Step 1-5 required a missed import correction:

```bash
git add client
git commit -m "test: complete settings package migration"
```

If no corrections were required, do not create an empty commit.
