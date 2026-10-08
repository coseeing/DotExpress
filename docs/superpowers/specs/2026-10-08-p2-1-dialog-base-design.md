# Dialog Base and Typed Name Errors (P2-1) Design

## Goal

Remove the dialog boilerplate that is copied across `client/dialog.py` and `client/settings/dialogs.py`, and replace the string matching on name-validation errors with a typed error. This is roadmap task P2-1 in `storage/refactor.md` (section 6.3), covering finding P-2 (the singleton implemented twice), the `__enter__/__exit__` row of section 5.1 (seven copies), the Mixin/Template and Typed-error rows of section 4.3, and the P1 review suggestion (`docs/superpowers/history/2026-10-08-02-refactor-p1/review_task.md`, P2 item 2) to move `ConvertingDialog` out of `gui.py`.

Concretely:

- New wx-free module `client/ui/dialog_base.py` with three bases: `ContextManagedDialog` (`__enter__` returns the dialog, `__exit__` destroys it), `NameDialogBase` (the shared `_on_ok` / `_validate_name` skeleton of the two name dialogs; subclasses give only a normalizer and their messages) and `SingletonDialogMixin` (the one-open-instance logic of the two settings dialogs).
- `client/shared/name_validation.py` gains `NameValidationError(ValueError)` with a `code` field (`"empty"`, `"invalid"`, `"too_long"`, `"reserved"`). `normalize_base_name` raises it instead of a bare `ValueError`; `str(error)` stays the same English text.
- `dialog.py` drops its seven `__enter__/__exit__` pairs and `_normalize_dialog_name` (which re-implemented half of the validation and guessed the error type with `"exceed" in str(exc)`). The two name dialogs map `error.code` to their messages.
- `settings/dialogs.py` drops the two copies of `_destroy`, `_is_destroyed_window_error` and the `show_singleton` body; each dialog keeps only a `show_singleton` that forwards its constructor arguments.
- `ConvertingDialog` moves unchanged from `gui.py` to `dialog.py`.

This is a behavior-preserving refactor. Every dialog shows the same text, in the same order, with the same focus and the same result. No msgid changes: the source msgid scan stays at 353, and `client/locales` does not change. Quirks found during the investigation are pinned by tests, not fixed (section "Known quirks kept").

## Current State (verified 2026-10-08 on `refactor/p2-1-dialog-base`, HEAD `000239b`, P0-1..P0-6, P1-1..P1-6 and the P1 review fixes merged)

Indentation: `dialog.py` and `gui.py` use tabs; `settings/dialogs.py`, `shared/name_validation.py`, the `ui/` modules added in P1 and the test modules named below use 4 spaces.

Baseline: `cd client && $PY -m unittest discover -s tests` gives `Ran 818 tests`, `FAILED (failures=1, skipped=9)`; the one failure is the P2-5 case `test_conversion_service ... test_translate_with_language_does_not_duplicate_existing_spaces_around_math`. The roadmap command `$PY -m unittest tests.test_dialog_validation tests.test_dialog_display tests.test_settings_dialogs` runs 40 tests, all green. Msgid scan (`$SP/p12/tools/msgid_scan.py client`): 353 source msgids; the `.pot` has the 4 known orphan import wildcards only.

### Dialog inventory

Every `wx.Dialog` subclass in the client (`ui/*` and `about.py` define none; the About box is a `wx.MessageDialog` used with `with` in `gui.on_about`):

| Class | File:line | Context manager | Other shared logic |
| --- | --- | --- | --- |
| `ConvertingDialog` | `gui.py:108` | no (modeless; `gui.close_converting_dialog` unbinds `EVT_CLOSE` and calls `Destroy()`) | vetoes `EVT_CLOSE` when `CanVeto()` |
| `AddSymbolDialog` | `dialog.py:89` | `185-189` | - |
| `DictionaryNameDialog` | `dialog.py:192` | `253-257` | `_on_ok` 225-240, `_validate_name` 242-251 |
| `DocumentNameDialog` | `dialog.py:260` | `316-320` | `_on_ok` 290-304, `_validate_name` 306-314 |
| `InvalidWorkspaceFilesDialog` | `dialog.py:323` | `356-360` | - |
| `FileIssuesDialog` | `dialog.py:363` | `378-382` | - |
| `SpeechSymbolsDialog` | `dialog.py:404` | `417-421` | - |
| `DictionaryManagementDialog` | `dialog.py:651` | `870-874` | - |
| `SettingsDialog` | `settings/dialogs.py:82` | no | base; `EVT_CLOSE` -> `on_cancel` |
| `TextProcessingDialog` | `settings/dialogs.py:107` | no | singleton: `_instance` 108, `_destroy` 168-171, `_is_destroyed_window_error` 173-185, `show_singleton` 187-208 |
| `MultiCategorySettingsDialog` | `settings/dialogs.py:211` | no | base |
| `DotExpressSettingsDialog` | `settings/dialogs.py:718` | no | singleton: `_instance` 726, `_destroy` 793-796, `_is_destroyed_window_error` 804-816 (identical to 173-185), `show_singleton` 818-851, `sync_open_font_size` 854-872 (P2-4, not touched) |

