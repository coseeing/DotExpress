# Dictionary Management Presenter (P0-6) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move the dictionary-management workflow (add, delete, rename, import, export, and the single dictionary name list) out of `BrailleFrame` into a wx-free `DictionaryManagementPresenter` in `client/dictionaries/presenter.py`. `DictionaryManagementDialog` takes `(parent, actions, selected_name)` and implements the presenter's view protocol with the exact wx calls the frame makes today. No user-visible change, no msgid change, `.po`/`.mo` untouched.

**Architecture:** The presenter owns the listing of the dictionary directory and the five flows; it reads the active dictionary through `get_active_name()` and changes it only through `set_active_name(name)` (wired to the frame's existing `_set_active_dictionary`). It talks to the user only through `DictionaryManagementView` (`prompt_dictionary_name`, `show_info`, `show_error`, `confirm`, `choose_import_path`, `choose_export_path`), which the dialog implements, parented on itself. Tasks 1-6 build the presenter flow by flow, test first, while the app does not use it yet. Task 7 switches the dialog and the frame in one commit (the dialog constructor and its only caller must change together). Task 8 deletes the gui helpers and imports that Task 7 left unused. Task 9 is the spec's acceptance run.

**Tech Stack:** Python 3 standard library (`unittest`, `unittest.mock`, `tempfile`, `ast`, `inspect`, `typing.Protocol`). wxPython is not installed; the dialog and the frame load through the P0-4 `tests/wx_stub.py` scopes.

**Spec:** `docs/superpowers/specs/2026-10-08-p0-6-dictionary-presenter-design.md` (authoritative, commit `18094ed`). The corrections and refinements decided here are listed below.

## Global Constraints

- Branch: `refactor/p0-6-dictionary-presenter`. Never switch to or merge into `main`, never push, never rewrite history.
- Files that may change: `client/dictionaries/presenter.py` (new), `client/tests/test_dictionary_presenter.py` (new), `client/dialog.py`, `client/gui.py`, `client/tests/test_dictionary_management_dialog.py`, `client/tests/test_gui_document_flows.py`, `client/tests/wx_stub.py`. Nothing else: no `.pot`/`.po`/`.mo`, no other module under `client/dictionaries/` or `client/translation/`, and none of the safety-net tests (`test_dictionary_manager`, `test_dictionary_actions`, `test_translation_dictionary_state`, `test_dictionary_name_prompt`, `test_dictionary_entries`, `test_speech_symbols_dialog`, `test_settings_dialogs`, `test_i18n`, `test_wx_stub`).
- Indentation per file, unchanged: TABS in `client/dictionaries/presenter.py`, `client/tests/test_dictionary_presenter.py`, `client/dialog.py`, `client/gui.py`, `client/tests/test_dictionary_management_dialog.py`; 4 spaces in `client/tests/test_gui_document_flows.py` and `client/tests/wx_stub.py`. The blocks below carry the right characters; run them as they are, do not retype them.
- ASCII only in every changed file (the tests write the braille cell U+2801 as the escape `\u2801`).
- Every commit message ends with a blank line, then `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>` (the commit blocks below already do this).
- Expected-failure blocks quote the `FAIL:`/`ERROR:` header lines, the first line of each exception and the summary lines, with timings omitted (the dry run filtered with `grep -E "^(FAIL|ERROR):|^[A-Za-z]+Error:|^Ran|^FAILED|^OK"`). Paths are shown for the repo at `/workspace/DotExpress`.
- Every file, patch and commit block is a complete shell command; run it as is (heredoc delimiters are quoted, so nothing is expanded). If `git apply` refuses a patch, stop and re-check the previous task; do not hand-merge.
- Shell variables used below:
  ```bash
  REPO=/workspace/DotExpress
  SP=/tmp/claude-0/-workspace-DotExpress/c0b338ab-efa4-4037-b0f9-1b4ce4e6c150/scratchpad
  PY=$SP/venv/bin/python
  T=$SP/p06impl
  cd $REPO/client
  ```
  Unless a step says otherwise, run commands from `$REPO/client`. `client/` must contain the git-ignored `log/` directory, as the working tree does today.
- Baseline (re-verified at `18094ed`, the spec commit; code identical to the spec's `70aae6b`): `$PY -m unittest discover -s tests` gives `Ran 482 tests`, `FAILED (failures=1, skipped=7)`; the one failure is the P2-5 case `test_conversion_service ... test_translate_with_language_does_not_duplicate_existing_spaces_around_math`. Task 0 records the baseline files the later checks compare against.

## Spec Corrections and Refinements (decided in this plan)

1. **Factual correction: acceptance criterion 3 cannot be a plain substring check.** `_dictionary_names` is a substring of `get_dictionary_names_for_dialog`, which the spec keeps (its name and callers do not change). After the change a plain `grep _dictionary_names client/gui.py` still prints 4 lines (the method and its three callers). Task 9 checks whole identifiers with `grep -nwE`, which prints nothing.
2. **Factual correction: acceptance criterion 2's "called exactly once" needs the definition excluded.** `grep "prompt_dictionary_name_until_success("` also matches `def prompt_dictionary_name_until_success(` in `dictionaries/name_prompt.py`. Task 9 drops the `def` line and expects exactly one call (in the presenter). The msgid `Dictionary "{name}" already exists.` check works as written (exactly one line).
3. **Factual correction (minor): "case-only change: renames" holds only on a case-sensitive file system.** On Windows (NTFS is case-insensitive) `rename_dictionary` sees `Alpha.csv` as existing when `alpha.csv` exists and raises `FileExistsError`, so the name loop shows the duplicate box and prompts again. That is today's behavior and this task keeps it (the presenter calls the same helper). `test_rename_case_only_change_renames_file` therefore skips itself on a case-insensitive file system (it runs on the Linux box). Added to the spec's follow-ups in spirit; no code change.
4. **Commit split refined.** Spec commit 1 becomes Tasks 1-6 (`feat:`, one commit per flow, each holding its tests and its code, red shown first). Spec commit 2 is Task 7 (`refactor: route dictionary management through presenter`). Task 7 also deletes the five frame callbacks and `_refresh_dictionary_names`, because after the switch they would read state (`self._dictionary_names`) that no longer exists. Task 8 then removes the remaining dead helpers and imports with the subject `refactor: remove dead dictionary helpers from gui` (the spec's commit 3 allows this: "if step 2 did not already remove them").
5. **Stub constants (refinement the spec allows).** `speech_dialog_stubs()` gets distinct power-of-two values for `ICON_INFORMATION`, `ICON_WARNING`, `YES_NO`, `NO_DEFAULT`, `YES`, `NO`, `FD_OPEN`, `FD_SAVE`, `FD_OVERWRITE_PROMPT` and plain ids `ID_OK = 5100`, `ID_CANCEL = 5101` (the spec's list plus `NO` and `ID_CANCEL`, so the cancel and "No" paths use real values). Without them the `AutoSubmoduleModule` folds `wx.YES_NO | wx.NO_DEFAULT | wx.ICON_WARNING` into `wx.YES_NO`, and a flag assertion could not catch a dropped flag. `gui_frame_stubs()` gets `ID_EDIT = 5030` (not in the spec): that stub's module `__getattr__` returns a new class on every access, so without it `gui.wx.ID_EDIT != gui.wx.ID_EDIT` and the edit branch of `on_open_dictionary_management` cannot be reached in a test. The dry run confirmed `test_speech_symbols_dialog` (21), `test_wx_stub` (16), `test_dialog_display` and `test_dialog_validation` pass unchanged.
6. **Dialog constructor detail.** It keeps the old order: `self._dictionary_names = list(actions.dictionary_names)` before `_build_ui()`, then `self.refresh_dictionaries(self._dictionary_names, selected_name)`. Same values as the spec's `refresh_dictionaries(actions.dictionary_names, selected_name)`, and the list exists while the widgets are built, as today. `_refresh_from_disk` becomes `_refresh_from_actions(preferred)`. `CSV_WILDCARD` moves to `dialog.py`; `_(CSV_WILDCARD)` is evaluated inside the two file-dialog view methods (call time).
7. **Presenter tests (refinement of the spec's minimum list).** `test_dictionary_presenter.py` has **43** tests in 7 classes. Beyond the spec's minimum cases it pins: the constructor does no I/O; `refresh` sees files added on disk (and `dictionary_names` does not until then); the presenter and `DictionaryManagementActions` expose the same members; import reports a duplicate name before it validates headers; delete and rename leave the active name and the list untouched on `OSError`. `FakeView` pops scripted answers (`None` means Cancel); an unexpected prompt raises `IndexError`, so every test also proves no extra prompt happens. The missing-source import test builds its expected message by opening the missing path the way `validate_dictionary_csv` does, so the text is right on any platform.
8. **Dialog and frame tests.** `test_dictionary_management_dialog.py` goes from 8 to **26** tests (one existing test is replaced: `test_disk_refresh_discovers_new_dictionary_files` becomes `test_refresh_after_action_takes_names_from_actions_not_disk`). `test_gui_document_flows.py` goes from 61 to **68** (6 in Task 7, 1 in Task 8, all in a new `DictionaryManagementFrameTest`).
9. **`_show_file_error` keeps its `parent` parameter** (the spec keeps the method). After this change no caller passes `parent`; removing the parameter is out of scope.

Everything else in the spec was re-checked at `18094ed`: the line ranges (`gui.py` 294-300, 563-571, 600-606, 611-612, 1234-1438; `dialog.py` 191-239 and 650-845), every flow-inventory step against the code, the absence of other callers of the five callbacks, `_prompt_for_dictionary_name`, `CSV_WILDCARD`/`_get_csv_wildcard` and `DictionaryNameDialog` in `gui.py`, `_show_file_error`/`_get_selected_dictionary_path`/`self.dictionary_dir` staying used elsewhere, the per-module counts (`test_dictionary_management_dialog` 8, `test_dictionary_manager` 11, `test_dictionary_actions` 6, `test_translation_dictionary_state` 6, `test_dictionary_name_prompt` 4, `test_gui_document_flows` 61, `test_dictionary_entries` 8, `test_speech_symbols_dialog` 21, `test_settings_dialogs` 27; also `test_i18n` 16, `test_wx_stub` 16), the roadmap command (96 tests, `OK`), and the msgid scan (357 msgids, source set == `.pot` set).

## Dry Run

The whole plan was executed on a scratch copy (`$SP/p06/dry`, built from the tracked `client/` and `scripts/` files at `18094ed`, never the repo): every test block was red exactly as quoted, every implementation block turned it green, and the suite check after each task gave the counts in the table below. The patches were then replayed mechanically on a fresh copy (`$SP/p06/dry2`), which produced the red outputs quoted in this file and a tree identical to the first copy. Finally the blocks of this file were extracted and run in order on a third fresh copy (`$SP/p06/dry3`): all 8 commits applied, each step gave the quoted result, and the final `client/dictionaries/presenter.py` has sha256 `9c1a396577e103b02ca6ac1d95b7f9da41044ffbaab80b4508a65266d1e9dd8a` and `client/tests/test_dictionary_presenter.py` has sha256 `baa8028794dcf9f49ed03053c5697d7c56a56c6856b06275a42f4593ec48856f`.

## Review Focus

1. Message text, caption, flags, parent and order are unchanged. Tests: the full `view.calls` sequences in `test_dictionary_presenter` (every flow, every exit path); `DictionaryManagementViewTest` (each view method makes exactly the old wx call, `parent=dialog`).
2. The exception quirks are kept and pinned: add does not catch `OSError`; delete does not catch `ValueError`; import maps every `ValueError` to the header message; rename of `default` is silent; add and import never change the active dictionary.
3. The active dictionary changes only through delete and rename, via `set_active_name` = `BrailleFrame._set_active_dictionary` (one `set_selected_dictionary` write). Test: `test_initialize_state_wires_presenter_to_active_dictionary` runs a real delete through the frame-built presenter.
4. One list source: the dialog takes names only from `actions.dictionary_names` (`test_refresh_after_action_takes_names_from_actions_not_disk`), the frame only from the presenter; `dialog.py` no longer lists the directory.
5. Strings: same msgids, all translated at call time; the AST msgid scan is identical before and after (Task 9).

## File Map

- Create `client/dictionaries/presenter.py` (Task 1; flows added in Tasks 2-6).
- Create `client/tests/test_dictionary_presenter.py` (Task 1; extended in Tasks 2-6).
- Modify `client/tests/wx_stub.py`, `client/tests/test_dictionary_management_dialog.py`, `client/dialog.py` (Task 7).
- Modify `client/tests/test_gui_document_flows.py`, `client/gui.py` (Tasks 7 and 8).

## Expected Counts

| After task | `test_dictionary_presenter` | new tests ok (suite check) | `discover` `Ran` |
| --- | --- | --- | --- |
| baseline | - | 0 | 482 |
| 1 skeleton + refresh | 9 | 9 | 491 |
| 2 add | 15 | 15 | 497 |
| 3 delete | 21 | 21 | 503 |
| 4 rename | 30 | 30 | 512 |
| 5 import | 38 | 38 | 520 |
| 6 export | 43 | 43 | 525 |
| 7 dialog + frame switch | 43 | 68 | 549 |
| 8 dead helpers | 43 | 69 | 550 |

Every row: `FAILED (failures=1, skipped=7)`, the one failure being the P2-5 case, and `BASELINE-TESTS-IDENTICAL`. "New tests" are the tests of `test_dictionary_presenter`, the three new classes `DictionaryManagementActionsWiringTest`, `DictionaryManagementViewTest`, `DictionaryManagementFrameTest`, and the replaced dialog test; every other test line of the verbose run must equal the baseline.

Per-task suite check (from `$REPO/client`):

```bash
$T/tools/check_suite.sh <Ran> <new tests ok>
```

Expected: `Ran <Ran> tests`, `FAILED (failures=1, skipped=7)`, the one `FAIL:` line of the P2-5 case, `BASELINE-TESTS-IDENTICAL`, `RAN-COUNT-OK (<Ran>)`, `new tests ok: <n> (expected <n>)`.

## Throwaway Tooling (not committed)

All in `$T/tools/`, outside the repo:

- `check_suite.sh <Ran> <new ok>`: full `discover -v`, compares every test line except the new ones and the replaced `test_disk_refresh_discovers_new_dictionary_files` with `$T/baseline_discover_verbose.txt`, counts passing new tests. Source in the Appendix.
- `msgid_scan.py <client_dir> [--save F] [--compare F]`: the P0-5 AST stand-in for xgettext (keywords `_` and `N_`, same file set as `scripts/generate-pot.bat`), unchanged. Copy it from `$SP/p05/tools/msgid_scan.py`; if that file is gone, its source is in the Appendix of `docs/superpowers/plans/2026-10-08-p0-5-i18n.md`.

---

### Task 0: Record the baseline (no commit)

- [ ] **Step 1: Check the starting point.**

```bash
git -C $REPO status --short
git -C $REPO log --oneline -1
git -C $REPO branch --show-current
```

Expected: no output from `status`; HEAD is the plan commit (`docs: plan dictionary management presenter`); branch `refactor/p0-6-dictionary-presenter`.

- [ ] **Step 2: Create the tools and record the baseline files.**

```bash
mkdir -p $T/tools   # then write check_suite.sh from the Appendix
chmod +x $T/tools/check_suite.sh
cp $SP/p05/tools/msgid_scan.py $T/tools/msgid_scan.py
$PY -m unittest discover -s tests -v 2>&1 | grep ' \.\.\. ' | sort > $T/baseline_discover_verbose.txt
wc -l < $T/baseline_discover_verbose.txt
$PY -I $T/tools/msgid_scan.py $REPO/client --save $T/baseline_msgids.json
$PY -m unittest tests.test_dictionary_management_dialog tests.test_dictionary_manager tests.test_dictionary_actions tests.test_translation_dictionary_state tests.test_dictionary_name_prompt tests.test_gui_document_flows 2>&1 | tail -3
```

Expected: `482`; `source msgids: 357`, `pot msgids: 357`, `SOURCE == POT`, `saved ...`; `Ran 96 tests`, `OK`.

---

### Task 1: Presenter skeleton, protocols, `refresh` and the name list

**Files:**
- Create: `client/tests/test_dictionary_presenter.py`
- Create: `client/dictionaries/presenter.py`

**Interfaces:** `DictionaryManagementView` and `DictionaryManagementActions` (`typing.Protocol`, complete); `DictionaryManagementPresenter(dictionary_dir, *, get_active_name, set_active_name)` with `dictionary_dir` (read-only property), `dictionary_names` (property, a new list each time), `refresh(preferred_name=None) -> str` and `dictionary_path(name) -> Path`. Manager functions are imported by name into the presenter module so tests can patch them there.

- [ ] **Step 1: Write the failing tests.** `FakeView` records `("prompt", title, initial)`, `("info", msg)`, `("error", msg)`, `("confirm", msg, caption)`, `("choose_import", title)`, `("choose_export", title, default_file)` and answers from scripted values. `PresenterTestCase` gives each test a fresh temporary `dictionary_dir`, an active name in `self.active[0]` and a `set_active_name` mock that also updates it. `make_presenter(*names, active=...)` writes header-only CSV files, builds the presenter and calls `refresh(active)` (as the frame does before opening the dialog).

```bash
cat > $REPO/client/tests/test_dictionary_presenter.py <<'EOF'
import ast
import tempfile
import unittest
from pathlib import Path
from typing import Protocol
from unittest.mock import Mock, patch

from dictionaries import presenter as presenter_module
from dictionaries.presenter import DictionaryManagementPresenter
from i18n import _


PRESENTER_PATH = Path(presenter_module.__file__)
HEADER = "text,braille,type\n"


class FakeView:
	"""Records every view call in order and answers from scripted values."""

	def __init__(self, *, names=(), confirm=True, import_path=None, export_path=None):
		self.calls = []
		self._names = list(names)
		self._confirm = confirm
		self._import_path = import_path
		self._export_path = export_path

	def prompt_dictionary_name(self, title, initial_name):
		self.calls.append(("prompt", title, initial_name))
		return self._names.pop(0)

	def show_info(self, message):
		self.calls.append(("info", message))

	def show_error(self, message):
		self.calls.append(("error", message))

	def confirm(self, message, caption):
		self.calls.append(("confirm", message, caption))
		return self._confirm

	def choose_import_path(self, title):
		self.calls.append(("choose_import", title))
		return self._import_path

	def choose_export_path(self, title, default_file):
		self.calls.append(("choose_export", title, default_file))
		return self._export_path


class PresenterTestCase(unittest.TestCase):
	def setUp(self):
		temp_dir = tempfile.TemporaryDirectory()
		self.addCleanup(temp_dir.cleanup)
		self.root = Path(temp_dir.name)
		self.dictionary_dir = self.root / "dictionaries"
		self.active = ["default"]
		self.set_active_name = Mock(side_effect=lambda name: self.active.__setitem__(0, name))

	def write_dictionary(self, name, content=HEADER):
		self.dictionary_dir.mkdir(parents=True, exist_ok=True)
		path = self.dictionary_dir / f"{name}.csv"
		path.write_text(content, encoding="utf-8")
		return path

	def make_presenter(self, *names, active="default"):
		for name in names:
			self.write_dictionary(name)
		self.active[0] = active
		presenter = DictionaryManagementPresenter(
			self.dictionary_dir,
			get_active_name=lambda: self.active[0],
			set_active_name=self.set_active_name,
		)
		presenter.refresh(active)
		return presenter

	def files(self):
		return sorted(path.stem for path in self.dictionary_dir.glob("*.csv"))


class PresenterModuleTest(unittest.TestCase):
	def test_presenter_module_does_not_import_wx(self):
		tree = ast.parse(PRESENTER_PATH.read_text(encoding="utf-8"))
		imported = set()
		for node in ast.walk(tree):
			if isinstance(node, ast.Import):
				imported.update(alias.name.split(".")[0] for alias in node.names)
			elif isinstance(node, ast.ImportFrom) and node.module:
				imported.add(node.module.split(".")[0])

		self.assertNotIn("wx", imported)

	def test_view_and_actions_are_protocols(self):
		for name in ("DictionaryManagementView", "DictionaryManagementActions"):
			with self.subTest(name=name):
				self.assertIn(Protocol, getattr(presenter_module, name).__bases__)


class PresenterRefreshTest(PresenterTestCase):
	def test_constructor_does_no_io(self):
		presenter = DictionaryManagementPresenter(
			self.dictionary_dir,
			get_active_name=lambda: "default",
			set_active_name=self.set_active_name,
		)

		self.assertFalse(self.dictionary_dir.exists())
		self.assertEqual(presenter.dictionary_names, [])
		self.assertEqual(presenter.dictionary_dir, self.dictionary_dir)

	def test_refresh_creates_default_dictionary_and_selects_it(self):
		presenter = DictionaryManagementPresenter(
			self.dictionary_dir,
			get_active_name=lambda: "default",
			set_active_name=self.set_active_name,
		)

		selected = presenter.refresh()

		self.assertEqual(selected, "default")
		self.assertEqual(presenter.dictionary_names, ["default"])
		self.assertEqual((self.dictionary_dir / "default.csv").read_text(encoding="utf-8").splitlines(), ["text,braille,type"])

	def test_refresh_lists_names_case_insensitively_and_keeps_preferred_name(self):
		presenter = self.make_presenter("beta", "Alpha")

		selected = presenter.refresh("beta")

		self.assertEqual(selected, "beta")
		self.assertEqual(presenter.dictionary_names, ["Alpha", "beta", "default"])

	def test_refresh_falls_back_to_default_for_unknown_name(self):
		presenter = self.make_presenter("alpha")

		self.assertEqual(presenter.refresh("missing"), "default")
		self.assertEqual(presenter.refresh(None), "default")

	def test_refresh_picks_up_files_added_on_disk(self):
		presenter = self.make_presenter()
		self.write_dictionary("later")

		self.assertEqual(presenter.dictionary_names, ["default"])
		presenter.refresh()
		self.assertEqual(presenter.dictionary_names, ["default", "later"])

	def test_dictionary_names_returns_a_copy(self):
		presenter = self.make_presenter("alpha")

		names = presenter.dictionary_names
		names.append("intruder")

		self.assertIsNot(presenter.dictionary_names, presenter.dictionary_names)
		self.assertEqual(presenter.dictionary_names, ["alpha", "default"])

	def test_dictionary_path_uses_dictionary_directory(self):
		presenter = self.make_presenter()

		self.assertEqual(presenter.dictionary_path("alpha"), self.dictionary_dir / "alpha.csv")
		self.set_active_name.assert_not_called()


if __name__ == "__main__":
	unittest.main()
EOF
```

- [ ] **Step 2: Run them and see them fail.**

```bash
$PY -m unittest tests.test_dictionary_presenter -v
```

Expected:

```
ERROR: test_dictionary_presenter (unittest.loader._FailedTest.test_dictionary_presenter)
ImportError: Failed to import test module: test_dictionary_presenter
ImportError: cannot import name 'presenter' from 'dictionaries' (/workspace/DotExpress/client/dictionaries/__init__.py)
Ran 1 test
FAILED (errors=1)
```

- [ ] **Step 3: Add the module.**

```bash
cat > $REPO/client/dictionaries/presenter.py <<'EOF'
"""Dictionary-management workflow without wx.

``DictionaryManagementPresenter`` owns the list of dictionary names and the
add, delete, rename, import and export flows. It talks to the user only through
a ``DictionaryManagementView`` (implemented by ``dialog.DictionaryManagementDialog``)
and builds every user-facing string with ``_`` at call time.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Protocol

from dictionaries.manager import (
	dictionary_path_for_name,
	ensure_default_dictionary,
	list_dictionary_names,
)
from translation.dictionary_state import resolve_management_selection


class DictionaryManagementView(Protocol):
	def prompt_dictionary_name(self, title: str, initial_name: str) -> str | None: ...

	def show_info(self, message: str) -> None: ...

	def show_error(self, message: str) -> None: ...

	def confirm(self, message: str, caption: str) -> bool: ...

	def choose_import_path(self, title: str) -> Path | None: ...

	def choose_export_path(self, title: str, default_file: str) -> Path | None: ...


class DictionaryManagementActions(Protocol):
	@property
	def dictionary_names(self) -> list[str]: ...

	def dictionary_path(self, name: str) -> Path: ...

	def add(self, view: DictionaryManagementView) -> str | None: ...

	def delete(self, view: DictionaryManagementView, name: str) -> str | None: ...

	def rename(self, view: DictionaryManagementView, name: str) -> str | None: ...

	def import_from_file(self, view: DictionaryManagementView) -> str | None: ...

	def export_to_file(self, view: DictionaryManagementView, name: str) -> None: ...


class DictionaryManagementPresenter:
	"""Satisfies ``DictionaryManagementActions``; the only owner of the dictionary name list."""

	def __init__(
		self,
		dictionary_dir: Path,
		*,
		get_active_name: Callable[[], str],
		set_active_name: Callable[[str], None],
	) -> None:
		self._dictionary_dir = Path(dictionary_dir)
		self._get_active_name = get_active_name
		self._set_active_name = set_active_name
		self._dictionary_names: list[str] = []

	@property
	def dictionary_dir(self) -> Path:
		return self._dictionary_dir

	@property
	def dictionary_names(self) -> list[str]:
		return list(self._dictionary_names)

	def refresh(self, preferred_name: str | None = None) -> str:
		ensure_default_dictionary(self._dictionary_dir)
		self._dictionary_names = list_dictionary_names(self._dictionary_dir)
		return resolve_management_selection(self._dictionary_names, preferred_name)

	def dictionary_path(self, name: str) -> Path:
		return dictionary_path_for_name(name, self._dictionary_dir)
EOF
```

- [ ] **Step 4: Run the tests.**

```bash
$PY -m unittest tests.test_dictionary_presenter -v
```

Expected: `Ran 9 tests`, `OK`.

- [ ] **Step 5: Suite check.**

```bash
$T/tools/check_suite.sh 491 9
```

- [ ] **Step 6: Commit.**

```bash
git -C $REPO add client/dictionaries/presenter.py client/tests/test_dictionary_presenter.py
git -C $REPO commit -F - <<'MSG'
feat: add dictionary management presenter skeleton

Add the wx-free presenter module with its view and actions protocols,
the single dictionary name list and refresh. Not used by the app yet.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
MSG
```

---

### Task 2: Add flow

**Files:**
- Modify: `client/tests/test_dictionary_presenter.py` (new class `PresenterAddTest`, 6 tests)
- Modify: `client/dictionaries/presenter.py` (`add`, the shared name-loop helper `_prompt_name_until_success`, `_selection_after_add`)

Flow (spec "Add"): name loop with title `_("Add Dictionary")` and initial `""`; `create_dictionary` on submit; `FileExistsError` shows `_('Dictionary "{name}" already exists.')` with the stripped name and prompts again with the typed name; `ValueError` shows `str(exc)` as info and returns `None`; other `OSError` propagates; success refreshes once with the active name and returns `plan_dictionary_state_after_add(...).management_selected_name`; the active name never changes. The helper is the only place that builds the `prompt_name` and `on_duplicate` lambdas (rename and import reuse it).

- [ ] **Step 1: Write the failing tests.** Recorded sequences: success `[("prompt", _("Add Dictionary"), "")]`; duplicate `[prompt "", ("error", <exists "alpha">), ("prompt", _("Add Dictionary"), " alpha")]` (typed `" alpha"`, message uses `"alpha"`); reserved name `[prompt "", ("info", "Name 'Default' is reserved.")]` (untranslated English, as today).

```bash
git -C $REPO apply <<'PATCH'
diff --git a/client/tests/test_dictionary_presenter.py b/client/tests/test_dictionary_presenter.py
index 58e0c88..8bb5385 100644
--- a/client/tests/test_dictionary_presenter.py
+++ b/client/tests/test_dictionary_presenter.py
@@ -159,5 +159,83 @@ class PresenterRefreshTest(PresenterTestCase):
 		self.set_active_name.assert_not_called()
 
 
+class PresenterAddTest(PresenterTestCase):
+	def test_add_creates_dictionary_and_selects_it(self):
+		presenter = self.make_presenter()
+		view = FakeView(names=["alpha"])
+
+		result = presenter.add(view)
+
+		self.assertEqual(result, "alpha")
+		self.assertEqual(view.calls, [("prompt", _("Add Dictionary"), "")])
+		self.assertEqual(self.files(), ["alpha", "default"])
+		self.assertEqual((self.dictionary_dir / "alpha.csv").read_text(encoding="utf-8").splitlines(), ["text,braille,type"])
+		self.assertEqual(presenter.dictionary_names, ["alpha", "default"])
+		self.set_active_name.assert_not_called()
+
+	def test_add_cancel_creates_nothing(self):
+		presenter = self.make_presenter()
+		view = FakeView(names=[None])
+
+		result = presenter.add(view)
+
+		self.assertIsNone(result)
+		self.assertEqual(view.calls, [("prompt", _("Add Dictionary"), "")])
+		self.assertEqual(self.files(), ["default"])
+		self.assertEqual(presenter.dictionary_names, ["default"])
+
+	def test_add_duplicate_shows_error_and_prompts_again_with_typed_name(self):
+		presenter = self.make_presenter("alpha")
+		view = FakeView(names=[" alpha", "beta"])
+
+		result = presenter.add(view)
+
+		self.assertEqual(result, "beta")
+		self.assertEqual(
+			view.calls,
+			[
+				("prompt", _("Add Dictionary"), ""),
+				("error", _('Dictionary "{name}" already exists.').format(name="alpha")),
+				("prompt", _("Add Dictionary"), " alpha"),
+			],
+		)
+		self.assertEqual(self.files(), ["alpha", "beta", "default"])
+		self.assertEqual(presenter.dictionary_names, ["alpha", "beta", "default"])
+
+	def test_add_invalid_name_shows_untranslated_info(self):
+		presenter = self.make_presenter()
+		view = FakeView(names=["Default"])
+
+		result = presenter.add(view)
+
+		self.assertIsNone(result)
+		self.assertEqual(
+			view.calls,
+			[("prompt", _("Add Dictionary"), ""), ("info", "Name 'Default' is reserved.")],
+		)
+		self.assertEqual(self.files(), ["default"])
+
+	def test_add_does_not_catch_os_error(self):
+		presenter = self.make_presenter()
+		view = FakeView(names=["alpha"])
+
+		with patch.object(presenter_module, "create_dictionary", side_effect=PermissionError("denied")):
+			with self.assertRaises(PermissionError):
+				presenter.add(view)
+
+		self.assertEqual(view.calls, [("prompt", _("Add Dictionary"), "")])
+		self.assertEqual(presenter.dictionary_names, ["default"])
+
+	def test_add_never_changes_active_dictionary(self):
+		presenter = self.make_presenter(active="missing")
+		view = FakeView(names=["alpha"])
+
+		result = presenter.add(view)
+
+		self.assertEqual(result, "alpha")
+		self.assertEqual(self.active, ["missing"])
+		self.set_active_name.assert_not_called()
+
+
 if __name__ == "__main__":
 	unittest.main()
PATCH
```

- [ ] **Step 2: Run them and see them fail.**

```bash
$PY -m unittest tests.test_dictionary_presenter -v
```

Expected:

```
ERROR: test_add_cancel_creates_nothing (tests.test_dictionary_presenter.PresenterAddTest.test_add_cancel_creates_nothing)
AttributeError: 'DictionaryManagementPresenter' object has no attribute 'add'
ERROR: test_add_creates_dictionary_and_selects_it (tests.test_dictionary_presenter.PresenterAddTest.test_add_creates_dictionary_and_selects_it)
AttributeError: 'DictionaryManagementPresenter' object has no attribute 'add'
ERROR: test_add_does_not_catch_os_error (tests.test_dictionary_presenter.PresenterAddTest.test_add_does_not_catch_os_error)
AttributeError: <module 'dictionaries.presenter' from '/workspace/DotExpress/client/dictionaries/presenter.py'> does not have the attribute 'create_dictionary'
ERROR: test_add_duplicate_shows_error_and_prompts_again_with_typed_name (tests.test_dictionary_presenter.PresenterAddTest.test_add_duplicate_shows_error_and_prompts_again_with_typed_name)
AttributeError: 'DictionaryManagementPresenter' object has no attribute 'add'
ERROR: test_add_invalid_name_shows_untranslated_info (tests.test_dictionary_presenter.PresenterAddTest.test_add_invalid_name_shows_untranslated_info)
AttributeError: 'DictionaryManagementPresenter' object has no attribute 'add'
ERROR: test_add_never_changes_active_dictionary (tests.test_dictionary_presenter.PresenterAddTest.test_add_never_changes_active_dictionary)
AttributeError: 'DictionaryManagementPresenter' object has no attribute 'add'
Ran 15 tests
FAILED (errors=6)
```

- [ ] **Step 3: Implement the flow.**

```bash
git -C $REPO apply <<'PATCH'
diff --git a/client/dictionaries/presenter.py b/client/dictionaries/presenter.py
index ff82873..f5197aa 100644
--- a/client/dictionaries/presenter.py
+++ b/client/dictionaries/presenter.py
@@ -13,11 +13,17 @@ from pathlib import Path
 from typing import Protocol
 
 from dictionaries.manager import (
+	create_dictionary,
 	dictionary_path_for_name,
 	ensure_default_dictionary,
 	list_dictionary_names,
 )
-from translation.dictionary_state import resolve_management_selection
+from dictionaries.name_prompt import prompt_dictionary_name_until_success
+from i18n import _
+from translation.dictionary_state import (
+	plan_dictionary_state_after_add,
+	resolve_management_selection,
+)
 
 
 class DictionaryManagementView(Protocol):
@@ -81,3 +87,40 @@ class DictionaryManagementPresenter:
 
 	def dictionary_path(self, name: str) -> Path:
 		return dictionary_path_for_name(name, self._dictionary_dir)
+
+	def add(self, view: DictionaryManagementView) -> str | None:
+		try:
+			path = self._prompt_name_until_success(
+				view,
+				_("Add Dictionary"),
+				"",
+				lambda dictionary_name: create_dictionary(self._dictionary_dir, dictionary_name),
+			)
+		except ValueError as exc:
+			view.show_info(str(exc))
+			return None
+		if path is None:
+			return None
+		return self._selection_after_add(path.stem)
+
+	def _prompt_name_until_success(
+		self,
+		view: DictionaryManagementView,
+		title: str,
+		initial_name: str,
+		submit: Callable[[str], Path],
+	) -> Path | None:
+		return prompt_dictionary_name_until_success(
+			initial_name,
+			prompt_name=lambda current_name: view.prompt_dictionary_name(title, current_name),
+			on_submit=submit,
+			on_duplicate=lambda dictionary_name: view.show_error(
+				_('Dictionary "{name}" already exists.').format(name=dictionary_name.strip())
+			),
+		)
+
+	def _selection_after_add(self, added_name: str) -> str:
+		active_name = self._get_active_name()
+		self.refresh(active_name)
+		update = plan_dictionary_state_after_add(active_name, self._dictionary_names, added_name)
+		return update.management_selected_name
PATCH
```

- [ ] **Step 4: Run the tests.**

```bash
$PY -m unittest tests.test_dictionary_presenter -v
```

Expected: `Ran 15 tests`, `OK`.

- [ ] **Step 5: Suite check.**

```bash
$T/tools/check_suite.sh 497 15
```

- [ ] **Step 6: Commit.**

```bash
git -C $REPO add client/dictionaries/presenter.py client/tests/test_dictionary_presenter.py
git -C $REPO commit -F - <<'MSG'
feat: add dictionary presenter add flow

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
MSG
```

---

### Task 3: Delete flow

**Files:**
- Modify: `client/tests/test_dictionary_presenter.py` (new class `PresenterDeleteTest`, 6 tests)
- Modify: `client/dictionaries/presenter.py` (`delete`)

Flow (spec "Delete"): `default` (any case) shows `_("The default dictionary cannot be deleted.")` as info, no confirm; confirm with `_('Do you want to delete dictionary "{name}"?')` and caption `_("Confirm Delete Dictionary")`, anything but Yes returns `None`; capture the presenter's list and the active name; `delete_dictionary`; `OSError` shows `_("Failed to delete dictionary: {error}")` and returns `None` with list and active name untouched; `ValueError` propagates; success refreshes once with the deleted name, plans with the captured list, calls `set_active_name(planned)` only when it differs, and returns the planned management selection.

- [ ] **Step 1: Write the failing tests.** Recorded sequences: `default` `[("info", <cannot delete>)]`; every other path starts with `("confirm", _('Do you want to delete dictionary "{name}"?').format(name=...), _("Confirm Delete Dictionary"))`; `OSError` adds `("error", _("Failed to delete dictionary: {error}").format(error="denied"))`. Deleting the active `beta` from `[alpha, beta, default]` activates `alpha` (one `set_active_name("alpha")`) and selects `default`; deleting the inactive `alpha` selects `default` and never calls `set_active_name`.

```bash
git -C $REPO apply <<'PATCH'
diff --git a/client/tests/test_dictionary_presenter.py b/client/tests/test_dictionary_presenter.py
index 8bb5385..ba68c18 100644
--- a/client/tests/test_dictionary_presenter.py
+++ b/client/tests/test_dictionary_presenter.py
@@ -237,5 +237,90 @@ class PresenterAddTest(PresenterTestCase):
 		self.set_active_name.assert_not_called()
 
 
+class PresenterDeleteTest(PresenterTestCase):
+	def confirm_call(self, name):
+		return (
+			"confirm",
+			_('Do you want to delete dictionary "{name}"?').format(name=name),
+			_("Confirm Delete Dictionary"),
+		)
+
+	def test_delete_default_shows_info_without_confirmation(self):
+		presenter = self.make_presenter("alpha")
+		view = FakeView()
+
+		result = presenter.delete(view, "default")
+
+		self.assertIsNone(result)
+		self.assertEqual(view.calls, [("info", _("The default dictionary cannot be deleted."))])
+		self.assertEqual(self.files(), ["alpha", "default"])
+
+	def test_delete_declined_keeps_file(self):
+		presenter = self.make_presenter("alpha")
+		view = FakeView(confirm=False)
+
+		result = presenter.delete(view, "alpha")
+
+		self.assertIsNone(result)
+		self.assertEqual(view.calls, [self.confirm_call("alpha")])
+		self.assertEqual(self.files(), ["alpha", "default"])
+		self.assertEqual(presenter.dictionary_names, ["alpha", "default"])
+
+	def test_delete_inactive_dictionary_keeps_active_name(self):
+		presenter = self.make_presenter("alpha", "beta", active="beta")
+		view = FakeView()
+
+		result = presenter.delete(view, "alpha")
+
+		self.assertEqual(result, "default")
+		self.assertEqual(view.calls, [self.confirm_call("alpha")])
+		self.assertEqual(self.files(), ["beta", "default"])
+		self.assertEqual(presenter.dictionary_names, ["beta", "default"])
+		self.assertEqual(self.active, ["beta"])
+		self.set_active_name.assert_not_called()
+
+	def test_delete_active_dictionary_activates_planned_fallback(self):
+		presenter = self.make_presenter("alpha", "beta", active="beta")
+		view = FakeView()
+
+		result = presenter.delete(view, "beta")
+
+		self.assertEqual(result, "default")
+		self.assertEqual(view.calls, [self.confirm_call("beta")])
+		self.assertEqual(self.files(), ["alpha", "default"])
+		self.set_active_name.assert_called_once_with("alpha")
+		self.assertEqual(self.active, ["alpha"])
+
+	def test_delete_os_error_shows_error_and_changes_nothing(self):
+		presenter = self.make_presenter("alpha", active="alpha")
+		view = FakeView()
+
+		with patch.object(presenter_module, "delete_dictionary", side_effect=PermissionError("denied")):
+			result = presenter.delete(view, "alpha")
+
+		self.assertIsNone(result)
+		self.assertEqual(
+			view.calls,
+			[
+				self.confirm_call("alpha"),
+				("error", _("Failed to delete dictionary: {error}").format(error="denied")),
+			],
+		)
+		self.assertEqual(self.files(), ["alpha", "default"])
+		self.assertEqual(presenter.dictionary_names, ["alpha", "default"])
+		self.set_active_name.assert_not_called()
+
+	def test_delete_does_not_catch_value_error_for_padded_default_name(self):
+		presenter = self.make_presenter(" default")
+		view = FakeView()
+
+		with self.assertRaises(ValueError):
+			presenter.delete(view, " default")
+
+		self.assertEqual(view.calls, [self.confirm_call(" default")])
+		self.assertEqual(self.files(), [" default", "default"])
+		self.set_active_name.assert_not_called()
+
+
 if __name__ == "__main__":
 	unittest.main()
PATCH
```

- [ ] **Step 2: Run them and see them fail.**

```bash
$PY -m unittest tests.test_dictionary_presenter -v
```

Expected:

```
ERROR: test_delete_active_dictionary_activates_planned_fallback (tests.test_dictionary_presenter.PresenterDeleteTest.test_delete_active_dictionary_activates_planned_fallback)
AttributeError: 'DictionaryManagementPresenter' object has no attribute 'delete'
ERROR: test_delete_declined_keeps_file (tests.test_dictionary_presenter.PresenterDeleteTest.test_delete_declined_keeps_file)
AttributeError: 'DictionaryManagementPresenter' object has no attribute 'delete'
ERROR: test_delete_default_shows_info_without_confirmation (tests.test_dictionary_presenter.PresenterDeleteTest.test_delete_default_shows_info_without_confirmation)
AttributeError: 'DictionaryManagementPresenter' object has no attribute 'delete'
ERROR: test_delete_does_not_catch_value_error_for_padded_default_name (tests.test_dictionary_presenter.PresenterDeleteTest.test_delete_does_not_catch_value_error_for_padded_default_name)
AttributeError: 'DictionaryManagementPresenter' object has no attribute 'delete'
ERROR: test_delete_inactive_dictionary_keeps_active_name (tests.test_dictionary_presenter.PresenterDeleteTest.test_delete_inactive_dictionary_keeps_active_name)
AttributeError: 'DictionaryManagementPresenter' object has no attribute 'delete'
ERROR: test_delete_os_error_shows_error_and_changes_nothing (tests.test_dictionary_presenter.PresenterDeleteTest.test_delete_os_error_shows_error_and_changes_nothing)
AttributeError: <module 'dictionaries.presenter' from '/workspace/DotExpress/client/dictionaries/presenter.py'> does not have the attribute 'delete_dictionary'
Ran 21 tests
FAILED (errors=6)
```

- [ ] **Step 3: Implement the flow.**

```bash
git -C $REPO apply <<'PATCH'
diff --git a/client/dictionaries/presenter.py b/client/dictionaries/presenter.py
index f5197aa..f6cdee7 100644
--- a/client/dictionaries/presenter.py
+++ b/client/dictionaries/presenter.py
@@ -12,8 +12,10 @@ from collections.abc import Callable
 from pathlib import Path
 from typing import Protocol
 
+from dictionaries.actions import is_default_dictionary
 from dictionaries.manager import (
 	create_dictionary,
+	delete_dictionary,
 	dictionary_path_for_name,
 	ensure_default_dictionary,
 	list_dictionary_names,
@@ -22,6 +24,7 @@ from dictionaries.name_prompt import prompt_dictionary_name_until_success
 from i18n import _
 from translation.dictionary_state import (
 	plan_dictionary_state_after_add,
+	plan_dictionary_state_after_delete,
 	resolve_management_selection,
 )
 
@@ -103,6 +106,29 @@ class DictionaryManagementPresenter:
 			return None
 		return self._selection_after_add(path.stem)
 
+	def delete(self, view: DictionaryManagementView, name: str) -> str | None:
+		if is_default_dictionary(name):
+			view.show_info(_("The default dictionary cannot be deleted."))
+			return None
+		if not view.confirm(
+			_('Do you want to delete dictionary "{name}"?').format(name=name),
+			_("Confirm Delete Dictionary"),
+		):
+			return None
+
+		previous_names = list(self._dictionary_names)
+		active_name = self._get_active_name()
+		try:
+			delete_dictionary(self._dictionary_dir, name)
+		except OSError as exc:
+			view.show_error(_("Failed to delete dictionary: {error}").format(error=exc))
+			return None
+		self.refresh(name)
+		update = plan_dictionary_state_after_delete(active_name, name, previous_names)
+		if update.active_selected_name != active_name:
+			self._set_active_name(update.active_selected_name)
+		return update.management_selected_name
+
 	def _prompt_name_until_success(
 		self,
 		view: DictionaryManagementView,
PATCH
```

- [ ] **Step 4: Run the tests.**

```bash
$PY -m unittest tests.test_dictionary_presenter -v
```

Expected: `Ran 21 tests`, `OK`.

- [ ] **Step 5: Suite check.**

```bash
$T/tools/check_suite.sh 503 21
```

- [ ] **Step 6: Commit.**

```bash
git -C $REPO add client/dictionaries/presenter.py client/tests/test_dictionary_presenter.py
git -C $REPO commit -F - <<'MSG'
feat: add dictionary presenter delete flow

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
MSG
```

---

### Task 4: Rename flow

**Files:**
- Modify: `client/tests/test_dictionary_presenter.py` (new class `PresenterRenameTest`, 9 tests)
- Modify: `client/dictionaries/presenter.py` (`rename`)

Flow (spec "Rename"): `default` returns `None` with no view call; name loop with title `_("Rename Dictionary")` and the selected name as initial value, submit `rename_dictionary_after_name_prompt`; `ValueError` shows `str(exc)` as info; `OSError` shows `_("Failed to save dictionary: {error}")`; cancel returns `None`; success reads the active name, refreshes once with `path.stem`, plans with `plan_dictionary_state_after_rename`, calls `set_active_name` only when the plan differs, and returns the planned selection.

- [ ] **Step 1: Write the failing tests.** Recorded sequences: `default` `[]`; duplicate `[("prompt", _("Rename Dictionary"), "alpha"), ("error", <exists "beta">), ("prompt", _("Rename Dictionary"), "beta")]`; invalid name `[prompt "alpha", ("info", "Name contains invalid characters.")]`; `OSError` `[prompt "alpha", ("error", _("Failed to save dictionary: {error}").format(error="denied"))]`. Renaming the active `alpha` to `gamma` calls `set_active_name("gamma")` once; the same name returns `alpha` with no file change and no `set_active_name`.

```bash
git -C $REPO apply <<'PATCH'
diff --git a/client/tests/test_dictionary_presenter.py b/client/tests/test_dictionary_presenter.py
index ba68c18..f40d9c2 100644
--- a/client/tests/test_dictionary_presenter.py
+++ b/client/tests/test_dictionary_presenter.py
@@ -322,5 +322,121 @@ class PresenterDeleteTest(PresenterTestCase):
 		self.set_active_name.assert_not_called()
 
 
+class PresenterRenameTest(PresenterTestCase):
+	def prompt_call(self, initial_name):
+		return ("prompt", _("Rename Dictionary"), initial_name)
+
+	def test_rename_default_does_nothing(self):
+		presenter = self.make_presenter()
+		view = FakeView()
+
+		result = presenter.rename(view, "default")
+
+		self.assertIsNone(result)
+		self.assertEqual(view.calls, [])
+		self.assertEqual(self.files(), ["default"])
+
+	def test_rename_cancel_keeps_file(self):
+		presenter = self.make_presenter("alpha")
+		view = FakeView(names=[None])
+
+		result = presenter.rename(view, "alpha")
+
+		self.assertIsNone(result)
+		self.assertEqual(view.calls, [self.prompt_call("alpha")])
+		self.assertEqual(self.files(), ["alpha", "default"])
+
+	def test_rename_inactive_dictionary_keeps_active_name(self):
+		presenter = self.make_presenter("alpha")
+		view = FakeView(names=["gamma"])
+
+		result = presenter.rename(view, "alpha")
+
+		self.assertEqual(result, "gamma")
+		self.assertEqual(view.calls, [self.prompt_call("alpha")])
+		self.assertEqual(self.files(), ["default", "gamma"])
+		self.assertEqual(presenter.dictionary_names, ["default", "gamma"])
+		self.set_active_name.assert_not_called()
+
+	def test_rename_active_dictionary_activates_new_name(self):
+		presenter = self.make_presenter("alpha", active="alpha")
+		view = FakeView(names=["gamma"])
+
+		result = presenter.rename(view, "alpha")
+
+		self.assertEqual(result, "gamma")
+		self.assertEqual(self.files(), ["default", "gamma"])
+		self.set_active_name.assert_called_once_with("gamma")
+		self.assertEqual(self.active, ["gamma"])
+
+	def test_rename_to_same_name_changes_nothing(self):
+		presenter = self.make_presenter("alpha", active="alpha")
+		view = FakeView(names=["alpha"])
+
+		result = presenter.rename(view, "alpha")
+
+		self.assertEqual(result, "alpha")
+		self.assertEqual(view.calls, [self.prompt_call("alpha")])
+		self.assertEqual(self.files(), ["alpha", "default"])
+		self.set_active_name.assert_not_called()
+
+	def test_rename_case_only_change_renames_file(self):
+		presenter = self.make_presenter("alpha")
+		if (self.dictionary_dir / "ALPHA.csv").exists():
+			self.skipTest("case-insensitive file system: a case-only rename is reported as a duplicate")
+		view = FakeView(names=["Alpha"])
+
+		result = presenter.rename(view, "alpha")
+
+		self.assertEqual(result, "Alpha")
+		self.assertEqual(view.calls, [self.prompt_call("alpha")])
+		self.assertEqual(self.files(), ["Alpha", "default"])
+
+	def test_rename_duplicate_shows_error_and_prompts_again_with_typed_name(self):
+		presenter = self.make_presenter("alpha", "beta")
+		view = FakeView(names=["beta", "gamma"])
+
+		result = presenter.rename(view, "alpha")
+
+		self.assertEqual(result, "gamma")
+		self.assertEqual(
+			view.calls,
+			[
+				self.prompt_call("alpha"),
+				("error", _('Dictionary "{name}" already exists.').format(name="beta")),
+				self.prompt_call("beta"),
+			],
+		)
+		self.assertEqual(self.files(), ["beta", "default", "gamma"])
+
+	def test_rename_invalid_name_shows_untranslated_info(self):
+		presenter = self.make_presenter("alpha")
+		view = FakeView(names=["bad|name"])
+
+		result = presenter.rename(view, "alpha")
+
+		self.assertIsNone(result)
+		self.assertEqual(view.calls, [self.prompt_call("alpha"), ("info", "Name contains invalid characters.")])
+		self.assertEqual(self.files(), ["alpha", "default"])
+
+	def test_rename_os_error_shows_save_error(self):
+		presenter = self.make_presenter("alpha", active="alpha")
+		view = FakeView(names=["gamma"])
+
+		with patch.object(presenter_module, "rename_dictionary_after_name_prompt", side_effect=PermissionError("denied")):
+			result = presenter.rename(view, "alpha")
+
+		self.assertIsNone(result)
+		self.assertEqual(
+			view.calls,
+			[
+				self.prompt_call("alpha"),
+				("error", _("Failed to save dictionary: {error}").format(error="denied")),
+			],
+		)
+		self.assertEqual(self.files(), ["alpha", "default"])
+		self.set_active_name.assert_not_called()
+
+
 if __name__ == "__main__":
 	unittest.main()
PATCH
```

- [ ] **Step 2: Run them and see them fail.**

```bash
$PY -m unittest tests.test_dictionary_presenter -v
```

Expected:

```
ERROR: test_rename_active_dictionary_activates_new_name (tests.test_dictionary_presenter.PresenterRenameTest.test_rename_active_dictionary_activates_new_name)
AttributeError: 'DictionaryManagementPresenter' object has no attribute 'rename'
ERROR: test_rename_cancel_keeps_file (tests.test_dictionary_presenter.PresenterRenameTest.test_rename_cancel_keeps_file)
AttributeError: 'DictionaryManagementPresenter' object has no attribute 'rename'
ERROR: test_rename_case_only_change_renames_file (tests.test_dictionary_presenter.PresenterRenameTest.test_rename_case_only_change_renames_file)
AttributeError: 'DictionaryManagementPresenter' object has no attribute 'rename'
ERROR: test_rename_default_does_nothing (tests.test_dictionary_presenter.PresenterRenameTest.test_rename_default_does_nothing)
AttributeError: 'DictionaryManagementPresenter' object has no attribute 'rename'
ERROR: test_rename_duplicate_shows_error_and_prompts_again_with_typed_name (tests.test_dictionary_presenter.PresenterRenameTest.test_rename_duplicate_shows_error_and_prompts_again_with_typed_name)
AttributeError: 'DictionaryManagementPresenter' object has no attribute 'rename'
ERROR: test_rename_inactive_dictionary_keeps_active_name (tests.test_dictionary_presenter.PresenterRenameTest.test_rename_inactive_dictionary_keeps_active_name)
AttributeError: 'DictionaryManagementPresenter' object has no attribute 'rename'
ERROR: test_rename_invalid_name_shows_untranslated_info (tests.test_dictionary_presenter.PresenterRenameTest.test_rename_invalid_name_shows_untranslated_info)
AttributeError: 'DictionaryManagementPresenter' object has no attribute 'rename'
ERROR: test_rename_os_error_shows_save_error (tests.test_dictionary_presenter.PresenterRenameTest.test_rename_os_error_shows_save_error)
AttributeError: <module 'dictionaries.presenter' from '/workspace/DotExpress/client/dictionaries/presenter.py'> does not have the attribute 'rename_dictionary_after_name_prompt'
ERROR: test_rename_to_same_name_changes_nothing (tests.test_dictionary_presenter.PresenterRenameTest.test_rename_to_same_name_changes_nothing)
AttributeError: 'DictionaryManagementPresenter' object has no attribute 'rename'
Ran 30 tests
FAILED (errors=9)
```

- [ ] **Step 3: Implement the flow.**

```bash
git -C $REPO apply <<'PATCH'
diff --git a/client/dictionaries/presenter.py b/client/dictionaries/presenter.py
index f6cdee7..c13c458 100644
--- a/client/dictionaries/presenter.py
+++ b/client/dictionaries/presenter.py
@@ -20,11 +20,12 @@ from dictionaries.manager import (
 	ensure_default_dictionary,
 	list_dictionary_names,
 )
-from dictionaries.name_prompt import prompt_dictionary_name_until_success
+from dictionaries.name_prompt import prompt_dictionary_name_until_success, rename_dictionary_after_name_prompt
 from i18n import _
 from translation.dictionary_state import (
 	plan_dictionary_state_after_add,
 	plan_dictionary_state_after_delete,
+	plan_dictionary_state_after_rename,
 	resolve_management_selection,
 )
 
@@ -129,6 +130,36 @@ class DictionaryManagementPresenter:
 			self._set_active_name(update.active_selected_name)
 		return update.management_selected_name
 
+	def rename(self, view: DictionaryManagementView, name: str) -> str | None:
+		if is_default_dictionary(name):
+			return None
+		try:
+			path = self._prompt_name_until_success(
+				view,
+				_("Rename Dictionary"),
+				name,
+				lambda dictionary_name: rename_dictionary_after_name_prompt(
+					self._dictionary_dir,
+					name,
+					dictionary_name,
+				),
+			)
+		except ValueError as exc:
+			view.show_info(str(exc))
+			return None
+		except OSError as exc:
+			view.show_error(_("Failed to save dictionary: {error}").format(error=exc))
+			return None
+		if path is None:
+			return None
+
+		active_name = self._get_active_name()
+		self.refresh(path.stem)
+		update = plan_dictionary_state_after_rename(active_name, name, path.stem, self._dictionary_names)
+		if update.active_selected_name != active_name:
+			self._set_active_name(update.active_selected_name)
+		return update.management_selected_name
+
 	def _prompt_name_until_success(
 		self,
 		view: DictionaryManagementView,
PATCH
```

- [ ] **Step 4: Run the tests.**

```bash
$PY -m unittest tests.test_dictionary_presenter -v
```

Expected: `Ran 30 tests`, `OK` (on a case-insensitive file system: `OK (skipped=1)`, see correction 3).

- [ ] **Step 5: Suite check.**

```bash
$T/tools/check_suite.sh 512 30
```

- [ ] **Step 6: Commit.**

```bash
git -C $REPO add client/dictionaries/presenter.py client/tests/test_dictionary_presenter.py
git -C $REPO commit -F - <<'MSG'
feat: add dictionary presenter rename flow

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
MSG
```

---

### Task 5: Import flow

**Files:**
- Modify: `client/tests/test_dictionary_presenter.py` (new class `PresenterImportTest`, 8 tests)
- Modify: `client/dictionaries/presenter.py` (`import_from_file`)

Flow (spec "Import"): `choose_import_path(_("Import Dictionary"))`, `None` returns `None` without a prompt; name loop with title `_("Add Dictionary")` (sic) and the source stem as initial value, submit `import_dictionary` (its duplicate check runs before CSV validation); every `ValueError` shows `_("Imported file must contain text, braille, and type headers.")` as an error; `OSError` shows `_("Failed to import dictionary: {error}")`; cancel returns `None`; success is the add success path (never changes the active name).

- [ ] **Step 1: Write the failing tests.** Recorded sequences start with `("choose_import", _("Import Dictionary"))`, then `("prompt", _("Add Dictionary"), <source stem>)`. A duplicate name with a header-less source prompts again (`[choose, prompt "alpha", ("error", <exists "alpha">), prompt "alpha"]`), proving the duplicate check comes first. Headers missing and an invalid name both end with `("error", _("Imported file must contain text, braille, and type headers."))`. A vanished source ends with `("error", _("Failed to import dictionary: {error}").format(error=<the FileNotFoundError>))`.

```bash
git -C $REPO apply <<'PATCH'
diff --git a/client/tests/test_dictionary_presenter.py b/client/tests/test_dictionary_presenter.py
index f40d9c2..dcda126 100644
--- a/client/tests/test_dictionary_presenter.py
+++ b/client/tests/test_dictionary_presenter.py
@@ -438,5 +438,144 @@ class PresenterRenameTest(PresenterTestCase):
 		self.set_active_name.assert_not_called()
 
 
+class PresenterImportTest(PresenterTestCase):
+	HEADER_ERROR = "Imported file must contain text, braille, and type headers."
+
+	def write_source(self, name, content=HEADER + "Alpha,\u2801,General\n"):
+		source_dir = self.root / "source"
+		source_dir.mkdir(exist_ok=True)
+		path = source_dir / f"{name}.csv"
+		path.write_text(content, encoding="utf-8")
+		return path
+
+	def choose_call(self):
+		return ("choose_import", _("Import Dictionary"))
+
+	def prompt_call(self, initial_name):
+		return ("prompt", _("Add Dictionary"), initial_name)
+
+	def test_import_cancelled_file_dialog_does_not_prompt(self):
+		presenter = self.make_presenter()
+		view = FakeView(import_path=None)
+
+		result = presenter.import_from_file(view)
+
+		self.assertIsNone(result)
+		self.assertEqual(view.calls, [self.choose_call()])
+		self.assertEqual(self.files(), ["default"])
+
+	def test_import_copies_source_under_prompted_name(self):
+		source = self.write_source("words")
+		presenter = self.make_presenter(active="missing")
+		view = FakeView(names=["words"], import_path=source)
+
+		result = presenter.import_from_file(view)
+
+		self.assertEqual(result, "words")
+		self.assertEqual(view.calls, [self.choose_call(), self.prompt_call("words")])
+		self.assertEqual(self.files(), ["default", "words"])
+		self.assertEqual((self.dictionary_dir / "words.csv").read_bytes(), source.read_bytes())
+		self.assertEqual(presenter.dictionary_names, ["default", "words"])
+		self.assertEqual(self.active, ["missing"])
+		self.set_active_name.assert_not_called()
+
+	def test_import_duplicate_shows_error_and_prompts_again_with_typed_name(self):
+		source = self.write_source("alpha")
+		presenter = self.make_presenter("alpha")
+		view = FakeView(names=["alpha", "beta"], import_path=source)
+
+		result = presenter.import_from_file(view)
+
+		self.assertEqual(result, "beta")
+		self.assertEqual(
+			view.calls,
+			[
+				self.choose_call(),
+				self.prompt_call("alpha"),
+				("error", _('Dictionary "{name}" already exists.').format(name="alpha")),
+				self.prompt_call("alpha"),
+			],
+		)
+		self.assertEqual(self.files(), ["alpha", "beta", "default"])
+
+	def test_import_reports_duplicate_name_before_checking_headers(self):
+		source = self.write_source("alpha", content="a,b\n")
+		presenter = self.make_presenter("alpha")
+		view = FakeView(names=["alpha", None], import_path=source)
+
+		result = presenter.import_from_file(view)
+
+		self.assertIsNone(result)
+		self.assertEqual(
+			view.calls,
+			[
+				self.choose_call(),
+				self.prompt_call("alpha"),
+				("error", _('Dictionary "{name}" already exists.').format(name="alpha")),
+				self.prompt_call("alpha"),
+			],
+		)
+		self.assertEqual(self.files(), ["alpha", "default"])
+
+	def test_import_without_headers_shows_header_error(self):
+		source = self.write_source("bad", content="a,b\n")
+		presenter = self.make_presenter()
+		view = FakeView(names=["bad"], import_path=source)
+
+		result = presenter.import_from_file(view)
+
+		self.assertIsNone(result)
+		self.assertEqual(
+			view.calls,
+			[self.choose_call(), self.prompt_call("bad"), ("error", _(self.HEADER_ERROR))],
+		)
+		self.assertEqual(self.files(), ["default"])
+
+	def test_import_invalid_name_shows_header_error(self):
+		source = self.write_source("words")
+		presenter = self.make_presenter()
+		view = FakeView(names=["bad|name"], import_path=source)
+
+		result = presenter.import_from_file(view)
+
+		self.assertIsNone(result)
+		self.assertEqual(
+			view.calls,
+			[self.choose_call(), self.prompt_call("words"), ("error", _(self.HEADER_ERROR))],
+		)
+		self.assertEqual(self.files(), ["default"])
+
+	def test_import_missing_source_shows_import_error(self):
+		source = self.root / "source" / "gone.csv"
+		with self.assertRaises(FileNotFoundError) as missing:
+			source.open("r", newline="", encoding="utf-8")
+		presenter = self.make_presenter()
+		view = FakeView(names=["gone"], import_path=source)
+
+		result = presenter.import_from_file(view)
+
+		self.assertIsNone(result)
+		self.assertEqual(
+			view.calls,
+			[
+				self.choose_call(),
+				self.prompt_call("gone"),
+				("error", _("Failed to import dictionary: {error}").format(error=missing.exception)),
+			],
+		)
+		self.assertEqual(self.files(), ["default"])
+
+	def test_import_cancelled_name_prompt_imports_nothing(self):
+		source = self.write_source("words")
+		presenter = self.make_presenter()
+		view = FakeView(names=[None], import_path=source)
+
+		result = presenter.import_from_file(view)
+
+		self.assertIsNone(result)
+		self.assertEqual(view.calls, [self.choose_call(), self.prompt_call("words")])
+		self.assertEqual(self.files(), ["default"])
+
+
 if __name__ == "__main__":
 	unittest.main()
PATCH
```

- [ ] **Step 2: Run them and see them fail.**

```bash
$PY -m unittest tests.test_dictionary_presenter -v
```

Expected:

```
ERROR: test_import_cancelled_file_dialog_does_not_prompt (tests.test_dictionary_presenter.PresenterImportTest.test_import_cancelled_file_dialog_does_not_prompt)
AttributeError: 'DictionaryManagementPresenter' object has no attribute 'import_from_file'
ERROR: test_import_cancelled_name_prompt_imports_nothing (tests.test_dictionary_presenter.PresenterImportTest.test_import_cancelled_name_prompt_imports_nothing)
AttributeError: 'DictionaryManagementPresenter' object has no attribute 'import_from_file'
ERROR: test_import_copies_source_under_prompted_name (tests.test_dictionary_presenter.PresenterImportTest.test_import_copies_source_under_prompted_name)
AttributeError: 'DictionaryManagementPresenter' object has no attribute 'import_from_file'
ERROR: test_import_duplicate_shows_error_and_prompts_again_with_typed_name (tests.test_dictionary_presenter.PresenterImportTest.test_import_duplicate_shows_error_and_prompts_again_with_typed_name)
AttributeError: 'DictionaryManagementPresenter' object has no attribute 'import_from_file'
ERROR: test_import_invalid_name_shows_header_error (tests.test_dictionary_presenter.PresenterImportTest.test_import_invalid_name_shows_header_error)
AttributeError: 'DictionaryManagementPresenter' object has no attribute 'import_from_file'
ERROR: test_import_missing_source_shows_import_error (tests.test_dictionary_presenter.PresenterImportTest.test_import_missing_source_shows_import_error)
AttributeError: 'DictionaryManagementPresenter' object has no attribute 'import_from_file'
ERROR: test_import_reports_duplicate_name_before_checking_headers (tests.test_dictionary_presenter.PresenterImportTest.test_import_reports_duplicate_name_before_checking_headers)
AttributeError: 'DictionaryManagementPresenter' object has no attribute 'import_from_file'
ERROR: test_import_without_headers_shows_header_error (tests.test_dictionary_presenter.PresenterImportTest.test_import_without_headers_shows_header_error)
AttributeError: 'DictionaryManagementPresenter' object has no attribute 'import_from_file'
Ran 38 tests
FAILED (errors=8)
```

- [ ] **Step 3: Implement the flow.**

```bash
git -C $REPO apply <<'PATCH'
diff --git a/client/dictionaries/presenter.py b/client/dictionaries/presenter.py
index c13c458..330ca1a 100644
--- a/client/dictionaries/presenter.py
+++ b/client/dictionaries/presenter.py
@@ -18,6 +18,7 @@ from dictionaries.manager import (
 	delete_dictionary,
 	dictionary_path_for_name,
 	ensure_default_dictionary,
+	import_dictionary,
 	list_dictionary_names,
 )
 from dictionaries.name_prompt import prompt_dictionary_name_until_success, rename_dictionary_after_name_prompt
@@ -160,6 +161,27 @@ class DictionaryManagementPresenter:
 			self._set_active_name(update.active_selected_name)
 		return update.management_selected_name
 
+	def import_from_file(self, view: DictionaryManagementView) -> str | None:
+		source_path = view.choose_import_path(_("Import Dictionary"))
+		if source_path is None:
+			return None
+		try:
+			path = self._prompt_name_until_success(
+				view,
+				_("Add Dictionary"),
+				source_path.stem,
+				lambda dictionary_name: import_dictionary(self._dictionary_dir, source_path, dictionary_name),
+			)
+		except ValueError:
+			view.show_error(_("Imported file must contain text, braille, and type headers."))
+			return None
+		except OSError as exc:
+			view.show_error(_("Failed to import dictionary: {error}").format(error=exc))
+			return None
+		if path is None:
+			return None
+		return self._selection_after_add(path.stem)
+
 	def _prompt_name_until_success(
 		self,
 		view: DictionaryManagementView,
PATCH
```

- [ ] **Step 4: Run the tests.**

```bash
$PY -m unittest tests.test_dictionary_presenter -v
```

Expected: `Ran 38 tests`, `OK`.

- [ ] **Step 5: Suite check.**

```bash
$T/tools/check_suite.sh 520 38
```

- [ ] **Step 6: Commit.**

```bash
git -C $REPO add client/dictionaries/presenter.py client/tests/test_dictionary_presenter.py
git -C $REPO commit -F - <<'MSG'
feat: add dictionary presenter import flow

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
MSG
```

---

### Task 6: Export flow and actions parity

**Files:**
- Modify: `client/tests/test_dictionary_presenter.py` (new class `PresenterExportTest`, 4 tests; `PresenterModuleTest.test_presenter_provides_every_action`)
- Modify: `client/dictionaries/presenter.py` (`export_to_file`)

Flow (spec "Export"): an empty presenter list returns with no view call; `choose_export_path(_("Export Dictionary"), f"{name}.csv")`, `None` returns; `export_dictionary`; `OSError` shows `_("Failed to export dictionary: {error}")`; always returns `None`, never refreshes.

- [ ] **Step 1: Write the failing tests.** Recorded sequences: empty list `[]`; cancel `[("choose_export", _("Export Dictionary"), "alpha.csv")]`; `OSError` adds `("error", _("Failed to export dictionary: {error}").format(error="denied"))`. The parity test checks that `DictionaryManagementActions` and `DictionaryManagementPresenter` both have `dictionary_names`, `dictionary_path`, `add`, `delete`, `rename`, `import_from_file`, `export_to_file`.

```bash
git -C $REPO apply <<'PATCH'
diff --git a/client/tests/test_dictionary_presenter.py b/client/tests/test_dictionary_presenter.py
index dcda126..97c3d04 100644
--- a/client/tests/test_dictionary_presenter.py
+++ b/client/tests/test_dictionary_presenter.py
@@ -95,6 +95,20 @@ class PresenterModuleTest(unittest.TestCase):
 			with self.subTest(name=name):
 				self.assertIn(Protocol, getattr(presenter_module, name).__bases__)
 
+	def test_presenter_provides_every_action(self):
+		for name in (
+			"dictionary_names",
+			"dictionary_path",
+			"add",
+			"delete",
+			"rename",
+			"import_from_file",
+			"export_to_file",
+		):
+			with self.subTest(name=name):
+				self.assertTrue(hasattr(presenter_module.DictionaryManagementActions, name))
+				self.assertTrue(hasattr(DictionaryManagementPresenter, name))
+
 
 class PresenterRefreshTest(PresenterTestCase):
 	def test_constructor_does_no_io(self):
@@ -577,5 +591,64 @@ class PresenterImportTest(PresenterTestCase):
 		self.assertEqual(self.files(), ["default"])
 
 
+class PresenterExportTest(PresenterTestCase):
+	def choose_call(self, default_file):
+		return ("choose_export", _("Export Dictionary"), default_file)
+
+	def test_export_with_empty_list_does_nothing(self):
+		self.write_dictionary("alpha")
+		presenter = DictionaryManagementPresenter(
+			self.dictionary_dir,
+			get_active_name=lambda: "default",
+			set_active_name=self.set_active_name,
+		)
+		view = FakeView(export_path=self.root / "copy.csv")
+
+		result = presenter.export_to_file(view, "alpha")
+
+		self.assertIsNone(result)
+		self.assertEqual(view.calls, [])
+		self.assertFalse((self.root / "copy.csv").exists())
+
+	def test_export_cancelled_writes_nothing(self):
+		presenter = self.make_presenter("alpha")
+		view = FakeView(export_path=None)
+
+		result = presenter.export_to_file(view, "alpha")
+
+		self.assertIsNone(result)
+		self.assertEqual(view.calls, [self.choose_call("alpha.csv")])
+		self.assertEqual(sorted(path.name for path in self.root.iterdir()), ["dictionaries"])
+
+	def test_export_copies_dictionary_to_chosen_path(self):
+		presenter = self.make_presenter()
+		source = self.write_dictionary("alpha", HEADER + "Alpha,\u2801,General\n")
+		destination = self.root / "copy.csv"
+		view = FakeView(export_path=destination)
+
+		result = presenter.export_to_file(view, "alpha")
+
+		self.assertIsNone(result)
+		self.assertEqual(view.calls, [self.choose_call("alpha.csv")])
+		self.assertEqual(destination.read_bytes(), source.read_bytes())
+		self.assertEqual(presenter.dictionary_names, ["default"])
+
+	def test_export_os_error_shows_error(self):
+		presenter = self.make_presenter("alpha")
+		view = FakeView(export_path=self.root / "copy.csv")
+
+		with patch.object(presenter_module, "export_dictionary", side_effect=PermissionError("denied")):
+			result = presenter.export_to_file(view, "alpha")
+
+		self.assertIsNone(result)
+		self.assertEqual(
+			view.calls,
+			[
+				self.choose_call("alpha.csv"),
+				("error", _("Failed to export dictionary: {error}").format(error="denied")),
+			],
+		)
+
+
 if __name__ == "__main__":
 	unittest.main()
PATCH
```

- [ ] **Step 2: Run them and see them fail.**

```bash
$PY -m unittest tests.test_dictionary_presenter -v
```

Expected:

```
ERROR: test_export_cancelled_writes_nothing (tests.test_dictionary_presenter.PresenterExportTest.test_export_cancelled_writes_nothing)
AttributeError: 'DictionaryManagementPresenter' object has no attribute 'export_to_file'. Did you mean: 'import_from_file'?
ERROR: test_export_copies_dictionary_to_chosen_path (tests.test_dictionary_presenter.PresenterExportTest.test_export_copies_dictionary_to_chosen_path)
AttributeError: 'DictionaryManagementPresenter' object has no attribute 'export_to_file'. Did you mean: 'import_from_file'?
ERROR: test_export_os_error_shows_error (tests.test_dictionary_presenter.PresenterExportTest.test_export_os_error_shows_error)
AttributeError: <module 'dictionaries.presenter' from '/workspace/DotExpress/client/dictionaries/presenter.py'> does not have the attribute 'export_dictionary'
ERROR: test_export_with_empty_list_does_nothing (tests.test_dictionary_presenter.PresenterExportTest.test_export_with_empty_list_does_nothing)
AttributeError: 'DictionaryManagementPresenter' object has no attribute 'export_to_file'. Did you mean: 'import_from_file'?
FAIL: test_presenter_provides_every_action (tests.test_dictionary_presenter.PresenterModuleTest.test_presenter_provides_every_action) (name='export_to_file')
AssertionError: False is not true
Ran 43 tests
FAILED (failures=1, errors=4)
```

- [ ] **Step 3: Implement the flow.**

```bash
git -C $REPO apply <<'PATCH'
diff --git a/client/dictionaries/presenter.py b/client/dictionaries/presenter.py
index 330ca1a..40f0685 100644
--- a/client/dictionaries/presenter.py
+++ b/client/dictionaries/presenter.py
@@ -18,6 +18,7 @@ from dictionaries.manager import (
 	delete_dictionary,
 	dictionary_path_for_name,
 	ensure_default_dictionary,
+	export_dictionary,
 	import_dictionary,
 	list_dictionary_names,
 )
@@ -182,6 +183,18 @@ class DictionaryManagementPresenter:
 			return None
 		return self._selection_after_add(path.stem)
 
+	def export_to_file(self, view: DictionaryManagementView, name: str) -> None:
+		if not self._dictionary_names:
+			return None
+		destination_path = view.choose_export_path(_("Export Dictionary"), f"{name}.csv")
+		if destination_path is None:
+			return None
+		try:
+			export_dictionary(self._dictionary_dir, name, destination_path)
+		except OSError as exc:
+			view.show_error(_("Failed to export dictionary: {error}").format(error=exc))
+		return None
+
 	def _prompt_name_until_success(
 		self,
 		view: DictionaryManagementView,
PATCH
```

- [ ] **Step 4: Run the tests.**

```bash
$PY -m unittest tests.test_dictionary_presenter -v
```

Expected: `Ran 43 tests`, `OK`.

- [ ] **Step 5: Suite check.**

```bash
$T/tools/check_suite.sh 525 43
```

- [ ] **Step 6: Commit.**

```bash
git -C $REPO add client/dictionaries/presenter.py client/tests/test_dictionary_presenter.py
git -C $REPO commit -F - <<'MSG'
feat: add dictionary presenter export flow

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
MSG
```

---

### Task 7: Route dictionary management through the presenter (dialog + frame, one commit)

**Files:**
- Modify: `client/tests/wx_stub.py` (constants, correction 5)
- Modify: `client/tests/test_dictionary_management_dialog.py` (`_FakeActions`, `_make_dialog(dictionary_dir, names, actions=None)`, the replaced refresh test, new classes `DictionaryManagementActionsWiringTest` (8 tests) and `DictionaryManagementViewTest` (10 tests))
- Modify: `client/tests/test_gui_document_flows.py` (`_initialize_state_with_loaded_tables` patches `gui.DictionaryManagementPresenter`; the two `frame._dictionary_names = ...` lines go; new class `DictionaryManagementFrameTest` (6 tests))
- Modify: `client/dialog.py` (constructor `(parent, actions, selected_name)`, counts through `actions.dictionary_path`, button handlers call `self._actions`, `_refresh_from_actions`, the six view methods, `CSV_WILDCARD`; drops the `dictionary_path_for_name`/`list_dictionary_names` imports)
- Modify: `client/gui.py` (imports `DictionaryManagementPresenter`; `_initialize_state` builds and refreshes it and loads settings from its names; `get_dictionary_names_for_dialog` and `on_open_dictionary_management` use it; removes `_refresh_dictionary_names` and the five callbacks)

View methods (each the exact old wx call, `parent=self`): `prompt_dictionary_name` = the body of `gui._prompt_for_dictionary_name`; `show_info` = `wx.MessageBox(msg, _("Info"), wx.OK | wx.ICON_INFORMATION, parent=self)`; `show_error` = `wx.MessageBox(msg, _("Error"), wx.OK | wx.ICON_ERROR, parent=self)` (what `_show_file_error` and the duplicate lambda did); `confirm` = `wx.MessageBox(msg, caption, wx.YES_NO | wx.NO_DEFAULT | wx.ICON_WARNING, parent=self) == wx.YES`; `choose_import_path` / `choose_export_path` = the two `wx.FileDialog` blocks (`wildcard=_(CSV_WILDCARD)`, `style=wx.FD_OPEN` / `defaultFile=..., style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT`), returning `Path(GetPath())` or `None`; the `with` block closes the file dialog before the presenter prompts for a name, as before.

- [ ] **Step 1: Write the failing tests.**

```bash
git -C $REPO apply <<'PATCH'
diff --git a/client/tests/test_dictionary_management_dialog.py b/client/tests/test_dictionary_management_dialog.py
index 0150118..fd6541b 100644
--- a/client/tests/test_dictionary_management_dialog.py
+++ b/client/tests/test_dictionary_management_dialog.py
@@ -1,9 +1,11 @@
 import csv
+import inspect
 import tempfile
 import unittest
 from pathlib import Path
-from unittest.mock import Mock
+from unittest.mock import MagicMock, Mock, patch
 
+from dictionaries.presenter import DictionaryManagementView
 from tests import wx_stub
 
 
@@ -49,9 +51,42 @@ class _FakeListCtrl:
 		self.column_widths[column] = width
 
 
-def _make_dialog(dictionary_dir, names):
+class _FakeActions:
+	"""Stands in for the presenter: fixed names, scripted results, recorded calls."""
+
+	def __init__(self, dictionary_dir, names, results=None):
+		self.dictionary_dir = Path(dictionary_dir)
+		self.dictionary_names = list(names)
+		self.results = dict(results or {})
+		self.calls = []
+
+	def dictionary_path(self, name):
+		return self.dictionary_dir / f"{name}.csv"
+
+	def add(self, view):
+		self.calls.append(("add", view))
+		return self.results.get("add")
+
+	def delete(self, view, name):
+		self.calls.append(("delete", view, name))
+		return self.results.get("delete")
+
+	def rename(self, view, name):
+		self.calls.append(("rename", view, name))
+		return self.results.get("rename")
+
+	def import_from_file(self, view):
+		self.calls.append(("import", view))
+		return self.results.get("import")
+
+	def export_to_file(self, view, name):
+		self.calls.append(("export", view, name))
+		return self.results.get("export")
+
+
+def _make_dialog(dictionary_dir, names, actions=None):
 	target = object.__new__(DictionaryManagementDialog)
-	target.dictionary_dir = Path(dictionary_dir)
+	target._actions = actions if actions is not None else _FakeActions(dictionary_dir, names)
 	target._dictionary_names = list(names)
 	target._dictionary_counts = {}
 	target._selected_name = names[0] if names else ""
@@ -93,15 +128,17 @@ class DictionaryManagementVirtualListTest(unittest.TestCase):
 
 		self.assertEqual(target._get_item_text(0, 1), "0")
 
-	def test_disk_refresh_discovers_new_dictionary_files(self):
+	def test_refresh_after_action_takes_names_from_actions_not_disk(self):
 		with tempfile.TemporaryDirectory() as temp_dir:
 			path = Path(temp_dir) / "new.csv"
 			path.write_text("text,braille,type\n", encoding="utf-8")
-			target = _make_dialog(temp_dir, ["old"])
+			actions = _FakeActions(temp_dir, ["listed"], results={"add": "listed"})
+			target = _make_dialog(temp_dir, ["old"], actions)
 
-			target._refresh_from_disk("new")
+			target._on_add_clicked(None)
 
-		self.assertEqual(target._dictionary_names, ["new"])
+		self.assertEqual(target._dictionary_names, ["listed"])
+		self.assertEqual(target._dictionary_counts, {"listed": 0})
 		self.assertEqual(target.list_ctrl.selected, 0)
 
 	def test_unknown_column_is_rejected(self):
@@ -151,5 +188,245 @@ class DictionaryManagementInteractionTest(unittest.TestCase):
 		target.EndModal.assert_called_once_with(dialog.wx.ID_EDIT)
 
 
+class DictionaryManagementActionsWiringTest(unittest.TestCase):
+	def test_constructor_takes_actions_and_selected_name(self):
+		parameters = list(inspect.signature(DictionaryManagementDialog.__init__).parameters)
+
+		self.assertEqual(parameters, ["self", "parent", "actions", "selected_name"])
+		self.assertFalse(hasattr(dialog, "list_dictionary_names"))
+
+	def test_constructor_lists_names_from_actions(self):
+		actions = _FakeActions(".", ["alpha", "beta"])
+		with (
+			patch.object(dialog.wx.Dialog, "__init__", lambda self, *args, **kwargs: None),
+			patch.object(DictionaryManagementDialog, "_build_ui"),
+			patch.object(DictionaryManagementDialog, "refresh_dictionaries") as refresh,
+		):
+			target = DictionaryManagementDialog(None, actions, "beta")
+
+		self.assertIs(target._actions, actions)
+		self.assertIsNone(target.edit_dictionary_name)
+		self.assertFalse(hasattr(target, "dictionary_dir"))
+		refresh.assert_called_once_with(["alpha", "beta"], "beta")
+
+	def test_add_and_import_pass_dialog_and_refresh_with_result(self):
+		for action, handler in (("add", "_on_add_clicked"), ("import", "_on_import_clicked")):
+			with self.subTest(action=action):
+				actions = _FakeActions(".", ["alpha", "beta"], results={action: "beta"})
+				target = _make_dialog(".", ["alpha"], actions)
+
+				getattr(target, handler)(None)
+
+				self.assertEqual(actions.calls, [(action, target)])
+				self.assertEqual(target._dictionary_names, ["alpha", "beta"])
+				self.assertEqual(target.list_ctrl.selected, 1)
+				self.assertEqual(target.list_ctrl.focused, 1)
+
+	def test_delete_and_rename_pass_selection_and_refresh_with_result(self):
+		for action, handler in (("delete", "_on_delete_clicked"), ("rename", "_on_rename_clicked")):
+			with self.subTest(action=action):
+				actions = _FakeActions(".", ["default", "gamma"], results={action: "gamma"})
+				target = _make_dialog(".", ["alpha", "default"], actions)
+				target.list_ctrl.selected = 0
+
+				getattr(target, handler)(None)
+
+				self.assertEqual(actions.calls, [(action, target, "alpha")])
+				self.assertEqual(target._dictionary_names, ["default", "gamma"])
+				self.assertEqual(target.list_ctrl.selected, 1)
+
+	def test_none_result_leaves_list_untouched(self):
+		for action, handler in (
+			("add", "_on_add_clicked"),
+			("delete", "_on_delete_clicked"),
+			("rename", "_on_rename_clicked"),
+			("import", "_on_import_clicked"),
+		):
+			with self.subTest(action=action):
+				actions = _FakeActions(".", ["other"])
+				target = _make_dialog(".", ["alpha"], actions)
+				target.list_ctrl.selected = 0
+
+				getattr(target, handler)(None)
+
+				self.assertEqual(len(actions.calls), 1)
+				self.assertEqual(target._dictionary_names, ["alpha"])
+				self.assertEqual(target.list_ctrl.refresh_count, 0)
+
+	def test_selection_actions_do_nothing_without_selection(self):
+		for handler in ("_on_delete_clicked", "_on_rename_clicked", "_on_export_clicked"):
+			with self.subTest(handler=handler):
+				actions = _FakeActions(".", ["alpha"], results={"delete": "alpha", "rename": "alpha"})
+				target = _make_dialog(".", ["alpha"], actions)
+				target.list_ctrl.selected = dialog.wx.NOT_FOUND
+
+				getattr(target, handler)(None)
+
+				self.assertEqual(actions.calls, [])
+
+	def test_export_passes_selection_and_never_refreshes(self):
+		actions = _FakeActions(".", ["other"], results={"export": "other"})
+		target = _make_dialog(".", ["alpha"], actions)
+		target.list_ctrl.selected = 0
+
+		target._on_export_clicked(None)
+
+		self.assertEqual(actions.calls, [("export", target, "alpha")])
+		self.assertEqual(target._dictionary_names, ["alpha"])
+		self.assertEqual(target.list_ctrl.refresh_count, 0)
+
+	def test_counts_are_read_through_actions_dictionary_path(self):
+		with tempfile.TemporaryDirectory() as temp_dir:
+			listed = Path(temp_dir) / "listed"
+			listed.mkdir()
+			(listed / "alpha.csv").write_text("text,braille,type\nAlpha,\u2801,General\n", encoding="utf-8")
+			target = _make_dialog(temp_dir, ["alpha"], _FakeActions(listed, ["alpha"]))
+
+			target.refresh_dictionaries(["alpha"], "alpha")
+
+		self.assertEqual(target._get_item_text(0, 1), "1")
+
+
+class DictionaryManagementViewTest(unittest.TestCase):
+	def setUp(self):
+		self.target = _make_dialog(".", ["alpha"])
+		self.wx = dialog.wx
+
+	def _name_dialog(self, result, name="typed"):
+		name_dialog = MagicMock()
+		name_dialog.__enter__.return_value = name_dialog
+		name_dialog.ShowModal.return_value = result
+		name_dialog.get_dictionary_name.return_value = name
+		return name_dialog
+
+	def _file_dialog_class(self, result, path="/data/words.csv"):
+		file_dialog = MagicMock()
+		file_dialog.ShowModal.return_value = result
+		file_dialog.GetPath.return_value = path
+		file_dialog_class = MagicMock()
+		file_dialog_class.return_value.__enter__.return_value = file_dialog
+		return file_dialog_class, file_dialog
+
+	def test_prompt_dictionary_name_returns_entered_name(self):
+		name_dialog = self._name_dialog(self.wx.ID_OK, "beta")
+
+		with patch.object(dialog, "DictionaryNameDialog", return_value=name_dialog) as name_dialog_class:
+			result = self.target.prompt_dictionary_name("Title", "alpha")
+
+		self.assertEqual(result, "beta")
+		name_dialog_class.assert_called_once_with(self.target, initial_name="alpha")
+		name_dialog.SetTitle.assert_called_once_with("Title")
+		name_dialog.ShowModal.assert_called_once_with()
+		name_dialog.__exit__.assert_called_once()
+
+	def test_prompt_dictionary_name_cancel_returns_none(self):
+		name_dialog = self._name_dialog(self.wx.ID_CANCEL)
+
+		with patch.object(dialog, "DictionaryNameDialog", return_value=name_dialog):
+			result = self.target.prompt_dictionary_name("Title", "")
+
+		self.assertIsNone(result)
+		name_dialog.get_dictionary_name.assert_not_called()
+		name_dialog.__exit__.assert_called_once()
+
+	def test_show_info_uses_information_box_on_dialog(self):
+		with patch.object(self.wx, "MessageBox") as message_box:
+			self.target.show_info("message")
+
+		message_box.assert_called_once_with(
+			"message",
+			dialog._("Info"),
+			self.wx.OK | self.wx.ICON_INFORMATION,
+			parent=self.target,
+		)
+
+	def test_show_error_uses_error_box_on_dialog(self):
+		with patch.object(self.wx, "MessageBox") as message_box:
+			self.target.show_error("message")
+
+		message_box.assert_called_once_with(
+			"message",
+			dialog._("Error"),
+			self.wx.OK | self.wx.ICON_ERROR,
+			parent=self.target,
+		)
+
+	def test_confirm_uses_warning_yes_no_box_with_no_default(self):
+		for answer, expected in ((self.wx.YES, True), (self.wx.NO, False)):
+			with self.subTest(answer=answer):
+				with patch.object(self.wx, "MessageBox", return_value=answer) as message_box:
+					result = self.target.confirm("message", "caption")
+
+				self.assertIs(result, expected)
+				message_box.assert_called_once_with(
+					"message",
+					"caption",
+					self.wx.YES_NO | self.wx.NO_DEFAULT | self.wx.ICON_WARNING,
+					parent=self.target,
+				)
+
+	def test_choose_import_path_opens_csv_file_dialog(self):
+		file_dialog_class, file_dialog = self._file_dialog_class(self.wx.ID_OK)
+
+		with patch.object(self.wx, "FileDialog", file_dialog_class, create=True):
+			result = self.target.choose_import_path("Import")
+
+		self.assertEqual(result, Path("/data/words.csv"))
+		file_dialog_class.assert_called_once_with(
+			self.target,
+			"Import",
+			wildcard=dialog._("CSV files (*.csv)|*.csv"),
+			style=self.wx.FD_OPEN,
+		)
+		file_dialog_class.return_value.__exit__.assert_called_once()
+
+	def test_choose_import_path_cancel_returns_none(self):
+		file_dialog_class, file_dialog = self._file_dialog_class(self.wx.ID_CANCEL)
+
+		with patch.object(self.wx, "FileDialog", file_dialog_class, create=True):
+			result = self.target.choose_import_path("Import")
+
+		self.assertIsNone(result)
+		file_dialog.GetPath.assert_not_called()
+
+	def test_choose_export_path_opens_save_dialog_with_default_file(self):
+		file_dialog_class, file_dialog = self._file_dialog_class(self.wx.ID_OK, "/data/out.csv")
+
+		with patch.object(self.wx, "FileDialog", file_dialog_class, create=True):
+			result = self.target.choose_export_path("Export", "alpha.csv")
+
+		self.assertEqual(result, Path("/data/out.csv"))
+		file_dialog_class.assert_called_once_with(
+			self.target,
+			"Export",
+			defaultFile="alpha.csv",
+			wildcard=dialog._("CSV files (*.csv)|*.csv"),
+			style=self.wx.FD_SAVE | self.wx.FD_OVERWRITE_PROMPT,
+		)
+		file_dialog_class.return_value.__exit__.assert_called_once()
+
+	def test_choose_export_path_cancel_returns_none(self):
+		file_dialog_class, file_dialog = self._file_dialog_class(self.wx.ID_CANCEL)
+
+		with patch.object(self.wx, "FileDialog", file_dialog_class, create=True):
+			result = self.target.choose_export_path("Export", "alpha.csv")
+
+		self.assertIsNone(result)
+		file_dialog.GetPath.assert_not_called()
+
+	def test_dialog_provides_every_view_method(self):
+		for name in (
+			"prompt_dictionary_name",
+			"show_info",
+			"show_error",
+			"confirm",
+			"choose_import_path",
+			"choose_export_path",
+		):
+			with self.subTest(name=name):
+				self.assertTrue(hasattr(DictionaryManagementView, name))
+				self.assertTrue(callable(vars(DictionaryManagementDialog).get(name)), name)
+
+
 if __name__ == "__main__":
 	unittest.main()
diff --git a/client/tests/test_gui_document_flows.py b/client/tests/test_gui_document_flows.py
index 6b8acee..c74ad79 100644
--- a/client/tests/test_gui_document_flows.py
+++ b/client/tests/test_gui_document_flows.py
@@ -1,6 +1,7 @@
 from __future__ import annotations
 
 import importlib
+import tempfile
 import unittest
 from dataclasses import replace
 from pathlib import Path
@@ -831,7 +832,6 @@ class BrailleAppLifecycleTest(GuiDocumentFlowsTest):
 
     def test_apply_settings_from_dialog_updates_all_live_state(self) -> None:
         frame = object.__new__(gui.BrailleFrame)
-        frame._dictionary_names = ["default", "math"]
         frame._apply_editor_view_settings = Mock()
         frame.get_dictionary_names_for_dialog = Mock(return_value=["default", "math"])
         snapshot = make_snapshot(
@@ -858,12 +858,10 @@ class BrailleAppLifecycleTest(GuiDocumentFlowsTest):
 
     def _initialize_state_with_loaded_tables(self, loaded_tables: dict[str, str]):
         frame = object.__new__(gui.BrailleFrame)
-        frame._refresh_dictionary_names = Mock()
         frame._register_output_font = Mock(return_value=False)
         with (
             patch.object(gui, "get_dictionary_directory", return_value=Path("dictionary")),
-            patch.object(gui, "ensure_default_dictionary"),
-            patch.object(gui, "list_dictionary_names", return_value=["default"]),
+            patch.object(gui, "DictionaryManagementPresenter", return_value=Mock(dictionary_names=["default"])),
             patch.object(
                 gui,
                 "load_translation_settings",
@@ -919,7 +917,6 @@ class BrailleAppLifecycleTest(GuiDocumentFlowsTest):
 
     def test_applied_settings_tables_reach_next_conversion_request(self) -> None:
         frame = self._make_frame()
-        frame._dictionary_names = ["default"]
         frame._apply_editor_view_settings = Mock()
         frame.get_dictionary_names_for_dialog = Mock(return_value=["default"])
         snapshot = make_snapshot(tables={"default": "test-default.ctb", "math": "test-math.ctb"})
@@ -1065,5 +1062,116 @@ class BrailleAppLifecycleTest(GuiDocumentFlowsTest):
         self.assertIs(show.call_args.kwargs["initial_category"], TranslationSettingsPanel)
 
 
+class DictionaryManagementFrameTest(unittest.TestCase):
+    def _make_frame(self, active: str = "default") -> gui.BrailleFrame:
+        frame = object.__new__(gui.BrailleFrame)
+        frame.translation_settings = TranslationSettings("unicode", 40, active)
+        frame._dictionary_presenter = Mock()
+        return frame
+
+    def _open_management(self, frame, result, edit_name):
+        with (
+            patch.object(gui, "DictionaryManagementDialog") as dialog_class,
+            patch.object(gui, "SpeechSymbolsDialog") as editor_class,
+        ):
+            dialog = dialog_class.return_value.__enter__.return_value
+            dialog.ShowModal.return_value = result
+            dialog.edit_dictionary_name = edit_name
+            frame.on_open_dictionary_management(None)
+        return dialog_class, editor_class
+
+    def test_open_management_passes_presenter_and_refreshed_selection(self) -> None:
+        frame = self._make_frame("alpha")
+        presenter = frame._dictionary_presenter
+        presenter.refresh.return_value = "alpha"
+
+        dialog_class, editor_class = self._open_management(frame, gui.wx.ID_OK, None)
+
+        presenter.refresh.assert_called_once_with("alpha")
+        dialog_class.assert_called_once_with(frame, presenter, "alpha")
+        dialog_class.return_value.__enter__.return_value.ShowModal.assert_called_once_with()
+        editor_class.assert_not_called()
+
+    def test_edit_result_opens_speech_symbols_for_presenter_path(self) -> None:
+        frame = self._make_frame()
+        presenter = frame._dictionary_presenter
+        presenter.dictionary_path.return_value = Path("dictionary/alpha.csv")
+
+        _dialog_class, editor_class = self._open_management(frame, gui.wx.ID_EDIT, "alpha")
+
+        presenter.dictionary_path.assert_called_once_with("alpha")
+        editor_class.assert_called_once_with(frame, dictionary_path=Path("dictionary/alpha.csv"))
+        editor_class.return_value.__enter__.return_value.ShowModal.assert_called_once_with()
+
+    def test_other_results_open_no_editor(self) -> None:
+        for result, edit_name in ((gui.wx.ID_OK, "alpha"), (gui.wx.ID_EDIT, None)):
+            with self.subTest(result=result, edit_name=edit_name):
+                frame = self._make_frame()
+
+                _dialog_class, editor_class = self._open_management(frame, result, edit_name)
+
+                editor_class.assert_not_called()
+                frame._dictionary_presenter.dictionary_path.assert_not_called()
+
+    def test_dictionary_names_for_dialog_refreshes_with_active_name(self) -> None:
+        frame = self._make_frame("alpha")
+        frame._dictionary_presenter.dictionary_names = ["alpha", "default"]
+
+        names = frame.get_dictionary_names_for_dialog()
+
+        self.assertEqual(names, ["alpha", "default"])
+        frame._dictionary_presenter.refresh.assert_called_once_with("alpha")
+
+    def test_initialize_state_wires_presenter_to_active_dictionary(self) -> None:
+        with tempfile.TemporaryDirectory() as temp_dir:
+            dictionary_dir = Path(temp_dir)
+            (dictionary_dir / "alpha.csv").write_text("text,braille,type\n", encoding="utf-8")
+            frame = object.__new__(gui.BrailleFrame)
+            frame._register_output_font = Mock(return_value=False)
+            with (
+                patch.object(gui, "get_dictionary_directory", return_value=dictionary_dir),
+                patch.object(
+                    gui,
+                    "load_translation_settings",
+                    return_value=TranslationSettings("unicode", 40, "alpha"),
+                ) as load_settings,
+                patch.object(gui, "get_workspace_directory", return_value=Path("workspace")),
+                patch.object(gui, "load_view_settings", return_value=ViewSettings(40, "light", "default")),
+                patch.object(gui, "load_translation_tables", return_value={}),
+            ):
+                frame._initialize_state()
+            presenter = frame._dictionary_presenter
+            view = Mock()
+            view.confirm.return_value = True
+
+            with patch.object(gui, "set_selected_dictionary") as set_selected:
+                selected = presenter.delete(view, "alpha")
+
+            remaining = sorted(path.name for path in dictionary_dir.iterdir())
+
+        self.assertIsInstance(presenter, gui.DictionaryManagementPresenter)
+        self.assertEqual(presenter.dictionary_dir, dictionary_dir)
+        load_settings.assert_called_once_with(["alpha", "default"])
+        self.assertEqual(selected, "default")
+        self.assertEqual(remaining, ["default.csv"])
+        set_selected.assert_called_once_with("default")
+        self.assertEqual(frame.translation_settings, TranslationSettings("unicode", 40, "default"))
+
+    def test_frame_dictionary_callbacks_are_removed(self) -> None:
+        # Check the class: the wx stub makes every missing instance attribute look present.
+        for name in (
+            "_refresh_dictionary_names",
+            "add_dictionary",
+            "delete_dictionary_from_dialog",
+            "rename_dictionary_from_dialog",
+            "import_dictionary_from_dialog",
+            "export_dictionary_from_dialog",
+        ):
+            with self.subTest(name=name):
+                self.assertFalse(hasattr(gui.BrailleFrame, name))
+        self.assertTrue(hasattr(gui.BrailleFrame, "_set_active_dictionary"))
+        self.assertTrue(hasattr(gui.BrailleFrame, "get_dictionary_names_for_dialog"))
+
+
 if __name__ == "__main__":
     unittest.main()
diff --git a/client/tests/wx_stub.py b/client/tests/wx_stub.py
index 9bf28d2..df281fd 100644
--- a/client/tests/wx_stub.py
+++ b/client/tests/wx_stub.py
@@ -554,6 +554,7 @@ def gui_frame_stubs():
     wx.ID_ANY = -1
     wx.ID_ABOUT = 1
     wx.ID_OK = 2
+    wx.ID_EDIT = 5030
     wx.OK = 4
     wx.CANCEL = 8
     wx.YES = 1
@@ -892,7 +893,13 @@ SPEECH_RESTORE_ROOTS = frozenset(
 
 
 def speech_dialog_stubs():
-    """Submodule-registering ``wx`` for ``dialog.py`` (``OK`` = 1, flags absorb ``|``)."""
+    """Submodule-registering ``wx`` for ``dialog.py`` (``OK`` = 1, flags absorb ``|``).
+
+    The message-box, file-dialog and result constants used by the dictionary
+    management view are distinct powers of two (``ID_OK``/``ID_CANCEL`` are
+    plain ids), so a test can tell ``wx.OK | wx.ICON_ERROR`` from
+    ``wx.YES_NO | wx.NO_DEFAULT | wx.ICON_WARNING``.
+    """
     wx = AutoSubmoduleModule("wx")
     wx.Dialog = _new_class("Dialog")
     wx.ListCtrl = _new_class("ListCtrl")
@@ -902,6 +909,17 @@ def speech_dialog_stubs():
     wx.NOT_FOUND = -1
     wx.OK = 1
     wx.ICON_ERROR = 2
+    wx.ICON_INFORMATION = 4
+    wx.ICON_WARNING = 8
+    wx.YES_NO = 16
+    wx.NO_DEFAULT = 32
+    wx.YES = 64
+    wx.NO = 128
+    wx.FD_OPEN = 256
+    wx.FD_SAVE = 512
+    wx.FD_OVERWRITE_PROMPT = 1024
+    wx.ID_OK = 5100
+    wx.ID_CANCEL = 5101
     wx.MessageBox = lambda *args, **kwargs: None
     return {"wx": wx}
 
PATCH
```

- [ ] **Step 2: Run them and see them fail.**

```bash
$PY -m unittest tests.test_dictionary_management_dialog tests.test_gui_document_flows -v
```

Expected (the `TypeError ... not 'function'` lines come from the old frame code running against the stub frame, where `dictionary_dir` is a no-op function; they disappear once the frame uses the presenter):

```
ERROR: test_add_and_import_pass_dialog_and_refresh_with_result (tests.test_dictionary_management_dialog.DictionaryManagementActionsWiringTest.test_add_and_import_pass_dialog_and_refresh_with_result) (action='add')
AttributeError: 'DictionaryManagementDialog' object has no attribute '_on_add'. Did you mean: '_on_edit'?
ERROR: test_add_and_import_pass_dialog_and_refresh_with_result (tests.test_dictionary_management_dialog.DictionaryManagementActionsWiringTest.test_add_and_import_pass_dialog_and_refresh_with_result) (action='import')
AttributeError: 'DictionaryManagementDialog' object has no attribute '_on_import'
ERROR: test_constructor_lists_names_from_actions (tests.test_dictionary_management_dialog.DictionaryManagementActionsWiringTest.test_constructor_lists_names_from_actions)
TypeError: DictionaryManagementDialog.__init__() missing 6 required positional arguments: 'dictionary_dir', 'on_add', 'on_delete', 'on_rename', 'on_import', and 'on_export'
ERROR: test_counts_are_read_through_actions_dictionary_path (tests.test_dictionary_management_dialog.DictionaryManagementActionsWiringTest.test_counts_are_read_through_actions_dictionary_path)
AttributeError: 'DictionaryManagementDialog' object has no attribute 'dictionary_dir'
ERROR: test_delete_and_rename_pass_selection_and_refresh_with_result (tests.test_dictionary_management_dialog.DictionaryManagementActionsWiringTest.test_delete_and_rename_pass_selection_and_refresh_with_result) (action='delete')
AttributeError: 'DictionaryManagementDialog' object has no attribute '_on_delete'
ERROR: test_delete_and_rename_pass_selection_and_refresh_with_result (tests.test_dictionary_management_dialog.DictionaryManagementActionsWiringTest.test_delete_and_rename_pass_selection_and_refresh_with_result) (action='rename')
AttributeError: 'DictionaryManagementDialog' object has no attribute '_on_rename'
ERROR: test_export_passes_selection_and_never_refreshes (tests.test_dictionary_management_dialog.DictionaryManagementActionsWiringTest.test_export_passes_selection_and_never_refreshes)
AttributeError: 'DictionaryManagementDialog' object has no attribute '_on_export'
ERROR: test_none_result_leaves_list_untouched (tests.test_dictionary_management_dialog.DictionaryManagementActionsWiringTest.test_none_result_leaves_list_untouched) (action='add')
AttributeError: 'DictionaryManagementDialog' object has no attribute '_on_add'. Did you mean: '_on_edit'?
ERROR: test_none_result_leaves_list_untouched (tests.test_dictionary_management_dialog.DictionaryManagementActionsWiringTest.test_none_result_leaves_list_untouched) (action='delete')
AttributeError: 'DictionaryManagementDialog' object has no attribute '_on_delete'
ERROR: test_none_result_leaves_list_untouched (tests.test_dictionary_management_dialog.DictionaryManagementActionsWiringTest.test_none_result_leaves_list_untouched) (action='rename')
AttributeError: 'DictionaryManagementDialog' object has no attribute '_on_rename'
ERROR: test_none_result_leaves_list_untouched (tests.test_dictionary_management_dialog.DictionaryManagementActionsWiringTest.test_none_result_leaves_list_untouched) (action='import')
AttributeError: 'DictionaryManagementDialog' object has no attribute '_on_import'
ERROR: test_refresh_restores_preferred_selection (tests.test_dictionary_management_dialog.DictionaryManagementInteractionTest.test_refresh_restores_preferred_selection)
AttributeError: 'DictionaryManagementDialog' object has no attribute 'dictionary_dir'
ERROR: test_choose_export_path_cancel_returns_none (tests.test_dictionary_management_dialog.DictionaryManagementViewTest.test_choose_export_path_cancel_returns_none)
AttributeError: 'DictionaryManagementDialog' object has no attribute 'choose_export_path'
ERROR: test_choose_export_path_opens_save_dialog_with_default_file (tests.test_dictionary_management_dialog.DictionaryManagementViewTest.test_choose_export_path_opens_save_dialog_with_default_file)
AttributeError: 'DictionaryManagementDialog' object has no attribute 'choose_export_path'
ERROR: test_choose_import_path_cancel_returns_none (tests.test_dictionary_management_dialog.DictionaryManagementViewTest.test_choose_import_path_cancel_returns_none)
AttributeError: 'DictionaryManagementDialog' object has no attribute 'choose_import_path'
ERROR: test_choose_import_path_opens_csv_file_dialog (tests.test_dictionary_management_dialog.DictionaryManagementViewTest.test_choose_import_path_opens_csv_file_dialog)
AttributeError: 'DictionaryManagementDialog' object has no attribute 'choose_import_path'
ERROR: test_confirm_uses_warning_yes_no_box_with_no_default (tests.test_dictionary_management_dialog.DictionaryManagementViewTest.test_confirm_uses_warning_yes_no_box_with_no_default) (answer=64)
AttributeError: 'DictionaryManagementDialog' object has no attribute 'confirm'
ERROR: test_confirm_uses_warning_yes_no_box_with_no_default (tests.test_dictionary_management_dialog.DictionaryManagementViewTest.test_confirm_uses_warning_yes_no_box_with_no_default) (answer=128)
AttributeError: 'DictionaryManagementDialog' object has no attribute 'confirm'
ERROR: test_prompt_dictionary_name_cancel_returns_none (tests.test_dictionary_management_dialog.DictionaryManagementViewTest.test_prompt_dictionary_name_cancel_returns_none)
AttributeError: 'DictionaryManagementDialog' object has no attribute 'prompt_dictionary_name'
ERROR: test_prompt_dictionary_name_returns_entered_name (tests.test_dictionary_management_dialog.DictionaryManagementViewTest.test_prompt_dictionary_name_returns_entered_name)
AttributeError: 'DictionaryManagementDialog' object has no attribute 'prompt_dictionary_name'
ERROR: test_show_error_uses_error_box_on_dialog (tests.test_dictionary_management_dialog.DictionaryManagementViewTest.test_show_error_uses_error_box_on_dialog)
AttributeError: 'DictionaryManagementDialog' object has no attribute 'show_error'
ERROR: test_show_info_uses_information_box_on_dialog (tests.test_dictionary_management_dialog.DictionaryManagementViewTest.test_show_info_uses_information_box_on_dialog)
AttributeError: 'DictionaryManagementDialog' object has no attribute 'show_info'
ERROR: test_missing_dictionary_has_zero_entries (tests.test_dictionary_management_dialog.DictionaryManagementVirtualListTest.test_missing_dictionary_has_zero_entries)
AttributeError: 'DictionaryManagementDialog' object has no attribute 'dictionary_dir'
ERROR: test_refresh_after_action_takes_names_from_actions_not_disk (tests.test_dictionary_management_dialog.DictionaryManagementVirtualListTest.test_refresh_after_action_takes_names_from_actions_not_disk)
AttributeError: 'DictionaryManagementDialog' object has no attribute '_on_add'. Did you mean: '_on_edit'?
ERROR: test_refresh_sets_virtual_count_and_valid_entry_counts (tests.test_dictionary_management_dialog.DictionaryManagementVirtualListTest.test_refresh_sets_virtual_count_and_valid_entry_counts)
AttributeError: 'DictionaryManagementDialog' object has no attribute 'dictionary_dir'
ERROR: test_initialize_state_falls_back_to_default_tables_when_loader_returns_empty (tests.test_gui_document_flows.BrailleAppLifecycleTest.test_initialize_state_falls_back_to_default_tables_when_loader_returns_empty)
AttributeError: <module 'gui' from '/workspace/DotExpress/client/gui.py'> does not have the attribute 'DictionaryManagementPresenter'
ERROR: test_initialize_state_loads_translation_tables_into_frame (tests.test_gui_document_flows.BrailleAppLifecycleTest.test_initialize_state_loads_translation_tables_into_frame)
AttributeError: <module 'gui' from '/workspace/DotExpress/client/gui.py'> does not have the attribute 'DictionaryManagementPresenter'
ERROR: test_dictionary_names_for_dialog_refreshes_with_active_name (tests.test_gui_document_flows.DictionaryManagementFrameTest.test_dictionary_names_for_dialog_refreshes_with_active_name)
TypeError: argument should be a str or an os.PathLike object where __fspath__ returns a str, not 'function'
ERROR: test_edit_result_opens_speech_symbols_for_presenter_path (tests.test_gui_document_flows.DictionaryManagementFrameTest.test_edit_result_opens_speech_symbols_for_presenter_path)
TypeError: argument should be a str or an os.PathLike object where __fspath__ returns a str, not 'function'
ERROR: test_initialize_state_wires_presenter_to_active_dictionary (tests.test_gui_document_flows.DictionaryManagementFrameTest.test_initialize_state_wires_presenter_to_active_dictionary)
AttributeError: 'function' object has no attribute 'delete'
ERROR: test_open_management_passes_presenter_and_refreshed_selection (tests.test_gui_document_flows.DictionaryManagementFrameTest.test_open_management_passes_presenter_and_refreshed_selection)
TypeError: argument should be a str or an os.PathLike object where __fspath__ returns a str, not 'function'
ERROR: test_other_results_open_no_editor (tests.test_gui_document_flows.DictionaryManagementFrameTest.test_other_results_open_no_editor) (result=2, edit_name='alpha')
TypeError: argument should be a str or an os.PathLike object where __fspath__ returns a str, not 'function'
ERROR: test_other_results_open_no_editor (tests.test_gui_document_flows.DictionaryManagementFrameTest.test_other_results_open_no_editor) (result=5030, edit_name=None)
TypeError: argument should be a str or an os.PathLike object where __fspath__ returns a str, not 'function'
FAIL: test_constructor_takes_actions_and_selected_name (tests.test_dictionary_management_dialog.DictionaryManagementActionsWiringTest.test_constructor_takes_actions_and_selected_name)
AssertionError: Lists differ: ['self', 'parent', 'dictionary_names', 'selected_name', 'dict[69 chars]ort'] != ['self', 'parent', 'actions', 'selected_name']
FAIL: test_dialog_provides_every_view_method (tests.test_dictionary_management_dialog.DictionaryManagementViewTest.test_dialog_provides_every_view_method) (name='prompt_dictionary_name')
AssertionError: False is not true : prompt_dictionary_name
FAIL: test_dialog_provides_every_view_method (tests.test_dictionary_management_dialog.DictionaryManagementViewTest.test_dialog_provides_every_view_method) (name='show_info')
AssertionError: False is not true : show_info
FAIL: test_dialog_provides_every_view_method (tests.test_dictionary_management_dialog.DictionaryManagementViewTest.test_dialog_provides_every_view_method) (name='show_error')
AssertionError: False is not true : show_error
FAIL: test_dialog_provides_every_view_method (tests.test_dictionary_management_dialog.DictionaryManagementViewTest.test_dialog_provides_every_view_method) (name='confirm')
AssertionError: False is not true : confirm
FAIL: test_dialog_provides_every_view_method (tests.test_dictionary_management_dialog.DictionaryManagementViewTest.test_dialog_provides_every_view_method) (name='choose_import_path')
AssertionError: False is not true : choose_import_path
FAIL: test_dialog_provides_every_view_method (tests.test_dictionary_management_dialog.DictionaryManagementViewTest.test_dialog_provides_every_view_method) (name='choose_export_path')
AssertionError: False is not true : choose_export_path
FAIL: test_frame_dictionary_callbacks_are_removed (tests.test_gui_document_flows.DictionaryManagementFrameTest.test_frame_dictionary_callbacks_are_removed) (name='_refresh_dictionary_names')
AssertionError: True is not false
FAIL: test_frame_dictionary_callbacks_are_removed (tests.test_gui_document_flows.DictionaryManagementFrameTest.test_frame_dictionary_callbacks_are_removed) (name='add_dictionary')
AssertionError: True is not false
FAIL: test_frame_dictionary_callbacks_are_removed (tests.test_gui_document_flows.DictionaryManagementFrameTest.test_frame_dictionary_callbacks_are_removed) (name='delete_dictionary_from_dialog')
AssertionError: True is not false
FAIL: test_frame_dictionary_callbacks_are_removed (tests.test_gui_document_flows.DictionaryManagementFrameTest.test_frame_dictionary_callbacks_are_removed) (name='rename_dictionary_from_dialog')
AssertionError: True is not false
FAIL: test_frame_dictionary_callbacks_are_removed (tests.test_gui_document_flows.DictionaryManagementFrameTest.test_frame_dictionary_callbacks_are_removed) (name='import_dictionary_from_dialog')
AssertionError: True is not false
FAIL: test_frame_dictionary_callbacks_are_removed (tests.test_gui_document_flows.DictionaryManagementFrameTest.test_frame_dictionary_callbacks_are_removed) (name='export_dictionary_from_dialog')
AssertionError: True is not false
Ran 93 tests
FAILED (failures=13, errors=33)
```

Also check that the stub constants did not disturb the other `dialog.py` and stub consumers:

```bash
$PY -m unittest tests.test_speech_symbols_dialog tests.test_wx_stub tests.test_dialog_display tests.test_dialog_validation 2>&1 | tail -3
```

Expected: `Ran 50 tests`, `OK`.

- [ ] **Step 3: Switch the dialog and the frame.**

```bash
git -C $REPO apply <<'PATCH'
diff --git a/client/dialog.py b/client/dialog.py
index 64d76d8..4e6d7c8 100644
--- a/client/dialog.py
+++ b/client/dialog.py
@@ -19,13 +19,14 @@ from dictionaries.entries import (
 from dictionaries.manager import (
 	DEFAULT_DICTIONARY_NAME,
 	MAX_DICTIONARY_NAME_LENGTH,
-	dictionary_path_for_name,
-	list_dictionary_names,
 	normalize_dictionary_name,
 )
+from dictionaries.presenter import DictionaryManagementActions
 from documents.workspace import normalize_document_name
 from i18n import _
 
+CSV_WILDCARD = "CSV files (*.csv)|*.csv"
+
 
 def finalize_dialog_layout(dialog: wx.Dialog, sizer: wx.Sizer) -> None:
 	dialog.SetSizerAndFit(sizer)
@@ -648,34 +649,23 @@ class SpeechSymbolsDialog(wx.Dialog):
 
 
 class DictionaryManagementDialog(wx.Dialog):
-	"""Dialog that stages dictionary lifecycle actions through callbacks."""
+	"""Passive view of dictionary management: runs ``actions`` and implements ``DictionaryManagementView``."""
 
 	def __init__(
 		self,
 		parent: wx.Window | None,
-		dictionary_names: list[str],
+		actions: DictionaryManagementActions,
 		selected_name: str,
-		dictionary_dir: Path,
-		on_add: Callable[[wx.Window | None], str | None],
-		on_delete: Callable[[wx.Window | None, str], str | None],
-		on_rename: Callable[[wx.Window | None, str], str | None],
-		on_import: Callable[[wx.Window | None], str | None],
-		on_export: Callable[[wx.Window | None, str], None],
 	):
 		super().__init__(
 			parent,
 			title=_("Dictionary Management"),
 			style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
 		)
-		self.dictionary_dir = Path(dictionary_dir)
-		self._dictionary_names = list(dictionary_names)
+		self._actions = actions
+		self._dictionary_names = list(actions.dictionary_names)
 		self._selected_name = selected_name
 		self._dictionary_counts: dict[str, int] = {}
-		self._on_add = on_add
-		self._on_delete = on_delete
-		self._on_rename = on_rename
-		self._on_import = on_import
-		self._on_export = on_export
 		self.edit_dictionary_name: str | None = None
 		self._build_ui()
 		self.refresh_dictionaries(self._dictionary_names, selected_name)
@@ -738,7 +728,7 @@ class DictionaryManagementDialog(wx.Dialog):
 
 	def _load_dictionary_counts(self) -> None:
 		self._dictionary_counts = {
-			name: len(load_dictionary_entries(dictionary_path_for_name(name, self.dictionary_dir)))
+			name: len(load_dictionary_entries(self._actions.dictionary_path(name)))
 			for name in self._dictionary_names
 		}
 
@@ -800,33 +790,33 @@ class DictionaryManagementDialog(wx.Dialog):
 		event.Skip()
 
 	def _on_add_clicked(self, _event: wx.CommandEvent) -> None:
-		preferred_name = self._on_add(self)
+		preferred_name = self._actions.add(self)
 		if preferred_name is not None:
-			self._refresh_from_disk(preferred_name)
+			self._refresh_from_actions(preferred_name)
 
 	def _on_delete_clicked(self, _event: wx.CommandEvent) -> None:
 		selected = self._get_selected_name()
 		if selected is not None:
-			preferred_name = self._on_delete(self, selected)
+			preferred_name = self._actions.delete(self, selected)
 			if preferred_name is not None:
-				self._refresh_from_disk(preferred_name)
+				self._refresh_from_actions(preferred_name)
 
 	def _on_rename_clicked(self, _event: wx.CommandEvent) -> None:
 		selected = self._get_selected_name()
 		if selected is not None:
-			preferred_name = self._on_rename(self, selected)
+			preferred_name = self._actions.rename(self, selected)
 			if preferred_name is not None:
-				self._refresh_from_disk(preferred_name)
+				self._refresh_from_actions(preferred_name)
 
 	def _on_import_clicked(self, _event: wx.CommandEvent) -> None:
-		preferred_name = self._on_import(self)
+		preferred_name = self._actions.import_from_file(self)
 		if preferred_name is not None:
-			self._refresh_from_disk(preferred_name)
+			self._refresh_from_actions(preferred_name)
 
 	def _on_export_clicked(self, _event: wx.CommandEvent) -> None:
 		selected = self._get_selected_name()
 		if selected is not None:
-			self._on_export(self, selected)
+			self._actions.export_to_file(self, selected)
 
 	def _on_edit(self, _event: wx.Event) -> None:
 		selected = self._get_selected_name()
@@ -835,8 +825,47 @@ class DictionaryManagementDialog(wx.Dialog):
 		self.edit_dictionary_name = selected
 		self.EndModal(wx.ID_EDIT)
 
-	def _refresh_from_disk(self, preferred_name: str | None) -> None:
-		self.refresh_dictionaries(list_dictionary_names(self.dictionary_dir), preferred_name)
+	def _refresh_from_actions(self, preferred_name: str | None) -> None:
+		self.refresh_dictionaries(self._actions.dictionary_names, preferred_name)
+
+	def prompt_dictionary_name(self, title: str, initial_name: str) -> str | None:
+		with DictionaryNameDialog(self, initial_name=initial_name) as name_dialog:
+			name_dialog.SetTitle(title)
+			if name_dialog.ShowModal() != wx.ID_OK:
+				return None
+			return name_dialog.get_dictionary_name()
+
+	def show_info(self, message: str) -> None:
+		wx.MessageBox(message, _("Info"), wx.OK | wx.ICON_INFORMATION, parent=self)
+
+	def show_error(self, message: str) -> None:
+		wx.MessageBox(message, _("Error"), wx.OK | wx.ICON_ERROR, parent=self)
+
+	def confirm(self, message: str, caption: str) -> bool:
+		return wx.MessageBox(message, caption, wx.YES_NO | wx.NO_DEFAULT | wx.ICON_WARNING, parent=self) == wx.YES
+
+	def choose_import_path(self, title: str) -> Path | None:
+		with wx.FileDialog(
+			self,
+			title,
+			wildcard=_(CSV_WILDCARD),
+			style=wx.FD_OPEN,
+		) as file_dialog:
+			if file_dialog.ShowModal() != wx.ID_OK:
+				return None
+			return Path(file_dialog.GetPath())
+
+	def choose_export_path(self, title: str, default_file: str) -> Path | None:
+		with wx.FileDialog(
+			self,
+			title,
+			defaultFile=default_file,
+			wildcard=_(CSV_WILDCARD),
+			style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT,
+		) as file_dialog:
+			if file_dialog.ShowModal() != wx.ID_OK:
+				return None
+			return Path(file_dialog.GetPath())
 
 	def __enter__(self) -> "DictionaryManagementDialog":
 		return self
diff --git a/client/gui.py b/client/gui.py
index 5663288..d535fa8 100644
--- a/client/gui.py
+++ b/client/gui.py
@@ -36,6 +36,7 @@ from dictionaries.manager import (
 	list_dictionary_names,
 )
 from dictionaries.name_prompt import prompt_dictionary_name_until_success, rename_dictionary_after_name_prompt
+from dictionaries.presenter import DictionaryManagementPresenter
 from documents.controller import DocumentController
 from documents.formats import get_format
 from documents.session import (
@@ -293,11 +294,14 @@ class BrailleFrame(wx.Frame):
 
 	def _initialize_state(self) -> ViewSettings:
 		self.dictionary_dir = get_dictionary_directory()
-		ensure_default_dictionary(self.dictionary_dir)
-		self._dictionary_names = list_dictionary_names(self.dictionary_dir)
-		self.translation_settings = load_translation_settings(self._dictionary_names)
+		self._dictionary_presenter = DictionaryManagementPresenter(
+			self.dictionary_dir,
+			get_active_name=lambda: self.translation_settings.selected_dictionary,
+			set_active_name=self._set_active_dictionary,
+		)
+		self._dictionary_presenter.refresh()
+		self.translation_settings = load_translation_settings(self._dictionary_presenter.dictionary_names)
 		self.translation_tables = load_translation_tables() or DEFAULT_TRANSLATION_TABLES.copy()
-		self._refresh_dictionary_names(self.translation_settings.selected_dictionary)
 		self.workspace_dir = get_workspace_directory()
 		self._document_controller = DocumentController()
 		self.documents = []
@@ -560,15 +564,9 @@ class BrailleFrame(wx.Frame):
 			control.Refresh()
 		self.Layout()
 
-	def _refresh_dictionary_names(self, preferred_name: str | None = None) -> str:
-		ensure_default_dictionary(self.dictionary_dir)
-		self._dictionary_names[:] = list_dictionary_names(self.dictionary_dir)
-		selected_name = resolve_management_selection(self._dictionary_names, preferred_name)
-		return selected_name
-
 	def get_dictionary_names_for_dialog(self) -> list[str]:
-		self._refresh_dictionary_names(self.translation_settings.selected_dictionary)
-		return list(self._dictionary_names)
+		self._dictionary_presenter.refresh(self.translation_settings.selected_dictionary)
+		return self._dictionary_presenter.dictionary_names
 
 	def get_settings_snapshot(self) -> DotExpressSettingsSnapshot:
 		dictionary_names = self.get_dictionary_names_for_dialog()
@@ -1232,211 +1230,17 @@ class BrailleFrame(wx.Frame):
 		self._focus_section(target_section)
 
 	def on_open_dictionary_management(self, _evt) -> None:
-		selected_name = self._refresh_dictionary_names(self.translation_settings.selected_dictionary)
-		with DictionaryManagementDialog(
-			self,
-			self._dictionary_names,
-			selected_name,
-			self.dictionary_dir,
-			self.add_dictionary,
-			self.delete_dictionary_from_dialog,
-			self.rename_dictionary_from_dialog,
-			self.import_dictionary_from_dialog,
-			self.export_dictionary_from_dialog,
-		) as dialog:
+		selected_name = self._dictionary_presenter.refresh(self.translation_settings.selected_dictionary)
+		with DictionaryManagementDialog(self, self._dictionary_presenter, selected_name) as dialog:
 			result = dialog.ShowModal()
 			edit_name = dialog.edit_dictionary_name
 
 		if result != wx.ID_EDIT or edit_name is None:
 			return
-		dictionary_path = dictionary_path_for_name(edit_name, self.dictionary_dir)
+		dictionary_path = self._dictionary_presenter.dictionary_path(edit_name)
 		with SpeechSymbolsDialog(self, dictionary_path=dictionary_path) as editor:
 			editor.ShowModal()
 
-	def add_dictionary(self, parent: wx.Window | None) -> str | None:
-		dialog_parent = parent or self
-		try:
-			path = prompt_dictionary_name_until_success(
-				"",
-				prompt_name=lambda initial_name: _prompt_for_dictionary_name(
-					dialog_parent,
-					title=_("Add Dictionary"),
-					initial_name=initial_name,
-				),
-				on_submit=lambda dictionary_name: create_dictionary(self.dictionary_dir, dictionary_name),
-				on_duplicate=lambda dictionary_name: wx.MessageBox(
-					_('Dictionary "{name}" already exists.').format(name=dictionary_name.strip()),
-					_("Error"),
-					wx.OK | wx.ICON_ERROR,
-					parent=dialog_parent,
-				),
-			)
-		except ValueError as exc:
-			wx.MessageBox(str(exc), _("Info"), wx.OK | wx.ICON_INFORMATION, parent=dialog_parent)
-			return None
-		if path is None:
-			return None
-
-		update = plan_dictionary_state_after_add(
-			self.translation_settings.selected_dictionary,
-			self.get_dictionary_names_for_dialog(),
-			path.stem,
-		)
-		return update.management_selected_name
-
-	def delete_dictionary_from_dialog(self, parent: wx.Window | None, selected_name: str) -> str | None:
-		dialog_parent = parent or self
-		if is_default_dictionary(selected_name):
-			wx.MessageBox(
-				_("The default dictionary cannot be deleted."),
-				_("Info"),
-				wx.OK | wx.ICON_INFORMATION,
-				parent=dialog_parent,
-			)
-			return None
-
-		if (
-			wx.MessageBox(
-				_('Do you want to delete dictionary "{name}"?').format(name=selected_name),
-				_("Confirm Delete Dictionary"),
-				wx.YES_NO | wx.NO_DEFAULT | wx.ICON_WARNING,
-				parent=dialog_parent,
-			)
-			!= wx.YES
-		):
-			return None
-
-		previous_names = list(self._dictionary_names)
-		current_active_name = self.translation_settings.selected_dictionary
-		try:
-			delete_dictionary(self.dictionary_dir, selected_name)
-		except OSError as exc:
-			self._show_file_error(_("Failed to delete dictionary: {error}"), exc, parent=dialog_parent)
-			return None
-		self._refresh_dictionary_names(selected_name)
-		update = plan_dictionary_state_after_delete(
-			current_active_name,
-			selected_name,
-			previous_names,
-		)
-		if update.active_selected_name != current_active_name:
-			self._set_active_dictionary(update.active_selected_name)
-		return update.management_selected_name
-
-	def rename_dictionary_from_dialog(self, parent: wx.Window | None, selected_name: str) -> str | None:
-		dialog_parent = parent or self
-		if is_default_dictionary(selected_name):
-			return None
-		try:
-			path = prompt_dictionary_name_until_success(
-				selected_name,
-				prompt_name=lambda initial_name: _prompt_for_dictionary_name(
-					dialog_parent,
-					title=_("Rename Dictionary"),
-					initial_name=initial_name,
-				),
-				on_submit=lambda dictionary_name: rename_dictionary_after_name_prompt(
-					self.dictionary_dir,
-					selected_name,
-					dictionary_name,
-				),
-				on_duplicate=lambda dictionary_name: wx.MessageBox(
-					_('Dictionary "{name}" already exists.').format(name=dictionary_name.strip()),
-					_("Error"),
-					wx.OK | wx.ICON_ERROR,
-					parent=dialog_parent,
-				),
-			)
-		except ValueError as exc:
-			wx.MessageBox(str(exc), _("Info"), wx.OK | wx.ICON_INFORMATION, parent=dialog_parent)
-			return None
-		except OSError as exc:
-			self._show_file_error(_("Failed to save dictionary: {error}"), exc, parent=dialog_parent)
-			return None
-		if path is None:
-			return None
-
-		current_active_name = self.translation_settings.selected_dictionary
-		self._refresh_dictionary_names(path.stem)
-		update = plan_dictionary_state_after_rename(
-			current_active_name,
-			selected_name,
-			path.stem,
-			self.get_dictionary_names_for_dialog(),
-		)
-		if update.active_selected_name != current_active_name:
-			self._set_active_dictionary(update.active_selected_name)
-		return update.management_selected_name
-
-	def import_dictionary_from_dialog(self, parent: wx.Window | None) -> str | None:
-		dialog_parent = parent or self
-		with wx.FileDialog(
-			dialog_parent,
-			_("Import Dictionary"),
-			wildcard=self._get_csv_wildcard(),
-			style=wx.FD_OPEN,
-		) as file_dialog:
-			if file_dialog.ShowModal() != wx.ID_OK:
-				return None
-			source_path = Path(file_dialog.GetPath())
-
-		try:
-			path = prompt_dictionary_name_until_success(
-				source_path.stem,
-				prompt_name=lambda initial_name: _prompt_for_dictionary_name(
-					dialog_parent,
-					title=_("Add Dictionary"),
-					initial_name=initial_name,
-				),
-				on_submit=lambda dictionary_name: import_dictionary(self.dictionary_dir, source_path, dictionary_name),
-				on_duplicate=lambda dictionary_name: wx.MessageBox(
-					_('Dictionary "{name}" already exists.').format(name=dictionary_name.strip()),
-					_("Error"),
-					wx.OK | wx.ICON_ERROR,
-					parent=dialog_parent,
-				),
-			)
-		except ValueError:
-			wx.MessageBox(
-				_("Imported file must contain text, braille, and type headers."),
-				_("Error"),
-				wx.OK | wx.ICON_ERROR,
-				parent=dialog_parent,
-			)
-			return None
-		except OSError as exc:
-			self._show_file_error(_("Failed to import dictionary: {error}"), exc, parent=dialog_parent)
-			return None
-		if path is None:
-			return None
-
-		update = plan_dictionary_state_after_add(
-			self.translation_settings.selected_dictionary,
-			self.get_dictionary_names_for_dialog(),
-			path.stem,
-		)
-		return update.management_selected_name
-
-	def export_dictionary_from_dialog(self, parent: wx.Window | None, selected_name: str) -> None:
-		dialog_parent = parent or self
-		if not self._dictionary_names:
-			return
-		with wx.FileDialog(
-			dialog_parent,
-			_("Export Dictionary"),
-			defaultFile=f"{selected_name}.csv",
-			wildcard=self._get_csv_wildcard(),
-			style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT,
-		) as file_dialog:
-			if file_dialog.ShowModal() != wx.ID_OK:
-				return
-			destination_path = Path(file_dialog.GetPath())
-
-		try:
-			export_dictionary(self.dictionary_dir, selected_name, destination_path)
-		except OSError as exc:
-			self._show_file_error(_("Failed to export dictionary: {error}"), exc, parent=dialog_parent)
-
 	def _write_export_document(self, destination_path: Path, document: Document, format_key: str) -> None:
 		descriptor = get_format(format_key)
 		if not descriptor.exportable or descriptor.writer is None:
PATCH
```

- [ ] **Step 4: Run the tests.**

```bash
$PY -m unittest tests.test_dictionary_management_dialog tests.test_gui_document_flows -v 2>&1 | tail -3
$PY -m unittest tests.test_speech_symbols_dialog tests.test_wx_stub tests.test_dialog_display tests.test_dialog_validation tests.test_i18n 2>&1 | tail -3
```

Expected: `Ran 93 tests`, `OK`; `Ran 66 tests`, `OK`.

- [ ] **Step 5: Suite check.**

```bash
$T/tools/check_suite.sh 549 68
```

- [ ] **Step 6: Commit.**

```bash
git -C $REPO add client/dialog.py client/gui.py client/tests/test_dictionary_management_dialog.py client/tests/test_gui_document_flows.py client/tests/wx_stub.py
git -C $REPO commit -F - <<'MSG'
refactor: route dictionary management through presenter

DictionaryManagementDialog now takes (parent, actions, selected_name),
lists names only from the actions object and implements the presenter's
view protocol with the same wx calls as before. BrailleFrame builds the
presenter, wires the active dictionary to _set_active_dictionary and no
longer keeps its own name list or the five dialog callbacks.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
MSG
```

---

### Task 8: Remove the dead dictionary helpers from `gui.py`

**Files:**
- Modify: `client/tests/test_gui_document_flows.py` (`DictionaryManagementFrameTest.test_dictionary_dialog_helpers_and_imports_are_removed_from_gui`)
- Modify: `client/gui.py` (removes `_prompt_for_dictionary_name`, `CSV_WILDCARD`, `BrailleFrame._get_csv_wildcard`, and the imports that Task 7 left unused: `is_default_dictionary`, `create_dictionary`, `delete_dictionary`, `ensure_default_dictionary`, `export_dictionary`, `import_dictionary`, `list_dictionary_names`, `prompt_dictionary_name_until_success`, `rename_dictionary_after_name_prompt`, `plan_dictionary_state_after_add/_delete/_rename`, `resolve_management_selection`, `DictionaryNameDialog`). `dictionary_path_for_name`, `get_dictionary_directory`, `_get_selected_dictionary_path`, `_show_file_error`, `self.dictionary_dir` and the `N_("CSV files (*.csv)|*.csv")` marker stay. Behavior-neutral.

- [ ] **Step 1: Write the failing test.** Module attributes are checked on `gui`, the wildcard helper on the class (the stub frame makes every missing instance attribute look present); it also asserts the kept names are still there.

```bash
git -C $REPO apply <<'PATCH'
diff --git a/client/tests/test_gui_document_flows.py b/client/tests/test_gui_document_flows.py
index c74ad79..7cba126 100644
--- a/client/tests/test_gui_document_flows.py
+++ b/client/tests/test_gui_document_flows.py
@@ -1172,6 +1172,35 @@ class DictionaryManagementFrameTest(unittest.TestCase):
         self.assertTrue(hasattr(gui.BrailleFrame, "_set_active_dictionary"))
         self.assertTrue(hasattr(gui.BrailleFrame, "get_dictionary_names_for_dialog"))
 
+    def test_dictionary_dialog_helpers_and_imports_are_removed_from_gui(self) -> None:
+        for name in (
+            "_prompt_for_dictionary_name",
+            "CSV_WILDCARD",
+            "DictionaryNameDialog",
+            "create_dictionary",
+            "delete_dictionary",
+            "ensure_default_dictionary",
+            "export_dictionary",
+            "import_dictionary",
+            "is_default_dictionary",
+            "list_dictionary_names",
+            "plan_dictionary_state_after_add",
+            "plan_dictionary_state_after_delete",
+            "plan_dictionary_state_after_rename",
+            "prompt_dictionary_name_until_success",
+            "rename_dictionary_after_name_prompt",
+            "resolve_management_selection",
+        ):
+            with self.subTest(module_attribute=name):
+                self.assertFalse(hasattr(gui, name))
+        self.assertFalse(hasattr(gui.BrailleFrame, "_get_csv_wildcard"))
+        for name in ("dictionary_path_for_name", "get_dictionary_directory", "DictionaryManagementDialog", "SpeechSymbolsDialog"):
+            with self.subTest(kept=name):
+                self.assertTrue(hasattr(gui, name))
+        for name in ("_get_selected_dictionary_path", "_show_file_error"):
+            with self.subTest(kept=name):
+                self.assertTrue(hasattr(gui.BrailleFrame, name))
+
 
 if __name__ == "__main__":
     unittest.main()
PATCH
```

- [ ] **Step 2: Run it and see it fail.**

```bash
$PY -m unittest tests.test_gui_document_flows -v
```

Expected:

```
FAIL: test_dictionary_dialog_helpers_and_imports_are_removed_from_gui (tests.test_gui_document_flows.DictionaryManagementFrameTest.test_dictionary_dialog_helpers_and_imports_are_removed_from_gui) (module_attribute='_prompt_for_dictionary_name')
AssertionError: True is not false
FAIL: test_dictionary_dialog_helpers_and_imports_are_removed_from_gui (tests.test_gui_document_flows.DictionaryManagementFrameTest.test_dictionary_dialog_helpers_and_imports_are_removed_from_gui) (module_attribute='CSV_WILDCARD')
AssertionError: True is not false
FAIL: test_dictionary_dialog_helpers_and_imports_are_removed_from_gui (tests.test_gui_document_flows.DictionaryManagementFrameTest.test_dictionary_dialog_helpers_and_imports_are_removed_from_gui) (module_attribute='DictionaryNameDialog')
AssertionError: True is not false
FAIL: test_dictionary_dialog_helpers_and_imports_are_removed_from_gui (tests.test_gui_document_flows.DictionaryManagementFrameTest.test_dictionary_dialog_helpers_and_imports_are_removed_from_gui) (module_attribute='create_dictionary')
AssertionError: True is not false
FAIL: test_dictionary_dialog_helpers_and_imports_are_removed_from_gui (tests.test_gui_document_flows.DictionaryManagementFrameTest.test_dictionary_dialog_helpers_and_imports_are_removed_from_gui) (module_attribute='delete_dictionary')
AssertionError: True is not false
FAIL: test_dictionary_dialog_helpers_and_imports_are_removed_from_gui (tests.test_gui_document_flows.DictionaryManagementFrameTest.test_dictionary_dialog_helpers_and_imports_are_removed_from_gui) (module_attribute='ensure_default_dictionary')
AssertionError: True is not false
FAIL: test_dictionary_dialog_helpers_and_imports_are_removed_from_gui (tests.test_gui_document_flows.DictionaryManagementFrameTest.test_dictionary_dialog_helpers_and_imports_are_removed_from_gui) (module_attribute='export_dictionary')
AssertionError: True is not false
FAIL: test_dictionary_dialog_helpers_and_imports_are_removed_from_gui (tests.test_gui_document_flows.DictionaryManagementFrameTest.test_dictionary_dialog_helpers_and_imports_are_removed_from_gui) (module_attribute='import_dictionary')
AssertionError: True is not false
FAIL: test_dictionary_dialog_helpers_and_imports_are_removed_from_gui (tests.test_gui_document_flows.DictionaryManagementFrameTest.test_dictionary_dialog_helpers_and_imports_are_removed_from_gui) (module_attribute='is_default_dictionary')
AssertionError: True is not false
FAIL: test_dictionary_dialog_helpers_and_imports_are_removed_from_gui (tests.test_gui_document_flows.DictionaryManagementFrameTest.test_dictionary_dialog_helpers_and_imports_are_removed_from_gui) (module_attribute='list_dictionary_names')
AssertionError: True is not false
FAIL: test_dictionary_dialog_helpers_and_imports_are_removed_from_gui (tests.test_gui_document_flows.DictionaryManagementFrameTest.test_dictionary_dialog_helpers_and_imports_are_removed_from_gui) (module_attribute='plan_dictionary_state_after_add')
AssertionError: True is not false
FAIL: test_dictionary_dialog_helpers_and_imports_are_removed_from_gui (tests.test_gui_document_flows.DictionaryManagementFrameTest.test_dictionary_dialog_helpers_and_imports_are_removed_from_gui) (module_attribute='plan_dictionary_state_after_delete')
AssertionError: True is not false
FAIL: test_dictionary_dialog_helpers_and_imports_are_removed_from_gui (tests.test_gui_document_flows.DictionaryManagementFrameTest.test_dictionary_dialog_helpers_and_imports_are_removed_from_gui) (module_attribute='plan_dictionary_state_after_rename')
AssertionError: True is not false
FAIL: test_dictionary_dialog_helpers_and_imports_are_removed_from_gui (tests.test_gui_document_flows.DictionaryManagementFrameTest.test_dictionary_dialog_helpers_and_imports_are_removed_from_gui) (module_attribute='prompt_dictionary_name_until_success')
AssertionError: True is not false
FAIL: test_dictionary_dialog_helpers_and_imports_are_removed_from_gui (tests.test_gui_document_flows.DictionaryManagementFrameTest.test_dictionary_dialog_helpers_and_imports_are_removed_from_gui) (module_attribute='rename_dictionary_after_name_prompt')
AssertionError: True is not false
FAIL: test_dictionary_dialog_helpers_and_imports_are_removed_from_gui (tests.test_gui_document_flows.DictionaryManagementFrameTest.test_dictionary_dialog_helpers_and_imports_are_removed_from_gui) (module_attribute='resolve_management_selection')
AssertionError: True is not false
FAIL: test_dictionary_dialog_helpers_and_imports_are_removed_from_gui (tests.test_gui_document_flows.DictionaryManagementFrameTest.test_dictionary_dialog_helpers_and_imports_are_removed_from_gui)
AssertionError: True is not false
Ran 68 tests
FAILED (failures=17)
```

- [ ] **Step 3: Remove the helpers and imports.**

```bash
git -C $REPO apply <<'PATCH'
diff --git a/client/gui.py b/client/gui.py
index d535fa8..c59ddc6 100644
--- a/client/gui.py
+++ b/client/gui.py
@@ -24,18 +24,7 @@ from conversion.service import (
 	get_public_error_message,
 )
 from conversion.preprocessing.user_script import preprocessing_script_path
-from dictionaries.actions import is_default_dictionary
-from dictionaries.manager import (
-	create_dictionary,
-	delete_dictionary,
-	dictionary_path_for_name,
-	ensure_default_dictionary,
-	export_dictionary,
-	get_dictionary_directory,
-	import_dictionary,
-	list_dictionary_names,
-)
-from dictionaries.name_prompt import prompt_dictionary_name_until_success, rename_dictionary_after_name_prompt
+from dictionaries.manager import dictionary_path_for_name, get_dictionary_directory
 from dictionaries.presenter import DictionaryManagementPresenter
 from documents.controller import DocumentController
 from documents.formats import get_format
@@ -78,12 +67,6 @@ from settings.translation import (
 	save_translation_settings,
 )
 from settings.translation_tables import load_translation_tables, save_translation_tables
-from translation.dictionary_state import (
-	plan_dictionary_state_after_add,
-	plan_dictionary_state_after_delete,
-	plan_dictionary_state_after_rename,
-	resolve_management_selection,
-)
 from ui.font_support import SIMBRAILLE_FACE_NAME, get_simbraille_font_path, register_private_font_for_windows
 from ui.shortcuts import (
 	get_font_size_step_from_wheel,
@@ -112,7 +95,6 @@ from client_init import start_client_init_background
 
 from dialog import (
 	DictionaryManagementDialog,
-	DictionaryNameDialog,
 	DocumentNameDialog,
 	FileIssuesDialog,
 	InvalidWorkspaceFilesDialog,
@@ -139,7 +121,6 @@ VIEW_SCHEMES = {
 		"foreground": wx.Colour(255, 255, 255),
 	},
 }
-CSV_WILDCARD = "CSV files (*.csv)|*.csv"
 DEP_WILDCARD = "DotExpress files (*.dep)|*.dep"
 BRL_WILDCARD = "Braille files (*.brl)|*.brl"
 HTML_WILDCARD = "HTML files (*.html)|*.html"
@@ -199,14 +180,6 @@ _MENU_TRANSLATION_MARKERS = (
 )
 
 
-def _prompt_for_dictionary_name(parent: wx.Window | None, *, title: str, initial_name: str = "") -> str | None:
-	with DictionaryNameDialog(parent, initial_name=initial_name) as dialog:
-		dialog.SetTitle(title)
-		if dialog.ShowModal() != wx.ID_OK:
-			return None
-		return dialog.get_dictionary_name()
-
-
 class ConvertingDialog(wx.Dialog):
 	def __init__(self, parent: wx.Window):
 		style = (wx.DEFAULT_DIALOG_STYLE & ~wx.CLOSE_BOX) | wx.STAY_ON_TOP
@@ -606,9 +579,6 @@ class BrailleFrame(wx.Frame):
 	def _get_selected_dictionary_path(self) -> Path:
 		return dictionary_path_for_name(self.translation_settings.selected_dictionary, self.dictionary_dir)
 
-	def _get_csv_wildcard(self) -> str:
-		return _(CSV_WILDCARD)
-
 	def _show_file_error(self, message: str, error: Exception, parent: wx.Window | None = None) -> None:
 		wx.MessageBox(
 			message.format(error=error),
PATCH
```

- [ ] **Step 4: Run the tests.**

```bash
$PY -m unittest tests.test_gui_document_flows -v 2>&1 | tail -3
```

Expected: `Ran 68 tests`, `OK`.

- [ ] **Step 5: Suite check.**

```bash
$T/tools/check_suite.sh 550 69
```

- [ ] **Step 6: Commit.**

```bash
git -C $REPO add client/gui.py client/tests/test_gui_document_flows.py
git -C $REPO commit -F - <<'MSG'
refactor: remove dead dictionary helpers from gui

Drop _prompt_for_dictionary_name, the CSV wildcard helper and the imports
that only the old dictionary callbacks used.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
MSG
```

---

### Task 9: Final verification (spec acceptance criteria, no commit)

Each block starts with its own `cd`, so it can run in a fresh shell.

- [ ] **Criterion 1: presenter module, no `wx`.**

```bash
cd $REPO
grep -nE "^\s*(import|from) wx" client/dictionaries/presenter.py; echo "wx imports: $?"
grep -nE "^class " client/dictionaries/presenter.py
```

Expected: `wx imports: 1` (no line); `class DictionaryManagementView(Protocol):`, `class DictionaryManagementActions(Protocol):`, `class DictionaryManagementPresenter:`. (`PresenterModuleTest` checks the same with `ast`.)

- [ ] **Criterion 2: one name loop, one duplicate msgid** (correction 2).

```bash
cd $REPO
grep -rn "prompt_dictionary_name_until_success(" client --include=*.py | grep -v "/tests/" | grep -v "def prompt_dictionary_name_until_success("
grep -rnF 'Dictionary "{name}" already exists.' client --include=*.py | grep -v "/tests/"
```

Expected: exactly one line each, both in `client/dictionaries/presenter.py`.

- [ ] **Criterion 3: the old frame names are gone** (whole identifiers, correction 1).

```bash
cd $REPO
grep -nwE "_dictionary_names|_refresh_dictionary_names|add_dictionary|delete_dictionary_from_dialog|rename_dictionary_from_dialog|import_dictionary_from_dialog|export_dictionary_from_dialog|_prompt_for_dictionary_name|_get_csv_wildcard" client/gui.py; echo "matches: $?"
```

Expected: `matches: 1` (no line).

- [ ] **Criterion 4: dialog constructor and no directory listing.**

```bash
cd $REPO
$PY -I -c "import ast; t = ast.parse(open('client/dialog.py', encoding='utf-8').read()); c = next(n for n in t.body if isinstance(n, ast.ClassDef) and n.name == 'DictionaryManagementDialog'); f = next(n for n in c.body if isinstance(n, ast.FunctionDef) and n.name == '__init__'); print([a.arg for a in f.args.args])"
grep -n "list_dictionary_names" client/dialog.py; echo "matches: $?"
```

Expected: `['self', 'parent', 'actions', 'selected_name']`; `matches: 1`.

- [ ] **Criterion 5: msgids and catalogs unchanged.**

```bash
cd $REPO
$PY -I $T/tools/msgid_scan.py $REPO/client --compare $T/baseline_msgids.json
git -C $REPO diff --stat main...HEAD -- client/locales
```

Expected: `source msgids: 357`, `pot msgids: 357`, `SOURCE == POT`, `SOURCE == SAVED`; no output from `git diff`.

- [ ] **Criterion 6: the roadmap command.**

```bash
cd $REPO/client
$PY -m unittest tests.test_dictionary_presenter tests.test_dictionary_management_dialog tests.test_dictionary_manager tests.test_dictionary_actions tests.test_translation_dictionary_state tests.test_dictionary_name_prompt tests.test_gui_document_flows -v 2>&1 | tail -3
$PY -m unittest tests.test_dictionary_entries tests.test_speech_symbols_dialog tests.test_settings_dialogs tests.test_i18n tests.test_wx_stub 2>&1 | tail -3
```

Expected: `Ran 164 tests`, `OK` (43 + 26 + 11 + 6 + 6 + 4 + 68); safety net `Ran 88 tests`, `OK`.

- [ ] **Criterion 7: the full suite.**

```bash
cd $REPO/client
$T/tools/check_suite.sh 550 69
```

Expected: `Ran 550 tests` (482 + 68 new), `FAILED (failures=1, skipped=7)`, only the P2-5 `FAIL:` line, `BASELINE-TESTS-IDENTICAL`, `RAN-COUNT-OK (550)`, `new tests ok: 69 (expected 69)`.

- [ ] **Scope check.**

```bash
cd $REPO
git diff --name-only main...HEAD
git log --oneline main..HEAD
```

Expected files: the spec pair (`docs/superpowers/specs/2026-10-08-p0-6-dictionary-presenter-design.md`, `..._zh-TW.md`), this plan, and exactly `client/dialog.py`, `client/dictionaries/presenter.py`, `client/gui.py`, `client/tests/test_dictionary_management_dialog.py`, `client/tests/test_dictionary_presenter.py`, `client/tests/test_gui_document_flows.py`, `client/tests/wx_stub.py`. Commits: the docs commits, then the 8 commits of Tasks 1-8 in order.

- [ ] **Criterion 8: Windows manual check: NOT RUN on the Linux box.** Report it as not run. On Windows: open Dictionary Management and walk through add (including a duplicate name), rename (active and non-active; a case-only rename shows the duplicate box there, as today), delete (active and non-active, then check Settings shows the fallback), import (valid file, file without headers), export, and edit. Each prompt, message, caption, button set and list selection must match the current build. wxPython is not installed here, so no real dialog was exercised.

## Appendix: `$T/tools/check_suite.sh`

```bash
#!/bin/bash
# Throwaway (P0-6). usage: check_suite.sh <expected Ran count> <expected new-test ok count>   (run from client/)
SP=/tmp/claude-0/-workspace-DotExpress/c0b338ab-efa4-4037-b0f9-1b4ce4e6c150/scratchpad
T=${T:-$SP/p06impl}
PY=$SP/venv/bin/python
NEW='\(test_dictionary_presenter\.|DictionaryManagementActionsWiringTest|DictionaryManagementViewTest|DictionaryManagementFrameTest|test_refresh_after_action_takes_names_from_actions_not_disk'
REPLACED='test_disk_refresh_discovers_new_dictionary_files'
$PY -m unittest discover -s tests -v > $T/run.txt 2>&1
grep -E '^Ran|^FAILED|^OK' $T/run.txt | sed -E 's/ in [0-9.]+s$//'
grep -E '^(FAIL|ERROR):' $T/run.txt
diff <(grep ' \.\.\. ' $T/run.txt | grep -vE "$NEW|$REPLACED" | sort) <(grep -vE "$NEW|$REPLACED" $T/baseline_discover_verbose.txt) && echo "BASELINE-TESTS-IDENTICAL"
grep -q "^Ran $1 tests" $T/run.txt && echo "RAN-COUNT-OK ($1)" || echo "RAN-COUNT-MISMATCH (expected $1)"
echo "new tests ok: $(grep ' \.\.\. ' $T/run.txt | grep -E "$NEW" | grep -c '\.\.\. ok$') (expected $2)"
```
