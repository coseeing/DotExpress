# Dead Code Removal (P0-3) Design

## Goal

Delete the dead code and dead APIs listed in `storage/refactor.md` section 5.4, and adjust tests that exist only for those APIs. This is roadmap task P0-3 (section 6.1). Removing them now shrinks the surface that P1 tasks have to split or move.

This is a behavior-preserving cleanup. No user-visible behavior, string, translation, persisted data or build input changes.

## Method (verified 2026-10-08 on `refactor/p0-3-dead-code`, HEAD `e5fa59a`, P0-1 and P0-2 merged)

For every name in section 5.4, plus the sibling helpers the deletions orphan:

1. `grep -rn` over `client/` (production and tests), `scripts/` (including `scripts/tests/`) and `server/`, for `*.py`, `*.bat`, `*.spec`, `*.toml`, `*.cfg` and `*.txt`.
2. Dynamic lookups: every `getattr`, `importlib` and `__import__` in `client/` and `scripts/`. None of them names any item below. They only read `sys.frozen`, wx/pdf/os attributes, `ctypes.WINFUNCTYPE` and `libmathcat_py`.
3. Packaging: there is no PyInstaller `.spec` in the repo. `scripts/build-dotexpress.bat` runs `pyinstaller ... gui.py` with only `--add-data` and `--collect-data latex2mathml`, and has no `--hidden-import`. The bundle is built from what `gui.py` imports, so a module that nothing imports, such as `dictionaries/import_flow.py`, is not packaged today.
4. Intent: `git log -S<name>` for every item that is used only by tests, to tell leftovers apart from APIs that were prepared on purpose.

Classes: **(a)** no caller anywhere, so delete. **(b)** only tests call it, so decide per item. **(c)** live, so keep and note that the review was wrong.

Baseline: full client suite `Ran 449 tests`, `FAILED (failures=1, skipped=7)`. The one failure is the known P2-5 case `test_conversion_service ... test_translate_with_language_does_not_duplicate_existing_spaces_around_math`.

## Item Inventory and Decisions

Line numbers are for HEAD `e5fa59a`.

### `client/gui.py` (tabs)

| Item | Evidence | Class | Decision |
| --- | --- | --- | --- |
| `IMPORT_WILDCARDS` 149-155 | Only the definition matches. Import dialogs use `ui.import_dialog.build_import_wildcard(_)` (`gui.py:1168`). Left over from `df01017`. | a | Delete. |
| `PDF_WILDCARD`, `DOCX_WILDCARD`, `EPUB_WILDCARD` 144-146 | Only `IMPORT_WILDCARDS` uses them. | a (orphaned by the deletion above) | Delete. |
| `_get_txt_wildcard` 761-762 and `TXT_WILDCARD` 143 | Not listed in 5.4. There is no caller in production or tests. `TXT_WILDCARD` has no other user. | a (extra finding) | Delete. |
| `_get_import_wildcard` 764-766 | Only the definition matches. Review O-2 confirms it was never called. | a | Delete. The `get_format` import stays because it has 5 other uses. |
| `_create_labeled_group` 554-559 | Only the definition matches. Its last user went away when translation controls moved into the menu (`e4af249`) and the settings dialog was introduced (`064e01d`). | a | Delete. |
| `_rename_dual_view_result` 538-540, `_delete_dual_view_result` 542-543 | Only `tests/test_gui_document_flows.py:988-995` (`test_rename_and_delete_keep_alignment_cache_consistent`) uses them. `DocumentController.rename_document`/`delete_document` replaced them (`documents/controller.py:82-83, 89`). That replacement is covered by `tests/test_document_controller.py` `test_rename_updates_names_and_dual_view_cache` (75), `test_delete_open_document_prefers_neighbor_and_removes_dual_view_cache` (94), `test_rename_document_moves_dual_view_cache_entries` (148) and `test_delete_document_removes_dual_view_cache_entry_and_preserves_preferred_selection` (161). | b | Delete the methods and that one test. The test checks only the dead methods, and the live path already has 4 controller tests. |