The seven `__enter__/__exit__` pairs are identical: `__enter__` returns `self`, `__exit__(exc_type, exc, _tb)` calls `self.Destroy()` and returns `None`, so exceptions propagate. Real wxPython 4 already gives `wx.Dialog` the same context manager (the code relies on it for `wx.FileDialog`, `wx.DirDialog` and `wx.MessageDialog`), but none of the test stubs do. No test calls the real `__enter__/__exit__` of these classes today; the gui and management-dialog tests replace the dialogs with fakes.

### Singleton logic (settings dialogs)

`show_singleton` (both copies):

1. (`DotExpressSettingsDialog` only) If `initial_category` is given and not in `category_classes`, raise `ValueError("initial_category is not registered")` before looking at the open instance.
2. If `cls._instance` is not `None`: call `Iconize(False)`, then (`DotExpressSettingsDialog` only, when `initial_category` is given) `select_category(initial_category)`, then `Raise()`, `SetFocus()`, and return that instance.
3. If step 2 raises `ReferenceError`, `RuntimeError` or `wx.PyDeadObjectError`: if `_is_destroyed_window_error(error)` is false, re-raise (the slot keeps the old instance); otherwise set `cls._instance = None` and fall through. Any other exception type propagates.
4. Build `cls(parent, ...)` with the forwarded keyword arguments, set `cls._instance` to it, then call `Show()` and return it. A constructor failure (for example `OSError` from `load_preprocessing_script`, which `gui.on_open_text_processing` catches) leaves the slot unchanged.

`_is_destroyed_window_error(error)`: true for an instance of `getattr(wx, "PyDeadObjectError", ())`; otherwise true only for a `ReferenceError` or `RuntimeError` whose lowercased message contains `"wrapped c/c++ object"`, `"has been deleted"`, `"already deleted"` or `"destroyed"`.

`_destroy()`: if the class's `_instance` is this dialog (the class is named literally: `TextProcessingDialog._instance`, `DotExpressSettingsDialog._instance`), clear it; then `Destroy()`. Called by `on_ok` (after a successful apply), `on_cancel`, and through `SettingsDialog._on_window_close` -> `on_cancel`.

Callers: `gui.on_open_text_processing` (`gui.py:482`) and `gui.on_open_settings` (`gui.py:893`) call `show_singleton` with keyword arguments; `gui._set_view_font_size` calls `DotExpressSettingsDialog.sync_open_font_size` (reads `cls._instance`). Tests read and write `TextProcessingDialog._instance` and `DotExpressSettingsDialog._instance` directly and subclass `DotExpressSettingsDialog` with its own `_instance = None`.

Latent issue: the `except` tuple names `wx.PyDeadObjectError` directly, while `_is_destroyed_window_error` uses `getattr(wx, "PyDeadObjectError", ())`. wxPython 4 (Phoenix, pinned at 4.2.5) is believed not to define `PyDeadObjectError` (it raises `RuntimeError` for deleted objects instead). If so, any exception in step 2 on real wx turns into `AttributeError` while the `except` clause is evaluated, and a dead instance can never be replaced. In practice the slot never holds a dead window: every path that destroys a settings dialog goes through `_destroy`, which clears the slot first, and the only other way to destroy it is closing the main frame, which ends the app. The settings test stub defines `PyDeadObjectError`, so the tests do not see this. See decision D1.

### Name validation

`shared/name_validation.normalize_base_name(name, *, reserved_names=None)` raises bare `ValueError`s:

| Check (in order) | Message (English, not a msgid) |
| --- | --- |
| `not name or not name.strip()` | `Name cannot be empty.` |
| any character below U+0020 | `Name contains invalid characters.` |
| ends with `" "` or `"."` (on the raw name) | `Name cannot end with a period or space.` |
| `len(name.strip()) > 32` | `Name cannot exceed 32 characters.` |
| stripped name is not a legal Windows file name (`<>:"/\|?*`, `.`/`..`, trailing `.`/space, device names such as `CON`, `com1.txt`) | `Name contains invalid characters.` |
| stripped name casefolds to a reserved name | `Name '<stripped name>' is reserved.` |

