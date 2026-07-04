# Dialog Display Optimization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Standardize custom dialog fitting and parent-relative centering, present dictionary names and valid entry counts in a two-column virtual list, and make Dual View cover the main window's current geometry.

**Architecture:** Add one small layout-finalization helper shared by custom `wx.Dialog` classes, and generalize the existing callback-backed virtual list so both dictionary dialogs can use it. Extract dictionary CSV loading into a module-level function so the editor and management count column use exactly the same validity rules. Keep Dual View geometry synchronization in `DualViewFrame`, where the parent geometry is available during construction.

**Tech Stack:** Python 3, wxPython (`wx.Dialog`, virtual `wx.ListCtrl`, `wx.Frame`), CSV, gettext, `unittest`

---

## File Structure

- Modify: `client/dialog.py` — add shared dialog finalization, reusable virtual list, shared dictionary entry loading, two-column dictionary management, count calculation, and responsive columns.
- Modify: `client/gui.py` — apply shared finalization to `ConvertingDialog` and pass the dictionary directory into `DictionaryManagementDialog`.
- Modify: `client/ui/dual_view.py` — initialize Dual View with the parent window's current position and size.
- Create: `client/tests/test_dialog_display.py` — verify fitting and parent/screen centering without requiring a live wx display.
- Modify: `client/tests/test_speech_symbols_dialog.py` — cover shared CSV loading and the generalized virtual list.
- Create: `client/tests/test_dictionary_management_dialog.py` — cover virtual cells, valid entry counts, refresh/selection behavior, responsive columns, and button-only editing.
- Modify: `client/tests/test_dual_view_frame.py` — verify parent geometry is copied at frame construction.
- Modify: `client/locales/dotexpress.pot` — add the new entry-count source string to the translation template.
- Modify: `client/locales/zh_TW/LC_MESSAGES/dotexpress.po` — translate the new entry-count column heading.
- Regenerate: `client/locales/zh_TW/LC_MESSAGES/dotexpress.mo` — compile the updated translation catalog.
- Reference: `docs/superpowers/specs/2026-07-04-dialog-display-optimization-design.md`

### Task 1: Add Shared Dialog Finalization

**Files:**
- Create: `client/tests/test_dialog_display.py`
- Modify: `client/dialog.py:89-993`
- Modify: `client/gui.py:20-45,221-230`

- [ ] **Step 1: Write tests for fitting and centering with and without a parent**

```python
# client/tests/test_dialog_display.py
import importlib.util
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import Mock


class _AutoModule(types.ModuleType):
    def __getattr__(self, name):
        if name.startswith("__") and name.endswith("__"):
            raise AttributeError(name)
        value = type(name, (), {})
        setattr(self, name, value)
        return value


def _load_dialog_module():
    dialog_path = Path(__file__).resolve().parents[1] / "dialog.py"
    previous = dict(sys.modules)
    try:
        wx = _AutoModule("wx")
        wx.Dialog = type("Dialog", (), {})
        wx.ListCtrl = type("ListCtrl", (), {})
        wx.Window = type("Window", (), {})
        wx.NOT_FOUND = -1
        sys.modules["wx"] = wx
        for name in ("braille", "braille.tables", "Bopomofo"):
            sys.modules.setdefault(name, _AutoModule(name))
        spec = importlib.util.spec_from_file_location("_dialog_display_test", dialog_path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        return module
    finally:
        for name in list(sys.modules):
            if name not in previous:
                del sys.modules[name]
        sys.modules.update(previous)


dialog_module = _load_dialog_module()


class FinalizeDialogLayoutTest(unittest.TestCase):
    def test_fits_and_centers_on_parent(self):
        owner = object()
        dialog = Mock()
        dialog.GetParent.return_value = owner
        sizer = object()

        dialog_module.finalize_dialog_layout(dialog, sizer)

        dialog.SetSizerAndFit.assert_called_once_with(sizer)
        dialog.CentreOnParent.assert_called_once_with()
        dialog.Centre.assert_not_called()

    def test_fits_and_centers_on_screen_without_parent(self):
        dialog = Mock()
        dialog.GetParent.return_value = None
        sizer = object()

        dialog_module.finalize_dialog_layout(dialog, sizer)

        dialog.SetSizerAndFit.assert_called_once_with(sizer)
        dialog.Centre.assert_called_once_with()
        dialog.CentreOnParent.assert_not_called()


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the focused test and confirm the helper is missing**

Run: `cd client && python3 -m unittest tests.test_dialog_display -v`

Expected: FAIL with `AttributeError` because `finalize_dialog_layout` does not exist.

- [ ] **Step 3: Add the shared finalization helper**

```python
# client/dialog.py, after gettext setup
def finalize_dialog_layout(dialog: wx.Dialog, sizer: wx.Sizer) -> None:
    """Fit a custom dialog to its content and place it relative to its owner."""
    dialog.SetSizerAndFit(sizer)
    if dialog.GetParent() is not None:
        dialog.CentreOnParent()
    else:
        dialog.Centre()
