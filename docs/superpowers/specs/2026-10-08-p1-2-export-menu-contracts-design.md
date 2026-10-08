# Export and Menu Contracts (P1-2) Design

## Goal

Make the document format registry and the document menu descriptors the only places that describe export formats and document menu items. Today `gui.py` repeats or patches around that information in four places. This is roadmap task P1-2 in `storage/refactor.md` (section 6.2). It covers findings O-1 and O-2 (section 3.2), L-3 (section 3.3) and P-4 (section 4.2), plus M-4 from the P0 phase review (`docs/superpowers/history/2026-10-08-01-refactor-p0/review_task.md`).

Concretely:

- **One writer contract (O-2, L-3, P-4).** Every export writer takes `(path, document, context: ExportContext)`. `ExportContext` carries the dual-view results. `gui._write_export_document` calls every writer the same way and no longer checks for `"html"`.
- **Export wildcard and Export submenus come from the registry (O-2, P-4).** `DocumentFormatDescriptor` gains `export_wildcard` and `export_label`. The save dialog's wildcard comes from `formats.build_export_wildcard(descriptor, _)`. The Export and Export All submenus are built from `formats.get_exportable_formats()`. This replaces the hard-coded dict in `gui._get_export_wildcard`, the three `*_WILDCARD` constants in `gui.py`, and the two hard-coded format tuples in `ui/action_menu.py`.
- **Menus are keyed by action (O-1).** `DocumentMenuItem` gains `enabled_when`. `get_document_menu_enabled_state` returns `{action: bool}` derived from the descriptors. A new wx-free `ui/menu_builder.py` builds and binds the document menu from the descriptors and a `{action: handler}` map. The File menu and the document-list context menu both use it. No code looks up a menu item by its English label any more.
- **Translatable strings are marked where they are defined (M-4).** `gui._MENU_TRANSLATION_MARKERS` is deleted. Each label is wrapped in `N_()` at its definition, and the extracted msgid set loses only the four orphan import-filter strings that nothing displays (357 becomes 353).

This is a behavior-preserving refactor. Menu order, labels, nesting, enabled states, handlers, shortcuts, dialog titles and wildcards, and the bytes of every exported file stay the same. No user-facing string changes, and nothing under `client/locales/` is edited by hand.

This spec includes the corrections and refinements from the implementation plan (`docs/superpowers/plans/2026-10-08-p1-2-export-menu-contracts.md`, section "Spec Corrections and Refinements"): one more test pins the marker tuple, the recording fakes are shared in `tests/menu_recording.py`, there are 11 characterization tests, `gui` stops importing `get_document_menu_descriptors`, the builder's `ValueError` text is fixed, `ExportContext` has its own test, and the zh_TW label test skips comments and obsolete entries.

## Current State (verified 2026-10-08 on `refactor/p1-2-export-menu-contracts`, HEAD `029a86e`, P0-1..P0-6 and P1-1 merged)