Not touched: `_MENU_TRANSLATION_MARKERS` (`gui.py` around 220-226) still lists the literal wildcard strings `_("Text files (*.txt)|*.txt")`, `_("PDF files ...")` and so on. These are gettext extraction markers, so `dotexpress.po` keeps its entries and no `.po`/`.mo` change is needed. Whether to clean up these markers belongs to P1-2/P0-5 (O-1).

### `client/config.py`

| Item | Evidence | Class | Decision |
| --- | --- | --- | --- |
| `set_view_font_size`, `set_view_scheme`, `set_braille_font` | P0-1 removed them. `tests/test_config.py:153` `test_unused_single_view_setters_are_removed` guards that. `gui.py:847` `_set_view_font_size` is a different, live frame method. | done | No action. |

### `client/conversion/text/` (4 spaces)

| Item | Evidence | Class | Decision |
| --- | --- | --- | --- |
| `dictionary_rules.translate__mapping_string` 111-140 | Only the definition matches. The `2026-07-08-conversion-text-processing` plan moved it over "if it is still used". It is not used. | a | Delete. `csv`, `Path` and `mapping` are still used elsewhere in the file. |
| `char_maps.preprocess_bopomofo_characters` 64-70, `char_maps.map_braille_to_ascii` 73-79 | Only the definitions match. The same plan allowed them as optional named wrappers ("if they reduce duplicated path handling"). They were added in `aec3331`, but no caller was ever written. | a | Delete. |
| `char_maps.translate__mapping_char` 49-61 | It is the default `map_char` in `conversion/service.py:113` and `conversion/output.py:45`, and `tests/test_conversion_text_char_maps.py` tests it 5 times. | c (review: "only an alias") | **Keep.** It is live. Folding the alias into `map_characters` is a rename, not dead-code removal, so it is out of scope. |
| `pipeline.apply_plain_text_rules` 49-61 | Only `tests/test_conversion_text_pipeline.py` (`test_apply_plain_text_rules_returns_bracketed_raw_and_replacement` and `test_atomic_flags_remain_paired_before_runtime_translation`) uses it. It passes its arguments straight to `apply_dictionary`, which `translate_plain_text_segment` calls directly. | b | Delete the wrapper. **Retarget** both tests to `conversion.text.dictionary_rules.apply_dictionary` with the same arguments and assertions. They check the bracket-pairing behavior of the code the pipeline really runs, so they keep their value. Rename the first test to `test_apply_dictionary_returns_bracketed_raw_and_replacement`. |

### `client/languageDetection/__init__.py` (tabs)

| Item | Evidence | Class | Decision |
| --- | --- | --- | --- |
| `LanguageDetector.process_for_spelling` 396-442 | No caller anywhere. It has been present since the initial commit `75ddcde` (2025-11-11, ported from WorldVoice) and was never used. | a | Delete. `find_language_for_charset` and `_preferred_full_lang` stay because `add_detected_language_commands` uses them. The `config` import stays because lines 183, 365 and 382 use it. |
| `if False and (...)` block in `add_detected_language_commands` 262-284 | The branch can never run. It includes WorldVoice `config.conf[...]` comments. | a | Delete the block. Also delete the stores the deletion makes dead: `prevInIgnore = False` at 204 and 287. The deleted block (271, 275) was the only code that read or set `prevInIgnore`. `rule`, `charset` and the other locals stay. |

### `client/dictionaries/import_flow.py` (whole module)