```

- [ ] **Step 4: Apply the helper to all custom dialogs in `client/dialog.py`**

Replace each final `SetSizerAndFit(main_sizer)` in these constructors with `finalize_dialog_layout(self, main_sizer)`:

```python
finalize_dialog_layout(self, main_sizer)
```

Apply it to:

- `AddSymbolDialog`
- `DictionaryNameDialog`
- `DocumentNameDialog`
- `InvalidWorkspaceFilesDialog`
- `FileIssuesDialog`
- `TranslationSettingsDialog`
- `TranslationTableDialog`

For `InvalidWorkspaceFilesDialog` and `FileIssuesDialog`, keep their existing `SetMinSize(...)` after the helper because those minimums protect long issue lists from opening unusably small; the shared helper still establishes the content-derived initial best size and centering. Do not change built-in file, directory, or message dialogs.

- [ ] **Step 5: Apply the helper to `ConvertingDialog`**

Add `finalize_dialog_layout` to the existing import from `dialog` in `client/gui.py`, then replace:

```python
self.SetSizerAndFit(sizer)
self.CentreOnParent()
```

with:

```python
finalize_dialog_layout(self, sizer)
```

- [ ] **Step 6: Run the focused and existing dialog-related tests**

Run: `cd client && python3 -m unittest tests.test_dialog_display tests.test_gui_document_flows -v`

Expected: PASS.

- [ ] **Step 7: Commit the shared display rule**

```bash
git add client/dialog.py client/gui.py client/tests/test_dialog_display.py
git commit -m "refactor: standardize dialog layout finalization"
```

### Task 2: Share Virtual List and Dictionary CSV Loading

**Files:**
- Modify: `client/dialog.py:396-510`
- Modify: `client/tests/test_speech_symbols_dialog.py:138-325`

- [ ] **Step 1: Add failing tests for a generic virtual list and shared valid-entry loading**

Update the imported names near the top of `client/tests/test_speech_symbols_dialog.py`:

```python
CallbackVirtualListCtrl = dialog.CallbackVirtualListCtrl
DictionaryEntry = dialog.DictionaryEntry
SpeechSymbolsDialog = dialog.SpeechSymbolsDialog
load_dictionary_entries = dialog.load_dictionary_entries
```

Replace `DictionaryEntryListCtrlTest` and add the loader tests:

```python
class CallbackVirtualListCtrlTest(unittest.TestCase):
    def test_get_item_text_delegates_to_callback(self) -> None:
        control = object.__new__(CallbackVirtualListCtrl)
        control._get_item_text = lambda item, column: f"{item}:{column}"

        self.assertEqual(control.OnGetItemText(4, 2), "4:2")