Indentation: `gui.py` and `dialog.py` use tabs. (`gui.py`'s import block has some 4-space continuation lines; leave them as they are.) `documents/formats.py`, `ui/action_menu.py`, `ui/translation_menu.py`, `conversion/preprocessing/user_script.py` and the touched tests use 4 spaces. The new `ui/menu_builder.py` and `tests/test_menu_builder.py` use 4 spaces, like the rest of `ui/`.

### Export path

| Step | Location | What it does |
| --- | --- | --- |
| Menu or shortcut | `gui.on_export_document(format_key)` 1117, `gui.on_export_all_documents(format_key)` 1126; Ctrl+S in the output editor, `gui.on_output_text_key_down` 1163-1171, calls `_export_document_with_dialog(document, get_format("brl").key)` | Save the open document, then export it. |
| Single export dialog | `gui._export_document_with_dialog` 730-765 | `wx.FileDialog(self, _("Export Document"), defaultFile=f"{name}{ext}", wildcard=self._get_export_wildcard(key), style=wx.FD_SAVE \| wx.FD_OVERWRITE_PROMPT)`. If the chosen path's suffix (compared case-insensitively) is not the format extension, the path gets `with_suffix(ext)`. If `document.braille is None`, the document is converted first for **every** format (not only for `requires_braille` formats), and then `_continue_single_export` runs. |
| Export All | `gui.on_export_all_documents` 1126-1139, `_export_next_document` 1278-1321 | `wx.DirDialog`, overwrite confirmation, then one document per `wx.CallAfter` step. Each target path is `dir / f"{name}{descriptor.extension}"`. |
| Write | `gui._write_export_document` 1217-1228 | `get_format(key)`. Raises `ValueError('Unsupported export format: "<key>".')` if the format is not exportable or has no writer. **Special case:** for `"html"` it calls `writer(path, document, dual_view_results=self._dual_view_results_by_document.get(document.name, ()))`. For every other format it calls `writer(path, document)`. |
| Registry writers | `documents/formats.py` 73-93 | `_write_dep(path, document)` returns `save_document_package(path, document, include_pending_metadata=False)` (a `Path`). `_write_brl(path, document)` returns `export_document_brl(...)` (a `Path`). `_write_html(path, document, *, dual_view_results=())` ignores the document and returns `Path(path).write_text(render_dual_view_html(build_dual_view_model(dual_view_results)), encoding="utf-8")`, which is an `int`. Nobody reads the return values. `_write_html` does not create missing parent directories, while the DEP and BRL writers do. |
| Descriptor types | `documents/formats.py` 21-30 | `loader: Callable[[Path \| str], object] \| None` and `writer: Callable[[Path \| str, object], object] \| None`. The real writer contract is not in the type (L-3). |

`documents/workspace.py:184-203` `batch_export_documents_to_folder`, which the roadmap row lists, was deleted in P0-3. There is nothing left to change in `documents/workspace.py`.

`DocumentFormatDescriptor.requires_braille` has no production reader. `gui` converts any document whose `braille is None` before exporting it, whatever the format. This task keeps that behavior and does not touch the field.

### Export wildcards

- `gui.py:125-127`: `DEP_WILDCARD = "DotExpress files (*.dep)|*.dep"`, `BRL_WILDCARD = "Braille files (*.brl)|*.brl"`, `HTML_WILDCARD = "HTML files (*.html)|*.html"`.
- `gui.py:591-592, 686-697`: `_get_dep_wildcard`, `_get_brl_wildcard` and `_get_html_wildcard` each return `_(<constant>)`. `_get_export_wildcard(key)` picks one of them from a hard-coded `{"dep", "brl", "html"}` dict. These methods have no other callers.
- The DEP and BRL strings are msgids (through `_MENU_TRANSLATION_MARKERS`) with zh_TW translations. `"HTML files (*.html)|*.html"` is **not** a msgid: it is only ever passed to `_()` through a variable, and `dotexpress.pot`/`.po` do not contain it. At runtime `_()` returns it unchanged.
- The registry's `wildcard_label` (`"DEP"`, `"BRL"`, `"HTML"`, ...) is the short label for the **import** wildcard (`build_import_wildcard`, which gives `"DEP (*.dep)|*.dep|..."`). The export dialog does not use it. The export strings are different text, so they cannot be derived from `wildcard_label` without changing what the user sees and the msgids.
- Import (`gui.on_import_document` 1082-1116) already uses the registry (`build_import_wildcard(_)`, `get_import_filters()[filter_index].key`, `ALL_SUPPORTED_FILTER_INDEX`). It is not changed here.

### Document menu

- Descriptors (`ui/action_menu.py:6-33`): `DocumentMenuItem(kind, label, action="", formats=())`, in this order: Open (`open`), Delete (`delete`), Delete All (`delete_all`), Add (`add`), Rename (`rename`), Import (`import`), Export (`export`, submenu), Export All (`export_all`, submenu). Both submenus list `(("dep", "Package DEP"), ("brl", "Braille BRL"), ("html", "Dual View HTML"))`, hard-coded twice. That is the same order as `get_exportable_formats()`.
- Enabled state (`ui/action_menu.py:40-50`): returns a dict keyed by **English label**: Open, Delete, Rename and Export follow `has_selection`. Delete All and Export All follow `has_documents`. Add and Import are always enabled.
- Construction (`gui._create_document_menu` 391-396, `_append_document_menu_items` 398-414): `menu = wx.Menu()`. For each descriptor in order: a command becomes `menu.Append(wx.ID_ANY, _(label))`. A submenu becomes `submenu = wx.Menu()`, then `menu.AppendSubMenu(submenu, _(label))`, then `submenu.Append(wx.ID_ANY, _(format_label))` for each format. Top-level items are stored by **label**, submenu items by `action` and then `format_key.casefold()`.
- Binding (`gui._bind_document_menu_handlers` 416-431): `menu.Bind(wx.EVT_MENU, handler, item)` on the **top-level** menu for every item, submenu items included, in this order: Open, Delete, Delete All, Add, Rename, Import (looked up as `menu_items["Open"]` and so on), then each Export format (`lambda _evt, fmt=key: self.on_export_document(fmt)`), then each Export All format (`self.on_export_all_documents(fmt)`). `DocumentMenuItem.action` is used only to find the submenu items. A renamed label would make `menu_items["..."]` raise `KeyError`. A label missing from the state dict is silently skipped by `_sync_document_menu_state`.
- State (`gui._sync_document_menu_state` 433-445): uses the given items, or `self._document_menu_items`. Returns early when there are no items or the frame is not initialized yet. `has_selection` is `False` until `document_list` exists. Then it calls `item.Enable(enabled)` for each label in the state dict (dict order = the order above). The init-order guards (`hasattr(self, "documents")`, `"document_list" in self.__dict__`) belong to P1-3 and stay as they are.
- Menu bar (`gui._create_menu_bar` 362-389): File (the document menu), Translation (`ui/translation_menu.get_translation_menu_items()`: Convert, Dual View, Text Processing, Dictionary Management..., Settings, bound on the frame through `self.Bind`), Help (Coseeing Website with `wx.ID_ANY`, About with `wx.ID_ABOUT`). The top-level titles are `_("File")`, `_("Translation")` and `_("Help")`.
- Context menu, which is the "Actions popup" in AGENTS.md (`gui.on_document_context_menu` 941-961): it hit-tests, selects or clears the selection, builds a fresh `wx.Menu()` with the same `_append_document_menu_items`, `_bind_document_menu_handlers` and `_sync_document_menu_state` calls, calls `document_list.PopupMenu(menu, position)`, then `menu.Destroy()`. The "ordering helpers" that AGENTS.md asks to check are the descriptor order and the registry order. P0-3 deleted the old Actions-button helpers (`build_actions_button_label`, `get_actions_menu_position`).
- Accelerators: no menu label has a `\t` accelerator or an `&` mnemonic, and there is no `wx.AcceleratorTable`. The keyboard shortcuts are key handlers that use `ui/shortcuts.py`: Ctrl+Enter converts, Ctrl+S in the output editor exports BRL, Ctrl+O imports, Ctrl+Tab and Ctrl+PageUp/PageDown cycle documents, F2 renames, Delete deletes, and F6/Shift+F6 move between sections. None of them goes through the menu, so this task does not affect them. Ctrl+S does reach `_export_document_with_dialog`, and the tests cover that.
- Not in scope: `gui._set_conversion_busy` (1370-1378) looks up menus with `FindMenu(_("File"))` by translated title (refactor.md section 5.3). It is part of the conversion busy state, which belongs to P1-4 (`ConversionPresenter`).

### Translation markers (`gui.py:131-181`)

`_MENU_TRANSLATION_MARKERS` is a tuple of 48 `N_("...")` calls that nothing reads. It exists only so `xgettext --keyword=_ --keyword=N_` (`scripts/generate-pot.bat`) can see strings that are translated through variables. Checked with an AST scan of all `_()`/`N_()` literal calls and all bare string constants under `client/` (excluding `tests/` and `.venv/`):

| Group | Markers | Other extraction site today | What happens |
| --- | --- | --- | --- |
| A. Already extracted elsewhere (23) | Add, Edit, Delete, Import, Export, Dual View, Rename, Default, Braille Font, SimBraille, Translation, "No conversion data is available for this document.", Text Processing, Text Processing Python Code, "Unable to open text processing script: {error}", "Unable to save text processing script: {error}", "Text processing failed: {error}", Confirm Delete Dictionary, `Do you want to delete dictionary "{name}"?`, Rename Dictionary, Help, Coseeing Website, About DotExpress | A literal `_()` call in `dialog.py`, `settings/dialogs.py`, `dictionaries/presenter.py` or `gui.py` | Delete the marker. The msgid stays. |
| B. Only extracted through the marker (21) | Open, Delete All, Export All (`ui/action_menu.py`); Package DEP, Braille BRL, Dual View HTML (`ui/action_menu.py` twice each, moving to `documents/formats.py`); DEP, DOCX, EPUB, PDF, TXT, BRL (`documents/formats.py` `wildcard_label`); All Supported Files (`documents/formats.py:200, 205`); Convert, Settings, Dictionary Management... (`ui/translation_menu.py`); the two `ValueError` messages in `conversion/preprocessing/user_script.py:39, 48` (shown through `settings/dialogs.py:148` `_(str(error))`); "CSV files (*.csv)\|*.csv" (`dialog.py:28` `CSV_WILDCARD`); "DotExpress files (*.dep)\|*.dep" and "Braille files (*.brl)\|*.brl" (`gui.py:125-126`, moving to `documents/formats.py`) | Only a bare string at the definition | Wrap the definition in `N_()`. |
| C. No definition site left (4) | "Text files (*.txt)\|*.txt", "PDF files (*.pdf)\|*.pdf", "Word documents (*.docx)\|*.docx", "EPUB books (*.epub)\|*.epub" | None. These were `IMPORT_WILDCARDS`, deleted in P0-3. Nothing shows them. | Drop them. See "Orphan msgids" below. |

The AST scan (`p06impl/tools/msgid_scan.py`, copied to the session scratchpad as `p12/tools/msgid_scan.py`, baseline saved as `p12/base_msgids.json`) gives 357 msgids in the source and 357 in `client/locales/dotexpress.pot`, and the two sets are equal. A dry run of the marking below on a scratch copy gives 353: the `.pot` has exactly the four group C strings in addition, and nothing else differs.

### Tests that pin the current shape

- `tests/test_action_menu.py`: enabled-state dicts keyed by label (4 tests), and the Export/Export All `formats` tuples.
- `tests/test_document_formats.py`: `test_html_writer_renders_cached_dual_view_results_as_utf8` calls the HTML writer with `dual_view_results=` as a keyword argument.
- `tests/test_gui_document_flows.py`: `test_write_export_document_uses_registry_writer` (asserts `writer(path, document)`), `test_write_html_export_document_passes_cached_dual_view_results` (asserts the `dual_view_results=` keyword argument), `test_sync_document_menu_state_before_document_list_exists` (label-keyed items), and `test_dead_frame_helpers_are_removed`, whose last two lines assert that `gui.DEP_WILDCARD` and `BrailleFrame._get_brl_wildcard` **still exist**. P0-3 added those as "kept on purpose" guards, and this task deletes both names.
- `tests/test_i18n.py::SharedSetupConsumerTest`: `gui.py` must import exactly `{"N_", "_", "resource_path"}` from `i18n`, and `dialog.py` exactly `{"_"}`.
- `tests/test_i18n.py::ExtractionMarkerTest::test_gui_menu_translation_markers_use_n_` (P0-5): parses `gui.py` and asserts that `_MENU_TRANSLATION_MARKERS` exists as a tuple of exactly 48 `N_()` calls. Deleting the tuple (step 6) fails it, so step 6 replaces it (see "Updated tests").
- `tests/test_removed_dead_code.py`: requires `action_menu.get_document_menu_descriptors`, `action_menu.get_document_menu_enabled_state`, `formats.get_exportable_formats` and `formats.get_import_filter_labels` to exist. All four stay.

### Baseline

Full suite at HEAD `029a86e` (Linux venv): 575 tests, `failures=1` (the known P2-5 `test_translate_with_language_does_not_duplicate_existing_spaces_around_math`), `skipped=7`. The focused modules (`test_document_formats`, `test_action_menu`, `test_gui_document_flows`, `test_i18n`, `test_removed_dead_code`, `test_translation_menu`, `test_export_results`, `test_user_preprocessing_script`) run 118 tests, all OK.

## Design

### Format registry (`documents/formats.py`)

```python
@dataclass(frozen=True)
class ExportContext:
    """What an export writer may need besides the document itself."""
    dual_view_results: tuple[object, ...] = ()

DocumentLoader = Callable[[Path | str], "Document"]
DocumentWriter = Callable[[Path | str, "Document", ExportContext], Path]

@dataclass(frozen=True)
class DocumentFormatDescriptor:
    key: str
    extension: str
    wildcard_label: str              # import-wildcard label, unchanged
    loader: DocumentLoader | None
    writer: DocumentWriter | None
    requires_braille: bool           # unchanged, still unread by gui
    importable: bool
    exportable: bool
    export_wildcard: str | None = None   # full single-format save-dialog filter, untranslated
    export_label: str | None = None      # Export / Export All submenu label, untranslated
```

- `Document` is imported under `TYPE_CHECKING` only. The runtime `formats` <-> `workspace` cycle (D-5) stays as it is: the loaders and writers still import `documents.workspace` inside the function.
- `context` is a **required** third positional parameter of every writer. Leaving it out raises `TypeError`, so a writer that forgets the contract fails loudly. All writers return the written `Path`:
  - `_write_dep(path, document, context)` ignores `context` and returns `save_document_package(path, document, include_pending_metadata=False)`, as today.
  - `_write_brl(path, document, context)` ignores `context` and returns `export_document_brl(path, document)`, as today.
  - `_write_html(path, document, context)` ignores `document`, writes `render_dual_view_html(build_dual_view_model(context.dual_view_results))` as UTF-8 to `Path(path)`, and returns that `Path`. It does **not** start creating parent directories (that would change behavior). The only difference is the return value, which nobody reads: a `Path` instead of the character count.
- Registry values. Only the new fields and the `N_()` wrapping change. Every other value stays the same:

  | key | `wildcard_label` | `export_wildcard` | `export_label` |
  | --- | --- | --- | --- |
  | dep | `N_("DEP")` | `N_("DotExpress files (*.dep)\|*.dep")` | `N_("Package DEP")` |
  | docx | `N_("DOCX")` | `None` | `None` |
  | epub | `N_("EPUB")` | `None` | `None` |
  | pdf | `N_("PDF")` | `None` | `None` |
  | txt | `N_("TXT")` | `None` | `None` |
  | brl | `N_("BRL")` | `N_("Braille files (*.brl)\|*.brl")` | `N_("Braille BRL")` |
  | html | `"HTML"` (not marked) | `"HTML files (*.html)\|*.html"` (not marked) | `N_("Dual View HTML")` |

  The two html strings stay unmarked because marking them would add two new msgids. That is a localization change, which is out of scope here. A one-line comment at the html entry says this. Neither string is a msgid today, so the UI shows them in English. The UI looks the same as before.
- `ALL_SUPPORTED_FILES_LABEL = N_("All Supported Files")` is a module constant. `build_import_wildcard` uses `translate(ALL_SUPPORTED_FILES_LABEL)` and `get_import_filter_labels` returns it as the last label. The import wildcard text does not change.
- New `build_export_wildcard(descriptor, translate=lambda value: value) -> str` mirrors `build_import_wildcard`. It returns `translate(descriptor.export_wildcard)`. It raises `ValueError(f'Unsupported export format: "{descriptor.key}".')` when `descriptor.export_wildcard is None`.
- `get_exportable_formats()` stays and now has production callers: `ui/action_menu.py` and the tests.
- Registry invariant (tested): for every descriptor, `exportable`, `writer is not None`, `export_wildcard is not None` and `export_label is not None` are all true or all false.

### Orphan msgids (decision)

The four group C strings have no definition site, because the import dialog uses the combined `build_import_wildcard` and P0-3 deleted the unused `IMPORT_WILDCARDS`. **Decision (orchestrator): drop them.** No replacement tuple is kept: keeping dead strings would contradict the P0-3 cleanup. The 357 count was only a proxy for "no visible string loses its translation", and these four are never displayed.

Consequences:

- The source extracts 353 msgids: the 357 baseline minus exactly "Text files (*.txt)|*.txt", "PDF files (*.pdf)|*.pdf", "Word documents (*.docx)|*.docx", "EPUB books (*.epub)|*.epub". The scan must show no other difference.
- `client/locales/dotexpress.pot`, `dotexpress.po` and the `.mo` are not hand-edited (as in P0-2 and P0-5). They keep the four entries until `scripts\generate-pot.bat` next runs on Windows. Then the `.pot` drops them, and a `msgmerge` turns the `.po` entries into obsolete (`#~`) entries. That is harmless: the strings are never looked up. This is a Windows follow-up.

### Menu descriptors (`ui/action_menu.py`)

```python
EnabledWhen = Literal["always", "has_selection", "has_documents"]

@dataclass(frozen=True)
class DocumentMenuItem:
    kind: str                      # "command" or "submenu"
    label: str                     # untranslated, N_()-marked
    action: str                    # unique key; handlers and state use it
    enabled_when: EnabledWhen
    formats: tuple[tuple[str, str], ...] = ()   # submenus: (format_key, untranslated label)

_EXPORT_FORMATS = tuple((d.key, d.export_label) for d in get_exportable_formats())
```

`DOCUMENT_MENU_ITEMS` is built with keyword arguments. Order, labels and actions do not change:

| action | label | kind | enabled_when |
| --- | --- | --- | --- |
| open | `N_("Open")` | command | has_selection |
| delete | `N_("Delete")` | command | has_selection |
| delete_all | `N_("Delete All")` | command | has_documents |
| add | `N_("Add")` | command | always |
| rename | `N_("Rename")` | command | has_selection |
| import | `N_("Import")` | command | always |
| export | `N_("Export")` | submenu, `formats=_EXPORT_FORMATS` | has_selection |
| export_all | `N_("Export All")` | submenu, `formats=_EXPORT_FORMATS` | has_documents |

`_EXPORT_FORMATS` evaluates to `(("dep", "Package DEP"), ("brl", "Braille BRL"), ("html", "Dual View HTML"))`, the same value as today. The order of the Export submenus is now the registry order.

`get_document_menu_enabled_state(*, has_selection, has_documents) -> dict[str, bool]` returns `{item.action: conditions[item.enabled_when] for item in DOCUMENT_MENU_ITEMS}` with `conditions = {"always": True, "has_selection": has_selection, "has_documents": has_documents}`. The dict order is the descriptor order, so the `Enable` calls happen in the same order as today. `get_document_menu_descriptors()` does not change.

`ui/action_menu.py` now imports `documents.formats` (for `get_exportable_formats`) and `i18n` (for `N_`). Both are pure. `ui/import_dialog.py` already depends on `documents.formats` the same way.

### Menu builder (`ui/menu_builder.py`, new, no wx import)

```python
def build_document_menu(
    menu,
    handlers: Mapping[str, Callable[..., None]],
    *,
    translate: Callable[[str], str],
    new_menu: Callable[[], object],
    menu_event: object,
    item_id: int,
    descriptors: Sequence[DocumentMenuItem] | None = None,   # default get_document_menu_descriptors()
) -> dict[str, object]:
    ...

def apply_document_menu_state(items_by_action: Mapping[str, object], enabled_by_action: Mapping[str, bool]) -> None:
    ...
```

`build_document_menu` makes exactly the same calls, in the same order, that `gui` makes today:

1. It raises `ValueError` before touching `menu` if `set(handlers)` differs from the set of descriptor actions. The message is `Document menu handlers do not match the menu actions: missing [...], extra [...].`, with `missing` in descriptor order and `extra` sorted. A missing handler or a stale extra handler fails at build time, where today a label typo would fail with `KeyError` or be skipped silently.
2. **Append pass**, in descriptor order. A command becomes `menu.Append(item_id, translate(label))`. A submenu becomes `submenu = new_menu()`, then `menu.AppendSubMenu(submenu, translate(label))`, then `submenu.Append(item_id, translate(format_label))` for each format in order.
3. **Bind pass**, in descriptor order, always on the top-level `menu`. A command becomes `menu.Bind(menu_event, handlers[action], item)`, which receives the wx event. Each submenu format item becomes `menu.Bind(menu_event, lambda _event, key=format_key, handler=handlers[action]: handler(key), item)`, where `format_key` is `format_key.casefold()` as today. Every command comes before every submenu in the descriptors, so this gives today's bind order exactly.
4. It returns the top-level items (the commands and the `AppendSubMenu` results) keyed by action.

`apply_document_menu_state` calls `items_by_action[action].Enable(enabled)` for each entry of `enabled_by_action`, in that order. An action with no item raises `KeyError`, where today it is skipped silently. In production both dicts come from the same descriptors.

The builder knows nothing about wx. `gui` passes `new_menu=wx.Menu`, `menu_event=wx.EVT_MENU` and `item_id=wx.ID_ANY`, read at call time. Tests pass recording fakes. No fluent API and no abstract View, following refactor.md section 4.3 and section 7 item 4.

One small difference, not visible to users: a submenu handler is the bound method captured when the menu is built. Today `self.on_export_document` is looked up when the event fires. Command handlers are already captured at bind time today, and production never replaces these methods. The File menu is built once, and the context menu is rebuilt on every popup.

### `gui.py`

- Delete: `DEP_WILDCARD`, `BRL_WILDCARD`, `HTML_WILDCARD`, `_get_dep_wildcard`, `_get_brl_wildcard`, `_get_html_wildcard`, `_get_export_wildcard`, `_append_document_menu_items`, `_bind_document_menu_handlers`, `_MENU_TRANSLATION_MARKERS` and its comment, `N_` from the `i18n` import, and `get_document_menu_descriptors` from the `ui.action_menu` import (after step 5 only `ui/menu_builder.py` reads the descriptors; `tests/test_removed_dead_code.py` only requires the function to exist in `ui.action_menu`, which it still does).
- New `_document_menu_handlers()` returns `{"open": self.on_open_document, "delete": self.on_delete_document, "delete_all": self.on_delete_all_documents, "add": self.on_add_document, "rename": self.on_rename_document, "import": self.on_import_document, "export": self.on_export_document, "export_all": self.on_export_all_documents}`.
- New `_append_document_menu(menu)` returns `build_document_menu(menu, self._document_menu_handlers(), translate=_, new_menu=wx.Menu, menu_event=wx.EVT_MENU, item_id=wx.ID_ANY)`.
- `_create_document_menu()` does `menu = wx.Menu()`, then `items = self._append_document_menu(menu)`, then `self._sync_document_menu_state(items)`, and returns `menu, items`. `self._document_menu_items` is now keyed by action.
- `on_document_context_menu` builds its popup with `self._append_document_menu(menu)` followed by `self._sync_document_menu_state(menu_items)`. Hit-testing, selection, the popup position, `PopupMenu` and `Destroy` do not change.
- `_sync_document_menu_state` keeps its guards and its `has_selection`/`has_documents` computation. Its loop becomes `apply_document_menu_state(target_items, get_document_menu_enabled_state(...))`.
- `_export_document_with_dialog` uses `wildcard = build_export_wildcard(descriptor, _)`. The rest does not change.
- `_write_export_document` keeps the `get_format(format_key)` lookup and the `ValueError` for non-exportable formats. It then calls `descriptor.writer(destination_path, document, ExportContext(dual_view_results=self._dual_view_results_by_document.get(document.name, ())))` for every format. No format key literal is left in this method. The cache is still read at write time, so Export All and conversions before export see the same cache as before.
- `on_output_text_key_down` keeps `get_format("brl").key`. That is the Ctrl+S shortcut picking its format, not a writer special case.
- `_create_menu_bar` and the Translation and Help menus do not change. Only their label source, `ui/translation_menu.py`, gets `N_()`.

### Other definition sites

- `ui/translation_menu.py`: wrap all five labels in `N_()` (`from i18n import N_`). The list value does not change.
- `dialog.py`: `CSV_WILDCARD = N_("CSV files (*.csv)|*.csv")`, and the import becomes `from i18n import N_, _`. The `_(CSV_WILDCARD)` uses do not change.
- `conversion/preprocessing/user_script.py`: `raise ValueError(N_("..."))` for the two messages (`from i18n import N_`). The exception text does not change. `settings/dialogs.py:148` still translates it at display time. Modules outside the UI import only `N_`, never `_`, so they still produce untranslated values.

### Migration steps (each step is one green commit; the plan details them)

1. `test:` add the characterization tests (see Test Plan). They pass on the unchanged code.
2. `refactor:` one writer contract. Add `ExportContext` and the typed aliases, make the writers take three arguments and return `Path`, make `gui._write_export_document` call them uniformly, and update the two writer tests in `test_gui_document_flows` and the HTML writer test in `test_document_formats`.
3. `refactor:` derive the export wildcard and the Export submenus from the registry. Add `export_wildcard`/`export_label` (`N_`-marked), `build_export_wildcard` and `_EXPORT_FORMATS`. Delete the `gui` wildcard constants and methods, and remove the two positive assertions in `test_dead_frame_helpers_are_removed` in the same commit. The markers in `gui` still exist, so the msgid set is unchanged.
4. `refactor:` key the document menu state by action. Add `enabled_when` and the action-keyed `get_document_menu_enabled_state`, and update `test_action_menu` and `test_sync_document_menu_state_before_document_list_exists`. `gui` binding moves to action keys in the same commit, so no step leaves label and action keys mixed.
5. `refactor:` add `ui/menu_builder.py` with `tests/test_menu_builder.py` and route the File and context menus through it. Delete `_append_document_menu_items` and `_bind_document_menu_handlers`.
6. `refactor:` mark translatable labels at their definitions. Add `N_()` in `ui/action_menu.py`, `ui/translation_menu.py`, `documents/formats.py` (`wildcard_label`, `ALL_SUPPORTED_FILES_LABEL`), `dialog.py` and `user_script.py`. Delete `_MENU_TRANSLATION_MARKERS` and `N_` from `gui`'s import, and update `SharedSetupConsumerTest` (`gui.py` to `{"_", "resource_path"}`, `dialog.py` to `{"N_", "_"}`) and replace `test_gui_menu_translation_markers_use_n_` with `test_former_marker_strings_are_still_extracted` in the same commit.

After each step, run the msgid scan. After steps 1-5 it gives 357 msgids, equal to the `.pot` and to `p12/base_msgids.json`. After step 6 it gives 353, and the only differences from both are the four group C strings.

## What Stays Identical

- File menu, Export/Export All submenus and context menu: the item order, nesting, `_()`-translated labels, IDs (`wx.ID_ANY`), the bind target (the top-level menu), the bind order, which frame method each item calls and with which format key, and the `Enable` values and their order for every combination of `has_selection`/`has_documents`.
- Menu bar: File, Translation, Help, in that order, with the same items and handlers. No accelerators or mnemonics, before or after. The keyboard shortcuts and the Ctrl+S BRL export do not change.
- Export dialog: title, `defaultFile`, wildcard text (`_()` of the same three strings), style flags, the extension correction, and conversion-before-export when `braille is None`.
- Export All: directory dialog, conflict detection, overwrite confirmation, per-document conversion, the result dialog, and the target paths.
- Exported bytes: the members and contents of the DEP zip (`<name>.txt`, `<name>.brl`, no pending-metadata member), the BRL text, and the HTML text (the same render of the same cached results, or the "No conversion data" page with its English default message when there is no cache).
- Errors: `ValueError('Unsupported export format: "<key>".')` for non-exportable formats, and `OSError` handling with the same messages.
- Import dialog wildcard and filter-index mapping. `formats.get_import_filter_labels` and `ui.import_dialog.*` do not change.
- msgids: every displayed string keeps its msgid and translation. The extracted set is the 357 baseline minus the four orphan import filters (353). `client/locales/` is not hand-edited. On the next Windows run of `generate-pot.bat` the `.pot` `#:` references shift (as in P0-5) and the four orphans leave the `.pot`.

Intentional differences, none visible to users: writers return `Path` (the HTML writer returned an `int`); the export submenu handler is captured at build time; a missing or extra menu handler, or a state entry with no menu item, now raises instead of being skipped silently; the four never-displayed orphan import-filter strings are no longer extracted.

## Test Plan

Write the characterization tests first, on the current code, so their expected values come from today's behavior. They must keep passing unchanged through steps 2-6. Only their setup may change, and only where an internal name they call was renamed.

### Characterization tests (step 1, `tests/test_gui_document_flows.py`, new class `DocumentMenuAndExportCharacterizationTest`, 11 tests)

The recording fakes (`MenuRecorder`, `RecordedMenu`, `RecordedItem`, `fake_translate`), the literal expected build log `DOCUMENT_MENU_BUILD_LOG` and the `enable_log(...)` helper live in a new helper module `tests/menu_recording.py` (no `test_` prefix, so `discover` does not collect it; no wx import, so no stub scope), so that `tests/test_menu_builder.py` compares against the same literal. Log format: `("new", "menu0")`, `("menu0", "Append", -1, "T[Open]")`, `("menu0", "AppendSubMenu", "menu1", "T[Export]")`, `("menu0", "Bind", "EVT_MENU", "menu1:T[Package DEP]")`, `("Enable", "menu0:T[Open]", False)`, `("menu0", "Destroy")`; an item is named `<owning menu>:<label>`.

These use a recording `wx.Menu` fake. `gui.wx.Menu` is patched with a factory that names each menu `menu0`, `menu1` and so on in creation order. It records `Append(id, label)`, `AppendSubMenu(submenu, label)` and `Bind(event, handler, item)`, and each returned item records its `Enable(value)` calls. `gui.wx.EVT_MENU` is patched to a sentinel (`patch.object(..., create=True)`), because under the stub every attribute access of the wx module creates a new class. `gui._` is patched to `lambda s: f"T[{s}]"`, so every label is shown to go through translation. Frame handler methods are `Mock`s set on the instance **before** the menu is built.

1. **File menu log.** `frame._create_document_menu()` records exactly: `menu0` created; `Append(-1, "T[Open]")`, `T[Delete]`, `T[Delete All]`, `T[Add]`, `T[Rename]`, `T[Import]`; `menu1` created; `menu0.AppendSubMenu(menu1, "T[Export]")`; `menu1.Append(-1, …)` with `T[Package DEP]`, `T[Braille BRL]`, `T[Dual View HTML]`; `menu2` the same for `T[Export All]`; then 12 `menu0.Bind(EVT_MENU, …)` calls in the order Open, Delete, Delete All, Add, Rename, Import, export dep/brl/html, export_all dep/brl/html; then the `Enable` calls. The expected log is written out literally in the test.
2. **Handler dispatch.** Calling each recorded handler with a fake event calls exactly one frame method: the commands call `on_open_document(event)` and so on with the event, `export/<key>` calls `on_export_document(key)`, and `export_all/<key>` calls `on_export_all_documents(key)`, with keys `dep`, `brl`, `html`.
3. **Enabled states.** Two cases, checked through the recorded `Enable` calls on the items whose labels are `T[...]` (not through dict keys). With no `document_list` and no documents: Open/Delete/Delete All/Rename/Export/Export All are `False` and Add/Import are `True`, in that order. With a `document_list` mock that has a selection and a controller with documents: all eight are `True`. This also covers `_sync_document_menu_state()` with no argument after the returned items are stored as `frame._document_menu_items`.
4. **Context menu** (two tests: `test_context_menu_on_item_selects_it_and_pops_up_below_it` and `test_keyboard_context_menu_without_selection_clears_it`). With `document_list` mocks for `ScreenToClient`, `HitTest -> (0, flags)`, `GetFirstSelected`, `GetItemRect` and `GetItemCount`, `frame.on_document_context_menu(event)` records the same append/bind log on a fresh menu, enables the items for "selection and documents", selects and focuses item 0, calls `PopupMenu(menu, (rect.x, rect.y + rect.height))` and then `Destroy()`. A second case, opened from the keyboard (`wx.DefaultPosition`) with no selected item while documents exist, clears the selection. It sets Delete All, Add, Import and Export All to `True` and the other four to `False`, and pops up at `wx.Point(0, 0)`. The keyboard case sets `frame._document_menu_items = {}`, because `_clear_document_selection()` calls `_sync_document_menu_state()` without arguments, and on the stub frame a missing attribute is a truthy no-op function (wx stub masking).
5. **Menu bar.** With `gui.wx.MenuBar` recorded and `frame.Bind` a `Mock`: the menus are added in the order `T[File]`, `T[Translation]`, `T[Help]`; Translation has `T[Convert]`, `T[Dual View]`, `T[Text Processing]`, `T[Dictionary Management...]`, `T[Settings]`, bound to the five frame handlers; Help has `T[Coseeing Website]` (`wx.ID_ANY`) and `T[About]` (`wx.ID_ABOUT`).
6. **Export dialog wildcard.** For `dep`, `brl` and `html`, `_export_document_with_dialog(Document("alpha", "t", "b"), key)` with a recording `wx.FileDialog` that returns cancel: title `T[Export Document]`, `defaultFile` `alpha.<ext>`, wildcard `T[DotExpress files (*.dep)|*.dep]` / `T[Braille files (*.brl)|*.brl]` / `T[HTML files (*.html)|*.html]`, style `FD_SAVE | FD_OVERWRITE_PROMPT`, and nothing written.
7. **Extension correction.** A dialog returning `/tmp/x/out.TXT` for `brl` writes to `/tmp/x/out.brl`, and one returning `/tmp/x/out.BRL` writes to `/tmp/x/out.BRL`. `_write_export_document` is a `Mock` in this test.
8. **Exported bytes, real writers.** In a temporary directory, with the real registry writers and `_write_export_document`: the DEP of `Document("alpha", "text", None)` has exactly the zip members `alpha.txt` = `text` and `alpha.brl` = `""`; for `Document("alpha", "text", "⠁⠃")` the BRL file is `⠁⠃` (UTF-8); the HTML for `alpha` with cached results (a small `DualViewSegment` list) equals `render_dual_view_html(build_dual_view_model(results))` computed in the test, byte for byte; the HTML for a document with no cache equals the render of `()`. Also: the HTML writer into a directory that does not exist raises `OSError` (it does not create parents), while the BRL writer still creates a missing parent directory.
9. **Export All per-document cache.** `_export_next_document([alpha, beta], dir, "html", ExportBatchResult())` with a synchronous `wx.CallAfter`, real writers, and a cache that holds only `alpha` writes `alpha.html` (alpha's render) and `beta.html` (the empty render).
10. **Ctrl+S.** `on_output_text_key_down` with key 83 and Ctrl down calls `_export_document_with_dialog(open_document, "brl")` and then `output_txt.SetFocus()`.

### Updated tests

- `tests/test_document_formats.py`: the HTML writer test passes `ExportContext(dual_view_results=(...))` as the third argument. New tests: DEP and BRL writers called with a non-empty context write the same files as with `ExportContext()`; every writer has exactly three positional parameters (`inspect.signature`) and calling it with two raises `TypeError`; every writer returns the destination `Path`; the registry invariant; `build_export_wildcard` gives the three strings for dep/brl/html (and applies `translate`) and raises `ValueError('Unsupported export format: "txt".')` for txt; `ALL_SUPPORTED_FILES_LABEL == "All Supported Files"`, `get_import_filter_labels()` ends with `ALL_SUPPORTED_FILES_LABEL` and keeps its full value `["DEP", "DOCX", "EPUB", "PDF", "TXT", "All Supported Files"]`; `ExportContext()` defaults to no results (`test_export_context_defaults_to_no_results`). The existing import wildcard test stays as it is.
- `tests/test_action_menu.py`: the four enabled-state tests become action-keyed with the same truth values. New tests: actions are unique; every `enabled_when` is one of the three rules; the labels in order are Open, Delete, Delete All, Add, Rename, Import, Export, Export All; the submenu `formats` equal `tuple((d.key, d.export_label) for d in get_exportable_formats())` and the literal `(("dep", "Package DEP"), ("brl", "Braille BRL"), ("html", "Dual View HTML"))`. The existing submenu test stays.
- `tests/test_gui_document_flows.py`: `test_write_export_document_uses_registry_writer` expects `writer(Path("/tmp/custom.dep"), document, ExportContext())`. A new sibling test checks that a cached `alpha` gives the DEP writer `ExportContext(dual_view_results=cached)` too (one uniform call). The HTML test expects `writer(path, document, ExportContext(dual_view_results=cached_results))`. `test_sync_document_menu_state_before_document_list_exists` uses action keys. In `test_dead_frame_helpers_are_removed`, delete the two `assertTrue(hasattr(gui, "DEP_WILDCARD"))`/`_get_brl_wildcard` lines: this task deliberately removes those names. No new absence guards are added (P0 review M-2). The acceptance greps below do that job.
- `tests/test_i18n.py::SharedSetupConsumerTest`: `gui.py` changes to `{"_", "resource_path"}` and `dialog.py` to `{"N_", "_"}`. This task deliberately changes which names those modules import. Redesigning the test into negative assertions (M-2) is left to the orchestrator's follow-up.
- `tests/test_i18n.py::ExtractionMarkerTest`: `test_gui_menu_translation_markers_use_n_` is replaced, in the step 6 commit, by `test_former_marker_strings_are_still_extracted`. The 44 strings of the old tuple that are still shown (48 minus the four group C orphans) must each be the literal first argument of some `_()`/`N_()` call in `client/` outside `tests/` and `.venv/` (the `generate-pot.bat` file set). It does not care where the mark sits, so it is not a placement guard, but it fails if a definition site loses its `N_()`. Its comment avoids the old constant's name so that acceptance grep 2 stays empty.

### New tests

- `tests/test_menu_builder.py` (no wx, no stub scope; imports `ui.menu_builder` directly):
  - With recording fakes and `translate=lambda s: f"T[{s}]"`, the log for the default descriptors equals the expected log from characterization test 1, without the `Enable` part (the same `DOCUMENT_MENU_BUILD_LOG` literal from `tests/menu_recording.py`).
  - Command handlers are bound as given and receive the event. Submenu handlers receive the casefolded format key. Bind target is always the top-level menu.
  - Return value: one item per action. Submenu actions map to the `AppendSubMenu` result.
  - A missing handler, or an extra one, raises `ValueError` and makes no menu calls.
  - Custom `descriptors` (one command plus one submenu with a mixed-case format key) build and bind in order.
  - `apply_document_menu_state` enables in the order given, and an unknown action raises `KeyError`.
  - `ui/menu_builder.py` has no `wx` import (AST check of its imports).
- `tests/test_action_menu.py`, `test_menu_labels_have_zh_tw_translations`: every document-menu label, every Export submenu label and every Translation-menu label has an entry with a non-empty `msgstr` in `client/locales/zh_TW/LC_MESSAGES/dotexpress.po` (a small msgid/msgstr parser in the test that skips comments and obsolete `#~` entries; there are no fuzzy entries in the `.po` today). It checks 16 labels: 8 document-menu, 3 Export submenu and 5 Translation menu labels. This keeps the purpose of the deleted marker tuple: the menus are actually translated. It checks user-visible translations, not where `N_()` is placed.

Run `tests.test_menu_builder`, `tests.test_gui_document_flows`, `tests.test_action_menu` and `tests.test_document_formats` alone, then together in several seeded shuffled orders (scratchpad `shuffle_harness.py`, seeds 1-5). `ui/menu_builder` is a new pure module imported by `gui` inside `StubScope.loading()` (P0 review note).

## Acceptance Criteria

1. `grep -n '"html"' client/gui.py` prints nothing.
2. `grep -rnE '_MENU_TRANSLATION_MARKERS|DEP_WILDCARD|BRL_WILDCARD|HTML_WILDCARD|_get_export_wildcard|_get_(dep|brl|html)_wildcard|_append_document_menu_items|_bind_document_menu_handlers' client --include='*.py'` prints nothing.
3. `grep -nE 'menu_items\["|"Delete All"|"Export All"' client/gui.py` prints nothing (no label-keyed lookups).
4. `grep -nE '\bN_\b' client/gui.py` prints nothing. `grep -nE '^(import wx|from wx)' client/ui/menu_builder.py` prints nothing.
5. msgid scan: `python -I <scratchpad>/p12/tools/msgid_scan.py client --compare <scratchpad>/p12/base_msgids.json` reports 353 source msgids. The only differences it lists, against both the `.pot` and the saved baseline, are exactly the four group C strings ("Text files (*.txt)|*.txt", "PDF files (*.pdf)|*.pdf", "Word documents (*.docx)|*.docx", "EPUB books (*.epub)|*.epub"). The tool exits 1 because of those expected differences. Any other difference fails this criterion.
6. `git diff main --stat -- client/locales scripts` is empty.
7. Focused verification passes:
   `cd client && python3 -m unittest tests.test_document_formats tests.test_action_menu tests.test_menu_builder tests.test_gui_document_flows tests.test_i18n tests.test_removed_dead_code tests.test_translation_menu tests.test_export_results tests.test_user_preprocessing_script tests.test_dictionary_management_dialog tests.test_wx_stub -v` (203 tests, OK).
8. Full suite: `cd client && python3 -m unittest discover -s tests -p "test_*.py"` reports `failures=1` (only the known P2-5 failure), `errors=0`, `skipped=7`, and 614 tests (575 plus 40 new test runs minus the one replaced marker test).
9. The shuffled runs from the Test Plan show no new failures or errors.
10. On Windows (not possible on this Linux host; tracked as verification debt, see below).

## Risks

- **User-visible menus with no wx here** (medium). wxPython is not installed, so every menu check runs against recording fakes. Mitigation: the characterization log pins every wx call (append, bind and enable order, labels, bind target), written before the change and unchanged after it. Screenshots, which AGENTS.md asks for on menu changes, cannot be taken here. They go on the Windows debt list.
- **Submenu bind target** (low). wx delivers submenu events through the top-level menu that the items are bound on today. The builder binds on the same object in the same order, and the log asserts the target.
- **Handler capture time** (low). Export submenu handlers are captured when the menu is built instead of when the event fires. Production never replaces frame methods. Tests set mocks before building.
- **Stub-scope import of a new module** (low). `ui/menu_builder` is first imported by `gui` inside the stub scope. It imports neither wx nor gui. Its test imports it directly. The shuffled runs cover module order.
- **i18n import in domain modules** (low). `documents/formats.py`, `ui/action_menu.py`, `ui/translation_menu.py` and `conversion/preprocessing/user_script.py` now import `N_` from `i18n`, which loads the catalog once when imported. `i18n` imports only the standard library, so there is no cycle and no `config` import (`test_translation_import_isolation` still holds). These modules never call `_`.
- **Strictness** (low). Mismatched handler maps and unknown state actions now raise errors. All callers build both from the same descriptors, and tests cover the mismatch paths.
- **Catalog drift** (low). Marking strings with `N_` at new places changes the `.pot` `#:` references, which refresh on Windows. Dropping the four orphans removes them from the `.pot` on that run, and their `.po` entries become obsolete. Nothing displays them, so no translation the user sees is lost. The scan criterion makes sure no other msgid disappears.
- **Overlap** (low). P1-3 owns the init-order guards in `_sync_document_menu_state`, and they are kept. P1-4 will move `_write_export_document`, `_export_next_document` and `_set_conversion_busy` into `ExportCoordinator`/`ConversionPresenter`. `ExportContext` gives it one clean writer call. D-5 (the `formats` <-> `workspace` cycle) is untouched.

## Windows verification debt

- Screenshots of the File menu, the Export and Export All submenus, and the document-list context menu (on an item, and from the keyboard menu key with no item selected), before and after, in the shipped zh_TW UI. Compare them with no documents, with documents but no selection, and with a selection.
- Manually export each format (single and Export All) from a pre-change build and a post-change build, and compare the outputs: DEP zip members and contents, BRL bytes, HTML bytes. Ctrl+S from the output editor opens the BRL save dialog.
- Run `scripts\generate-pot.bat`, and check that the regenerated `.pot` has the baseline msgid set minus exactly the four orphan import filters (besides `#:` references and the creation date). Then `msgmerge` the zh_TW `.po` (the four become obsolete `#~` entries) and recompile the `.mo`.

## Out of Scope

- Adding `"HTML"` or `"HTML files (*.html)|*.html"` to the catalog, translating the exported HTML's "No conversion data" message, and the empty `"Close"` translation. These are localization changes.
- Using `requires_braille` to skip conversion for DEP/HTML exports (a behavior change).
- `_set_conversion_busy`'s `FindMenu(_("File"))` lookup (P1-4), the init-order guards (P1-3), and `ExportCoordinator` (P1-4).
- The import dialog and `ui/import_dialog.py` forwarding helpers (refactor.md section 5.1).
- The dictionary management dialog's buttons (they are not a menu, and P0-6 already refactored that dialog).
- Redesigning `SharedSetupConsumerTest` or merging the P0 guard tests (P0 review M-2 follow-up).
- Moving `Document` or breaking the `formats` <-> `workspace` cycle (D-5).