It returns `name.strip()` (Python `str.strip`, so U+3000 and other Unicode spaces are trimmed too). Callers: `dictionaries/manager.normalize_dictionary_name` (reserved `{"default"}`; used by `create_dictionary`, `import_dictionary`, `rename_dictionary`), `documents/workspace.normalize_document_name` (no reserved names; used by `save_document_package`, `load_document_package`, `load_text_document`, `gui._prompt_for_document_name`), and `documents/importers/base.py:23` (document name from a file stem).

`dialog._normalize_dialog_name(candidate, normalizer, empty, length, invalid, reserved=None)` (`dialog.py:62-86`) repeats the first four checks itself, then calls `normalizer(candidate.strip())` and, on `ValueError`, guesses the reason: reserved message if a reserved message was given and the stripped name casefolds to `"default"`; length message if `"exceed" in str(exc)` (unreachable, the length was checked already); otherwise the invalid message. The dialogs map:

| Outcome | `DictionaryNameDialog` (zh_TW shown) | `DocumentNameDialog` (zh_TW shown) |
| --- | --- | --- |
| empty | `Please enter the dictionary name.` (請輸入字典名稱。) | `Please enter the document name.` (請輸入文件名稱。) |
| too long | `Dictionary name must be 1 to 32 characters.` | `Document name must be 1 to 32 characters.` |
| control character, trailing space/period, Windows-illegal | `Dictionary name is not a valid Windows file name.` | `Document name is not a valid Windows file name.` |
| reserved | `Dictionary name "{name}" is reserved.` formatted with `DEFAULT_DICTIONARY_NAME` (`default`), whatever case the user typed | (cannot happen; documents have no reserved names) |

`_on_ok(event)` (both dialogs): validate `name_ctrl.GetValue()`; on a message, `wx.MessageBox(message, _("Info"), wx.OK | wx.ICON_INFORMATION, parent=self)`, then `name_ctrl.SetFocus()`, and return without `event.Skip()` (the dialog stays open); otherwise `name_ctrl.SetValue(normalized)` and `event.Skip()`. `_validate_name(candidate)` returns only the message; only tests call it. The seven message strings (four for dictionaries, three for documents) are passed through `_()` at each call, so each literal appears twice in `dialog.py`.

Consumers of the English messages (`str(exc)` of a name error):

- `dictionaries/presenter.py` `add` (line 105) and `rename` (line 149) catch `ValueError` and call `view.show_info(str(exc))`: the untranslated English text (P0-6 known quirk, pinned by `test_add_invalid_name_shows_untranslated_info` and `test_rename_invalid_name_shows_untranslated_info`). Not reachable from the real dialog, which validates first. `rename` must keep catching every `ValueError`: a padded `" default"` source passes `is_default_dictionary` and `rename_dictionary` raises `ValueError("Default dictionary cannot be renamed.")`.
- `presenter.import_from_file` maps every `ValueError`, including a name error, to `Imported file must contain text, braille, and type headers.` (P0-6 quirk).
- `documents/workspace.batch_import_documents` turns any loader exception into `BatchIssue(reason=str(exc))`, shown by `FileIssuesDialog` as `<file>: <reason>`. Importing `CON.txt` or a file with a 40-character stem shows the English name message. This one is reachable.
- `load_workspace_documents` catches every exception per package (invalid package list; the message is not shown).
- `documents/workspace_service.rename_document` raises its own `ValueError("A document cannot be renamed to its own name.")`, not a name error. `gui._prompt_for_document_name` normalizes the already-validated dialog result and does not catch.

The only string matching on the error text is `dialog.py:84` (`"exceed" in str(exc)`) plus the `"default"` casefold guess at `dialog.py:82`.

### `ConvertingDialog` (`gui.py:108-121`)

Title `_("Info")`, style `(wx.DEFAULT_DIALOG_STYLE & ~wx.CLOSE_BOX) | wx.STAY_ON_TOP`, one `wx.StaticText` `_("converting")` in a vertical `BoxSizer` with `wx.ALL | wx.ALIGN_CENTER_HORIZONTAL`, border 20, `finalize_dialog_layout`, `Bind(wx.EVT_CLOSE, self._on_close)`; `_on_close` vetoes when `evt.CanVeto()`. It is the only reason `gui.py` imports `finalize_dialog_layout`. Tests always patch `gui.ConvertingDialog`.

### Test stubs that the new code must work under