| Evidence | Class | Decision |
| --- | --- | --- |
| Only `tests/test_dictionary_import_flow.py` (2 tests) imports it. History: `96366f3` (2026-06-29 08:07, "fix: streamline dictionary import prompt") added it and wired it into `gui.py`. `f975aa5` (2026-06-29 08:50, "fix: keep duplicate dictionary dialogs open") replaced the `gui.py` import with `dictionaries.name_prompt.prompt_dictionary_name_until_success` 43 minutes later. That function also re-prompts after a duplicate name. So this is code that a newer design replaced the same day, not an unfinished planned feature. Its behavior is covered on the live path: `gui.py:1435-1442` pre-fills `source_path.stem` and calls `import_dictionary` in `on_submit`, and `tests/test_dictionary_name_prompt.py::test_cancel_returns_none_without_submitting` covers the case where cancelling imports nothing. The P0-6 presenter will build on `name_prompt`, not on `import_flow`. | b | Delete the module and `tests/test_dictionary_import_flow.py`. `docs/superpowers/plans/2026-06-29-windows-filename-validation-implementation-plan.md` mentions it. That plan is a historical record and is not edited. |

### `client/ui/action_menu.py` (4 spaces)

| Item | Evidence | Class | Decision |
| --- | --- | --- | --- |
| `build_actions_button_label`, `get_actions_menu_position`, `get_dictionary_action_labels` | No caller anywhere. They supported the old "Actions ▼" popup button, which `e4af249` ("feat: move translation controls to menu") removed. | a | Delete. |
| `get_document_action_labels`, `get_document_export_format_keys` | No caller anywhere. | a | Delete. |
| `get_document_menu_items`, `get_document_export_format_labels` | Only `tests/test_action_menu.py::test_export_submenus_use_descriptive_formats_in_order` uses them. The `DOCUMENT_MENU_ITEMS[-2]` negative index (80, 84), which breaks if the order changes, goes away with them. | b | Delete. **Rewrite** that test against `get_document_menu_descriptors()`, which `gui.py:456` actually uses (see Test Strategy). |
| `DocumentMenuItem`, `DOCUMENT_MENU_ITEMS`, `get_document_menu_descriptors`, `get_document_menu_enabled_state` | `gui.py:64-67, 456, 463` and `_sync_document_menu_state` use them. | c | Keep, unchanged. |

### `client/ui/import_dialog.py` (4 spaces)

| Item | Evidence | Class | Decision |
| --- | --- | --- | --- |
| `get_import_wildcard_text`, `get_default_import_filter_index` | No caller anywhere. | a | Delete. |
| `get_import_filter_labels` (36-37) | Not listed in 5.4. It has no caller anywhere. `get_import_filters` uses the aliased import `get_format_import_filter_labels` directly. | a (extra finding) | Delete. |
| `ImportFilter`, `get_import_filters`, `build_import_wildcard`, re-exported `ALL_SUPPORTED_FILTER_INDEX` | `gui.py:68, 1168-1177` use them. | c | Keep. Every import in the module stays: `ALL_SUPPORTED_FILTER_INDEX` is re-exported to `gui`, and the rest are used by `get_import_filters`/`build_import_wildcard`. |

### `client/documents/workspace.py` (4 spaces)

| Item | Evidence | Class | Decision |
| --- | --- | --- | --- |
| `list_document_names` 133-138 | The review says "tests only", but no test uses it either, so no caller anywhere. It has existed since `dd43d6f`. | a | Delete. `get_workspace_directory` is still used at 38 and 48. |
| `batch_export_documents_to_folder` 184-203 | Only 3 tests in `tests/test_document_workspace.py` (264, 282, 301) use it. `85bf669` (2026-06-30) removed its `gui.py` callers. The GUI now exports through `_export_document_with_dialog`/`_export_next_document`. Review O-2 also notes it would write an empty dual view for `html`, so it is not a safe base for P1-4. | b | Delete the function and its 3 tests. The behaviors they checked are covered on live units: `test_export_document_brl_writes_plain_braille_text` (BRL writer) and `test_save_document_package_can_skip_pending_metadata_for_exports` (DEP export without pending metadata). Conflict and overwrite handling is now owned by the GUI chain and `export_results`. After the deletion `get_format` is no longer used in this module, so remove it from the `documents.formats` import (no test patches `documents.workspace.get_format`). |
| `prepare_document_for_save(..., auto_convert=None)` 122-130 | Nothing passes `auto_convert`: the only caller is `gui.py:887`, and the two tests call it without it. `85bf669` removed its last users. The function always returns `(document, None)`. Review S-6 calls both the parameter and the always-`None` error slot remnants of auto-conversion. | a | Remove the parameter **and** the dead `None` error slot, so the function returns `Document`. Update the caller to `updated_document = prepare_document_for_save(...)`. This also removes a hazard: today `updated_document, _ = ...` makes `_` local to `_save_open_document`, which hides gettext's `_` inside that method. Update the two tests (see Test Strategy). |

