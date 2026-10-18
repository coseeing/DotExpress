# Script Management (F-18) Design

## Goal

The user asked (2026-10-18) to make Text Processing (文字處理) work like dictionaries: there can be several text-processing scripts, the user selects one to run, and the user can add, edit, rename, delete, import and export them.

1. A new "Script Management" (腳本管理) feature with Add, Delete, Rename, Edit, Import and Export. Like the default dictionary, one script cannot be renamed or deleted. Its name is 「不處理」 ("No Processing").
2. Unlike the default dictionary, No Processing cannot be edited either. Its content is:

   ```python
   def main(input: str) -> str:
       return input
   ```

3. A new `script` folder, a sibling of the `dictionary` folder and managed the same way, holds the scripts as `.py` files.
4. No Processing is stored in that folder as `no-processing.py`.
5. Add and Edit open a dialog with a multi-line text area. The dialog title is the script name. The editor holds the code, which must have this shape:

   ```python
   def main(input: str) -> str:
       ...  # free code in between
       return input
   ```

6. Import accepts only `.py` files. It checks that the file defines a `main` that takes one `str` parameter and returns a `str`.

After this task:

- The Translation menu item 「文字處理」 becomes 「腳本管理...」, at the same position. It opens a modal Script Management dialog shaped like Dictionary Management.
- The script used for conversion is chosen where the dictionary is chosen today: a new 「文字處理腳本」 choice in Settings > Translation, right below 「字典」 (D-C). It is saved in `config.json` as `conversion.selected_script`.
- No Processing skips the script stage. The single `dictionary/preprocessing.py` is no longer read: no migration (D-A, decided by the user).
- Conversion output with No Processing is identical to today's output without a `preprocessing.py`. The three fixtures keep their sha256.

Non-goals: a code editor with syntax highlighting or line numbers; running a script on sample text from the editor; sandboxing scripts (D-H); a selection control inside Script Management (D-C, Q1); changing anything about dictionaries, apart from reusing their helpers.

## Decisions Taken Before This Spec

**Decided by the user (2026-10-18).** These are not asked again:

- **D-A (changed by the user): no migration.** The legacy `dictionary/preprocessing.py` is not copied anywhere. It stays on disk untouched and is no longer used by conversion. Every user starts with No Processing selected. A user who had a custom `preprocessing.py` gets different conversion output after the upgrade until they import that file (Import accepts it if it passes D-B) and select it. The user accepted this. The app says nothing about the stale file and adds no string for it (minor question Q2).
- **D-B: the signature rule** for Save, Import and execution:
  - `main` is a single top-level synchronous function (today's rule).
  - It has exactly one positional parameter, with any name, and no other parameters (today's rule).
  - The type annotations `: str` and `-> str` are optional, so scripts written for today's rule keep working. If an annotation is present, it must be `str` (new).
  - The type of the return value is checked at run time, as today.
- **D-C: selection mirrors the dictionary.** The Text Processing menu item becomes Script Management. "Mirror the dictionary selection flow" is applied to the flow as the code has it: the dictionary is chosen in Settings > Translation, not in Dictionary Management (Current State, "How the dictionary is selected"). The script is therefore chosen in Settings > Translation. See Q1: the user's wording ("inside Script Management") may assume otherwise.
- **D-D: No Processing.** File `no-processing.py`, internal name `no-processing`, displayed through the msgid `No Processing` as 「不處理」.

**Decided by orchestrator with the recommended default; user may override before merge:** D-E (Add and Edit), D-F (Import and Export), D-G (unreadable and invalid scripts), D-H (no security warning), and the smaller defaults O1-O9 under "Open Questions". Each one is written so that it can be changed in one place.

## Current State (verified 2026-10-18 on `main` `67c2a97`, worktree `D:/workspace/DotExpress-f18`)

Line numbers are from `67c2a97`. They are only for orientation.

### The single text-processing script

- `client/conversion/preprocessing/user_script.py`:
  - `PREPROCESSING_FILENAME = "preprocessing.py"` (`:10`) and `DEFAULT_PREPROCESSING_SCRIPT = "def main(input: str) -> str:\n    return input\n"` (`:11`).
  - `preprocessing_script_path(dictionary_dir)` (`:14-15`) puts the script in the dictionary folder.
  - `load_preprocessing_script` (`:18-23`) reads UTF-8 (not `utf-8-sig`). **A missing file reads as the default script.** The file exists only after the user pressed OK or Apply in the Text Processing dialog.
  - `validate_preprocessing_script` (`:26-49`) parses and compiles the source without running it. It requires exactly one top-level `main` that is a `FunctionDef`, not async (msgid `The script must define exactly one top-level synchronous main function.`, `:40`), with exactly one positional parameter, no keyword-only parameters, no `*args` and no `**kwargs` (msgid `main must define exactly one positional parameter and no other parameters.`, `:49`). Annotations are not checked.
  - `save_preprocessing_script` (`:52-61`) validates, then writes with `write_text_atomically(..., newline="")` (F-8).
  - `execute_preprocessing_script` (`:64-80`) loads, validates, then `exec`s the source in a fresh namespace (`__name__ = "__dotexpress_preprocessing__"`, `__file__` = the path) with full Python privileges. It checks that `main` is callable (`:75-76`), calls it and checks that the result is a `str` (`:78-79`).
- `client/conversion/text/pipeline.py` `preprocess_source_text` (`:23-45`) calls `execute_script(preprocessing_path, text)` (`:32`). It wraps any `BaseException` in `TextProcessingError`, then maps Bopomofo characters with `map_char` (`BopomofoChar2Braille.csv`). The character map runs whether or not the script changed anything.
- `client/conversion/output.py`:
  - `ConversionRequest` (`:11-20`) has no script field.
  - `convert_text_with_alignment` passes `preprocessing_script_path(request.dictionary_path.parent)` (`:62`). The script is therefore whatever `preprocessing.py` sits next to the selected dictionary.
  - `TextProcessingError` becomes `ConversionStageError("text_processing", ...)` (`:65-66`).
- `client/ui/conversion_presenter.py` `format_conversion_error` (`:136-146`) shows `Text processing failed: {error}` / 「文字處理失敗：{error}」 for that stage.
- The presenter builds the request on the main thread when a job is queued or started (`conversion_presenter.py:227-229`, `build_request`). The worker thread reads and runs the script.

### The Text Processing dialog and menu item

- `client/ui/translation_menu.py:6-13` lists the Translation menu: `convert`, `dual_view`, `text_processing` (`N_("Text Processing")`), `dictionaries` (`N_("Dictionary Management...")`), `settings`. No item has an access key or an accelerator.
- `client/gui.py:283-294` builds the menu from that list. `on_open_text_processing` (`gui.py:592-604`) shows `TextProcessingDialog.show_singleton(script_path=preprocessing_script_path(self.dictionary_dir))`. An `OSError` gives `Unable to open text processing script: {error}`.
- `client/settings/dialogs.py` `TextProcessingDialog` (`:118-190`) is a **modeless singleton** (`SingletonDialogMixin`, `ui/dialog_base.py:90-133`):
  - The title is `Text Processing`.
  - It holds one `wx.TextCtrl` (`TE_MULTILINE | TE_RICH2 | TE_DONTWRAP`, teletype font), named `Text Processing Python Code` (`:138`).
  - The buttons are OK, Cancel and Apply.
  - `on_apply` (`:156-171`) saves. On `OSError`, `SyntaxError` or `ValueError` it shows `Unable to save text processing script: {error}` (with the `ValueError` msgid translated) in a box titled `Text Processing`, then puts the focus back in the editor.
  - Cancel, Esc and the close box destroy the dialog **without asking** about unsaved changes.

### Dictionaries (the model to mirror)

- **Folder and names.** `client/app_paths.py` `ApplicationPaths` (`:12-23`) has `dictionary = root / "dictionary"` (`:38-47`). `writable_directories` (`:21-22`) are created and probed at startup by `prepare_application_directories` (`:50-68`). The root is `client/` from source and the exe's folder when frozen (`get_application_root`). `client/.gitignore:3` ignores `dictionary/`.
- `client/dictionaries/manager.py`:
  - A name maps to `<name>.csv` (`dictionary_path_for_name`, `:38-39`). The displayed name is the file stem, Unicode allowed.
  - `ensure_default_dictionary` (`:52-58`) recreates `default.csv` when it is missing.
  - `list_dictionary_names` (`:61-66`) sorts by `casefold`, so `default` sits in alphabetical order. It is displayed untranslated.
  - `normalize_dictionary_name` (`:69-70`) is `shared/name_validation.normalize_base_name` with `default` reserved: 1-32 characters, a legal Windows file name, no surrogates, case-insensitive reserved names.
  - `create_dictionary` (`:90-98`) and `import_dictionary` (`:101-117`) raise `FileExistsError` for a taken name. `import_dictionary` validates the source, reads it, then writes the bytes atomically. A `PermissionError` on the source becomes `DictionaryImportSourceError`.
  - `rename_dictionary` (`:120-130`) allows a case-only rename on Windows (`_is_same_file`, `:133-142`).
  - `export_dictionary` (`:145-156`) refuses a folder as the target and copies the bytes atomically.
  - `delete_dictionary` (`:159-164`) refuses `default`.
- `client/dictionaries/actions.py:22-30` `get_action_availability`: Edit and Export are enabled for any selection; Delete and Rename for anything but `default`.
- `client/dictionaries/name_prompt.py:14-30` `prompt_dictionary_name_until_success` asks for a name again after a `FileExistsError`. It is generic: it knows nothing about dictionaries.
- `client/dictionaries/presenter.py` `DictionaryManagementPresenter` (`:69-229`) runs the flows through a passive view.
  - **Import** (`:168-195`): file dialog first, then the name prompt with the source's stem. A taken name shows `Dictionary "{name}" already exists.` and **asks for another name; there is no overwrite confirmation** (`:209-223`).
  - **Delete** asks `Do you want to delete dictionary "{name}"?` / `Confirm Delete Dictionary` (system Yes/No box, No the default, buttons without access keys since F-17: `ui/message_box.py:21-40`).
  - **Delete and Rename update the active dictionary** through `translation/dictionary_state.py`. After a rename the active name follows the file (`:29-39`). **After deleting the active dictionary, its neighbour above becomes active**, not `default` (`plan_dictionary_state_after_delete` `:42-55` and `manager.choose_selection_after_delete` `:173-182`).
- `client/dialog.py`:
  - `DictionaryNameDialog` (`:212-252`) uses `NameDialogBase` (`ui/dialog_base.py:52-87`). `NameDialogMessages` (`ui/dialog_base.py:31-49`) formats `reserved` with the one fixed `reserved_name`, not with the name typed.
  - `DictionaryManagementDialog` (`:646-925`) is **modal** (`ShowModal` in `gui.py:1139-1141`). It has:
    - a virtual list with the columns `Dictionary` and `Entries` (`:672-682`);
    - the F-6 reason row `Why this dictionary cannot be read:` plus a read-only multi-line field, shown only while an unreadable dictionary is selected (`:684-699`, `:779-798`);
    - the buttons Add, Delete, Rename, Edit, Import, Export (`:701-717`) and Close (`:719-723`);
    - **Edit ends the modal loop with `wx.ID_EDIT`** (`:869-883`) after reading the file again (F-6 D5: an unreadable one is explained and the dialog stays). `gui.on_open_dictionary_management` then opens the editor (`gui.py:1143-1172`), so Dictionary Management is gone when the editor closes;
    - the file filter `CSV files (*.csv)|*.csv` (`:34`, `:904-925`).
  - `DictionaryEntriesDialog._on_cancel` (`dialog.py:588-600`) asks `Do you want to discard the changes you made to dictionary "{name}"?` / `Unsaved Changes` / `Discard Changes` / `Back to Editing` through `confirm_box` (F-15) when there are changes. It puts the focus back where it was (`_restore_focus`, `:639-644`).
- `client/dictionaries/read_problems.py`: `classify_dictionary_read_error` (`:29-37`), `describe_dictionary_read_error` (`:40-57`; its UTF-8 advice names the CSV format and Excel) and `log_dictionary_read_error` (`:66-74`).
- `client/documents/import_problems.py:53` already has the plain-text UTF-8 advice `The file is not saved as UTF-8 text. Save it again as UTF-8, for example with Save As in Notepad.` / 「檔案不是以 UTF-8 文字儲存。請重新存成 UTF-8，例如在記事本中使用「另存新檔」。」.

### How the dictionary is selected

- **The active dictionary is chosen in Settings > Translation**, in a `wx.Choice` labelled `Dictionary` (`settings/dialogs.py:388-391`, `_select_dictionary` `:427-436`, `_selected_dictionary` `:416-422`). Dictionary Management only edits the files. It changes the active dictionary only when the active one is renamed or deleted.
- `TranslationSettings` (`settings/translation.py:15-19`) holds `output_mode`, `width` and `selected_dictionary`. `load_translation_settings` / `normalize_translation_settings` / `save_translation_settings` (`:41-71`) resolve the saved name against the current names (`resolve_selected_dictionary`, `manager.py:167-170`: a saved name that is gone becomes `default`). They save the three keys, keeping the first problem (F-12 D6).
- `config.py`: `SELECTED_DICTIONARY_KEY = "selected_dictionary"` (`:28`) lives in the `conversion` section. `get_selected_dictionary` / `set_selected_dictionary` (`:297-303`).
- `gui.py`:
  - `_initialize_state` (`:154-172`) builds the presenter and loads the settings.
  - `_set_active_dictionary` (`:477-483`) is the presenter's `set_active_name`.
  - `get_dictionary_names_for_dialog` (`:443-445`) refreshes the list.
  - `on_open_settings` (`:1079-1086`) passes `dictionary_names` to the **modeless** `DotExpressSettingsDialog` (`settings/dialogs.py:654-735`).
  - `apply_settings_from_dialog` (`:455-475`) normalizes against fresh names.
  - `_get_selected_dictionary_path` (`:536-537`) and `_build_conversion_request[_for_text]` (`:650-669`) build the request.

### Packaging

`scripts/build-dotexpress.bat` bundles `braille`, `mathcat/assets`, `data` and `locales`. `dictionary\`, `workspace\`, `log\` and `dual_view\` are created at run time next to the exe by `prepare_application_directories`. Nothing in the build changes for `script\`.

### Tests that pin the current behaviour

- `tests/test_user_preprocessing_script.py`: 15 tests of `user_script.py`, among them `test_path_uses_dictionary_directory` and `test_missing_file_loads_identity_script_without_creating_file`.
- `tests/test_conversion_service.py:102-174` and `:517-539` write `dictionary/preprocessing.py` and expect it to run.
- `tests/test_conversion_text_pipeline.py:86-124` and `:204-212`.
- `tests/test_settings_dialogs.py` `TextProcessingDialogTest` (`:144-249`) and `TextProcessingSingletonTest` (`:786-793`); `:855` lists the singleton classes.
- `tests/test_gui_document_flows.py:544-561` (`on_open_text_processing`), `:1570-1606` (the menu bindings, `T[Text Processing]`) and `:5907-5917` (`test_an_open_text_processing_dialog_is_left_alone`).
- `tests/test_translation_menu.py:7-17`.
- `tests/test_app_paths.py:27-67` and `:132-146` (the fields of `ApplicationPaths`).
- `tests/test_translation_settings.py`, `tests/test_config.py` (the settings keys).
- `tests/test_translation_liblouis_golden.py:99-108` and `tests/test_main_demo.py` build a `ConversionRequest` without a script. Their dictionary folders have no `preprocessing.py`, so they run the identity script today.

### Catalog

410 msgids (`dotexpress.po` has 411 `msgid` lines, header included), all translated, 0 fuzzy. `POT-Creation-Date` is `2026-10-10 12:00+0800`.

## Decisions

### D1. The script folder and file layout

- `ApplicationPaths` gets `script = root / "script"`, and it is added to `writable_directories` after `dictionary`. From source this is `client/script/`. Frozen, it is `<exe folder>\script\`, created at startup like `dictionary\`. If it cannot be written, startup reports it as today (`ApplicationDataError`).
- `client/.gitignore` gets `script/` next to `dictionary/`.
- A script name maps to `<name>.py` in that folder, as a dictionary name maps to `<name>.csv`. Every stem of a `*.py` file there is a script. The internal name of No Processing is `no-processing`, so its file is `no-processing.py`.
- `ensure_no_processing_script(script_dir)` creates `no-processing.py` with `NO_PROCESSING_SCRIPT` (today's `DEFAULT_PREPROCESSING_SCRIPT` text) when it is missing, through `write_text_atomically`. It is called on each refresh, like `ensure_default_dictionary`. An existing file is never rewritten (D4).
- **Order in every list:** No Processing first, then the user scripts sorted like dictionaries (`casefold`, then the name). No Processing's displayed name is not its file stem, so alphabetical order would put it in a confusing place (O1).

### D2. Module layout (reuse before duplication)

- **`client/conversion/preprocessing/user_script.py`** (4 spaces) stays the place for the script contract:
  - `NO_PROCESSING_SCRIPT_NAME = "no-processing"`, `NO_PROCESSING_SCRIPT` (the text above), `SCRIPT_SUFFIX = ".py"`.
  - `validate_script(source, *, filename)` is today's validation plus the D-B annotation rule (D5).
  - `read_script_source(path) -> str` is a strict read with `utf-8-sig` (D6). There is no fallback for a missing file.
  - `save_script(path, source)` validates and writes atomically, as today's save.
  - `execute_script(path, input_text) -> str` reads strictly, validates, `exec`s and checks the result, as today.
  - `preprocessing_script_path`, `PREPROCESSING_FILENAME` and the missing-file fallback are removed: nothing reads `dictionary/preprocessing.py` any more (D-A).
- **New package `client/text_scripts/`** (tabs, like `dictionaries/`). It is not called `scripts` because the repo root already has `scripts/` for the build.
  - `manager.py` holds the file operations: `script_path_for_name`, `ensure_no_processing_script`, `list_script_names`, `normalize_script_name`, `script_exists`, `create_script`, `import_script`, `rename_script`, `export_script`, `delete_script`, `resolve_selected_script`. Each one mirrors its dictionary twin, and the atomic-write and same-file helpers are reused, not copied: `_is_same_file` moves to `shared/` or is imported.
  - `actions.py` holds `is_no_processing_script`, `get_script_action_availability` and `script_display_name(name)` (`_("No Processing")` for `no-processing`, else the name).
  - `presenter.py` holds `ScriptManagementPresenter`, the passive-view twin of `DictionaryManagementPresenter`. It reuses `dictionaries/name_prompt.prompt_dictionary_name_until_success` as it is (generic).
  - `read_problems.py` holds `ScriptReadProblem` / `describe_script_problem` / `read_script_status` / `log_script_read_error`. These reuse `classify_dictionary_read_error`; only the UTF-8 advice differs (D7).
- **`client/dialog.py`** (tabs) gets `ScriptNameDialog`, `ScriptManagementDialog` and `ScriptEditorDialog`, next to their dictionary twins. They reuse `finalize_dialog_layout`, `localize_standard_buttons`, `CallbackVirtualListCtrl`, `_NameDialog` and `confirm_box`.
- **`client/settings/dialogs.py`**: `TextProcessingDialog` is removed, and `TranslationSettingsPanel` gets the script choice (D3).

### D3. Selecting the script (D-C)

- `TranslationSettings` gets `selected_script: str` (default `no-processing`). `DEFAULT_TRANSLATION_SETTINGS`, `normalize_translation_settings(settings, dictionary_names, script_names)`, `load_translation_settings(store, dictionary_names, script_names)` and `save_translation_settings` change accordingly. Save writes four keys and still returns the first problem.
- `config.py`: `SELECTED_SCRIPT_KEY = "selected_script"` in the `conversion` section; `get_selected_script(default="no-processing")` and `set_selected_script(name)`, the twins of the dictionary pair. A value that is not a `str` reads as the default.
- `resolve_selected_script(names, saved)`: the saved name if it is listed, else `no-processing`. A script deleted or renamed outside the app therefore falls back to No Processing at the next load, or when Settings is applied, as a missing dictionary falls back to `default`.
- **Settings > Translation** gets a fourth row below `Dictionary`: label `Text Processing Script` (「文字處理腳本」) and a `wx.Choice` of the display names in D1 order. The first entry is 「不處理」. The panel keeps the internal names in a parallel list, as `dictionary_names`. `DotExpressSettingsDialog.__init__` gets `script_names`, and `gui.on_open_settings` passes `get_script_names_for_dialog()`. The panel description becomes `Translation output mode, width, dictionary, and text processing script options`.
- The choice lists unreadable and invalid scripts too, as the dictionary choice lists unreadable dictionaries. Converting with one of them gives the text-processing error (D9).
- **Script Management never changes the active script, except** that renaming the active script makes the new name active (twin of `plan_dictionary_state_after_rename`), and deleting it makes **No Processing** active (D8.3, O5).
- `BrailleFrame` gets `script_dir`, a `_script_presenter` (built in `_initialize_state` next to the dictionary presenter, with `get_active_name` / `set_active_name=self._set_active_script`), `_set_active_script` (twin of `_set_active_dictionary`, reporting a save problem with `_report_settings_save_problem`), `get_script_names_for_dialog`, and `_get_selected_script_path() -> Path | None` (`None` for No Processing).

### D4. No Processing never runs a file (D-D)

- For the internal name `no-processing`, the request's `script_path` is `None`, and the script stage is skipped. The Bopomofo character map still runs, as today. The file `no-processing.py` is never read for conversion.
- **Why not rewrite the file:** a file the user altered (or a damaged disk) cannot change the output of No Processing, and the app does not write a file at every start. Skipping the stage is also what keeps the fixtures identical: the output equals today's identity script without any `exec`.
- The file is created when missing (D1), so that the folder shows the user what No Processing is. It is never rewritten: user bytes in it are left alone.
- **Export of No Processing writes `NO_PROCESSING_SCRIPT`**, not the disk file. The exported file is always the documented content.
- Rename, Delete and Edit are disabled for it. Export is enabled.
- Reserved names for user scripts, case-insensitive and after `strip()`: `no-processing`, the msgid `No Processing`, and its translation in the current language (「不處理」). The `reserved` message shows the name as typed. `NameDialogMessages` gets a way to format `{name}` with the typed name (for example `reserved_name=None` meaning "the typed name"); the dictionary message stays as it is.

### D5. The signature rule (D-B)

`validate_script` raises `SyntaxError` for a source that does not parse or compile, and `ValueError` with a msgid in these cases:

| Case | msgid (existing or new) |
| --- | --- |
| zero or several top-level `main`, or an `async def main` | `The script must define exactly one top-level synchronous main function.` (existing) |
| not exactly one positional parameter, or keyword-only, `*args` or `**kwargs` | `main must define exactly one positional parameter and no other parameters.` (existing) |
| the parameter has an annotation that is not `str` | `The parameter of main must be annotated as str, or not annotated.` (new) |
| a return annotation that is not `str` | `The return value of main must be annotated as str, or not annotated.` (new) |

- "Is `str`" means the annotation node is `ast.Name(id="str")` or the string constant `"str"` (a quoted annotation). `typing.Text`, `builtins.str` and `Optional[str]` are refused (O2).
- A parameter default such as `def main(input="")` stays allowed (today's rule does not look at defaults).
- Nothing is executed during validation, as today. The checks in execution stay: `main is not callable.` and `main must return str, got {type}.`.
- The rule applies to Save in the editor, to Import, to the status in Script Management (D7), and to every execution.

### D6. Reading a script

- `read_script_source` reads bytes and decodes them with `utf-8-sig`, so a file saved with a BOM (some editors add one) is accepted. A file that is not UTF-8 raises `UnicodeDecodeError`. `PermissionError` and other `OSError`s pass through.
- The editor writes what it holds, without a BOM and without newline translation (as today).

### D7. Script Management dialog

`ScriptManagementDialog(parent, actions, selected_name)`, modal, `wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER`, title `Script Management` (「腳本管理」). Top to bottom, which is also the Tab order:

1. **List**: `CallbackVirtualListCtrl`, report style, single selection.
   - The columns are `Script` (「腳本」) and `Status` (「狀態」).
   - Column 1 is the display name (「不處理」 for `no-processing`).
   - Column 2 is `Ready` (「可使用」), `Unreadable` (existing, 「無法讀取」) or `Not Valid` (「格式不正確」).
   - The list's accessible name is the first column header, as the dictionary list's is today.
2. **Reason row** (F-6 D3 twin): the label `Why this script cannot be used:` (「無法使用的原因：」) and a read-only multi-line field. Both are hidden unless the selected script is Unreadable or Not Valid. The text is selected, so NVDA reads all of it on focus. The text comes from `describe_script_problem`:
   - not UTF-8: the existing plain-text advice (`documents/import_problems.py:53`);
   - cannot open: the existing `The file cannot be opened. It may be in use by another program, ...`;
   - other read errors: the existing `The file cannot be read: {error}`;
   - `SyntaxError`: `str(error)`, as the editor shows it today;
   - `ValueError`: the translated msgid of D5.
3. **Buttons** in the dictionary's order and with its existing msgids: `Add`, `Delete`, `Rename`, `Edit`, `Import`, `Export`. The availability:

   | Selection | Add | Delete | Rename | Edit | Import | Export |
   | --- | --- | --- | --- | --- | --- | --- |
   | No Processing | yes | no | no | **no** | yes | yes |
   | a user script (any status) | yes | yes | yes | yes | yes | yes |

4. **Close** (`CreateButtonSizer(wx.CLOSE)`, localized). Esc and the close box close the dialog, as in Dictionary Management.

- On open, `gui.on_open_script_management` refreshes the presenter with the active script. The list selects and focuses that script, so the focus starts in the list on the active script (twin of `gui.py:1137-1141`).
- Each status is read when the list is refreshed (the F-6 twin `_load_dictionary_counts`). A file that cannot be read or is invalid never stops the dialog from opening. The read error is logged once per refresh to `gui.log` (`log_script_read_error`, the twin of `log_dictionary_read_error`). Invalid code is not logged: it is the user's content, not an error.

### D8. Flows (D-E, D-F)

1. **Add.**
   - The name prompt `ScriptNameDialog` opens, titled `Add Script` (「新增腳本」), with the label `Script Name` (「腳本名稱」) and an empty field. It validates like `DictionaryNameDialog` with the script messages (D4 reserved names).
   - A name that is taken (`script_exists`) shows `Script "{name}" already exists.` and asks again (`prompt_dictionary_name_until_success`).
   - Then `ScriptEditorDialog` opens over Script Management, titled with the name and filled with `NO_PROCESSING_SCRIPT` (the template the user gave).
   - **No file is written until OK or Apply succeeds.** Cancel, with or without the discard question, creates nothing.
   - The first successful save creates the file exclusively. If a file of that name appeared meanwhile, the save fails with `Script "{name}" already exists.` and the editor stays open.
   - After the editor closes, the list is refreshed. It selects the new script if it was saved, else the previous selection. The active script does not change.
2. **Edit** (user scripts only).
   - The file is read again (F-6 D5 twin). If it cannot be read, the box `Script "{name}" cannot be read.` + blank line + reason appears, and the dialog stays.
   - An invalid script **does** open, so the user can fix it.
   - `ScriptEditorDialog` opens over Script Management with the file's text. When it closes, the focus is back in Script Management's list, with that script selected and its status refreshed.
   - This differs from Dictionary Edit, which closes Dictionary Management first (O4). The reason: Add must open the editor from inside Script Management, and one owner for both keeps the flows the same.
3. **Delete** (user scripts only).
   - The question is `Do you want to delete script "{name}"?` / `Confirm Delete Script` (「要刪除腳本「{name}」嗎？」 / 「確認刪除腳本」), through `DictionaryManagementDialog.confirm`'s twin: a system Yes/No box, No the default, no access keys (F-17).
   - The list selection moves as in Dictionary Management (the neighbour above).
   - **If the deleted script was active, No Processing becomes active** and is saved (O5). The dictionary rule would pick the neighbour, which would silently start running another user script.
   - An `OSError` shows `Failed to delete script: {error}`.
4. **Rename** (user scripts only).
   - The name prompt is titled `Rename Script` (「重新命名腳本」) and holds the current name. Same validation. A taken name asks again. A case-only rename works on Windows, as for dictionaries.
   - The active name follows the rename and is saved.
   - An `OSError` shows `Failed to save script: {error}`.
5. **Import** (D-F).
   1. A `wx.FileDialog` (`FD_OPEN`) titled `Import Script` (「匯入腳本」), with the filter `Python files (*.py)|*.py`.
   2. The name prompt titled `Add Script`, with the source's stem.
   3. On submit, `import_script`:
      - **refuses a source whose suffix is not `.py`** (casefold), with `Only Python files (.py) can be imported.`, since the filter can be bypassed by typing a name;
      - reads the bytes (a `PermissionError` becomes `ScriptImportSourceError`, the F-11 D11 twin);
      - decodes them as D6 and validates them with D5;
      - writes the **original bytes** atomically to `<name>.py`.
   4. A taken name shows `Script "{name}" already exists.` and asks again. **This mirrors dictionary Import exactly; dictionary Import has no overwrite confirmation** (Current State; the orchestrator's brief assumed one).
   5. The errors all start with `Failed to import script: {error}`. `{error}` is the not-UTF-8 advice, the cannot-open advice, `str(SyntaxError)`, the translated D5 msgid, the `.py` refusal, or the `OSError`. Nothing is copied on any error.
   6. The imported script is selected in the list. The active script does not change.
6. **Export** (any script).
   1. A `wx.FileDialog` (`FD_SAVE | FD_OVERWRITE_PROMPT`) titled `Export Script` (「匯出腳本」), with the same filter. The default file name is `<name>.py`, and `no-processing.py` for No Processing.
   2. A user script's bytes are copied as they are, through `export_dictionary`'s twin: atomic, and a folder target is refused the same way. No Processing writes `NO_PROCESSING_SCRIPT`.
   3. An unreadable script still exports, or fails with `Failed to export script: {error}`, as a dictionary does.

### D9. The script editor (D-E)

`ScriptEditorDialog(parent, *, script_name, source, save)`, modal. It replaces `TextProcessingDialog` and keeps its behaviour:

- Title: the script name as is (user scripts only; No Processing is never edited).
- One `wx.TextCtrl` (`TE_MULTILINE | TE_RICH2 | TE_DONTWRAP`, teletype font). Its accessible name (`SetName`) is `Python Code` (「Python 程式碼」), because the title already names the script. The focus starts in it, with the caret at the start.
- The buttons are `OK`, `Cancel` and `Apply`, as today, right-aligned. Esc is Cancel.
- **Apply** calls `save(text)`. On `OSError`, `SyntaxError` or `ValueError` it shows `Failed to save script: {error}` in an `Error` box owned by the editor, then puts the focus back in the editor (today's behaviour, with the new msgid). For a `ValueError` the msgid is translated, as today.
- **OK** is Apply, then close on success.
- **Cancel, Esc or the close box**:
  - When the text differs from the last saved text, or from the initial text for an Add that was never saved, the dialog asks with `confirm_box`: `Do you want to discard the changes you made to script "{name}"?` (「要放棄對腳本「{name}」所做的變更嗎？」), caption `Unsaved Changes`, buttons `Discard Changes` / `Back to Editing`, all existing except the message. No, which is Back to Editing, is the default (F-15).
  - Back to Editing puts the focus back where it was. Without changes it closes at once.
  - This is new compared with `TextProcessingDialog`, and it is the dictionary editor's rule (D-E).
- `save` is supplied by the presenter: `create_script` + `save_script` for the first save of an Add, `save_script` for the rest. The editor holds no file logic.

### D10. Conversion pipeline

- `ConversionRequest` gets `script_path: Path | None = None` as its last field. `None` means No Processing. The default keeps `main.py`, the goldens and every test that builds a request without a script on today's output.
- `preprocess_source_text(text, *, data_dir, script_path: Path | None, execute_script=execute_script, map_char=...)`. When `script_path is None` the script is not run, and the text goes straight to `map_char`. Otherwise it is run as today, and any failure becomes `TextProcessingError`.
- `convert_text_with_alignment` passes `request.script_path`. It no longer derives a path from `request.dictionary_path.parent`.
- `gui._build_conversion_request_for_text` passes `self._get_selected_script_path()`. The path is fixed when the job is built on the main thread (as the dictionary path is). The worker reads the file.
- **A selected script that is missing, unreadable or invalid at conversion time** gives the existing `Text processing failed: {error}` box (stage `text_processing`, `format_conversion_error`). A missing file now fails with the `FileNotFoundError` text instead of silently running the identity script, as a missing dictionary fails today. No new string.

### D11. Menu (D-C)

- `ui/translation_menu.py`: `("scripts", N_("Script Management..."))` takes the place of `("text_processing", N_("Text Processing"))`, between Dual View and Dictionary Management.
- `gui.py`: the handler `on_open_script_management` replaces `on_open_text_processing`.
- No access key and no accelerator, like every item of that menu (O3). The ellipsis matches 「字典管理...」.

### D12. The legacy `dictionary/preprocessing.py` (D-A)

It is not read, moved, copied or deleted. Dictionary Management lists only `*.csv`, so it stays invisible, as today. No message and no new string (Q2).

### D13. Security (D-H)

Scripts run with full Python privileges, in the DotExpress process, as today. Importing a script means trusting it. Default: no new warning text and no confirmation on Import, which keeps parity with today's editor, which already runs whatever the user types (Q3).

## Behaviour per Path, Before and After

| Path | Before | After |
| --- | --- | --- |
| Translation menu | 「文字處理」 opens the modeless code editor for `dictionary/preprocessing.py` | 「腳本管理...」 opens the modal Script Management dialog |
| First start after the upgrade, no `preprocessing.py` | identity script | `script\no-processing.py` created; No Processing selected; same output |
| First start after the upgrade, custom `preprocessing.py` | the custom script runs | **No Processing; the custom script no longer runs** (D-A, accepted by the user); the file is untouched |
| Settings > Translation | output mode, width, dictionary | plus 「文字處理腳本」 (default 「不處理」) |
| Convert with No Processing | the identity script runs | the stage is skipped; identical output |
| Convert with a user script | n/a | the script runs; errors as today's 「文字處理失敗：…」 |
| The selected script deleted outside the app | n/a | No Processing at the next load or Settings Apply; during the session, 「文字處理失敗：…」 |
| Cancel in the editor after typing | closes, changes lost | asks 「要放棄對腳本「X」所做的變更嗎？」 |

## User-Visible Strings

All `.py` msgids, marked with `N_` where they are defined at module level and translated when shown (F-14 D4). Proposed `zh_TW` msgstr values:

**New (33):**

| # | msgid | msgstr |
| --- | --- | --- |
| 1 | `Script Management...` | 腳本管理... |
| 2 | `Script Management` | 腳本管理 |
| 3 | `Script` | 腳本 |
| 4 | `Status` | 狀態 |
| 5 | `Ready` | 可使用 |
| 6 | `Not Valid` | 格式不正確 |
| 7 | `Why this script cannot be used:` | 無法使用的原因： |
| 8 | `No Processing` | 不處理 |
| 9 | `Add Script` | 新增腳本 |
| 10 | `Rename Script` | 重新命名腳本 |
| 11 | `Import Script` | 匯入腳本 |
| 12 | `Export Script` | 匯出腳本 |
| 13 | `Script Name` | 腳本名稱 |
| 14 | `Please enter the script name.` | 請輸入腳本名稱。 |
| 15 | `Script name must be 1 to 32 characters.` | 腳本名稱長度需為 1 到 32 個字元。 |
| 16 | `Script name is not a valid Windows file name.` | 腳本名稱不是有效的 Windows 檔名。 |
| 17 | `Script name "{name}" is reserved.` | 腳本名稱「{name}」為保留名稱。 |
| 18 | `Script "{name}" already exists.` | 腳本「{name}」已存在。 |
| 19 | `Do you want to delete script "{name}"?` | 要刪除腳本「{name}」嗎？ |
| 20 | `Confirm Delete Script` | 確認刪除腳本 |
| 21 | `Failed to delete script: {error}` | 無法刪除腳本：{error} |
| 22 | `Failed to save script: {error}` | 儲存腳本失敗：{error} |
| 23 | `Failed to import script: {error}` | 匯入腳本失敗：{error} |
| 24 | `Failed to export script: {error}` | 匯出腳本失敗：{error} |
| 25 | `Python files (*.py)\|*.py` | Python 檔案 (*.py)\|*.py |
| 26 | `Only Python files (.py) can be imported.` | 只能匯入 Python 檔案（.py）。 |
| 27 | `Script "{name}" cannot be read.` | 無法讀取腳本「{name}」。 |
| 28 | `Do you want to discard the changes you made to script "{name}"?` | 要放棄對腳本「{name}」所做的變更嗎？ |
| 29 | `Python Code` | Python 程式碼 |
| 30 | `Text Processing Script` | 文字處理腳本 |
| 31 | `Translation output mode, width, dictionary, and text processing script options` | 轉譯輸出模式、寬度、字典與文字處理腳本選項 |
| 32 | `The parameter of main must be annotated as str, or not annotated.` | main 的參數只能標註為 str，或不加標註。 |
| 33 | `The return value of main must be annotated as str, or not annotated.` | main 的傳回值只能標註為 str，或不加標註。 |

**33 new msgids** (none of them exists in the catalog today). The plan confirms the count after `generate-pot.bat`. No other new string is needed: the exclusive-create failure of D8.1 reuses #18.

**Reused unchanged:** `Add`, `Delete`, `Rename`, `Edit`, `Import`, `Export`, `Close`, `OK`, `Cancel`, `Apply`, `Error`, `Info`, `Yes`, `No`, `Unreadable`, `Unsaved Changes`, `Discard Changes`, `Back to Editing`, `The file cannot be opened. ...`, `The file cannot be read: {error}`, `The file is not saved as UTF-8 text. ...`, `Text processing failed: {error}`, `The script must define exactly one top-level synchronous main function.`, `main must define exactly one positional parameter and no other parameters.`, `main is not callable.`, `main must return str, got {type}.`.

**Removed (no source reference left, 5):** `Text Processing`, `Text Processing Python Code`, `Unable to save text processing script: {error}`, `Unable to open text processing script: {error}`, `Translation output mode, width, and dictionary options`.

Expected total: 410 + 33 - 5 = **438 msgids**, all translated, 0 fuzzy. Workflow: HANDOFF section 5. Run `scripts\generate-pot.bat`, then `msgmerge`, then fill in the msgstr values (replace any fuzzy match `msgmerge` invents, for example `Script` matched to `Dictionary`, and drop `#, fuzzy` / `#|`), then `msgfmt --check --statistics`. `POT-Creation-Date` stays `2026-10-10 12:00+0800`. Obsolete `#~` entries are not kept (as in earlier tasks).

## Accessibility (NVDA)

- The menu item reads 「腳本管理...」. The dialog title reads 「腳本管理」. The focus lands on the list item of the active script, read as 「不處理 可使用」 or 「<名稱> 格式不正確」.
- Disabled buttons (Delete, Rename and Edit for No Processing) are read as unavailable, as in Dictionary Management.
- The reason field is a Tab stop only while it is shown. Its label is its accessible name, and its text is selected (F-6).
- The editor dialog's title is the script name. The editor's name is 「Python 程式碼」, read with "multi-line edit". NVDA reads the code line by line. A tab character in the code is read as NVDA reads tabs.
- Every box is a system box owned by the dialog that raised it. Yes/No boxes have no access keys (F-17).
- The Settings choice reads 「文字處理腳本 下拉式方塊 不處理」.

## Test Plan

Each test is written red first where possible, against `67c2a97`.

### A. `tests/test_user_preprocessing_script.py` (renamed or kept; the plan decides)

1. Drop or flip `test_path_uses_dictionary_directory` and `test_missing_file_loads_identity_script_without_creating_file`: a missing file now raises `FileNotFoundError` from `read_script_source` and from `execute_script`.
2. New: annotations. `def main(x)`, `def main(x: str)`, `def main(x) -> str`, `def main(x: "str") -> "str"` pass. `def main(x: int)`, `def main(x) -> int`, `def main(x: Optional[str])`, `def main(x) -> None` fail with the right msgid (one subtest each).
3. New: a UTF-8 BOM source validates and executes. A cp950 source raises `UnicodeDecodeError`.
4. Kept: syntax error, one top-level sync main, one positional parameter, no execution during validation, atomic save, read-only refusal, run-time checks.

### B. `tests/test_text_scripts_manager.py` (new; twin of `tests/test_dictionary_manager.py`)

`ensure_no_processing_script` creates the file once and never rewrites an altered file. Other tests check:

- the list order (No Processing first, then casefold order);
- `normalize_script_name` (empty, too long, invalid, the three reserved forms in any case);
- `create_script` / `script_exists`;
- `import_script` (a `.py` suffix check including `.PY` and `.txt`; not UTF-8; a `PermissionError` becoming `ScriptImportSourceError`; invalid code; the original bytes copied; a taken name raising `FileExistsError`; nothing written on any error);
- `rename_script` (refusing No Processing, a case-only rename, a taken name);
- `export_script` (the bytes; a folder refused; No Processing exporting `NO_PROCESSING_SCRIPT` even when the disk file was altered);
- `delete_script` (refusing No Processing);
- `resolve_selected_script`.

### C. `tests/test_text_scripts_presenter.py` (new; twin of the dictionary presenter tests)

Fake view. The cases:

- Add: name prompt, then editor; nothing written on Cancel; a taken name asks again.
- The editor's first save creates the file, and the exclusive-create race gives `Script "{name}" already exists.`.
- Edit of an unreadable script shows the box and stays. Edit of an invalid script opens.
- Delete: confirm; No confirm does nothing; deleting the active script sets `no-processing` active; deleting another one leaves the active script alone.
- Rename of the active script sets the new name active.
- Import: the error texts per class; the selection after import.
- Export: the default file names.

### D. `tests/test_script_dialogs.py` (new, with wx stubs as in `tests/test_dictionary_management_dialog.py`)

- The management dialog: the availability table of D7; the list text per column (「不處理」, Ready, Unreadable, Not Valid); the reason row shown or hidden; the initial selection is the active script.
- The editor: the title is the name; the editor name; Apply failure shows the box and refocuses the editor; OK closes only on success.
- The discard question only after a change, and Back to Editing restores the focus.
- The name dialog's reserved message shows the typed name.

### E. Settings and config

- `tests/test_config.py`: `get_selected_script` default, round trip, a non-string value read as the default.
- `tests/test_translation_settings.py`: load, normalize and save with `selected_script`; four keys; the first problem returned.
- `tests/test_settings_dialogs.py`:
  - drop `TextProcessingDialogTest` and `TextProcessingSingletonTest`, and the `:855` list entry;
  - the Translation panel lists 「不處理」 first;
  - the choice round-trips the internal name;
  - `on_save` carries `selected_script`.

### F. Conversion

- `tests/test_conversion_text_pipeline.py`: `script_path=None` does not call `execute_script` and still maps characters. A path runs it.
- `tests/test_conversion_service.py`: the tests at `:102-174` and `:517-539` write a script into a script folder and pass `script_path`. A new test: `dictionary/preprocessing.py` next to the dictionary is **not** run (D-A). A new test: a missing `script_path` gives stage `text_processing`.
- The goldens and `test_main_demo` pass unchanged: no `script_path`, so `None`.

### G. GUI wiring (`tests/test_gui_document_flows.py`, `tests/test_translation_menu.py`, `tests/test_app_paths.py`)

- The menu list and bindings use `Script Management...` / `on_open_script_management`.
- `on_open_script_management` refreshes with the active script and shows the dialog modally.
- `_build_conversion_request_for_text` passes `None` for No Processing and `script_dir / "<name>.py"` otherwise.
- `_set_active_script` saves and reports a problem once.
- `test_an_open_text_processing_dialog_is_left_alone` is removed with the dialog.
- `ApplicationPaths.script` is in `writable_directories`, and `prepare_application_directories` creates it.
- No test reads `client/script/`, `client/dictionary/` or `storage/`.

### Mutation check (the plan runs these; each must be caught)

1. No Processing executes its file.
2. The annotation check removed.
3. The annotation check made mandatory.
4. The `.py` suffix check removed.
5. Import copies decoded text instead of the original bytes.
6. Deleting the active script picks the neighbour.
7. Renaming the active script leaves the old name active.
8. Edit enabled for No Processing.
9. The editor writes on Cancel, or on Add before OK/Apply.
10. The discard question asked without a change.
11. The legacy `dictionary/preprocessing.py` still runs.
12. A missing script reads as identity.
13. The reserved-name check made case-sensitive.
14. `export` of No Processing reads the disk file.

### Counts

The plan fixes the exact `Ran`. The full suite on `67c2a97` is to be measured by the plan (HANDOFF section 1 gives `Ran 1681` on `67f3181`; F-17 added tests).

## Migration Steps (each one green commit, red first; the plan may split further)

1. `feat: keep text-processing scripts in a script folder with a stricter signature rule (F-18)`: `app_paths.py`, `.gitignore`, `user_script.py`, `text_scripts/manager.py`, `text_scripts/actions.py`, `text_scripts/read_problems.py`; tests A, B; catalogs for the strings this step adds.
2. `feat: select the text-processing script in Settings and run it at conversion (F-18)`: `config.py`, `settings/translation.py`, `conversion/output.py`, `conversion/text/pipeline.py`, `gui.py` request path, the Settings panel; tests E, F; catalogs.
3. `feat: replace Text Processing with Script Management (F-18)`: `text_scripts/presenter.py`, `dialog.py`, `ui/translation_menu.py`, `gui.py`, removal of `TextProcessingDialog`; tests C, D, G; catalogs.

Each commit stages explicit paths only and has no `Co-Authored-By` line (HANDOFF section 5).

## Acceptance Criteria

Run on Windows from `client/` with the main checkout's `.venv` python. The runtime is copied into the worktree as in F-3 plan Task 0 and never staged.

1. Full suite: no failure and no error; `Ran` as the plan states; `OK (skipped=6)`.
2. Focused tests: `-m unittest tests.test_user_preprocessing_script tests.test_text_scripts_manager tests.test_text_scripts_presenter tests.test_script_dialogs tests.test_config tests.test_translation_settings tests.test_settings_dialogs tests.test_conversion_text_pipeline tests.test_conversion_service tests.test_gui_document_flows tests.test_translation_menu tests.test_app_paths -v` pass.
3. Catalogs: 438 msgids (or the number the plan confirms), all translated, 0 fuzzy; regenerating gives no diff.
4. The three fixture sha256 values are unchanged (HANDOFF section 5).
5. App data untouched: the main checkout's `client/dictionary/`, `client/workspace/`, `client/config.json` and `client/log/` are unchanged. No `client/script/` is created by the tests in the main checkout.
6. `client/braille/tables/__tables.py`, `client/braille/liblouis/` and `client/braille/tables/__init__.py` (CRLF bytes) are unchanged.
7. The mutation check above.
8. The packaged GUI items below, with results in `docs/superpowers/history/<date>-<n>-f18-script-management/`.

## Windows Verification (packaged build; the plan agent runs these)

Rules as in F-13/F-14 (HANDOFF sections 4.6 and 4.7):

- The new build goes to `D:/dxtest/N-f18`; the old one is `D:/dxtest/N-f14b`.
- Each item runs in its own `D:/dxtest/auto<item>-f18` folder, using `safe_run.py` and `f13gui.start`.
- Check memory before each item, and put the stand-in `chrome.exe` on `PATH`.
- **No script reads or writes the clipboard.** Code goes into the editor by UIA `ValuePattern.SetValue` or by `type_keys`, never Ctrl+V. File names go into file dialogs by typing.
- Item numbers are proposals (150+); the plan may renumber.

| # | Class | Steps | Expected on N-f18 |
| --- | --- | --- | --- |
| 150 | fix | Fresh folder, start | `script\no-processing.py` exists with the exact text; Translation menu shows 「腳本管理...」 where 「文字處理」 was; Settings > Translation shows 「文字處理腳本」 = 「不處理」 |
| 151 | fix | Upgrade: folder with `config.json` from N-f14b and `dictionary\preprocessing.py` whose `main` returns `input.upper()`; convert `abc` | output is the Braille of `abc` in lower case (script not run); `preprocessing.py` bytes unchanged; `config.json` gains `selected_script` only after a Settings Apply |
| 152 | fix | Script Management: select 「不處理」 | Delete, Rename and Edit disabled; Export enabled; list text 「不處理」 「可使用」 |
| 153 | fix | Add `upper`: name prompt, editor title `upper`, template text present; replace with an upper-casing `main`; OK; select it in Settings; convert `abc` | `script\upper.py` holds the text; output of `ABC` |
| 154 | fix | Add `bad`, type `def main(a, b): return a`, Apply | box 「儲存腳本失敗：main 必須恰好定義一個位置參數，且不得有其他參數。」; focus back in editor; no `bad.py`; Cancel → discard question; 放棄變更 closes; list has no `bad` |
| 155 | fix | Add with annotation `def main(x: int) -> str` | box with the parameter-annotation message |
| 156 | fix | Import `upper2.py` (valid), `x.txt` typed by name, `cp950.py`, `bad.py` (syntax error) | the first is imported (bytes equal); the other three each give 「匯入腳本失敗：…」 with the right reason; nothing copied |
| 157 | fix | Import a name that exists | 「腳本「upper」已存在。」, the name prompt again |
| 158 | fix | Rename the active `upper` to `Upper2`; Settings shows it; Delete it (Yes) | after Delete Settings shows 「不處理」; conversion unchanged from No Processing |
| 159 | fix | Export 「不處理」 after altering `script\no-processing.py` on disk | the exported file equals the canonical text; conversion still identity |
| 160 | fix | Place `script\locked.py` held open with a deny-read share by a helper process, and `script\broken.py` with a syntax error; open Script Management | dialog opens; statuses 「無法讀取」 and 「格式不正確」; reason field text; Edit on `locked` shows 「無法讀取腳本「locked」。」 and the dialog stays; Edit on `broken` opens the editor |
| 161 | fix | Select a user script, then delete its file outside the app, convert | 「文字處理失敗：…」 box; after restart Settings shows 「不處理」 |
| 162 | regression | Dictionary Management full flow (F-6/F-11 items' scripts), conversion goldens on the exe (F-12 item 118), startup items (F-13 item 126 subset) | as in their logs |

**Manual for the user (NVDA, items 163-164):**

- 163: open Script Management and Settings. Does NVDA read the list rows (name and status), the disabled buttons and the reason field?
- 164: the editor. Is the title read as the script name, is 「Python 程式碼」 announced, and is the discard question read in full?

These stay unchecked for the user.

## Risks

- **Output change for users with a custom `preprocessing.py`** (accepted by the user, D-A). Release notes may want a line; not part of this task.
- **Settings dialog left open** (low, pre-existing pattern). The Settings dialog is modeless; Script Management is modal. Suppose Settings is open and the active script is renamed or deleted in Script Management. A later Settings Apply saves the stale name, which normalizes to No Processing. The same happens today with dictionaries.
- **A conversion running while its script is deleted or edited** (low). The worker may read the new or no file. A missing file gives the text-processing error. The atomic write means a read never sees a half-written file.
- **File names in Chinese** (none new). Dictionaries already use Unicode stems.
- **Scripts are trusted code** (as today, D13).

## Open Questions

**Decided by the user (2026-10-18):** D-A (no migration), D-B, D-C, D-D.

**Decided by orchestrator with the recommended default; user may override before merge:**

- **D-E** Add = name prompt, then the editor; nothing written before OK/Apply. Edit = the same editor. OK/Cancel/Apply, monospace, error box, focus back in the editor, and the discard question of the dictionary editor (new for scripts).
- **D-F** Import = `.py` filter + suffix check + D-B validation + original bytes; a taken name asks for another one (mirrors dictionary Import, which has no overwrite confirmation). Export = bytes as they are (No Processing: the canonical text).
- **D-G** An unreadable or invalid script never blocks the dialog: a status column + the F-6 reason row. At conversion time it gives the existing text-processing error.
- **D-H** No new security warning.
- **O1** No Processing is listed first, not in alphabetical order.
- **O2** Only `str` / `"str"` annotations count as `str`.
- **O3** The menu item has no access key or accelerator, like its neighbours.
- **O4** Edit opens the editor over Script Management and returns to it, unlike Dictionary Edit, which closes Dictionary Management.
- **O5** Deleting the active script makes No Processing active, not the neighbour (the dictionary rule).
- **O6** The status words 「可使用」 / 「無法讀取」 / 「格式不正確」 and the Settings label 「文字處理腳本」.
- **O7** A BOM is accepted when reading a script.
- **O8** A missing selected script fails at conversion instead of running the identity script.
- **O9** The editor's accessible name is 「Python 程式碼」.

**Questions for the user** (not blocking; the plan proceeds with the defaults):

- **Q1. Where is the script selected?** In the code, the dictionary is **not** selected inside Dictionary Management. It is selected in 設定 > 轉譯 > 字典. "Mirroring the dictionary" therefore puts the script choice in 設定 > 轉譯 (「文字處理腳本」), and that is what this spec does. If the user wants to pick the active script inside Script Management instead (for example a 「使用」 button, or the active script marked in the list), that is an extra design. Say so before the plan.
- **Q2.** The stale `dictionary/preprocessing.py` is left alone silently. Show a one-time notice? (Default: no.)
- **Q3.** Add a warning on Import that scripts run with full privileges? (Default: no.)
- **Q4.** O5: after deleting the active script, No Processing (this spec) or the dictionary's neighbour rule?

## Out of Scope / Follow-ups

- Selecting the script inside Script Management (Q1).
- A migration helper for the legacy `preprocessing.py` (declined by the user).
- Sandboxing or a timeout for scripts.
- The pre-existing stale-name behaviour of an open Settings dialog (Risks).