| Factory (`tests/wx_stub.py`) | `wx.Dialog` | Loads |
| --- | --- | --- |
| `dialog_validation_stubs` | `type("Dialog", (), {})`; the module has only 4 attributes, anything else raises `AttributeError` | `dialog` (isolate) |
| `speech_dialog_stubs` | plain class; `AutoSubmoduleModule`; evicts `dialog`, `dictionaries`, `documents`, `wx`, ... but not `ui`, `shared`, `i18n` | `dialog.py` under a private name |
| `dialog_display_stubs` | plain class; `AutoClassModule` (missing attributes become classes); evicts everything | `dialog.py` under a private name |
| `settings_dialog_stubs` | `RecordingWidget` subclass (masking `__getattr__`); defines `PyDeadObjectError(RuntimeError)` | `settings.dialogs` (isolate) |
| `gui_frame_stubs` | `Widget` subclass; replaces the whole `dialog` module with `_GUI_DIALOG_NAMES` fakes; defines `PyDeadObjectError` | `gui` |

Consequences: a base that subclasses `wx.Dialog` or holds a `wx` reference would bind to whichever stub imported it first and trip `StubScope`'s leak check (the speech scope does not evict `ui`). Module-level access to any `wx` attribute other than `Dialog`, `ListCtrl`, `Window`, `CommandEvent` breaks `test_dialog_validation`. So the new bases must be plain mixins with no `wx` import.

## Design

### Decision summary

- `ui/dialog_base.py` is wx-free and gui-free (4 spaces). It imports only the standard library, `i18n._` and `shared.name_validation`. The bases are plain mixins without `__init__`, `__new__`, `__slots__` or a metaclass, and come first in the base list (`class X(Mixin, wx.Dialog)`), so they combine with the sip classes of real wx and with every stub base.
- The only wx call a base needs (the name-error message box) is a hook implemented once in `dialog.py`; the only wx value (the dead-object exception type) is a class attribute set in `settings/dialogs.py`.
- `NameValidationError` subclasses `ValueError` and keeps the English message as its only argument, so every existing `except ValueError` and every `str(exc)` consumer behaves exactly as before. Consumers outside the name dialogs do not change.

### `NameValidationError` (`shared/name_validation.py`)

```python
NameValidationCode = Literal["empty", "invalid", "too_long", "reserved"]


class NameValidationError(ValueError):
    """``normalize_base_name`` rejected a name: ``code`` says why, ``str(error)`` is the English message."""

    def __init__(self, code: NameValidationCode, message: str) -> None:
        super().__init__(message)
        self.code = code
```

Each `raise ValueError(msg)` in `normalize_base_name` becomes `raise NameValidationError(code, msg)` with the same message and order: empty -> `"empty"`; control character, trailing space/period and Windows-illegal -> `"invalid"`; length -> `"too_long"`; reserved -> `"reserved"`. `error.args == (message,)` as before. Four codes, as section 4.3 asks; the trailing-space/period case shares `"invalid"` because every consumer treats it as invalid, and its distinct English message is still in `str(error)`. No hierarchy of error classes.

`dictionaries/manager.py`, `documents/workspace.py`, `documents/importers/base.py`, `dictionaries/presenter.py`, `documents/workspace_service.py` and `gui._prompt_for_document_name` need no code change: their normalize functions now raise `NameValidationError` through the same paths, and their handlers catch `ValueError` or `Exception`. The presenter deliberately keeps `except ValueError` (the padded-default rename case above needs it). Their tests gain assertions on the type and `code`.

### `ui/dialog_base.py`