### `client/documents/formats.py` (4 spaces)

| Item | Evidence | Class | Decision |
| --- | --- | --- | --- |
| `get_exportable_formats` 186-187 | Only `tests/test_document_formats.py::test_exportable_formats_include_dep_and_brl` uses it. It came in with the format registry in `df01017` ("refactor: converge document and conversion boundaries"), as the counterpart of the live `get_importable_formats`. | b | **Keep.** It is a 2-line registry query that looks prepared on purpose. Its test pins the `exportable` flags that `gui.py:1493` relies on. P1-2 (derive the export submenu and wildcards from the registry instead of the hard-coded `(("dep", ...), ("brl", ...), ("html", ...))` tuples) is its natural consumer. |
| `get_import_wildcard_text` 208-209 | Not listed in 5.4. It has no caller anywhere and duplicates the `ui/import_dialog.py` function of the same name. | a (extra finding) | Delete. |

### `client/braille/tables/__init__.py` (tabs, NVDA-derived)

| Item | Evidence | Class | Decision |
| --- | --- | --- | --- |
| `getDefaultTableForCurLang` 105-124 | No caller anywhere. It is the only user of `config` in the module (`config.get_lang()` at 117). | a | **Keep, defer to P1-1.** The P1-1 row explicitly owns "remove `braille/tables`' import of `config`", and section 3.5 proposes to *parameterize* this function with `lang`, not delete it. The module is a hand-adapted copy of NVDA `brailleTables` (`scripts/sync-nvda.py` does not regenerate it). Deleting the function would also leave `_inputTableForLangs`/`_outputTableForLangs` written by `addTable` but never read, which widens the gap from upstream. The liblouis runtime is Windows-only and cannot be checked here. P1-1 decides between deleting and parameterizing, together with the rest of the `config` decoupling. |

### Out of scope (seen, not changed)

- `dialog.py` `DictionaryEntryListCtrl` alias (section 4.1, not 5.4). Left to P2-2.
- `_MENU_TRANSLATION_MARKERS` and stale `.po` entries (O-1, P1-2/P0-5).
- `translate__mapping_char` naming (live).
- `documents/formats.get_format_keys(importable=None)` branch (not listed, and part of the registry).

## Test Strategy (TDD)

A deletion has no new behavior to drive. The red step is instead a **guard test** that fails while the dead name still exists and passes once it is gone. P0-1 used the same pattern (`test_unused_single_view_setters_are_removed`). Test changes, in order:

1. **New `client/tests/test_removed_dead_code.py`** (4 spaces, `unittest`). It holds one guard per non-GUI area and uses `subTest` per name:
   - `test_dictionary_import_flow_module_is_removed`: `importlib.util.find_spec("dictionaries.import_flow") is None`.
   - `test_dead_conversion_text_helpers_are_removed`: `dictionary_rules.translate__mapping_string`, `char_maps.preprocess_bopomofo_characters`, `char_maps.map_braille_to_ascii` and `pipeline.apply_plain_text_rules` are absent (`hasattr` is false), and `char_maps.translate__mapping_char` is still present (live guard).
   - `test_dead_language_detection_method_is_removed`: `LanguageDetector` has no `process_for_spelling`.
   - `test_dead_ui_helpers_are_removed`: the 7 `ui.action_menu` names and the 3 `ui.import_dialog` names are absent, and `get_document_menu_descriptors`/`get_document_menu_enabled_state`/`get_import_filters`/`build_import_wildcard` are present.
   - `test_dead_document_helpers_are_removed`: `documents.workspace.list_document_names`, `documents.workspace.batch_export_documents_to_folder` and `documents.formats.get_import_wildcard_text` are absent, and `"auto_convert"` is not in `inspect.signature(prepare_document_for_save).parameters`.
2. **`client/tests/test_gui_document_flows.py`** (reuses its wx stubs):
   - Add `test_dead_frame_helpers_are_removed`: module attributes `IMPORT_WILDCARDS`, `TXT_WILDCARD`, `PDF_WILDCARD`, `DOCX_WILDCARD`, `EPUB_WILDCARD` and `BrailleFrame` attributes `_create_labeled_group`, `_get_import_wildcard`, `_get_txt_wildcard`, `_rename_dual_view_result`, `_delete_dual_view_result` are absent.
   - Delete `test_rename_and_delete_keep_alignment_cache_consistent`. It tests only the deleted methods, and the live path is covered in `test_document_controller.py`.
3. **`client/tests/test_action_menu.py`**: replace `test_export_submenus_use_descriptive_formats_in_order` with `test_export_submenus_use_descriptive_formats_in_order` built on `get_document_menu_descriptors()`. Look up the `Export` and `Export All` items by `label`. For each, assert `kind == "submenu"`, `action` is `"export"`/`"export_all"`, and `formats == (("dep", "Package DEP"), ("brl", "Braille BRL"), ("html", "Dual View HTML"))`. Drop the imports of the deleted functions. The 4 `get_document_menu_enabled_state` tests stay unchanged.
4. **`client/tests/test_conversion_text_pipeline.py`**: import `apply_dictionary` from `conversion.text.dictionary_rules` instead of `apply_plain_text_rules`, and call it with the same keyword arguments. Rename the first test as above. Assertions are unchanged.
5. **`client/tests/test_document_workspace.py`**: delete the 3 `batch_export_documents_to_folder_*` tests and the import. In the 2 `prepare_document_for_save` tests, change to `prepared = prepare_document_for_save(...)`, drop `assertIsNone(auto_error)`, and drop the `_without_auto_conversion` suffix from their names. Against the current code they fail red, because the function returns a tuple.
6. **Delete `client/tests/test_dictionary_import_flow.py`.**

No guard is possible for the unreachable `if False` block or the dead `prevInIgnore` stores. The existing language-detection tests (`tests.test_language_detection_translation`, `tests.test_language_detection_char_langinfo`, `tests.test_language_detection_unicode_braille`, plus the pipeline tests that run `add_detected_language_commands`) must stay green unchanged. The acceptance grep below confirms the block is gone.

Expected count: 449 − 2 (`test_dictionary_import_flow`) − 1 (gui rename/delete) − 3 (batch export) + 5 (`test_removed_dead_code`) + 1 (gui guard) = **449**. If the plan arranges the guards differently, it must restate the expected count.

## Acceptance Criteria