class DictionaryEntryLoadingTest(unittest.TestCase):
    def test_loads_only_rows_accepted_by_the_editor(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "sample.csv"
            with path.open("w", newline="", encoding="utf-8") as stream:
                writer = csv.writer(stream)
                writer.writerow(["text", "braille", "type"])
                writer.writerow(["Alpha", "\u2801", "General"])
                writer.writerow(["", "\u2803", "General"])
                writer.writerow(["Zhuyin", "invalid", "Bopomofo"])

            with patch.object(dialog, "normalize_zhuyin_sequence", side_effect=ValueError):
                entries = load_dictionary_entries(path)

        self.assertEqual(entries, [DictionaryEntry("Alpha", "\u2801", "General")])

    def test_missing_dictionary_returns_empty_list(self) -> None:
        self.assertEqual(load_dictionary_entries(Path("missing.csv")), [])
```

- [ ] **Step 2: Run the test and confirm the new public names are missing**

Run: `cd client && python3 -m unittest tests.test_speech_symbols_dialog -v`

Expected: FAIL because `CallbackVirtualListCtrl` and `load_dictionary_entries` are not defined.

- [ ] **Step 3: Generalize the virtual list control**

Rename `DictionaryEntryListCtrl` in `client/dialog.py` and preserve its callback contract:

```python
class CallbackVirtualListCtrl(wx.ListCtrl):
    """Virtual list that asks its owner for cell text."""

    def __init__(
        self,
        parent: wx.Window,
        get_item_text: Callable[[int, int], str],
        **kwargs,
    ):
        super().__init__(parent, **kwargs)
        self._get_item_text = get_item_text

    def OnGetItemText(self, item: int, column: int) -> str:
        return self._get_item_text(item, column)
```

Change `SpeechSymbolsDialog._build_ui()` to construct `CallbackVirtualListCtrl`; do not change its three columns, virtual style, filtering, or item activation behavior.

- [ ] **Step 4: Extract the editor's exact CSV validity rules**

Move the body of `_load_entries()` into these module-level functions:

```python
def normalize_entry_type(entry_type: str | None) -> str:
    if entry_type in ENTRY_TYPE_LABELS:
        return str(entry_type)
    return DEFAULT_ENTRY_TYPE


def load_dictionary_entries(dictionary_path: Path) -> list[DictionaryEntry]:
    if not dictionary_path.exists():
        return []

    entries: list[DictionaryEntry] = []
    with dictionary_path.open("r", newline="", encoding="utf-8") as fp:
        reader = csv.DictReader(fp)
        for row in reader:
            text = (row.get("text") or "").strip()
            if not text:
                continue
            braille = (row.get("braille") or "").strip()
            entry_type = normalize_entry_type(row.get("type"))
            if entry_type == "Bopomofo":
                try:
                    normalize_zhuyin_sequence(braille)
                except Exception:
                    continue
            entries.append(
                DictionaryEntry(
                    text=text,
                    braille=braille,
                    entry_type=entry_type,
                )
            )
    return entries
```

Then make the dialog delegate to it:

```python
def _load_entries(self) -> list[DictionaryEntry]:
    return load_dictionary_entries(self.dictionary_path)

def _normalize_type(self, entry_type: str | None) -> str:
    return normalize_entry_type(entry_type)
```

Keep `_normalize_type()` as a compatibility wrapper because existing tests and callers exercise it.

- [ ] **Step 5: Run the Speech Symbols tests**

Run: `cd client && python3 -m unittest tests.test_speech_symbols_dialog -v`

Expected: PASS, including filtering and CRUD tests.

- [ ] **Step 6: Commit the reusable list and loader**

```bash
git add client/dialog.py client/tests/test_speech_symbols_dialog.py
git commit -m "refactor: share dictionary virtual list loading"
```

### Task 3: Convert Dictionary Management to a Two-Column Virtual List

**Files:**
- Create: `client/tests/test_dictionary_management_dialog.py`
- Modify: `client/dialog.py:777-936`
- Modify: `client/gui.py:1296-1314`
- Modify: `client/locales/dotexpress.pot`
- Modify: `client/locales/zh_TW/LC_MESSAGES/dotexpress.po`
- Regenerate: `client/locales/zh_TW/LC_MESSAGES/dotexpress.mo`

- [ ] **Step 1: Create controlled fakes and failing tests for virtual rows and valid counts**

```python
# client/tests/test_dictionary_management_dialog.py
import csv
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from tests.test_speech_symbols_dialog import dialog


DictionaryManagementDialog = dialog.DictionaryManagementDialog


class _FakeListCtrl:
    def __init__(self, width=500):
        self.item_count = 0
        self.selected = -1
        self.focused = -1
        self.refresh_count = 0
        self.width = width
        self.column_widths = {}

    def SetItemCount(self, count):
        self.item_count = count

    def Refresh(self):
        self.refresh_count += 1

    def GetFirstSelected(self):
        return self.selected

    def Select(self, index, on=True):
        self.selected = index if on else -1

    def Focus(self, index):
        self.focused = index

    def GetClientSize(self):
        return type("Size", (), {"width": self.width})()

    def GetTextExtent(self, text):
        return (len(text) * 8, 16)

    def SetColumnWidth(self, column, width):
        self.column_widths[column] = width


def _make_dialog(dictionary_dir, names):
    target = object.__new__(DictionaryManagementDialog)
    target.dictionary_dir = Path(dictionary_dir)
    target._dictionary_names = list(names)
    target._dictionary_counts = {}
    target._selected_name = names[0] if names else ""
    target.list_ctrl = _FakeListCtrl()
    target.add_button = Mock()
    target.delete_button = Mock()
    target.rename_button = Mock()
    target.edit_button = Mock()
    target.import_button = Mock()
    target.export_button = Mock()
    return target


class DictionaryManagementVirtualListTest(unittest.TestCase):
    def test_refresh_sets_virtual_count_and_valid_entry_counts(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "alpha.csv"
            with path.open("w", newline="", encoding="utf-8") as stream:
                writer = csv.writer(stream)
                writer.writerow(["text", "braille", "type"])
                writer.writerow(["Alpha", "\u2801", "General"])
                writer.writerow(["", "\u2803", "General"])
            target = _make_dialog(temp_dir, ["alpha"])

            target.refresh_dictionaries(["alpha"], "alpha")

        self.assertEqual(target.list_ctrl.item_count, 1)
        self.assertEqual(target.list_ctrl.refresh_count, 1)
        self.assertEqual(target._get_item_text(0, 0), "alpha")
        self.assertEqual(target._get_item_text(0, 1), "1")
        self.assertEqual(target.list_ctrl.selected, 0)

    def test_missing_dictionary_has_zero_entries(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            target = _make_dialog(temp_dir, ["missing"])

            target.refresh_dictionaries(["missing"], "missing")

        self.assertEqual(target._get_item_text(0, 1), "0")

    def test_disk_refresh_discovers_new_dictionary_files(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "new.csv"
            path.write_text("text,braille,type\n", encoding="utf-8")
            target = _make_dialog(temp_dir, ["old"])

            target._refresh_from_disk("new")

        self.assertEqual(target._dictionary_names, ["new"])
        self.assertEqual(target.list_ctrl.selected, 0)

    def test_unknown_column_is_rejected(self):
        target = _make_dialog(".", ["alpha"])
        target._dictionary_counts = {"alpha": 1}

        with self.assertRaisesRegex(ValueError, "Unknown column"):
            target._get_item_text(0, 2)
```

- [ ] **Step 2: Add failing tests for selection restoration, widths, and button-only editing**

```python
# append to client/tests/test_dictionary_management_dialog.py
class DictionaryManagementInteractionTest(unittest.TestCase):
    def test_refresh_restores_preferred_selection(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            target = _make_dialog(temp_dir, ["alpha", "beta"])

            target.refresh_dictionaries(["alpha", "beta"], "beta")

        self.assertEqual(target.list_ctrl.selected, 1)
        self.assertEqual(target.list_ctrl.focused, 1)

    def test_column_widths_fill_available_client_width(self):
        target = _make_dialog(".", ["alpha"])
        target.list_ctrl.width = 600

        target._resize_columns()

        self.assertEqual(sum(target.list_ctrl.column_widths.values()), 600)
        self.assertGreater(
            target.list_ctrl.column_widths[0],
            target.list_ctrl.column_widths[1],
        )

    def test_resize_event_recalculates_columns_and_continues_propagation(self):
        target = _make_dialog(".", ["alpha"])
        target._resize_columns = Mock()
        event = Mock()

        target._on_list_size(event)

        target._resize_columns.assert_called_once_with()
        event.Skip.assert_called_once_with()

    def test_only_explicit_edit_handler_sets_edit_result(self):
        target = _make_dialog(".", ["alpha"])
        target.list_ctrl.selected = 0
        target.EndModal = Mock()
        target.edit_dictionary_name = None

        target._on_edit(None)

        self.assertEqual(target.edit_dictionary_name, "alpha")
        target.EndModal.assert_called_once_with(dialog.wx.ID_EDIT)
```

- [ ] **Step 3: Run the new tests and confirm the old normal-list implementation fails**

Run: `cd client && python3 -m unittest tests.test_dictionary_management_dialog -v`

Expected: FAIL because counts, virtual cells, and responsive column methods do not exist and refresh still calls `DeleteAllItems()`.

- [ ] **Step 4: Add the dictionary directory and virtual data model**

Extend the constructor signature and state in `client/dialog.py`:

```python
def __init__(
    self,
    parent: wx.Window | None,
    dictionary_names: list[str],
    selected_name: str,
    dictionary_dir: Path,
    on_add: Callable[[wx.Window | None], str | None],
    on_delete: Callable[[wx.Window | None, str], str | None],
    on_rename: Callable[[wx.Window | None, str], str | None],
    on_import: Callable[[wx.Window | None], str | None],
    on_export: Callable[[wx.Window | None, str], None],
):
    # existing super call
    self.dictionary_dir = Path(dictionary_dir)
    self._dictionary_names = list(dictionary_names)
    self._dictionary_counts: dict[str, int] = {}
```

Add `dictionary_path_for_name` and `list_dictionary_names` to the imports from `dictionaries.manager`; using these helpers keeps path construction and ordering consistent with the rest of the application.

Pass the directory from `MainFrame.on_open_dictionary_management()`:

```python
with DictionaryManagementDialog(
    self,
    self._dictionary_names,
    selected_name,
    self.dictionary_dir,
    self.add_dictionary,
    self.delete_dictionary_from_dialog,
    self.rename_dictionary_from_dialog,
    self.import_dictionary_from_dialog,
    self.export_dictionary_from_dialog,
) as dialog:
```

- [ ] **Step 5: Replace the normal list with the callback-backed virtual list**

```python
self.list_ctrl = CallbackVirtualListCtrl(
    self,
    self._get_item_text,
    style=wx.LC_REPORT | wx.BORDER_SUNKEN | wx.LC_SINGLE_SEL | wx.LC_VIRTUAL,
)
self.list_ctrl.InsertColumn(0, _("Dictionary"))
self.list_ctrl.InsertColumn(1, _("Entries"))
self.list_ctrl.Bind(wx.EVT_LIST_ITEM_SELECTED, self._on_selection_changed)
self.list_ctrl.Bind(wx.EVT_LIST_ITEM_DESELECTED, self._on_selection_changed)
self.list_ctrl.Bind(wx.EVT_SIZE, self._on_list_size)
```

Do not bind `wx.EVT_LIST_ITEM_ACTIVATED`; the existing Edit button binding remains the sole edit entry point.

Add the virtual cell callback:

```python
def _get_item_text(self, item: int, column: int) -> str:
    name = self._dictionary_names[item]
    if column == 0:
        return name
    if column == 1:
        return str(self._dictionary_counts.get(name, 0))
    raise ValueError(f"Unknown column: {column}")
```

- [ ] **Step 6: Replace row insertion with count calculation and virtual refresh**

```python
def _load_dictionary_counts(self) -> None:
    self._dictionary_counts = {
        name: len(
            load_dictionary_entries(
                dictionary_path_for_name(name, self.dictionary_dir)
            )
        )
        for name in self._dictionary_names
    }


def refresh_dictionaries(
    self,
    dictionary_names: list[str],
    preferred_name: str | None,
) -> None:
    self._dictionary_names = list(dictionary_names)
    self._load_dictionary_counts()
    self.list_ctrl.SetItemCount(len(self._dictionary_names))
    self.list_ctrl.Refresh()
    selected = resolve_dictionary_selection(
        self._dictionary_names,
        preferred_name,
    )
    self._selected_name = selected
    if selected in self._dictionary_names:
        index = self._dictionary_names.index(selected)
        self.list_ctrl.Select(index)
        self.list_ctrl.Focus(index)
    self._resize_columns()
    self._update_button_states()


def _refresh_from_disk(self, preferred_name: str | None) -> None:
    self.refresh_dictionaries(
        list_dictionary_names(self.dictionary_dir),
        preferred_name,
    )
```

This intentionally reads files synchronously on every refresh. Do not add caching or a worker thread.

Update `_on_add_clicked`, `_on_delete_clicked`, `_on_rename_clicked`, and `_on_import_clicked` so successful callbacks call:

```python
self._refresh_from_disk(preferred_name)
```

Do not pass `self._dictionary_names` back into `refresh_dictionaries()` after a filesystem mutation: the dialog received a list copy at construction time, while the callback updates the main frame's separate list.

- [ ] **Step 7: Add responsive column sizing**

```python
def _resize_columns(self) -> None:
    available_width = max(0, self.list_ctrl.GetClientSize().width)
    if available_width == 0:
        return
    count_text_width = self.list_ctrl.GetTextExtent(_("Entries"))[0]
    count_width = min(
        available_width,
        max(96, count_text_width + 32),
    )
    name_width = max(0, available_width - count_width)
    self.list_ctrl.SetColumnWidth(0, name_width)
    self.list_ctrl.SetColumnWidth(1, count_width)


def _on_list_size(self, event: wx.SizeEvent) -> None:
    self._resize_columns()
    event.Skip()
```

Call `_resize_columns()` after the dialog's final layout as well as during refresh and `EVT_SIZE`, satisfying all three recalculation points in the spec.

- [ ] **Step 8: Fit and center the dictionary dialogs**

At the end of `SpeechSymbolsDialog._build_ui()` and `DictionaryManagementDialog._build_ui()`, replace `SetSizer`, fixed `SetMinSize`, and `Layout` with:

```python
finalize_dialog_layout(self, main_sizer)
```

For Dictionary Management, immediately follow it with:

```python
self._resize_columns()
```

Keep `wx.RESIZE_BORDER` on both dialogs. Keep Speech Symbols' three columns and separators unchanged.

- [ ] **Step 9: Update the translation template and Traditional Chinese catalog**

Regenerate `client/locales/dotexpress.pot` on Windows:

Run: `scripts\generate-pot.bat`

Expected: command exits with status 0 and `client/locales/dotexpress.pot` contains `msgid "Entries"`.

Add this entry to `client/locales/zh_TW/LC_MESSAGES/dotexpress.po`:

```po
msgid "Entries"
msgstr "條目數量"
```

Compile and validate the catalog with gettext:

Run: `msgfmt --check --check-format -o client/locales/zh_TW/LC_MESSAGES/dotexpress.mo client/locales/zh_TW/LC_MESSAGES/dotexpress.po`

Expected: command exits with status 0 and updates `dotexpress.mo`.

- [ ] **Step 10: Run dictionary and GUI flow tests**

Run: `cd client && python3 -m unittest tests.test_dictionary_management_dialog tests.test_speech_symbols_dialog tests.test_gui_document_flows -v`

Expected: PASS. If the GUI flow test directly asserts `DictionaryManagementDialog` arguments, update its expected call to include `self.dictionary_dir`.

- [ ] **Step 11: Commit the two-column virtual dictionary list**

```bash
git add client/dialog.py client/gui.py client/tests/test_dictionary_management_dialog.py client/tests/test_speech_symbols_dialog.py client/tests/test_gui_document_flows.py client/locales/dotexpress.pot client/locales/zh_TW/LC_MESSAGES/dotexpress.po client/locales/zh_TW/LC_MESSAGES/dotexpress.mo
git commit -m "feat: show dictionary entry counts"
```

### Task 4: Match Dual View to Main Window Geometry

**Files:**
- Modify: `client/ui/dual_view.py:31-47`
- Modify: `client/tests/test_dual_view_frame.py:1-106`

- [ ] **Step 1: Make the wx frame stub record construction arguments**

```python
# client/tests/test_dual_view_frame.py
class Frame(Window):
    def __init__(self, *args, **kwargs):
        self.init_args = args
        self.init_kwargs = kwargs

    def SetSizer(self, sizer):
        self.sizer = sizer

    def Bind(self, event, handler):
        self.binding = (event, handler)
```

- [ ] **Step 2: Add a failing constructor test for copied geometry**

```python
def test_initial_geometry_matches_parent(self):
    parent = Mock()
    parent.GetPosition.return_value = (120, 80)
    parent.GetSize.return_value = (1024, 768)

    frame = DualViewFrame(
        parent,
        title="Dual View",
        on_closed=Mock(),
    )

    self.assertEqual(frame.init_kwargs["pos"], (120, 80))
    self.assertEqual(frame.init_kwargs["size"], (1024, 768))
    parent.GetPosition.assert_called_once_with()
    parent.GetSize.assert_called_once_with()
```

- [ ] **Step 3: Run the focused test and confirm the default size is still used**

Run: `cd client && python3 -m unittest tests.test_dual_view_frame.DualViewFrameTest.test_initial_geometry_matches_parent -v`

Expected: FAIL because `pos` is absent and `size` is still `(900, 650)`.

- [ ] **Step 4: Initialize the frame from effective parent geometry**

```python
# client/ui/dual_view.py, in DualViewFrame.__init__
super().__init__(
    parent,
    title=title,
    pos=parent.GetPosition(),
    size=parent.GetSize(),
)
```

Do not call `Maximize()`, copy maximized state, center the frame, or add ongoing move/resize synchronization.

- [ ] **Step 5: Run Dual View and GUI flow tests**

Run: `cd client && python3 -m unittest tests.test_dual_view_frame tests.test_gui_document_flows -v`

Expected: PASS.

- [ ] **Step 6: Commit the geometry behavior**

```bash
git add client/ui/dual_view.py client/tests/test_dual_view_frame.py
git commit -m "fix: align dual view with main window"
```

### Task 5: Regression Verification and Manual Windows Check

**Files:**
- Verify: `client/dialog.py`
- Verify: `client/gui.py`
- Verify: `client/ui/dual_view.py`
- Verify: `client/locales/dotexpress.pot`
- Verify: `client/locales/zh_TW/LC_MESSAGES/dotexpress.po`
- Verify: `client/locales/zh_TW/LC_MESSAGES/dotexpress.mo`

- [ ] **Step 1: Run all focused automated tests together**

Run:

```bash
cd client
python3 -m unittest \
  tests.test_dialog_display \
  tests.test_dictionary_management_dialog \
  tests.test_speech_symbols_dialog \
  tests.test_dual_view_frame \
  tests.test_gui_document_flows \
  -v
```

Expected: all tests PASS.

- [ ] **Step 2: Run the complete client test suite**

Run: `cd client && python3 -m unittest discover -s tests -v`

Expected: all available tests PASS; tests requiring Windows-only liblouis bindings may report SKIP on non-Windows systems.

- [ ] **Step 3: Check the translation catalog**

Run: `msgfmt --check --check-format -o /tmp/dotexpress.mo client/locales/zh_TW/LC_MESSAGES/dotexpress.po`

Expected: command exits with status 0.

- [ ] **Step 4: Perform the Windows wxPython display check**

On Windows, launch DotExpress and verify:

1. `AddSymbolDialog`, `DictionaryNameDialog`, `DocumentNameDialog`, `InvalidWorkspaceFilesDialog`, `FileIssuesDialog`, `TranslationSettingsDialog`, `TranslationTableDialog`, and `ConvertingDialog` center on their parent.
2. `SpeechSymbolsDialog` fits its controls, remains resizable, and keeps all three visible columns and separators.
3. `DictionaryManagementDialog` fits its controls, displays Dictionary and Entries columns, selects with one click, does nothing on double-click, and opens the entry editor only from Edit.
4. Adding, deleting, renaming, importing, and editing dictionaries refreshes names, counts, and selection correctly.
5. Resizing Dictionary Management reallocates both column widths without leaving a blank trailing column.
6. Windows text scaling changes are reflected by control sizing and fitted dialog dimensions.
7. Dual View opens at exactly the current main-window position and size and covers it without explicit maximized-state handling.

- [ ] **Step 5: Inspect the final diff for unintended behavior**

Run: `git diff --check && git status --short`

Expected: no whitespace errors; only planned files are modified.

- [ ] **Step 6: Commit any verification-only corrections**

If verification required code or test corrections, stage only those files and commit:

```bash
git add client
git commit -m "test: cover dialog display behavior"
```

If no corrections were needed, do not create an empty commit.