```python
class ContextManagedDialog:
    """``with Dialog(...) as dialog:`` destroys the dialog on exit and never swallows an exception."""

    def __enter__(self: _DialogT) -> _DialogT:
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.Destroy()


@dataclass(frozen=True)
class NameDialogMessages:
    """Untranslated msgids (marked with ``N_`` where defined); translated when shown."""

    empty: str
    too_long: str
    invalid: str
    reserved: str | None = None   # may contain "{name}"
    reserved_name: str = ""       # value for "{name}"

    def message_for(self, code: str) -> str:
        if code == "empty":
            return _(self.empty)
        if code == "too_long":
            return _(self.too_long)
        if code == "reserved" and self.reserved is not None:
            return _(self.reserved).format(name=self.reserved_name)
        return _(self.invalid)


class NameDialogBase(ContextManagedDialog):
    """``_on_ok``/``_validate_name`` of a dialog with a ``name_ctrl`` text box.

    Subclasses set ``normalize_name`` (a staticmethod) and ``name_messages`` and implement
    ``_show_name_error``.
    """

    name_messages: ClassVar[NameDialogMessages]

    @staticmethod
    def normalize_name(name: str) -> str:
        raise NotImplementedError

    def _check_name(self, candidate: str) -> tuple[str | None, str | None]:
        try:
            return self.normalize_name(candidate), None
        except NameValidationError as error:
            code = error.code
        except ValueError:
            code = "invalid"
        return None, self.name_messages.message_for(code)

    def _validate_name(self, candidate: str) -> str | None:
        return self._check_name(candidate)[1]

    def _on_ok(self, event) -> None:
        normalized, message = self._check_name(self.name_ctrl.GetValue())
        if message:
            self._show_name_error(message)
            self.name_ctrl.SetFocus()
            return
        self.name_ctrl.SetValue(normalized)
        event.Skip()

    def _show_name_error(self, message: str) -> None:
        raise NotImplementedError


class SingletonDialogMixin:
    """At most one open dialog per class; ``show_singleton`` raises it or builds a new one.

    The open dialog lives in the class's own ``_instance`` (read through ``cls.__dict__``,
    so a subclass never sees its parent's dialog).
    """

    dead_window_error_types: ClassVar[tuple[type[BaseException], ...]] = ()

    @classmethod
    def _raise_existing(cls, prepare=None):
        instance = cls.__dict__.get("_instance")
        if instance is None:
            return None
        try:
            instance.Iconize(False)
            if prepare is not None:
                prepare(instance)
            instance.Raise()
            instance.SetFocus()
            return instance
        except (ReferenceError, RuntimeError, *cls.dead_window_error_types) as error:
            if not cls._is_destroyed_window_error(error):
                raise
            cls._instance = None
            return None

    @classmethod
    def _show_new(cls, instance):
        cls._instance = instance
        instance.Show()
        return instance

    def _destroy(self) -> None:
        owner = type(self)
        if owner.__dict__.get("_instance") is self:
            owner._instance = None
        self.Destroy()

    @classmethod
    def _is_destroyed_window_error(cls, error: BaseException) -> bool:
        if isinstance(error, cls.dead_window_error_types):
            return True
        if not isinstance(error, (ReferenceError, RuntimeError)):
            return False
        message = str(error).lower()
        return (
            "wrapped c/c++ object" in message
            or "has been deleted" in message
            or "already deleted" in message
            or "destroyed" in message
        )
```

Why the name check calls the normalizer on the raw text: `normalize_base_name` already runs the dialog's four pre-checks in the same order on the same raw text, then strips, so `normalizer(candidate)` gives the same normalized name and the same failing check as the old pre-checks followed by `normalizer(candidate.strip())`. A throwaway comparison of the old `_normalize_dialog_name` with the new mapping over 3,431 generated names (all strings up to 3 characters over 15 interesting characters, plus device names, `default` in three cases, 31-34 character names, U+3000/U+00A0/U+0085 padding) found no difference for either dialog, in message or normalized name. The `except ValueError` fallback keeps the old breadth: any other `ValueError` from a normalizer still means "invalid".

### `dialog.py`

- `from ui.dialog_base import ContextManagedDialog, NameDialogBase, NameDialogMessages`.
- `AddSymbolDialog`, `InvalidWorkspaceFilesDialog`, `FileIssuesDialog`, `SpeechSymbolsDialog`, `DictionaryManagementDialog` become `class X(ContextManagedDialog, wx.Dialog)` and lose their `__enter__/__exit__`. Nothing else in them changes.
- A private wx base for the two name dialogs:

```python
class _NameDialog(NameDialogBase, wx.Dialog):
	def _show_name_error(self, message: str) -> None:
		wx.MessageBox(message, _("Info"), wx.OK | wx.ICON_INFORMATION, parent=self)
```

- `DictionaryNameDialog(_NameDialog)` sets `normalize_name = staticmethod(normalize_dictionary_name)` and `name_messages = NameDialogMessages(empty=N_("Please enter the dictionary name."), too_long=N_("Dictionary name must be 1 to 32 characters."), invalid=N_("Dictionary name is not a valid Windows file name."), reserved=N_('Dictionary name "{name}" is reserved.'), reserved_name=DEFAULT_DICTIONARY_NAME)`. `DocumentNameDialog(_NameDialog)` sets `normalize_document_name` and its three messages (no reserved message). Both lose `_on_ok`, `_validate_name`, `__enter__`, `__exit__`. Constructors, `get_dictionary_name`, `get_document_name` and `_apply_initial_name` do not change.
- `_normalize_dialog_name` is deleted; the `MAX_DICTIONARY_NAME_LENGTH` import goes (the constant stays in `dictionaries/manager.py`, now without a consumer; see Out of Scope).
- `ConvertingDialog` is added with its class body copied unchanged (both files use tabs).

