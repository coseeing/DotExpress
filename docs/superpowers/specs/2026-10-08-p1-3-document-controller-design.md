# Document Controller Adoption (P1-3) Design

## Goal

Finish moving document state and workspace file IO out of `BrailleFrame`. This is roadmap task P1-3 in `storage/refactor.md` (section 6.2). It covers finding P-1 (section 4.2, "Controller half adopted"), the document CRUD and disk IO part of S-1 (section 3.1, item 1 "`DocumentWorkspaceService`"), and the part of S-6 (section 3.1) that concerns workspace IO coordination.

Concretely:

- **`DocumentController` is the only owner of document state (P-1).** The controller gains the methods the frame is missing (`add_document`, `add_documents`, `load_documents`, `select_document`, `document_name_at`, `has_documents`, `first_document_name`, `documents_snapshot`, `adjacent_document_name`, `document_name_exists`, `get_dual_view_results`, `set_dual_view_results`). `BrailleFrame` loses its four forwarding properties (`documents`, `_open_document_name`, `_selected_document_name`, `_dual_view_results_by_document`), the lazy `_get_document_controller()`, and its one-line wrapper methods. It never reads or writes the controller's list, names or cache attributes directly.
- **One wx-free workspace service (S-1 item 1).** A new `documents/workspace_service.py` with `DocumentWorkspaceService(controller, workspace_dir)` does every workspace disk operation of the document flows, together with the matching controller update, in the same order as today: startup load, invalid-file deletion, save of the open document, create, import persistence, rename (write the new package, then delete the old one), delete, and Delete All with its failure rollback (reload from disk and restore the controller). The frame keeps only dialogs, confirmations, error messages, list-box refreshes and editor updates.
- **The init-order guards go away.** The controller is created in `BrailleFrame.__init__` before the menu bar is built, so `_sync_document_menu_state` no longer needs `hasattr(self, "documents")` or `hasattr(self, "_selected_document_name")`.

This is a behavior-preserving refactor. Every flow keeps its disk effects and their order, its error handling, its dialogs and messages, its selection and focus results, and the window title. No user-facing string changes, and nothing under `client/locales/` is edited.

Starting point (P0 phase review, item 5): `prepare_document_for_save(document, *, text, braille) -> Document` already has its new signature, and `batch_export_documents_to_folder` is gone. The service builds on the new signature. Nothing here revives batch export.

This spec includes the corrections and refinements from the implementation plan (`docs/superpowers/plans/2026-10-08-p1-3-document-controller.md`, section "Spec Corrections and Refinements"): acceptance criterion 3 uses word boundaries; `test_save_open_document_saves_prepared_document` is rewritten in step 5, not step 7; four case-sensitivity tests pin known defects 1 and 2 (two of them skip on each platform, so Linux reports `skipped=9`); the characterization frame uses recording fakes and one ordered event log instead of a shared `Mock` parent; its helper drops `frame.workspace_dir` in step 5; every refactor step gets a red test (`DocumentControllerOwnershipTest`, `FrameWorkspaceServiceDelegationTest`); the rewritten Delete All GUI test uses a stub service; the Delete All service tests check the order inside `on_error`; each unused import leaves `gui` in the step that stops using it; and three internal behavior notes are listed under "What Stays Identical".

## Current State (verified 2026-10-08 on `refactor/p1-3-document-controller`, HEAD `ef1988e`, P0-1..P0-6, P1-1 and P1-2 merged)

Baseline: `cd client && python -m unittest discover -s tests -p "test_*.py"` runs 614 tests, `failures=1` (the known P2-5 test), `skipped=7`. The roadmap's focused set `tests.test_document_controller tests.test_document_session tests.test_document_workspace tests.test_gui_document_flows` runs 120 tests, OK. The msgid scan reports 353 source msgids and only the four known `.pot`-only import-filter orphans.

Indentation: `gui.py` and `documents/session.py` use tabs (the `gui.py` import block has a few 4-space continuation lines; leave them). `documents/controller.py`, `documents/workspace.py` and the document tests use 4 spaces. The new `documents/workspace_service.py` and `tests/test_workspace_service.py` use 4 spaces.

### Forwarding layer (`gui.py`)