1. Run from `client/` with the venv Python: `python -m unittest discover -s tests -p "test_*.py"` gives `Ran 449 tests` and `FAILED (failures=1, skipped=7)`. The only failure is the known P2-5 `test_conversion_service` case, and there are no new failures or errors.
2. Focused suites pass: `python -m unittest tests.test_removed_dead_code tests.test_action_menu tests.test_conversion_text_pipeline tests.test_conversion_text_char_maps tests.test_conversion_text_dictionary_rules tests.test_document_workspace tests.test_document_formats tests.test_document_controller tests.test_dictionary_name_prompt tests.test_gui_document_flows tests.test_language_detection_translation tests.test_language_detection_char_langinfo tests.test_language_detection_unicode_braille -v`.
3. Run from the repo root: the following grep matches only lines in `client/tests/test_removed_dead_code.py` and `client/tests/test_gui_document_flows.py` (the guard strings):
   `grep -rnE 'IMPORT_WILDCARDS|PDF_WILDCARD|DOCX_WILDCARD|EPUB_WILDCARD|TXT_WILDCARD|_create_labeled_group|_get_import_wildcard|_get_txt_wildcard|_rename_dual_view_result|_delete_dual_view_result|translate__mapping_string|preprocess_bopomofo_characters|map_braille_to_ascii|apply_plain_text_rules|process_for_spelling|import_flow|build_actions_button_label|get_actions_menu_position|get_document_menu_items|get_dictionary_action_labels|get_document_action_labels|get_document_export_format_|get_default_import_filter_index|get_import_wildcard_text|list_document_names|batch_export_documents_to_folder|auto_convert' client scripts --include='*.py' --include='*.bat'`
   Separately, `grep -n "get_import_filter_labels" client/ui/import_dialog.py` prints exactly one line: the aliased import `get_import_filter_labels as get_format_import_filter_labels,`. The live `documents.formats.get_import_filter_labels` keeps its definition.
4. `grep -n "if False" client/languageDetection/__init__.py` and `grep -n prevInIgnore client/languageDetection/__init__.py` print nothing.
5. `client/dictionaries/import_flow.py` and `client/tests/test_dictionary_import_flow.py` no longer exist.
6. Kept on purpose, so each still matches its definition: `translate__mapping_char`, `get_exportable_formats`, `getDefaultTableForCurLang`, `get_document_menu_descriptors`, `get_document_menu_enabled_state`, `get_import_filters`.
7. `git diff main --stat -- client/locales` is empty. No `.po`/`.mo` change, because no user-facing string changes.
8. Indentation follows each file (tabs in `gui.py` and `languageDetection/__init__.py`, 4 spaces elsewhere). Nothing is reformatted.
9. One logical deletion per commit, for example gui helpers, conversion text helpers, language detection, import flow module, action menu and import dialog, documents. After each commit the full suite has no failures or errors beyond the known P2-5 case.

## Risks

- **Hidden callers outside the greps.** Covered by the dynamic-lookup and packaging check above. No string-based access, no `--hidden-import`, no `.spec`. `server/` does not import any of these modules. Residual risk is low.
- **Windows-only paths.** None of the deleted code runs only on Windows, and `braille/tables` (liblouis) is deliberately left alone. A Windows PyInstaller build is not run on this Linux box. It is expected to be unaffected because `import_flow` was never imported by `gui.py`, and the handoff must say this was not verified.
- **`prepare_document_for_save` return type change.** It is a public function in `documents/workspace.py`. The grep shows exactly one production caller, `gui.py:887`, and two tests, all updated in the same commit.
- **Retargeted pipeline tests now call `apply_dictionary` directly.** That is the function the pipeline calls, so coverage of the real path is unchanged.
- **`batch_export_documents_to_folder` removal.** If P1-4 later wants a pure batch-export helper, it should write one against the unified `ExportContext` writer contract (P1-2) rather than revive this one, which mishandles `html`.
- **Deviations from the review.** `translate__mapping_char` is live, not dead. `list_document_names` has no test caller either. `get_exportable_formats` and `getDefaultTableForCurLang` are kept on purpose, and four extra dead helpers are removed (`_get_txt_wildcard`/`TXT_WILDCARD`, `ui.import_dialog.get_import_filter_labels`, `documents.formats.get_import_wildcard_text`, and the always-`None` slot of `prepare_document_for_save`). These are recorded above so later tasks do not re-open them by accident.