### `settings/dialogs.py`

```python
_DEAD_WINDOW_ERROR_TYPES = tuple(
    error_type for error_type in (getattr(wx, "PyDeadObjectError", None),) if error_type is not None
)


class TextProcessingDialog(SingletonDialogMixin, SettingsDialog):
    _instance: "TextProcessingDialog | None" = None
    dead_window_error_types = _DEAD_WINDOW_ERROR_TYPES
    ...
    @classmethod
    def show_singleton(cls, *, parent, script_path: Path | str) -> "TextProcessingDialog":
        existing = cls._raise_existing()
        if existing is not None:
            return existing
        return cls._show_new(cls(parent, script_path=script_path))
```

`DotExpressSettingsDialog(SingletonDialogMixin, MultiCategorySettingsDialog)` does the same, keeping its `initial_category` check first and passing `prepare=lambda instance: instance.select_category(initial_category)` only when `initial_category is not None`. Both lose `_destroy` and `_is_destroyed_window_error`; `on_ok`/`on_cancel` keep calling `self._destroy()`. Signatures of `show_singleton` do not change. `sync_open_font_size` is not touched (P2-4).

### `gui.py`

`ConvertingDialog` is removed and imported from `dialog`; the `finalize_dialog_layout` import is removed (no other user). `show_converting_dialog` / `close_converting_dialog` do not change. `tests/wx_stub.py` adds `"ConvertingDialog"` to `_GUI_DIALOG_NAMES` so the stubbed `dialog` module provides it; tests keep patching `gui.ConvertingDialog`.

Why `dialog.py` and not a new `ui/` module: `dialog.py` is the home of the wx dialog classes and of `finalize_dialog_layout`, and the gui test scope already replaces it as a whole. A new wx-importing `ui/` module would need to be added to the gui scope's isolate names and would break the "`ui/` P1 modules are wx-free" pattern.

### Decisions on behavior

- **D1 (dead-window exception type, not observable in the app).** The mixin resolves `PyDeadObjectError` with `getattr`, as `_is_destroyed_window_error` already did, instead of naming `wx.PyDeadObjectError` in the `except` tuple. Where wx defines the type (every test stub) nothing changes. Where it does not (believed: real wxPython 4.2.5), an exception raised while raising the existing dialog is now handled as the code intends (dead -> rebuild, other -> re-raise the original error) instead of becoming `AttributeError`. That path cannot be reached in the app (see Current State). Rejected alternative: a classmethod hook that names `wx.PyDeadObjectError` lazily, which would keep the `AttributeError` on purpose. Windows check listed below.
- **D2 (`_destroy` owner).** `_destroy` clears `type(self)`'s slot instead of a named class. For the two production classes this is the same class; it differs only for a subclass, which then clears its own slot (the one `show_singleton` set), not the parent's.
- **D3 (normalizer binding).** `normalize_name` is bound when the class is defined instead of looked up as a module global on every call. Nothing patches `dialog.normalize_dictionary_name` or `dialog.normalize_document_name`.
- **D4 (translation timing).** The seven name-dialog messages are defined once with `N_()` and translated with `_()` when shown. Same catalog, same text, same msgid set (353).

## What Stays Identical

- Every string a user can see, in English and zh_TW, for every name input; the reserved message still says `default` whatever case was typed.
- `_on_ok` order: message box, then focus, no `Skip`; or `SetValue(normalized)`, then `Skip`.
- `str()` and `args` of every name error; every `except ValueError` and `except Exception` handler; the presenter's untranslated info text; the import header mapping; the file-issues reasons.
- `show_singleton` call order (`Iconize(False)`, [`select_category`], `Raise`, `SetFocus`), slot assignment before `Show`, `ValueError` for an unregistered category before the slot is read, re-raise of non-dead errors with the slot kept, constructor failure leaving the slot unchanged.
- `with` semantics: same object returned, `Destroy` exactly once, exceptions propagate.
- `ConvertingDialog` construction and veto.
- `client/locales`, `scripts/`, `client/dictionaries/`, `client/documents/`, `client/conversion/` have no diff.

## Test Plan

Characterization first: part A is committed before any production change and is not edited afterwards, except that tests which name `gui.ConvertingDialog` as the class under test switch to `dialog.ConvertingDialog` in the move commit.

### A. Characterization (step 1)