- `_get_document_controller()` 169-174 reads `self.__dict__.get("_document_controller")` and creates a controller lazily if there is none.
- Four property pairs 176-206 forward `documents`, `_open_document_name`, `_selected_document_name` and `_dual_view_results_by_document` to the controller's `documents`, `open_name`, `selected_name` and `dual_view_results_by_document`.
- `_initialize_state` 222-229 sets `self.workspace_dir = get_workspace_directory()`, creates a **second** controller (`self._document_controller = DocumentController()`), and then assigns `[]`, `None`, `None` and `{}` through the property setters.
- Why the lazy creation exists: `__init__` calls `_initialize_frame()` (which builds the menu bar and calls `_sync_document_menu_state(menu_items)`) **before** `_initialize_state()`. During that first sync the properties lazily create a throwaway controller with no documents, so the File menu starts with "no selection, no documents" enabled states. `_sync_document_menu_state` 362-371 still guards with `hasattr(self, "documents")` and `hasattr(self, "_selected_document_name")` (always true because of the properties) and `"document_list" in self.__dict__` (false during the first sync, because the list control is created later in `_create_main_layout`).
- One-line wrappers: `_get_document_names` 517, `_sort_documents` 558, `_get_document_by_name` 561, `_replace_document` 564, `_document_name_exists` 567 (calls `session.document_name_exists` on the controller's list).
- Mixed access: some flows call `self._document_controller.*` directly (rename 915, delete 943, Delete All 975 and 984). Others mutate the list through the property: `self.documents.append(document)` 761, `self.documents = documents` 822, `self.documents.extend(saved_documents)` 1015. The dual-view cache is written as `self._dual_view_results_by_document[self._open_document_name] = ...` 1379 and read at 384 and 1130.
- `DocumentController.set_state(...)` (`documents/controller.py:52-63`) has no callers.

Every `self.documents` read: 369 (`bool`), 581-590 (list refresh), 700 (adjacent document), 801 (first document), 832-834 and 841-844 (index to name), 856-859 (context menu hit), 945, 955, 978-979 (emptiness and first name), 1036, 1045, 1048 (Export All). 22 occurrences in total.

### Disk effects, messages and state, per flow

"Save first" means `_save_open_document_with_feedback()`. If it returns `False`, the flow stops and nothing else happens. `<ws>` is the workspace directory and `<ws>/<name>.dep` is `document_package_path_for_name(name, <ws>)`. "Error box" means `wx.MessageBox(template.format(error=exc), _("Error"), wx.OK | wx.ICON_ERROR, parent=self)` (`_show_file_error`). Only `OSError` is caught anywhere below. Any other exception propagates, as today.

| Flow | Location | Disk effects (in order) | On failure | State and UI afterwards |
| --- | --- | --- | --- | --- |
| Startup | `_load_startup_documents` 299-303, `_load_workspace_documents_at_startup` 819-826 | Clear editors. `ensure_workspace_directory(<ws>)` (mkdir -p), then `load_workspace_documents(<ws>)` (mkdir -p again, glob `*.dep`, load each, and collect the ones that fail to load as invalid paths; documents sorted by casefold then name). | `OSError` from mkdir or glob is not caught. | List set to the loaded documents. `_refresh_document_list()` selects the first one. Invalid-file review (next row). `_ensure_open_document_exists()` opens the first document, or creates the default document. Title updated, then focus goes to the source editor. |
| Invalid-file review | `_review_invalid_workspace_files` 733-745 | Only if there are invalid paths: `InvalidWorkspaceFilesDialog(self, invalid_paths)`. If the user chose delete, `path.unlink(missing_ok=True)` for each path, in order. | Per path: error box "Failed to delete invalid workspace file: {error}", then **continue** with the next path. | No state change. |
| Save open document | `_save_open_document` 711-723, `_save_open_document_with_feedback` 725-731 | No open name, or the open name is not in the list: nothing. Otherwise `updated = prepare_document_for_save(document, text=input, braille=output)` (`braille` stays `None` if it was pending). **The in-memory document is replaced first**, then `save_document_package(<ws>/<name>.dep, updated)`. | Error box "Failed to save document: {error}", returns `False`. Memory keeps the new content, so disk and memory differ until the next successful save. | Called before Open, Add, Rename, Delete, Delete All (only when there are documents), Import, Export, Export All, Ctrl+S, Ctrl+Tab cycling and window close. On close a failed save vetoes the close when `evt.CanVeto()` (`_on_close` 1258-1265). |
| Add | `on_add_document` 881-887, `_prompt_for_document_name` 768-789, `_create_document` 747-766 | Save first. Prompt with `DocumentNameDialog(self, title=_("Add Document"), initial_name=...)`. The name is normalized. An **exact, case-sensitive** match with an existing name shows `wx.MessageBox(_('Document "{name}" already exists.').format(name=...), _("Error"), wx.OK \| wx.ICON_ERROR, parent=self)` and re-prompts, prefilled with that name. Cancel: nothing. Then write `<ws>/<name>.dep` for `Document(name, "", "")` (braille `""`, so no pending-metadata member). | Error box "Failed to save document: {error}". No state change. | Document appended. `_refresh_document_list(name)`, then `_open_document_by_name(name)` (editors loaded, cursor at 0, list refreshed, title, dual view refreshed). Add does not move the focus. |
| Default document | `_ensure_open_document_exists` 800-805, `_create_default_document` 791-798 | Only when the list is empty: `_create_document("new", "", None, focus_input=True)`. It writes `<ws>/new.dep` **with** the pending-metadata member. | Same error box. No document is created and nothing is open. | Like Add, then focus goes to the source editor. |
| Open | `on_open_document` 872-879, `on_document_activated` 848 | Save first. | — | `_open_document_by_name(selected)`, then focus the source editor. No selection: nothing (not even the save). |
| Ctrl+Tab cycle | `_open_adjacent_document` 698-709 | Target = `get_adjacent_document_name(documents, open or selected, step)`. No target: nothing. Otherwise save first. | — | Open the target, focus the source editor. |
| Rename | `on_rename_document` 889-920 | Selected document (list selection, else the controller's selected name); none: nothing. Save first. Look the document up again; gone: nothing. Prompt "Rename Document" prefilled with the name, duplicate check excluding the current name. Cancel or the same name: nothing. Write `<ws>/<new>.dep` with the document's text and braille (a pending document stays pending). Then, **if `<ws>/<old>.dep` exists**, unlink it. | Any `OSError` from either step: error box "Failed to save document: {error}". No state change. If the unlink failed, both packages stay on disk. | `controller.rename_document(old, new)`: list entry, open and selected names, and the cache key move to the new name. `_refresh_document_list(new)`, title, dual view refreshed. The editors are not reloaded. |
| Delete | `on_delete_document` 922-952 | Selected document; none: nothing. Save first. Confirm `wx.MessageBox(_('Do you want to delete document "{name}"?').format(...), _("Confirm Delete Document"), wx.YES_NO \| wx.NO_DEFAULT \| wx.ICON_WARNING, parent=self)`; anything but `wx.YES`: nothing. If `<ws>/<name>.dep` exists, unlink it. | Error box "Failed to delete document: {error}". No state change. | `controller.delete_document(name)`: entry and cache entry removed; preferred name is the previous neighbour, else the next one; the open name moves to it if the deleted document was open; the selected name moves to it if it was the deleted one. `_refresh_document_list(selected)`. If documents remain and the deleted one was open, the preferred document is opened. If none remain: title updated, editors cleared, default document created. Dual view refreshed last. |
| Delete All | `on_delete_all_documents` 954-989 | No documents: nothing (no save, no confirm). Save first. Confirm `_("Delete All will remove all documents. Do you want to continue?")`, `_("Confirm Delete All")`, same flags. Then for each document in a **snapshot** of the list order: if `<ws>/<name>.dep` exists, unlink it. | On the **first** `OSError`: error box "Failed to delete document: {error}" **first**; then `load_workspace_documents(<ws>)` (packages already unlinked stay deleted); `controller.restore_documents_after_delete_all_failure(remaining)` (list replaced, cache kept only for names still on disk, open and selected names cleared when not on disk); `_refresh_document_list()`; invalid-file review of the reloaded invalid paths; open the first remaining document, or clear the editors (in that case the title is **not** updated and **no** default document is created); dual view refreshed; stop. An `OSError` from the reload itself propagates after the error box. | Success: `controller.delete_all_documents()` (list, names and cache cleared); title updated (shows "DotExpress"); list refreshed; editors cleared; default document created and opened; dual view refreshed. |
| Import | `on_import_document` 991-1024, `_persist_documents` 807-817 | Save first. `wx.FileDialog(self, _("Import Document"), wildcard=build_import_wildcard(_), style=wx.FD_OPEN \| wx.FD_MULTIPLE)`, filter index set to All Supported; cancel: nothing. An out-of-range filter index falls back to All Supported. `batch_import_documents(paths, format_key=..., existing_names=set(names))` (casefold duplicate check; load failures become `BatchIssue(path, str(exc))`). Then for each loaded document, in order, write `<ws>/<name>.dep`. | A failed write becomes `BatchIssue(path=<ws>/<name>.dep, reason=str(exc))` and the loop continues. The `ValueError` for an unknown format key is not caught. | Saved documents are appended in order. Exactly one saved: `_open_document_by_name(it)` (no focus change). Otherwise `_refresh_document_list(open or selected)`. Then, if `load issues + save issues` (in that order) is not empty, `FileIssuesDialog(self, title=_("Import Issues"), message=_("Some files were skipped during import."), issues=["<file name>: <reason>", ...])`. |
| Selection change | `on_document_selection_changed` 839-846, `_get_selected_document_name` 828-834, `on_document_context_menu` 851-870 | — | — | Index to name. `wx.NOT_FOUND` or an index past the end gives `None` (`_get_selected_document_name` then falls back to the controller's selected name; before `document_list` exists it returns the selected name). The context menu selects and focuses a hit item and makes it the selected name; with no hit and no keyboard selection it clears the selection. |
| List refresh | `_refresh_document_list` 578-595, `_clear_document_selection` 570-576 | — | — | Sort, rebuild the list control, select and focus the preferred name if present, else the first; set the selected name; sync menu state. An empty list sets the selected name to `None`. |
| Manual conversion done | `_complete_conversion` 1335-1384 | **No disk write.** | — | If a document is open, it is replaced in memory with (source editor text, converted braille), and `cache[open name] = output.dual_view_segments` (even if the open name is not in the list). Export conversions do not touch the cache. |
| Export, Export All, Ctrl+S | 1026-1048, 1072-1080, `_write_export_document` 1126-1131 | Save first (Export re-reads the selected document after the save). Export All iterates a copy of the list. | (P1-2, unchanged.) | The cache is read at write time for each document. |

### Tests that touch this today

- `tests/test_document_controller.py` (11 tests) and `tests/test_document_session.py` (7) test the controller and the plan functions.
- `tests/test_document_workspace.py` (20) tests packages, imports, `prepare_document_for_save` and `load_workspace_documents`.
- `tests/test_gui_document_flows.py` builds frames with `object.__new__` under the wx stub. `GuiDocumentFlowsTest._make_frame` sets state through the forwarding properties (`frame._dual_view_results_by_document = {}`, `frame._open_document_name = "alpha"`) and replaces `_get_document_by_name` and `_replace_document` with lambdas over a `frame._documents_by_name` dict, while `frame.documents` stays an empty list. 27 statements in the file set or read the properties. `test_delete_all_partial_failure_reconciles_dual_view_cache_and_refreshes_viewer` patches `gui.document_package_path_for_name` and `gui.load_workspace_documents`; `test_save_open_document_saves_prepared_document` patches `gui.save_document_package`. Both patch points move.
- No GUI test covers Add, Rename, single Delete, Delete All success, Import, startup loading, the invalid-file review, or the default document. These flows have no safety net today.
- wx stub masking (`tests/wx_stub.py`, `NoOpAttributes.__getattr__`): on a stub frame every missing instance attribute is a no-op function. A test frame without `_document_controller` therefore gets a function, not an `AttributeError`. Tests must always set the controller explicitly.

## Design

### `DocumentController` additions (`documents/controller.py`)

All new methods are small and pure. Existing methods, attributes and their behavior do not change, except that the unused `set_state` is deleted.

| Method | Behavior |
| --- | --- |
| `add_document(document)` | Append to the list. No sorting (the list refresh sorts), no duplicate check (the name prompt does that, exactly as today). |
| `add_documents(documents)` | Append each, in the given order. |
| `load_documents(documents)` | Replace the list with `list(documents)`, and clear the open name, the selected name and the dual-view cache. At startup these are already empty, so the startup result is unchanged. |
| `select_document(name)` | Set the selected name to `name` (which may be `None`). No validation, like today's assignments. |
| `document_name_at(index)` | Name at `index`, or `None` if `index < 0` (this covers `wx.NOT_FOUND == -1`) or `index >= len`. |
| `has_documents` (property) | `bool(list)`. |
| `first_document_name` (property) | Name of the first document, or `None`. |
| `documents_snapshot()` | A new `list` with the current documents. Mutating it does not affect the controller. |
| `adjacent_document_name(step)` | `get_adjacent_document_name(list, open_name or selected_name, step)`. |
| `document_name_exists(name, exclude_name=None)` | `session.document_name_exists(list, name, exclude_name=exclude_name)` (exact, case-sensitive, as today). |
| `get_dual_view_results(name)` | `cache.get(name or "", ())`. |
| `set_dual_view_results(name, results)` | `cache[name] = results`. |

The public attributes (`documents`, `open_name`, `selected_name`, `dual_view_results_by_document`) stay, because the controller's own tests use them. Outside `documents/controller.py` and its tests, nothing reads or writes them. The service and the frame use methods only. `open_document_name` and `selected_document_name` remain the read accessors.

### `DocumentWorkspaceService` (`documents/workspace_service.py`, new, no wx import)

```python
@dataclass(frozen=True)
class ImportResult:
    saved: list[Document]       # saved and added, in batch_import_documents order
    issues: list[BatchIssue]    # load issues first, then save issues


@dataclass(frozen=True)
class DeleteAllResult:
    completed: bool             # False after a failure and rollback
    invalid_paths: list[Path]   # invalid packages found by the rollback reload, else []


class DocumentWorkspaceService:
    def __init__(self, controller: DocumentController, workspace_dir: Path) -> None: ...
    @property
    def workspace_dir(self) -> Path: ...
    def package_path(self, name: str) -> Path: ...
    def load_documents(self) -> list[Path]: ...
    def delete_invalid_files(self, paths: Iterable[Path], *, on_error: Callable[[OSError], None]) -> None: ...
    def save_open_document(self, *, text: str, braille: str) -> Document | None: ...
    def create_document(self, document: Document) -> None: ...
    def import_files(self, paths: Iterable[Path], *, format_key: str) -> ImportResult: ...
    def rename_document(self, source_name: str, new_name: str) -> Document | None: ...
    def delete_document(self, name: str) -> DeleteDocumentDecision: ...
    def delete_all_documents(self, *, on_error: Callable[[OSError], None]) -> DeleteAllResult: ...
```

`workspace_dir` is required and has no default. The service never calls `get_workspace_directory(None)`. The frame passes `get_workspace_directory()`, so P2-6 can later pass `ApplicationPaths.workspace` instead. The service reuses `documents/workspace.py` (`save_document_package`, `document_package_path_for_name`, `ensure_workspace_directory`, `load_workspace_documents`, `batch_import_documents`, `prepare_document_for_save`) and changes none of them.

Each method does exactly what the table above lists for its flow, in the same order:

- `load_documents()`: `ensure_workspace_directory(dir)`, `load_workspace_documents(dir)`, `controller.load_documents(documents)`, then return the invalid paths. `OSError` propagates.
- `delete_invalid_files(paths, on_error)`: `path.unlink(missing_ok=True)` for each path; on `OSError` call `on_error(exc)` and continue.
- `save_open_document(text, braille)`: returns `None` with no IO when there is no open document or it is not in the list. Otherwise `prepare_document_for_save`, then `controller.replace_document(updated)`, then `save_document_package(package_path(name), updated)`, and returns `updated`. The memory update happens **before** the write, as today. `OSError` propagates.
- `create_document(document)`: `save_document_package(package_path(document.name), document)`, then `controller.add_document(document)`. On `OSError` the controller is not touched, and the error propagates.
- `import_files(paths, format_key)`: `batch_import_documents(paths, format_key=format_key, existing_names=set(controller.document_names))`, then write each loaded document; a failed write becomes `BatchIssue(path=package_path(name), reason=str(exc))`. Then `controller.add_documents(saved)`. Returns `ImportResult(saved, load_issues + save_issues)`. `ValueError` for an unknown format key propagates, as today.
- `rename_document(source_name, new_name)`: `ValueError` with no IO if the two names are equal (the frame never calls it that way; the guard stops the method from deleting the package it just wrote). Returns `None` with no IO if the source is not in the list. Otherwise writes `package_path(new_name)` with `Document(new_name, source.text, source.braille)`, then unlinks `package_path(source_name)` if it exists, then returns `controller.rename_document(source_name, new_name)`. An `OSError` from either step propagates and the controller is not touched.
- `delete_document(name)`: unlinks `package_path(name)` if it exists, then returns `controller.delete_document(name)`. On `OSError` the controller is not touched, and the error propagates. The frame only calls it for a document in the list, as today.
- `delete_all_documents(on_error)`: for each document of `controller.documents_snapshot()`, unlink its package if it exists. On the first `OSError`: call `on_error(exc)` **first**, then `load_workspace_documents(dir)`, then `controller.restore_documents_after_delete_all_failure(remaining)`, and return `DeleteAllResult(False, invalid_paths)`. If the reload raises, that error propagates after `on_error` has run, as today. On success: `controller.delete_all_documents()` and return `DeleteAllResult(True, [])`.

Why a callback for Delete All, but exceptions elsewhere: in every other flow the error box is the only thing that happens after the failure, so the frame can catch the `OSError`. In Delete All the error box comes **before** the reload, and the reload can itself fail. A callback keeps that order exactly. This is the "pure presenter plus callables" style that refactor.md section 4.3 and `dictionaries/name_prompt.py` already use.

The service holds a reference to the controller. The frame creates both once and never replaces either. Tests that need a different controller build a new service with it (see the test helper below).

### `BrailleFrame` (`gui.py`)

Construction:

- `__init__` creates `self._document_controller = DocumentController()` right after `self.translation_runtime = runtime`, before `_initialize_frame()`. The first menu sync therefore sees a real, empty controller, which gives the same "no selection, no documents" states as today's throwaway controller.
- `_initialize_state` no longer creates a controller and no longer assigns the four state values. It replaces `self.workspace_dir = get_workspace_directory()` with `self._workspace_service = DocumentWorkspaceService(self._document_controller, get_workspace_directory())`. `get_workspace_directory` stays imported in `gui` (tests patch it there).
- The `workspace_dir` attribute is removed. Its only readers were the document flows, which now go through the service.

Deleted from `gui.py`: `_get_document_controller`, the four property pairs, `_get_document_names`, `_sort_documents`, `_get_document_by_name`, `_replace_document`, `_document_name_exists`, `_persist_documents`, and the imports that become unused (`document_name_exists`, `get_adjacent_document_name`, `document_package_path_for_name`, `ensure_workspace_directory`, `load_workspace_documents`, `prepare_document_for_save`, `save_document_package`, `batch_import_documents`; `BatchIssue`, `Document`, `DEFAULT_DOCUMENT_NAME`, `create_default_document` and `normalize_document_name` stay because the frame still uses them). Each import is dropped in the step that stops using it (see the migration steps); the only unused import left in `gui` is the pre-existing `ConversionStageError` (P1-4).

Kept, with the same names and the same callers: `_save_open_document`, `_save_open_document_with_feedback`, `_create_document`, `_create_default_document`, `_ensure_open_document_exists`, `_prompt_for_document_name`, `_review_invalid_workspace_files`, `_load_workspace_documents_at_startup`, `_refresh_document_list`, `_clear_document_selection`, `_open_document_by_name`, `_open_adjacent_document`, `_get_selected_document_name`, `_get_selected_document`, `_sync_document_menu_state`, `_update_window_title`, `_render_dual_view_for_open_document`, `_write_export_document`, `_complete_conversion`, and every `on_*` handler. Keeping these names lets the characterization tests and the P1-2 tests run unchanged against the new code.

How each kept method changes (bodies only):

- `_sync_document_menu_state`: the guard becomes `if not target_items: return`. The `"document_list" in self.__dict__` check stays (the list control still does not exist during the first sync). `has_documents=self._document_controller.has_documents`.
- `_update_window_title`, `_render_dual_view_for_open_document`, `_write_export_document`, `on_output_text_key_down`, `_complete_conversion`: read `open_document_name`, `get_document`, `get_dual_view_results`; `_complete_conversion` writes with `replace_document` and `set_dual_view_results`.
- `_clear_document_selection`, `_refresh_document_list`, `on_document_selection_changed`, `on_document_context_menu`, `_get_selected_document_name`: use `select_document`, `sort_documents`, `document_names`, `selected_document_name` and `document_name_at`. `_refresh_document_list` inserts from `document_names` and selects `names.index(selected)`. That is the same first match as today's loop, because names are unique.
- `_open_adjacent_document`: `adjacent_document_name(step)`. `_ensure_open_document_exists`: `first_document_name`. `_prompt_for_document_name`: `document_name_exists`.
- `_save_open_document`: `self._workspace_service.save_open_document(text=self.input_txt.GetValue(), braille=self.output_txt.GetValue())`.
- `_create_document`: builds the `Document`, calls `create_document` inside the existing `try/except OSError` with the same error box, then refreshes, opens and focuses as today.
- `_load_workspace_documents_at_startup`: `invalid_paths = self._workspace_service.load_documents()`, then the same refresh, review, ensure and title calls.
- `_review_invalid_workspace_files`: the dialog part is unchanged; the deletion is `delete_invalid_files(invalid_paths, on_error=lambda exc: self._show_file_error(_("Failed to delete invalid workspace file: {error}"), exc))`.
- `on_import_document`: dialog part unchanged; then `result = self._workspace_service.import_files(source_paths, format_key=format_key)`, the same open-or-refresh branch on `len(result.saved) == 1`, and `_show_file_issues_dialog(..., result.issues)`.
- `on_rename_document`: prompt part unchanged; then `try: renamed = self._workspace_service.rename_document(selected_document.name, new_name)` with the same `except OSError` error box ("Failed to save document: {error}"); `None` returns; then the same refresh, title and dual-view calls.
- `on_delete_document`: confirmation unchanged; then `try: decision = self._workspace_service.delete_document(name)` with the same error box ("Failed to delete document: {error}"); the rest reads `has_documents`, `selected_document_name` and `open_document_name`.
- `on_delete_all_documents`: emptiness check through `has_documents`; confirmation unchanged; `result = self._workspace_service.delete_all_documents(on_error=lambda exc: self._show_file_error(_("Failed to delete document: {error}"), exc))`. If `not result.completed`: `_refresh_document_list()`, `_review_invalid_workspace_files(result.invalid_paths)`, open `first_document_name` or clear the editors, refresh the dual view, return. Otherwise the same success tail as today.
- `on_export_all_documents`: `has_documents` and `documents_snapshot()` (one snapshot for both the conflict scan and the batch, which is the same list today).

The `_("...")` literals stay in `gui.py`, at the same call sites, so the msgid set and the `.pot` references do not change.

### Migration steps (each step is one green commit; the plan details them)

1. `test:` add the characterization tests (Test Plan, part A) to `tests/test_gui_document_flows.py`. They pass on today's code.
2. `refactor:` add the controller methods and delete `set_state`, with their tests in `tests/test_document_controller.py`. `gui` does not use them yet.
3. `refactor:` add `documents/workspace_service.py` and `tests/test_workspace_service.py` (part B), written test-first. `gui` does not use it yet.
4. `refactor:` move the frame to controller methods. Create the controller in `__init__`; delete the forwarding properties, `_get_document_controller` and the one-line wrappers; drop the two `hasattr` guards; replace every state read and write listed above (including `_complete_conversion` and the export reads). Drop the `document_name_exists` and `get_adjacent_document_name` imports. Disk IO still runs in `gui`, reading the directory from `self.workspace_dir`. In the same commit, update the setup of the existing GUI tests (part C), because the properties they assign no longer exist. Red test first: `DocumentControllerOwnershipTest` (the controller exists before `_initialize_frame()` builds the menu bar; `_initialize_state` keeps it).
5. `refactor:` route startup, the invalid-file review, save of the open document and Add/default creation through the service. `_initialize_state` creates the service and drops `workspace_dir`; the remaining direct IO in rename, delete, Delete All and import reads `self._workspace_service.workspace_dir` until steps 6-7. Drop the `ensure_workspace_directory` and `prepare_document_for_save` imports. Rewrite `test_save_open_document_saves_prepared_document` as a temporary-directory test (from this step on the service writes through `documents.workspace_service.save_document_package`, so the old `gui.save_document_package` patch would no longer intercept the write). The characterization helper's `frame.workspace_dir` line becomes the service line. Red tests first: `FrameWorkspaceServiceDelegationTest` (a `Mock` service).
6. `refactor:` route Import through the service; delete `_persist_documents` and the `batch_import_documents` import. One more delegation test.
7. `refactor:` route Rename, Delete and Delete All through the service, delete the now-unused `document_package_path_for_name`, `load_workspace_documents` and `save_document_package` imports from `gui`, and rewrite `test_delete_all_partial_failure_reconciles_dual_view_cache_and_refreshes_viewer`, which patched `gui.document_package_path_for_name` and `gui.load_workspace_documents` (part C). Six more delegation tests.

The characterization tests from step 1 must pass unchanged after every step. Only their shared setup helper may change: in step 5 its `frame.workspace_dir = self.workspace` line becomes `frame._workspace_service = DocumentWorkspaceService(frame._document_controller, self.workspace)`. From step 5 on `gui` must not read `workspace_dir`; on a stub frame a stray read would get a no-op function and fail loudly.

## What Stays Identical

- For every flow in the table: the save-first call and its abort, the confirmation dialogs (text, title, flags), the disk operations and their order, which exception type is caught and where, the error box templates and titles, and what happens to the list, the open and selected names, the cache, the editors, the focus and the title.
- Package contents: members and pending metadata are written by the unchanged `save_document_package`. Add writes no pending member; the default document and pending documents do.
- The exact, case-sensitive duplicate check of the name prompt and the casefold duplicate check of Import.
- Startup order: list, invalid-file review, default document, title, focus.
- Menu states, including the first sync before the document list exists (the P1-2 characterization log of `_create_document_menu` is unchanged).
- msgids: no string is added, removed or moved to another module. `client/locales/` and `scripts/` are not touched.

Intentional differences, none visible to users: the controller is created once in `__init__` instead of lazily plus once more in `_initialize_state`; `load_documents` also clears the open and selected names and the cache, which are already empty at startup; `DocumentController.set_state` is deleted; `rename_document` on the service refuses equal names with a `ValueError` (unreachable from the GUI); `_save_open_document` now reads both editors even when no document is open (the service then does nothing); `document_name_at` returns `None` for every negative index, where today's `self.documents[selection]` would have wrapped for `-2` and below (`wx` only returns `-1` or a valid index); `load_documents` replaces the cache dict instead of clearing it in place (nothing else holds a reference).

## Test Plan

### A. Characterization tests (step 1, `tests/test_gui_document_flows.py`, new class `DocumentWorkspaceFlowsCharacterizationTest`)

Written first, against today's code, with expected values taken from today's behavior. Each test uses a real temporary workspace directory and a real `DocumentController`. A class helper `_make_workspace_frame(documents=(), open_name=None, selected_name=None)` builds the frame with `object.__new__` on the test's temporary `self.workspace`, sets `frame._document_controller = DocumentController(...)` and `frame.workspace_dir = self.workspace`, and uses recording fakes instead of `Mock`s: `_FakeEditor` for `input_txt` and `output_txt` (holds its value, records `SetFocus`) and `_FakeDocumentList` for `document_list` (holds items and the selection, so `_refresh_document_list` and the selection lookups run for real). `SetTitle` records the title. It also sets `_dual_view_frame = None`, `_document_menu_items = {}` and a `Mock` conversion runner that is not running. In step 5 the helper's `frame.workspace_dir` line becomes `frame._workspace_service = DocumentWorkspaceService(frame._document_controller, self.workspace)`. That is the only change these tests get. Assertions read state through `frame._document_controller` attributes (they exist before and after) and read the disk with `load_document_package` and directory listings.

Dialogs are patched on `gui`: `wx.MessageBox` (records calls, returns `wx.YES` or `wx.NO`), `DocumentNameDialog` (a fake that returns queued names, or cancels), `wx.FileDialog` (returns paths and a filter index), `InvalidWorkspaceFilesDialog` (records paths, returns a delete choice), and `FileIssuesDialog` (records title, message and issue lines). Each fake, `SetTitle` and the editors' `SetFocus` append to one ordered `self.events` list (this replaces a shared `Mock` parent with the same purpose); `self.answers` and `self.names` queue the message-box answers and the dialog names (`None` cancels).

Faults are injected through the file system, not by patching module functions, so the same test works whether `gui` or the service does the IO: a **directory** at `<ws>/<name>.dep` makes the package write fail (`zipfile` cannot open a directory for writing) and makes `unlink()` fail (`IsADirectoryError` on Linux, `PermissionError` on Windows and macOS; both are `OSError`). The load step treats such a directory as an invalid package. Error boxes are checked by title (`_("Error")`), flags, parent, and a message that starts with the template text and contains the failing package's file name (part of `str(exc)` on every platform; the full path is not, because Windows doubles backslashes in the message).

Cases:

1. Add: saves the open document first; the prompt result `beta` writes `beta.dep` with braille `""` and no pending member; names `[alpha, beta]`; `beta` open and selected; editors loaded; title `beta - DotExpress`.
2. Add, duplicate then valid: first name `alpha` shows `Document "alpha" already exists.` and re-prompts with `initial_name="alpha"`; the second name is created.
3. Add, write failure (`beta.dep` is a directory): one error box "Failed to save document: ..."; the controller is unchanged; `alpha` stays open.
4. Default document: with an empty controller, `_ensure_open_document_exists()` writes `new.dep` with the pending member and opens `new`; the source editor gets the focus.
5. Startup, empty workspace: `_load_workspace_documents_at_startup()` creates the directory and the `new` document.
6. Startup, invalid packages: a corrupt `bad.dep` and a valid `good.dep`; the review dialog receives `[bad.dep]`; choosing delete removes it; `good` is opened.
7. Startup, invalid-file deletion error: two invalid entries where the first cannot be deleted (a non-empty directory); error box "Failed to delete invalid workspace file: ..." once, and the second entry is still deleted.
8. Save open document: memory and `alpha.dep` both hold the editor text; a pending document stays pending (pending member present).
9. Save open document, write failure: `_save_open_document_with_feedback()` returns `False` with "Failed to save document: ..."; memory already holds the new text (pins the memory-first order).
10. Close with a failing save: `_on_close` vetoes the event.
11. Rename success: `alpha.dep` gone, `gamma.dep` holds alpha's content (pending state preserved); names, open and selected names and the cache key move to `gamma`; title `gamma - DotExpress`.
12. Rename when the old package is missing: `gamma.dep` written, no error.
13. Rename, write failure (`gamma.dep` is a directory): "Failed to save document: ..."; `alpha.dep` intact; controller unchanged.
14. Rename, unlink failure (the selected, not open, document's package is a directory): "Failed to save document: ..."; the new package exists and the old entry remains; controller unchanged (pins known defect 3).
15. Rename cancelled, and rename to the same name: no disk change besides the save-first write; controller unchanged.
16. Delete the open middle document: file gone; the previous neighbour is opened; its cache entry is kept and the deleted one is dropped.
17. Delete a selected document that is not open: the open document and editors stay.
18. Delete the last document: `new` is created and opened.
19. Delete answered No: nothing changes.
20. Delete, unlink failure: "Failed to delete document: ..."; state unchanged.
21. Delete All success: every package gone; `new` created and opened; cache empty.
22. Delete All failure: `alpha.dep` file, `beta.dep` directory, `gamma.dep` file. `alpha.dep` is deleted, the error box comes before the review dialog (checked in the ordered `self.events` log), the review dialog receives `[beta.dep]`, the controller holds `[gamma]`, the cache keeps only `gamma`, and `gamma` is opened.
23. Delete All failure where nothing valid remains: the editors are cleared, no `new` document is created, and `SetTitle` is not called after the failure (pins known defect 4).
24. Delete All with no documents: no save, no confirmation.
25. Import two `.txt` files: both packages written; names added; the open document stays open; no issues dialog.
26. Import one file: it is opened.
27. Import with a duplicate and a write failure: the issues dialog shows `Import Issues` / `Some files were skipped during import.` and the load issue line before the save issue line (`<name>.dep: <reason>`); only the saved document is added.
28. Selection change: index 1 selects the second name; `wx.NOT_FOUND` and an index past the end select `None`.
29. Case-only rename (`Alpha` to `alpha`) on a case-sensitive file system: only `alpha.dep` remains and holds the document. Skips on a case-insensitive file system.
30. Case-only rename on a case-insensitive file system: the package is deleted while the controller holds `alpha` (pins known defect 1). Skips on a case-sensitive file system (Linux).
31. Add `Alpha` while `alpha` exists, on a case-sensitive file system: both packages exist and `alpha.dep` is unchanged. Skips on a case-insensitive file system.
32. Add `Alpha` while `alpha` exists, on a case-insensitive file system: the single package now has `Alpha.*` members (pins known defect 2). Skips on a case-sensitive file system (Linux).

Cases 29-32 probe the file system at run time (`<ws>/case-probe` against `<ws>/CASE-PROBE`) instead of guessing from `sys.platform`. Every test that pins a known defect carries a `# KNOWN BUG (P1-3 spec, known defect N)` comment that says it pins today's behavior, not the desired one, so that the fix task knows to flip it.

The existing `test_delete_all_partial_failure_reconciles_dual_view_cache_and_refreshes_viewer` stays in step 1 and is rewritten in step 7 (part C).

### B. `tests/test_workspace_service.py` (new, step 3, no wx and no stub scope)

Test-first, with temporary directories and a real `DocumentController`:

- `load_documents`: creates the directory, loads sorted documents into the controller, returns the invalid paths, clears open and selected names.
- `delete_invalid_files`: deletes each path, calls `on_error` once for a failing path, and continues.
- `save_open_document`: memory and disk updated; pending braille kept pending; no open document gives `None` and no file; on a write failure the error propagates **after** the controller was updated.
- `create_document`: package written then added; on failure nothing is added and the error propagates.
- `import_files`: saved documents added in order; a write failure becomes a `BatchIssue` with the package path and `str(exc)`; load issues come before save issues; an unknown format key raises `ValueError`.
- `rename_document`: the new package holds the source content and **the old package is deleted**; a missing old package is fine; a write failure and an unlink failure each propagate with the controller unchanged (and, for the unlink failure, both packages on disk); an unknown source gives `None` and no IO; equal names raise `ValueError` and leave the package in place. The unlink-failure test pins known defect 3.
- `delete_document`: package deleted, decision returned and applied; a missing package is fine; an unlink failure propagates with the controller unchanged.
- `delete_all_documents`: success clears disk, list, names and cache, and returns `completed=True`; **on failure** packages before the failing one are deleted, `on_error` is called exactly once and before the reload (checked by recording the directory listing and the controller's names inside the callback: the names are still the original ones, so the restore has not run yet; the listing alone cannot tell, because the reload does not change the disk), the controller matches the disk afterwards, the cache keeps only names still on disk, open and selected names are cleared when gone, the invalid paths are returned, and the remaining documents are not touched; a reload that fails (the test replaces the workspace with a file inside `on_error`) propagates after `on_error`, with the controller unchanged.
- The module imports neither `wx` nor `gui` (AST check of its imports).

### C. Updated tests

- `tests/test_document_controller.py`: tests for every new method (including `document_name_at(-1)`, an index past the end, the snapshot being a copy, `load_documents` clearing names and cache, and `adjacent_document_name` using the open name before the selected one).
- `tests/test_gui_document_flows.py`:
  - `GuiDocumentFlowsTest._make_frame(documents=(Document("alpha", "source", None),), open_name="alpha")` builds `frame._document_controller = DocumentController(...)` and, from step 5, a service on a placeholder directory. The `_documents_by_name` dict and the `_get_document_by_name`/`_replace_document` lambdas are deleted; tests read documents through the controller.
  - Tests that need an empty workspace pass `documents=()`: `test_sync_document_menu_state_before_document_list_exists`, and `DocumentMenuAndExportCharacterizationTest._make_menu_frame` (its expected logs assume no documents until `_select_first_of`). `_select_first_of` loads its names with `frame._document_controller.load_documents(...)`.
  - Every `frame.documents = ...`, `frame._open_document_name = ...`, `frame._selected_document_name = ...` and `frame._dual_view_results_by_document[...]` becomes a controller constructor argument or a controller method call (`select_document`, `set_dual_view_results`), and every read becomes `open_document_name`, `selected_document_name` or `get_dual_view_results`. Test bodies and expected values do not change.
  - `_initialize_state_with_loaded_tables` and `test_initialize_state_wires_presenter_to_active_dictionary` set `frame._document_controller = DocumentController()` before calling `_initialize_state` (stub masking would otherwise hand the service a function).
  - `test_save_open_document_saves_prepared_document` becomes, in step 5, a temporary-directory test of the same expectation (the package holds `Document("alpha", "edited", "edited braille")`).
  - `test_delete_all_partial_failure_reconciles_dual_view_cache_and_refreshes_viewer` keeps its scenario and assertions, in step 7, with a stub service: its `delete_all_documents` calls `on_error`, restores `[beta]` through the controller and returns `DeleteAllResult(completed=False, invalid_paths=[])`. The test also checks the error box and the review call now. A file-system fault cannot make `beta`'s unlink fail while `beta` reloads as a valid document (a directory package is invalid on reload); the real file-system rollback is covered by characterization case 22 and the service tests.
  - New positive contract tests, red first, which P1-4 can reuse (not absence guards): `DocumentControllerOwnershipTest` (step 4: `test_frame_creates_its_controller_before_building_the_menu_bar`, `test_initialize_state_keeps_the_frame_controller`) and `FrameWorkspaceServiceDelegationTest` (steps 5-7, 13 tests: `test_initialize_state_creates_service_for_frame_controller`, and for each flow, with a `Mock` service, that the frame hands its IO to the service with the right arguments and shows the service's result and errors through the same frame calls).
- No new absence guards (P0 review M-2). The acceptance greps do that job. `test_dead_frame_helpers_are_removed` is not extended.

Run the touched modules alone, then together in several seeded shuffled orders (scratchpad `shuffle_harness.py`, seeds 1-5). `documents.workspace_service` is a new pure module that `gui` first imports inside `StubScope.loading()`, so module order matters (P0 review note and I-1).

## Acceptance Criteria

1. `grep -nE '@property|\.setter|_get_document_controller' client/gui.py` prints nothing.
2. `grep -nE '\.(documents|open_name|selected_name|dual_view_results_by_document)\b' client/gui.py` prints nothing (no direct state access, no `self.documents` list manipulation).
3. `grep -nE '\b(save_document_package|load_workspace_documents|ensure_workspace_directory|document_package_path_for_name|batch_import_documents|prepare_document_for_save)\b|\.unlink\(' client/gui.py` prints nothing (all workspace IO is in the service). The word boundaries are needed: `load_workspace_documents` is a substring of the kept method `_load_workspace_documents_at_startup`, so the pattern without them prints that method and its caller even after a correct migration.
4. `grep -nE '_sort_documents|_get_document_by_name|_replace_document|_document_name_exists|_get_document_names|_persist_documents|\bworkspace_dir\b' client/gui.py` prints nothing.
5. `grep -nE 'hasattr\(self, "(documents|_selected_document_name)"\)' client/gui.py` prints nothing.
6. `grep -nE '^(import wx|from wx)|^from gui|^import gui' client/documents/workspace_service.py client/documents/controller.py` prints nothing. `grep -n 'set_state' client/documents/controller.py` prints nothing.
7. `grep -nE '\.(documents|open_name|selected_name|dual_view_results_by_document)\b' client/documents/workspace_service.py` prints nothing (the service uses controller methods only). This is also why `ImportResult` names its field `saved`, not `documents`.
8. `git diff main --stat -- client/locales scripts` is empty, and the msgid scan prints the same output as before the task (353 source msgids, only the four known `.pot`-only orphans).
9. Roadmap verification passes: `cd client && python3 -m unittest tests.test_document_controller tests.test_document_session tests.test_document_workspace tests.test_workspace_service tests.test_gui_document_flows -v`. Also `tests.test_removed_dead_code tests.test_menu_builder tests.test_action_menu tests.test_wx_stub`. (202 tests, `OK (skipped=2)`; 47 tests, OK.)
10. Full suite: `cd client && python3 -m unittest discover -s tests -p "test_*.py"` reports `failures=1` (only the known P2-5 failure), `errors=0`, and 696 tests (614 plus 82 new). On Linux it reports `skipped=9`: the 7 Windows-only liblouis skips plus the two case-insensitive file-system tests (cases 30 and 32); on Windows the two case-sensitive ones (cases 29 and 31) skip instead.
11. The shuffled runs show no new failures or errors.
12. On Windows: see the verification debt below (not possible on this Linux host).

## Risks

- **Init order** (medium). Removing the lazy controller would break the first menu sync if the controller were created later. Mitigation: it is created in `__init__` before `_initialize_frame()`. The P1-2 characterization log of `_create_document_menu` (with its `Enable` calls) is unchanged and covers this.
- **Stub masking in tests** (medium). On a stub frame a missing `_document_controller` or `_workspace_service` is a no-op function. Mitigation: every frame helper sets both explicitly, and the characterization assertions check real disk and controller state, so a silently missing object fails loudly.
- **Order of side effects** (medium). Three flows depend on order: save (memory before disk), rename (write before unlink) and Delete All (error box before reload). Characterization tests 9, 13, 14, 22 and the service tests pin each one. The Delete All callback keeps the order even when the reload itself fails.
- **Controller identity** (low). The service holds the controller. If a test or later code replaced `frame._document_controller`, the service would update a stale object. Mitigation: production creates both once; the test helpers build them together; the plan has no code path that reassigns the controller.
- **Patch-point churn** (low). Two GUI tests patched functions imported into `gui`. They are rewritten to use the file system, so they do not depend on where the IO lives.
- **Stub-scope import of a new module** (low). `documents.workspace_service` imports only `documents.*` and the standard library. Its own test imports it directly. The shuffled runs cover module order.
- **Overlap with P1-4** (low). P1-4 will move `_write_export_document`, `_export_next_document` and `_complete_conversion` into `ExportCoordinator` and `ConversionPresenter`. After this task they read and write the cache only through `get_dual_view_results` and `set_dual_view_results`, which P1-4 can inject.
- **Windows-only file behavior** (medium, unverifiable here). On Windows, `unlink` fails when another program holds the file open, which is the real-world trigger of the Delete All rollback. The tests use a directory to fail `unlink`, which also fails on Windows (`PermissionError`), but the locked-file case can only be checked by hand.

## Known defects found during this investigation (not fixed here)

These exist on `main` today. This task keeps the behavior identical. They are listed so that a follow-up can decide on a fix.

1. **Case-only rename deletes the document on case-insensitive file systems (Windows, default macOS).** Renaming `Alpha` to `alpha` passes the duplicate check (it excludes the current name and is case-sensitive), writes `alpha.dep` (which on Windows is the same file as `Alpha.dep`), and then `Alpha.dep` "exists" and is unlinked. The package is gone; the document disappears on the next start.
2. **Add with a name that differs only in case overwrites another document's package on Windows.** The prompt's duplicate check is case-sensitive, so `Alpha` is accepted when `alpha` exists. The write replaces `alpha.dep`. Its members are named `Alpha.*`, so on the next start the file fails the name check and is reported as invalid. Import does not have this problem, because it compares casefolded names.
3. **A failed unlink during rename leaves both packages on disk,** while the in-memory list keeps only the old name. The next start shows both documents.
4. **A Delete All rollback that leaves no valid document** clears the editors but does not update the title and does not create the default document.

The tests that pin them, each marked with a `KNOWN BUG` comment, are: defect 1 `test_case_only_rename_on_case_insensitive_file_system_deletes_package` and defect 2 `test_add_case_variant_on_case_insensitive_file_system_overwrites_package` (both run only on case-insensitive file systems), defect 3 `test_rename_unlink_failure_leaves_both_packages_and_state` and the service test `test_rename_unlink_failure_propagates_and_leaves_both_packages`, and defect 4 `test_delete_all_failure_without_valid_document_clears_editors_only`. A fix task flips them.

A fix for 1 and 2 would compare names with `casefold()` in the prompt (and skip the unlink when the old and new paths are the same file). That is a user-visible behavior change and belongs in its own task.

## Windows verification debt

- Run `tests.test_gui_document_flows` on Windows (and, if available, macOS): the two case-insensitive tests (cases 30 and 32) run there and must pass, pinning known defects 1 and 2 as they are; the two case-sensitive ones skip. The directory-as-package faults raise `PermissionError` there instead of `IsADirectoryError`; the tests rely only on `OSError` and the file name in the message.
- Walk through Add, Rename, Delete, Delete All, Import (single and multiple files, with a duplicate), Ctrl+Tab and window close on a packaged build, before and after, and compare the workspace folder contents and the list, title and editor state.
- Delete All with one `.dep` held open by another program (for example in a zip tool), to trigger the rollback: the error box, then the invalid-file dialog if any, then the reloaded list.
- Start with a corrupt `.dep` in the workspace and check the invalid-file dialog and both of its choices.
- No menu, dialog or string changes, so no screenshots and no `generate-pot.bat` run are needed for this task.

## Out of Scope

- Splitting `documents/workspace.py` into `documents/package.py` and `documents/batch.py`, and merging the two `choose_selection_after_delete` functions into `shared/selection.py` (the rest of S-6; P2-level work).
- The known defects above.
- `ExportCoordinator`, `ConversionPresenter`, `_show_file_error`'s unused `parent` parameter (M-9), and the unused `ConversionStageError` import in `gui` (all P1-4 territory).
- Injecting `ApplicationPaths` into `BrailleFrame` (P2-6). The service already takes its directory as a parameter.
- Reordering `_initialize_frame` and `_create_main_layout` so that the `document_list` guard disappears too.
- Making the controller's attributes private or read-only.
- Indentation changes (P2-8).