1. `tests/test_dialog_validation.py` (dialog-validation stubs):
   - Frozen oracle: a verbatim copy of today's `_normalize_dialog_name` lives in the test module (renamed, with a comment that it is the pre-P2-1 reference). For a generated corpus (as above) both dialogs' `_validate_name` must equal the oracle's message, and on a sample the normalized name is checked through `_on_ok` (`SetValue`).
   - Explicit table, exact zh_TW text: empty, whitespace-only, U+3000-only, control character, trailing space, trailing period, trailing U+3000 accepted (`name　` -> `name`), leading space accepted, 32 vs 33 characters, 33 characters after stripping, `a?b`, `CON`, `con.txt`, `..`, `default`/`Default`/`DEFAULT` (dictionary: reserved message with `default`; document: accepted).
   - `_on_ok` for both dialogs (with `wx.MessageBox`, `wx.OK`, `wx.ICON_INFORMATION` patched onto the stub with `create=True`): invalid input records exactly `MessageBox(message, "資訊", OK | ICON_INFORMATION, parent=dialog)`, then `SetFocus`, no `SetValue`, no `Skip`; `" name"` records `SetValue("name")` then one `Skip`, no message box.
   - Context manager for the seven classes (instances from `object.__new__`, `Destroy` a `Mock`): `with` returns the same object; `Destroy` called once on normal exit and once when the block raises; the exception propagates; `__exit__` returns `None`.
2. New `tests/test_name_validation.py`: every check of `normalize_base_name` with its exact English message and `ValueError` type, the returned stripped name, reserved casefolding, and `str(error)`/`args`.
3. `tests/test_settings_dialogs.py`, for both singleton classes: new-instance path (forwarded keyword arguments, slot set before `Show`, returns the instance); live instance path order, with and without `initial_category`; dead instance rebuilt for `PyDeadObjectError`, for `RuntimeError` with each of the four phrases and for `ReferenceError("... has been deleted")`; `ReferenceError` without a phrase and an unrelated `RuntimeError` re-raised with the slot kept; `_destroy` clears only its own instance and always calls `Destroy`; the two classes' slots are independent; unregistered category raises before the slot is touched; a constructor `OSError` leaves the slot `None`.
4. `ConvertingDialog`: constructor arguments (parent, title, style value), label, sizer flags and border, `EVT_CLOSE` binding, veto only when `CanVeto()`; run against `gui.ConvertingDialog` under the gui stubs (recording `wx.Dialog.__init__`) until the move.

### B. Typed error (step 2)

`NameValidationError` is a `ValueError`; `code` for each check; message unchanged; `normalize_dictionary_name`, `normalize_document_name` and the importer base name raise it with the expected code; the presenter tests stay unchanged and green.

### C. `ui/dialog_base.py` (step 3, new `tests/test_dialog_base.py`, no wx, no stub scope)

Each base combined with (a) a plain `type("Dialog", (), {})` base and (b) `wx_stub.RecordingWidget`-style masking bases, proving MRO and behavior: `ContextManagedDialog` semantics; `NameDialogMessages.message_for` for each code, the missing-reserved fallback and `{name}` formatting; `NameDialogBase` with a fake normalizer (typed codes, plain `ValueError` -> invalid, `_on_ok` call order); `SingletonDialogMixin` slot isolation through `cls.__dict__` (a subclass that does not declare `_instance` does not see the parent's), raise/rebuild/re-raise paths with a custom `dead_window_error_types`. An AST guard asserts the module imports no `wx`, `gui`, `dialog` or `settings`.

### D. Migration (steps 4-6)

No new assertions; parts A and B must stay green unchanged. Guards updated in the same commit as the change they guard: `_GUI_DIALOG_NAMES` gains `ConvertingDialog`.

The plan fixes the exact number of new tests.

## Migration Steps (each step one green commit)

1. `test: characterize dialog lifecycle, name validation and singletons` (part A).
2. `refactor: raise typed NameValidationError for invalid names` (part B).
3. `refactor: add wx-free dialog base mixins` (part C; module not used yet).
4. `refactor: use dialog base mixins in dialog.py` (seven context managers, two name dialogs, delete `_normalize_dialog_name`).
5. `refactor: use SingletonDialogMixin in settings dialogs`.
6. `refactor: move ConvertingDialog into dialog.py`.

## Acceptance Criteria

1. Roadmap verification on Linux: `cd client && python -m unittest tests.test_dialog_validation tests.test_dialog_display tests.test_settings_dialogs -v` passes.
2. Also green: `tests.test_name_validation tests.test_dialog_base tests.test_dictionary_manager tests.test_document_workspace tests.test_dictionary_presenter tests.test_dictionary_management_dialog tests.test_speech_symbols_dialog tests.test_gui_document_flows tests.test_workspace_service tests.test_i18n tests.test_removed_dead_code tests.test_wx_stub`.
3. Full suite: 818 + the new tests, `failures=1` (P2-5 only), `errors=0`, `skipped=9`. The shuffle harness (`$SP/shuffle_harness.py`, seeds 0-19) shows the same single failure for every seed; `test_dialog_validation`, `test_dialog_display`, `test_speech_symbols_dialog`, `test_dictionary_management_dialog`, `test_settings_dialogs` and `test_gui_document_flows` also pass alone and in both orders of each pair with `test_dialog_base`.
4. `grep -n "def __enter__\|def __exit__\|_normalize_dialog_name\|\"exceed\"" client/dialog.py` prints nothing; `grep -n "_is_destroyed_window_error\|def _destroy" client/settings/dialogs.py` prints nothing; `grep -n "raise ValueError" client/shared/name_validation.py` prints nothing; `grep -n "class ConvertingDialog\|finalize_dialog_layout" client/gui.py` prints nothing; `grep -rn "in str(exc)" client --include=*.py --exclude-dir=tests` prints nothing.
5. Msgid scan: 353 source msgids, the same 4 only-in-pot orphans, nothing only in source; `git diff main --stat -- client/locales scripts` is empty.
6. `git diff main --stat -- client/dictionaries client/documents client/conversion client/about.py client/ui` lists only `client/ui/dialog_base.py` (new).
7. `client/ui/dialog_base.py` passes the AST guard (no `wx`, `gui`, `dialog`, `settings` import).

## Risks

- **Mixins on real wx (cannot run here).** Plain mixins before a sip class are a standard wxPython pattern; the mixins define no `__init__`, `__new__`, `__slots__` or metaclass. Verified only with stubs on Linux.
- **Stub-scope class identity.** If `shared.name_validation` were evicted and re-imported while `ui.dialog_base` kept the old class, `except NameValidationError` would miss and every error would show the invalid message. It cannot happen with the current eviction rules (a module is evicted only if first imported inside that scope, and `ui.dialog_base` imports `shared.name_validation` itself), and the oracle tests in shuffled order would catch it.
- **Hidden callers of removed names.** `_normalize_dialog_name`, `_is_destroyed_window_error` and the per-class `__enter__/__exit__` have no callers outside the files changed (grep); `_validate_name`, `_destroy` and `show_singleton` keep their names.
- **D1 changes an unreachable path on real wx**; listed for Windows verification.

## Known quirks kept (pinned, not fixed)

1. The dictionary presenter shows `str(exc)` (untranslated English) for a name error in add/rename (P0-6). Unreachable from the real dialog. Fix later by mapping `NameValidationError.code` to the dialog messages; that changes presenter output, so it is a separate task.
2. The presenter maps a name error during import to the CSV header message (P0-6).
3. Import file-issue reasons show the English name message (for example `CON.txt: Name contains invalid characters.`) to zh_TW users. Reachable. Belongs with the P1 localization defect (defect 4 in the P1 review list); the typed `code` now makes it a small change.
4. The reserved-name message always names `default`, even when the user typed `Default` or `DEFAULT`.
5. `_is_destroyed_window_error` treats a `ReferenceError` without one of the four phrases (for example `weakly-referenced object no longer exists`) as not dead.

## Windows verification debt

- `python -c "import wx; print(wx.version(), hasattr(wx, 'PyDeadObjectError'))"` on the build machine (expected `4.2.5 ... False`; confirms D1's premise).
- Packaged build: open and close every dialog in the inventory; Add/Rename Dictionary and Add/Rename Document with an empty, a 33-character, a `CON` and (dictionary) a `Default` name show the same zh_TW messages and keep the dialog open; Settings and Text Processing opened twice raise the existing window, then close and reopen; the converting dialog appears during a long conversion and cannot be closed with Alt+F4. No screenshots needed (no visual change).
- PyInstaller picks up `ui/dialog_base.py` through the static imports in `dialog.py` and `settings/dialogs.py` (read, not run).

## Out of Scope

- Unifying the two name-dialog constructors (different title handling and `SetValue` timing) or the `get_*_name` accessors.
- `AddSymbolDialog` and the translated domain messages in `dictionaries/entries.py` (section 4.3 note).
- `sync_open_font_size` and the reverse probe (P2-4); making the settings dialogs context managers.
- Changing any presenter or importer error handling, or removing `MAX_DICTIONARY_NAME_LENGTH` (no consumer after this task; dead-code follow-up).
- Converging the stub profiles in `tests/wx_stub.py`.
