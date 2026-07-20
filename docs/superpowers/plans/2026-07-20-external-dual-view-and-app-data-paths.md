# External Dual View and Unified Application Data Paths Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Open dual-view HTML in a size-targeted external browser window and resolve every DotExpress-managed writable file from one application root.

**Architecture:** Add a side-effect-free `app_paths` module that owns application-root resolution, managed paths, directory creation, and writability validation. Add focused dual-view modules for owned HTML-file lifecycle and browser discovery/launching, then adapt GUI startup, shutdown, and the existing menu handler while preserving the embedded wx.html viewer code.

**Tech Stack:** Python 3, wxPython, `pathlib`, `tempfile`, `logging`, `subprocess`, `shutil`, `os.startfile`, `uuid`, `unittest`, `unittest.mock`, gettext (`xgettext`, `msgmerge`, `msgfmt`).

## Global Constraints

- Packaged application root is `Path(sys.executable).resolve().parent`, the directory containing `DotExpress.exe`.
- Development application root is `client/`.
- Managed writable paths are exactly `<application-root>/config.json`, `dictionary/`, `workspace/`, `log/`, and `dual_view/`.
- Do not read, preserve, migrate, or delete the old `~/.DotExpress/config.json`.
- Do not move user-selected import sources or export destinations under the application root.
- Validate the application root and every managed directory by creating and removing a probe file; if `config.json` exists, also open that exact file in append mode without changing its content. Complete validation before creating the translation runtime or main frame.
- Do not silently fall back to the user home directory or another hidden location when application data is not writable.
- Logger construction during module import must not create `log/` or open a log file.
- Browser order is Chrome → Microsoft Edge → Firefox → Windows `os.startfile()`.
- Requested browser dimensions equal the current wx main-window `GetSize()`; exact external geometry is not guaranteed.
- Only files matching `dual-view-*.html` inside `dual_view/` may be automatically removed.
- Keep `DualViewFrame`, `wx.html2.WebView`, `_show_dual_view()`, and existing embedded-viewer tests.
- Keep English gettext source strings, `client/locales/dotexpress.pot`, Traditional Chinese PO, and compiled MO synchronized.
- Follow TDD: add a failing focused test before each production change.
- Do not edit generated liblouis runtime files.

---

### Task 1: Define the application-root and managed-path contract

**Files:**
- Create: `client/app_paths.py`
- Create: `client/tests/test_app_paths.py`

**Interfaces:**
- Produces: `ApplicationPaths(root, config, dictionary, workspace, log, dual_view)`.
- Produces: `ApplicationDataError(path: Path, cause: OSError)` with public `path` and `cause` attributes.
- Produces: `get_application_root() -> Path`.
- Produces: `build_application_paths(root: Path | None = None) -> ApplicationPaths`.
- Produces: `get_config_path()`, `get_dictionary_directory()`, `get_workspace_directory()`, `get_log_directory()`, and `get_dual_view_directory()`, each with an optional direct-path override for existing tests and callers.
- Produces: `prepare_application_directories(paths: ApplicationPaths | None = None, *, probe_factory=tempfile.TemporaryFile) -> ApplicationPaths`.

- [ ] **Step 1: Write failing application-path resolution tests**

Create `client/tests/test_app_paths.py` with these initial tests:

```python
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

import app_paths


class ApplicationPathsTest(unittest.TestCase):
    def test_development_root_is_client_directory(self) -> None:
        with patch.object(app_paths.sys, "frozen", False, create=True):
            root = app_paths.get_application_root()

        self.assertEqual(root, Path(app_paths.__file__).resolve().parent)

    def test_frozen_root_is_executable_parent(self) -> None:
        executable = Path("C:/Portable/DotExpress/DotExpress.exe")
        with (
            patch.object(app_paths.sys, "frozen", True, create=True),
            patch.object(app_paths.sys, "executable", str(executable)),
        ):
            root = app_paths.get_application_root()

        self.assertEqual(root, executable.resolve().parent)

    def test_build_application_paths_uses_one_root(self) -> None:
        root = Path("C:/DotExpress")

        paths = app_paths.build_application_paths(root)

        self.assertEqual(paths.root, root)
        self.assertEqual(paths.config, root / "config.json")
        self.assertEqual(paths.dictionary, root / "dictionary")
        self.assertEqual(paths.workspace, root / "workspace")
        self.assertEqual(paths.log, root / "log")
        self.assertEqual(paths.dual_view, root / "dual_view")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the path tests and verify they fail**

Run:

```bash
cd client
python3 -m unittest tests.test_app_paths -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'app_paths'`.

- [ ] **Step 3: Implement the path value object and resolution helpers**

Create `client/app_paths.py`:

```python
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sys
import tempfile
from collections.abc import Callable
from typing import BinaryIO


@dataclass(frozen=True)
class ApplicationPaths:
    root: Path
    config: Path
    dictionary: Path
    workspace: Path
    log: Path
    dual_view: Path

    @property
    def writable_directories(self) -> tuple[Path, ...]:
        return (self.root, self.dictionary, self.workspace, self.log, self.dual_view)


class ApplicationDataError(OSError):
    def __init__(self, path: Path, cause: OSError):
        self.path = Path(path)
        self.cause = cause
        super().__init__(f'Cannot write to "{self.path}": {cause}')


def get_application_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def build_application_paths(root: Path | None = None) -> ApplicationPaths:
    application_root = Path(root) if root is not None else get_application_root()
    return ApplicationPaths(
        root=application_root,
        config=application_root / "config.json",
        dictionary=application_root / "dictionary",
        workspace=application_root / "workspace",
        log=application_root / "log",
        dual_view=application_root / "dual_view",
    )


def get_config_path(path: Path | None = None) -> Path:
    return Path(path) if path is not None else build_application_paths().config


def get_dictionary_directory(path: Path | None = None) -> Path:
    return Path(path) if path is not None else build_application_paths().dictionary


def get_workspace_directory(path: Path | None = None) -> Path:
    return Path(path) if path is not None else build_application_paths().workspace


def get_log_directory(path: Path | None = None) -> Path:
    return Path(path) if path is not None else build_application_paths().log


def get_dual_view_directory(path: Path | None = None) -> Path:
    return Path(path) if path is not None else build_application_paths().dual_view
```

- [ ] **Step 4: Add failing directory preparation and error-path tests**

Append to `ApplicationPathsTest`:

```python
    def test_prepare_creates_and_probes_every_writable_directory(self) -> None:
        from tempfile import TemporaryDirectory

        with TemporaryDirectory() as directory:
            root = Path(directory) / "application"
            paths = app_paths.build_application_paths(root)
            probed: list[Path] = []

            class Probe:
                def __init__(self, path: Path):
                    self.path = path

                def __enter__(self):
                    probed.append(self.path)
                    return self

                def __exit__(self, exc_type, exc, traceback):
                    return False

            prepared = app_paths.prepare_application_directories(
                paths,
                probe_factory=lambda *, dir: Probe(Path(dir)),
            )

            self.assertEqual(prepared, paths)
            self.assertEqual(probed, list(paths.writable_directories))
            self.assertTrue(all(path.is_dir() for path in paths.writable_directories))

    def test_prepare_reports_the_exact_unwritable_directory(self) -> None:
        from tempfile import TemporaryDirectory

        with TemporaryDirectory() as directory:
            paths = app_paths.build_application_paths(Path(directory))

            class Probe:
                def __init__(self, path: Path):
                    self.path = path

                def __enter__(self):
                    if self.path == paths.log:
                        raise PermissionError("denied")
                    return self

                def __exit__(self, exc_type, exc, traceback):
                    return False

            with self.assertRaises(app_paths.ApplicationDataError) as raised:
                app_paths.prepare_application_directories(
                    paths,
                    probe_factory=lambda *, dir: Probe(Path(dir)),
                )

        self.assertEqual(raised.exception.path, paths.log)
        self.assertIsInstance(raised.exception.cause, PermissionError)

    def test_prepare_reports_an_existing_unwritable_config_file(self) -> None:
        from tempfile import TemporaryDirectory
        from unittest.mock import patch

        with TemporaryDirectory() as directory:
            paths = app_paths.build_application_paths(Path(directory))
            paths.config.write_text("{}", encoding="utf-8")
            with patch.object(Path, "open", side_effect=PermissionError("read only")):
                with self.assertRaises(app_paths.ApplicationDataError) as raised:
                    app_paths.prepare_application_directories(paths)

        self.assertEqual(raised.exception.path, paths.config)
        self.assertIsInstance(raised.exception.cause, PermissionError)
```

- [ ] **Step 5: Run the new tests and verify preparation is missing**

Run:

```bash
cd client
python3 -m unittest tests.test_app_paths -v
```

Expected: resolution tests PASS; preparation tests FAIL because `prepare_application_directories` is not defined.

- [ ] **Step 6: Implement directory creation and per-directory write probes**

Append to `client/app_paths.py`:

```python
def prepare_application_directories(
    paths: ApplicationPaths | None = None,
    *,
    probe_factory: Callable[..., BinaryIO] = tempfile.TemporaryFile,
) -> ApplicationPaths:
    managed_paths = paths or build_application_paths()
    for directory in managed_paths.writable_directories:
        try:
            directory.mkdir(parents=True, exist_ok=True)
            with probe_factory(dir=directory):
                pass
        except OSError as error:
            raise ApplicationDataError(directory, error) from error
    if managed_paths.config.exists():
        try:
            with managed_paths.config.open("a", encoding="utf-8"):
                pass
        except OSError as error:
            raise ApplicationDataError(managed_paths.config, error) from error
    return managed_paths
```

- [ ] **Step 7: Run focused tests and commit the path contract**

Run:

```bash
cd client
python3 -m unittest tests.test_app_paths -v
```

Expected: all tests PASS.

Commit during implementation execution:

```bash
git add client/app_paths.py client/tests/test_app_paths.py
git commit -m "refactor: centralize application data paths"
```

---

### Task 2: Route config, dictionaries, workspace, and logs through the application root

**Files:**
- Modify: `client/config.py:1-10`
- Modify: `client/dictionaries/manager.py:1-24`
- Modify: `client/documents/workspace.py:1-50`
- Modify: `client/log.py:1-25`
- Modify: `client/adapters/translation/provider.py:13`
- Modify: `client/conversion/math_service.py:10`
- Modify: `client/client_init.py:17`
- Modify: `client/ui/dual_view.py:13`
- Modify: `client/tests/test_app_paths.py`
- Create: `client/tests/test_log.py`

**Interfaces:**
- Consumes: Task 1 path getters.
- Preserves: `config.CONFIG_PATH` as a patchable string for existing tests.
- Preserves: `dictionaries.manager.get_dictionary_directory(path=None)` and `documents.workspace.get_workspace_directory(path=None)` as importable names.
- Produces: `get_logger(name: str, filename: str = "init.log", level: int = logging.ERROR) -> logging.Logger` with a delayed absolute file handler under `<application-root>/log/`.

- [ ] **Step 1: Add failing default-location tests**

Append to `client/tests/test_app_paths.py`:

```python
    def test_consumers_use_the_common_application_root(self) -> None:
        import config
        import dictionaries.manager as dictionary_manager
        import documents.workspace as document_workspace

        paths = app_paths.build_application_paths()

        self.assertEqual(Path(config.CONFIG_PATH), paths.config)
        self.assertEqual(dictionary_manager.get_dictionary_directory(), paths.dictionary)
        self.assertEqual(document_workspace.get_workspace_directory(), paths.workspace)
```

Create `client/tests/test_log.py`:

```python
import logging
import tempfile
import unittest
from pathlib import Path
from uuid import uuid4
from unittest.mock import patch

import log


class FileLoggerTest(unittest.TestCase):
    def test_logger_defers_file_creation_and_uses_application_log_directory(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            log_dir = Path(directory) / "log"
            logger_name = f"dotexpress.test.{uuid4().hex}"
            with patch.object(log, "get_log_directory", return_value=log_dir):
                logger = log.get_logger(logger_name, "sample.log")

            handler = next(item for item in logger.handlers if isinstance(item, logging.FileHandler))
            self.assertEqual(Path(handler.baseFilename), log_dir / "sample.log")
            self.assertIsNone(handler.stream)
            self.assertFalse(log_dir.exists())

            log_dir.mkdir()
            logger.error("written after validation")
            self.assertTrue((log_dir / "sample.log").is_file())

            handler.close()
            logger.removeHandler(handler)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the focused tests and verify old locations/eager logging fail**

Run:

```bash
cd client
python3 -m unittest tests.test_app_paths tests.test_log -v
```

Expected: FAIL because config still points to the home directory, workspace uses `client/documents/`, and `get_logger` creates `log/` eagerly.

- [ ] **Step 3: Replace duplicate path resolution with shared getters**

Apply these production changes:

```python
# client/config.py
import json
import os
from typing import Optional
from uuid import uuid4

from app_paths import get_config_path

CONFIG_PATH = str(get_config_path())
```

Keep the remainder of `config.py` unchanged, including its test-patchable `CONFIG_PATH` access.

```python
# client/dictionaries/manager.py imports
import csv
from pathlib import Path
import shutil

from app_paths import get_dictionary_directory
from shared.name_validation import MAX_NAME_LENGTH, normalize_base_name
```

Delete the local `get_application_directory()` and `get_dictionary_directory()` definitions. The imported getter remains available as `dictionaries.manager.get_dictionary_directory`.

```python
# client/documents/workspace.py imports
from dataclasses import dataclass
import json
from pathlib import Path
import zipfile
from collections.abc import Callable

from app_paths import get_workspace_directory
```

Delete the local `get_application_directory()` and `get_workspace_directory()` definitions. The imported getter remains available as `documents.workspace.get_workspace_directory`.

- [ ] **Step 4: Implement delayed application-root logging**

Replace `client/log.py` with:

```python
import logging
from pathlib import Path

from app_paths import get_log_directory


def get_logger(
    name: str,
    filename: str = "init.log",
    level: int = logging.ERROR,
) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(level)

    if not logger.handlers:
        file_handler = logging.FileHandler(
            get_log_directory() / Path(filename).name,
            encoding="utf-8",
            delay=True,
        )
        file_handler.setLevel(level)
        file_handler.setFormatter(
            logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
        )
        logger.addHandler(file_handler)
        logger.propagate = False

    return logger
```

Update all logger registrations to pass filenames rather than paths:

```python
# client/adapters/translation/provider.py
logger = get_logger("dotexpress.translation", "translation.log", level=logging.WARNING)

# client/conversion/math_service.py
logger = get_logger("dotexpress.math", "math.log")

# client/client_init.py
logger = get_logger("dotexpress.client_init", "init.log")

# client/ui/dual_view.py
logger = get_logger("dotexpress.dual_view", "dual_view.log", level=logging.DEBUG)
```

- [ ] **Step 5: Run path, logger, config, dictionary, and workspace tests**

Run:

```bash
cd client
python3 -m unittest \
  tests.test_app_paths \
  tests.test_log \
  tests.test_config \
  tests.test_dictionary_manager \
  tests.test_document_workspace -v
```

Expected: all tests PASS. Existing tests that override `CONFIG_PATH`, dictionary directories, or workspace directories continue to pass.

- [ ] **Step 6: Commit the consumer migration**

```bash
git add \
  client/app_paths.py \
  client/config.py \
  client/log.py \
  client/dictionaries/manager.py \
  client/documents/workspace.py \
  client/adapters/translation/provider.py \
  client/conversion/math_service.py \
  client/client_init.py \
  client/ui/dual_view.py \
  client/tests/test_app_paths.py \
  client/tests/test_log.py
git commit -m "refactor: unify managed file locations"
```

---

### Task 3: Stop startup clearly when application data is not writable

**Files:**
- Modify: `client/gui.py:1-125,1759-1769`
- Modify: `client/tests/test_gui_document_flows.py:453-503`

**Interfaces:**
- Consumes: `prepare_application_directories()` and `ApplicationDataError` from Task 1.
- Produces: `BrailleApp.OnInit() -> bool` that validates paths before building the translation runtime or frame.
- Preserves: `BrailleApp.OnExit() -> int`, safely handling an `OnInit` failure where no runtime exists.

- [ ] **Step 1: Add failing startup validation tests**

Add these methods to `BrailleAppLifecycleTest` in `client/tests/test_gui_document_flows.py` and update the existing success test to patch `prepare_application_directories`:

```python
    def test_app_validates_application_data_before_building_runtime(self) -> None:
        runtime = Mock()
        frame = Mock()
        order: list[str] = []

        with (
            patch.object(gui, "prepare_application_directories", side_effect=lambda: order.append("paths")),
            patch.object(gui, "build_default_translation_runtime", side_effect=lambda: (order.append("runtime"), runtime)[1]),
            patch.object(gui, "BrailleFrame", side_effect=lambda *args, **kwargs: (order.append("frame"), frame)[1]),
            patch.object(gui, "start_client_init_background"),
        ):
            app = gui.BrailleApp()
            result = app.OnInit()

        self.assertTrue(result)
        self.assertEqual(order, ["paths", "runtime", "frame"])

    def test_app_reports_unwritable_path_and_stops_before_runtime(self) -> None:
        error = gui.ApplicationDataError(Path("C:/Program Files/DotExpress/log"), PermissionError("denied"))

        with (
            patch.object(gui, "prepare_application_directories", side_effect=error),
            patch.object(gui, "build_default_translation_runtime") as build_runtime,
            patch.object(gui, "BrailleFrame") as frame_class,
            patch.object(gui.wx, "MessageBox") as message_box,
        ):
            app = gui.BrailleApp()
            result = app.OnInit()

        self.assertFalse(result)
        build_runtime.assert_not_called()
        frame_class.assert_not_called()
        message_box.assert_called_once_with(
            gui._(
                "DotExpress cannot write to its application data directory:\n"
                "{path}\n\nChoose a writable installation or execution location.\n\n{error}"
            ).format(path=error.path, error=error.cause),
            gui._("Startup Error"),
            gui.wx.OK | gui.wx.ICON_ERROR,
        )

    def test_app_exit_without_initialized_runtime_is_safe(self) -> None:
        app = gui.BrailleApp()

        self.assertEqual(app.OnExit(), 0)
```

In `test_app_builds_runtime_and_passes_it_to_frame`, add:

```python
patch.object(gui, "prepare_application_directories"),
```

- [ ] **Step 2: Run the lifecycle tests and verify validation is absent**

Run:

```bash
cd client
python3 -m unittest tests.test_gui_document_flows.BrailleAppLifecycleTest -v
```

Expected: new tests FAIL because `gui.prepare_application_directories` and `gui.ApplicationDataError` are not imported and startup builds the runtime immediately.

- [ ] **Step 3: Implement validation-first startup and safe exit**

Add the import in `client/gui.py`:

```python
from app_paths import ApplicationDataError, prepare_application_directories
```

Add one startup-error presenter and replace `BrailleApp` lifecycle methods with:

```python
def _show_application_data_error(error: ApplicationDataError) -> None:
    wx.MessageBox(
        _(
            "DotExpress cannot write to its application data directory:\n"
            "{path}\n\nChoose a writable installation or execution location.\n\n{error}"
        ).format(path=error.path, error=error.cause),
        _("Startup Error"),
        wx.OK | wx.ICON_ERROR,
    )


class BrailleApp(wx.App):
    def OnInit(self):
        try:
            prepare_application_directories()
        except ApplicationDataError as error:
            _show_application_data_error(error)
            return False

        self.translation_runtime = build_default_translation_runtime()
        self.frame = BrailleFrame(None, runtime=self.translation_runtime)
        self.frame.Show()
        start_client_init_background()
        return True

    def OnExit(self):
        runtime = getattr(self, "translation_runtime", None)
        if runtime is not None:
            runtime.close()
        return 0
```

Use the repository’s existing tab indentation when applying this code to `gui.py`.

- [ ] **Step 4: Run lifecycle and import-time logging tests**

Run:

```bash
cd client
python3 -m unittest \
  tests.test_gui_document_flows.BrailleAppLifecycleTest \
  tests.test_log -v
```

Expected: all tests PASS; logger tests prove imports do not create a file before validation.

- [ ] **Step 5: Commit startup validation**

```bash
git add client/gui.py client/tests/test_gui_document_flows.py
git commit -m "fix: reject unwritable application data root"
```

---

### Task 4: Manage owned dual-view HTML files

**Files:**
- Create: `client/dual_view/files.py`
- Create: `client/tests/test_dual_view_files.py`

**Interfaces:**
- Consumes: `get_dual_view_directory(path=None)` from Task 1.
- Produces: `write_dual_view_html(content: str, directory: Path | None = None, *, token_factory: Callable[[], str] = _new_token) -> Path`.
- Produces: `cleanup_dual_view_html(directory: Path | None = None) -> None`.
- Owns only filenames matching `dual-view-*.html`.

- [ ] **Step 1: Write failing owned-file creation and cleanup tests**

Create `client/tests/test_dual_view_files.py`:

```python
import tempfile
import unittest
from pathlib import Path

from dual_view.files import cleanup_dual_view_html, write_dual_view_html


class DualViewFilesTest(unittest.TestCase):
    def test_write_creates_unique_utf8_owned_html(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "dual_view"
            tokens = iter(("first", "second"))

            first = write_dual_view_html("雙視一", target, token_factory=lambda: next(tokens))
            second = write_dual_view_html("雙視二", target, token_factory=lambda: next(tokens))

            self.assertEqual(first, target / "dual-view-first.html")
            self.assertEqual(second, target / "dual-view-second.html")
            self.assertEqual(first.read_text(encoding="utf-8"), "雙視一")
            self.assertEqual(second.read_text(encoding="utf-8"), "雙視二")

    def test_cleanup_removes_only_owned_html_files(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "dual_view"
            target.mkdir()
            owned = target / "dual-view-stale.html"
            unrelated_html = target / "notes.html"
            unrelated_file = target / "dual-view-not-html.txt"
            owned.write_text("old", encoding="utf-8")
            unrelated_html.write_text("keep", encoding="utf-8")
            unrelated_file.write_text("keep", encoding="utf-8")

            cleanup_dual_view_html(target)

            self.assertFalse(owned.exists())
            self.assertTrue(unrelated_html.exists())
            self.assertTrue(unrelated_file.exists())

    def test_cleanup_accepts_a_missing_directory(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            cleanup_dual_view_html(Path(directory) / "missing")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the file tests and verify the module is missing**

Run:

```bash
cd client
python3 -m unittest tests.test_dual_view_files -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'dual_view.files'`.

- [ ] **Step 3: Implement UTF-8 creation and narrowly scoped cleanup**

Create `client/dual_view/files.py`:

```python
from __future__ import annotations

from pathlib import Path
from uuid import uuid4
from collections.abc import Callable

from app_paths import get_dual_view_directory


OWNED_HTML_PATTERN = "dual-view-*.html"


def _new_token() -> str:
    return uuid4().hex


def write_dual_view_html(
    content: str,
    directory: Path | None = None,
    *,
    token_factory: Callable[[], str] = _new_token,
) -> Path:
    target_directory = get_dual_view_directory(directory)
    target_directory.mkdir(parents=True, exist_ok=True)
    target = target_directory / f"dual-view-{token_factory()}.html"
    target.write_text(content, encoding="utf-8")
    return target


def cleanup_dual_view_html(directory: Path | None = None) -> None:
    target_directory = get_dual_view_directory(directory)
    if not target_directory.exists():
        return
    for path in target_directory.glob(OWNED_HTML_PATTERN):
        if path.is_file():
            path.unlink()
```

- [ ] **Step 4: Run the focused file tests and commit**

Run:

```bash
cd client
python3 -m unittest tests.test_dual_view_files -v
```

Expected: all tests PASS.

Commit during implementation execution:

```bash
git add client/dual_view/files.py client/tests/test_dual_view_files.py
git commit -m "feat: manage dual-view html files"
```

---

### Task 5: Discover and launch external browsers in fixed order

**Files:**
- Create: `client/dual_view/browser.py`
- Create: `client/tests/test_dual_view_browser.py`

**Interfaces:**
- Produces: `find_browser_executable(browser: str, *, which=shutil.which, environ=os.environ) -> Path | None`.
- Produces: `build_browser_command(browser: str, executable: Path, html_path: Path, window_size: tuple[int, int]) -> list[str]`.
- Produces: `open_html_in_browser(html_path: Path, window_size: tuple[int, int], *, finder=find_browser_executable, popen=subprocess.Popen, startfile=_DEFAULT_STARTFILE) -> str` returning `chrome`, `edge`, `firefox`, or `system`.
- Raises: `OSError` when no browser can be launched and no usable `os.startfile` fallback exists, or when the fallback itself fails.

- [ ] **Step 1: Write failing command construction tests**

Create `client/tests/test_dual_view_browser.py`:

```python
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, call

from dual_view.browser import build_browser_command, find_browser_executable, open_html_in_browser


class DualViewBrowserTest(unittest.TestCase):
    def test_chromium_commands_request_new_window_and_size(self) -> None:
        html_path = Path("C:/DotExpress/dual_view/dual-view-one.html")

        chrome = build_browser_command("chrome", Path("C:/Chrome/chrome.exe"), html_path, (900, 600))
        edge = build_browser_command("edge", Path("C:/Edge/msedge.exe"), html_path, (900, 600))

        self.assertEqual(chrome[:3], ["C:/Chrome/chrome.exe", "--new-window", "--window-size=900,600"])
        self.assertEqual(edge[:3], ["C:/Edge/msedge.exe", "--new-window", "--window-size=900,600"])
        self.assertTrue(chrome[-1].startswith("file:"))
        self.assertTrue(edge[-1].startswith("file:"))

    def test_firefox_command_requests_new_window_and_size(self) -> None:
        command = build_browser_command(
            "firefox",
            Path("C:/Firefox/firefox.exe"),
            Path("C:/DotExpress/dual_view/dual-view-one.html"),
            (1024, 768),
        )

        self.assertEqual(command[0:2], ["C:/Firefox/firefox.exe", "-new-window"])
        self.assertIn("file:", command[2])
        self.assertEqual(command[3:], ["-width", "1024", "-height", "768"])
```

- [ ] **Step 2: Run command tests and verify the module is missing**

Run:

```bash
cd client
python3 -m unittest tests.test_dual_view_browser -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'dual_view.browser'`.

- [ ] **Step 3: Implement browser definitions, discovery, and exact commands**

Create `client/dual_view/browser.py`:

```python
from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import shutil
import subprocess
from collections.abc import Callable, Mapping


@dataclass(frozen=True)
class BrowserDefinition:
    executable_names: tuple[str, ...]
    installed_paths: tuple[tuple[str, tuple[str, ...]], ...]


BROWSER_ORDER = ("chrome", "edge", "firefox")
_DEFAULT_STARTFILE = object()
BROWSERS = {
    "chrome": BrowserDefinition(
        executable_names=("chrome.exe", "chrome"),
        installed_paths=(
            ("LOCALAPPDATA", ("Google", "Chrome", "Application", "chrome.exe")),
            ("PROGRAMFILES", ("Google", "Chrome", "Application", "chrome.exe")),
            ("PROGRAMFILES(X86)", ("Google", "Chrome", "Application", "chrome.exe")),
        ),
    ),
    "edge": BrowserDefinition(
        executable_names=("msedge.exe", "msedge"),
        installed_paths=(
            ("LOCALAPPDATA", ("Microsoft", "Edge", "Application", "msedge.exe")),
            ("PROGRAMFILES", ("Microsoft", "Edge", "Application", "msedge.exe")),
            ("PROGRAMFILES(X86)", ("Microsoft", "Edge", "Application", "msedge.exe")),
        ),
    ),
    "firefox": BrowserDefinition(
        executable_names=("firefox.exe", "firefox"),
        installed_paths=(
            ("LOCALAPPDATA", ("Mozilla Firefox", "firefox.exe")),
            ("PROGRAMFILES", ("Mozilla Firefox", "firefox.exe")),
            ("PROGRAMFILES(X86)", ("Mozilla Firefox", "firefox.exe")),
        ),
    ),
}


def find_browser_executable(
    browser: str,
    *,
    which: Callable[[str], str | None] = shutil.which,
    environ: Mapping[str, str] = os.environ,
) -> Path | None:
    definition = BROWSERS[browser]
    for executable_name in definition.executable_names:
        located = which(executable_name)
        if located:
            return Path(located)
    for environment_name, relative_parts in definition.installed_paths:
        base = environ.get(environment_name)
        if not base:
            continue
        candidate = Path(base).joinpath(*relative_parts)
        if candidate.is_file():
            return candidate
    return None


def build_browser_command(
    browser: str,
    executable: Path,
    html_path: Path,
    window_size: tuple[int, int],
) -> list[str]:
    width, height = window_size
    uri = html_path.resolve().as_uri()
    if browser in ("chrome", "edge"):
        return [str(executable), "--new-window", f"--window-size={width},{height}", uri]
    if browser == "firefox":
        return [str(executable), "-new-window", uri, "-width", str(width), "-height", str(height)]
    raise ValueError(f'Unsupported browser: "{browser}"')
```

- [ ] **Step 4: Add failing discovery and fallback-order tests**

Append to `DualViewBrowserTest`:

```python
    def test_discovery_prefers_path_before_standard_install_location(self) -> None:
        which = Mock(side_effect=lambda name: "C:/Path/chrome.exe" if name == "chrome.exe" else None)

        found = find_browser_executable(
            "chrome",
            which=which,
            environ={"LOCALAPPDATA": "C:/Users/me/AppData/Local"},
        )

        self.assertEqual(found, Path("C:/Path/chrome.exe"))
        self.assertEqual(which.call_args_list, [call("chrome.exe")])

    def test_discovery_uses_standard_install_location_when_path_misses(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            program_files = Path(directory) / "Program Files"
            executable = program_files / "Microsoft" / "Edge" / "Application" / "msedge.exe"
            executable.parent.mkdir(parents=True)
            executable.write_bytes(b"")

            found = find_browser_executable(
                "edge",
                which=Mock(return_value=None),
                environ={"PROGRAMFILES": str(program_files)},
            )

        self.assertEqual(found, executable)

    def test_launch_falls_through_chrome_edge_firefox_then_system(self) -> None:
        finder = Mock(side_effect=lambda browser: {
            "chrome": Path("C:/Chrome/chrome.exe"),
            "edge": Path("C:/Edge/msedge.exe"),
            "firefox": None,
        }[browser])
        popen = Mock(side_effect=[OSError("chrome failed"), OSError("edge failed")])
        startfile = Mock()
        html_path = Path("C:/DotExpress/dual_view/dual-view-one.html")

        result = open_html_in_browser(
            html_path,
            (900, 600),
            finder=finder,
            popen=popen,
            startfile=startfile,
        )

        self.assertEqual(result, "system")
        self.assertEqual(finder.call_args_list, [call("chrome"), call("edge"), call("firefox")])
        self.assertEqual(popen.call_count, 2)
        startfile.assert_called_once_with(str(html_path.resolve()))

    def test_launch_stops_after_first_successful_process_creation(self) -> None:
        finder = Mock(return_value=Path("C:/Chrome/chrome.exe"))
        popen = Mock()
        startfile = Mock()

        result = open_html_in_browser(
            Path("C:/DotExpress/dual_view/dual-view-one.html"),
            (900, 600),
            finder=finder,
            popen=popen,
            startfile=startfile,
        )

        self.assertEqual(result, "chrome")
        finder.assert_called_once_with("chrome")
        popen.assert_called_once()
        startfile.assert_not_called()

    def test_missing_non_windows_fallback_raises_os_error(self) -> None:
        with self.assertRaisesRegex(OSError, "No supported browser"):
            open_html_in_browser(
                Path("/tmp/dual-view-one.html"),
                (900, 600),
                finder=lambda _browser: None,
                startfile=None,
            )

    def test_system_fallback_error_is_propagated(self) -> None:
        startfile = Mock(side_effect=OSError("association failed"))

        with self.assertRaisesRegex(OSError, "association failed"):
            open_html_in_browser(
                Path("C:/DotExpress/dual_view/dual-view-one.html"),
                (900, 600),
                finder=lambda _browser: None,
                startfile=startfile,
            )

        startfile.assert_called_once()
```

- [ ] **Step 5: Run tests and verify launch orchestration is missing**

Run:

```bash
cd client
python3 -m unittest tests.test_dual_view_browser -v
```

Expected: command and discovery tests PASS; launch tests FAIL because `open_html_in_browser` is not implemented.

- [ ] **Step 6: Implement fixed-order launch and Windows fallback**

Append to `client/dual_view/browser.py`:

```python
def open_html_in_browser(
    html_path: Path,
    window_size: tuple[int, int],
    *,
    finder: Callable[[str], Path | None] = find_browser_executable,
    popen: Callable[[list[str]], object] = subprocess.Popen,
    startfile: Callable[[str], object] | None | object = _DEFAULT_STARTFILE,
) -> str:
    for browser in BROWSER_ORDER:
        executable = finder(browser)
        if executable is None:
            continue
        try:
            popen(build_browser_command(browser, executable, html_path, window_size))
        except OSError:
            continue
        return browser

    fallback = getattr(os, "startfile", None) if startfile is _DEFAULT_STARTFILE else startfile
    if fallback is None:
        raise OSError("No supported browser or system HTML opener is available.")
    fallback(str(html_path.resolve()))
    return "system"
```

- [ ] **Step 7: Run browser tests and commit**

Run:

```bash
cd client
python3 -m unittest tests.test_dual_view_browser -v
```

Expected: all tests PASS without launching a real browser.

Commit during implementation execution:

```bash
git add client/dual_view/browser.py client/tests/test_dual_view_browser.py
git commit -m "feat: launch dual view in external browsers"
```

---

### Task 6: Connect the menu and application lifecycle to external dual view

**Files:**
- Modify: `client/gui.py:1-125,497-522,674-675,1759-1769`
- Modify: `client/tests/test_gui_document_flows.py:346-366,453-503,698-724`

**Interfaces:**
- Consumes: `write_dual_view_html()`, `cleanup_dual_view_html()`, and `open_html_in_browser()` from Tasks 4 and 5.
- Produces: `BrailleFrame._open_dual_view_in_browser() -> None`.
- Changes: `BrailleFrame.on_open_dual_view()` calls the external path.
- Preserves: `_create_dual_view_frame()`, `_show_dual_view()`, `_refresh_dual_view()`, and all embedded viewer behavior.
- Changes: startup clears prior owned HTML after path validation; shutdown clears owned HTML and still closes the runtime if cleanup fails.

- [ ] **Step 1: Add failing menu integration and error tests**

Add these methods to `GuiDocumentFlowsTest`:

```python
    def test_dual_view_menu_opens_rendered_html_with_main_window_size(self) -> None:
        frame = self._make_frame()
        frame.GetSize = Mock(return_value=(1024, 768))
        frame._render_dual_view_for_open_document = Mock(return_value="<html>dual</html>")
        html_path = Path("C:/DotExpress/dual_view/dual-view-one.html")

        with (
            patch.object(gui, "write_dual_view_html", return_value=html_path) as write_html,
            patch.object(gui, "open_html_in_browser") as open_browser,
        ):
            frame.on_open_dual_view(None)

        write_html.assert_called_once_with("<html>dual</html>")
        open_browser.assert_called_once_with(html_path, (1024, 768))

    def test_dual_view_menu_reports_write_or_launch_failure(self) -> None:
        frame = self._make_frame()
        frame.GetSize = Mock(return_value=(900, 600))
        frame._render_dual_view_for_open_document = Mock(return_value="<html>dual</html>")
        frame._show_file_error = Mock()
        error = OSError("browser failed")

        with (
            patch.object(gui, "write_dual_view_html", side_effect=error),
            patch.object(gui.logger, "exception") as log_exception,
        ):
            frame.on_open_dual_view(None)

        log_exception.assert_called_once_with("Failed to open dual view")
        frame._show_file_error.assert_called_once_with(gui._("Failed to open dual view: {error}"), error)
```

Keep the existing `_show_dual_view()` reuse/refresh tests unchanged; they prove the embedded viewer remains available.

- [ ] **Step 2: Run the GUI tests and verify the menu still calls the embedded viewer**

Run:

```bash
cd client
python3 -m unittest \
  tests.test_gui_document_flows.GuiDocumentFlowsTest.test_dual_view_menu_opens_rendered_html_with_main_window_size \
  tests.test_gui_document_flows.GuiDocumentFlowsTest.test_dual_view_menu_reports_write_or_launch_failure \
  tests.test_gui_document_flows.GuiDocumentFlowsTest.test_open_dual_view_creates_refreshes_and_shows_viewer \
  tests.test_gui_document_flows.GuiDocumentFlowsTest.test_open_existing_dual_view_reuses_and_refreshes_it -v
```

Expected: new menu tests FAIL because the external helpers and logger are not connected; existing embedded-viewer tests PASS.

- [ ] **Step 3: Implement the external menu path without removing embedded code**

Add these imports and logger registration in `client/gui.py`:

```python
from dual_view.browser import open_html_in_browser
from dual_view.files import cleanup_dual_view_html, write_dual_view_html
from log import get_logger

logger = get_logger("dotexpress.gui", "gui.log")
```

Add this method beside `_show_dual_view()` and change only the menu handler:

```python
    def _open_dual_view_in_browser(self) -> None:
        try:
            html_path = write_dual_view_html(self._render_dual_view_for_open_document())
            width, height = self.GetSize()
            open_html_in_browser(html_path, (width, height))
        except Exception as error:
            logger.exception("Failed to open dual view")
            self._show_file_error(_("Failed to open dual view: {error}"), error)

    def on_open_dual_view(self, _evt) -> None:
        self._open_dual_view_in_browser()
```

Do not change `_create_dual_view_frame()`, `_on_dual_view_closed()`, `_refresh_dual_view()`, or `_show_dual_view()`.

- [ ] **Step 4: Add failing startup and shutdown cleanup tests**

Add to `BrailleAppLifecycleTest`:

```python
    def test_app_cleans_stale_dual_view_html_after_path_validation(self) -> None:
        paths = Mock()
        paths.dual_view = Path("C:/DotExpress/dual_view")
        runtime = Mock()
        frame = Mock()

        with (
            patch.object(gui, "prepare_application_directories", return_value=paths),
            patch.object(gui, "cleanup_dual_view_html") as cleanup,
            patch.object(gui, "build_default_translation_runtime", return_value=runtime),
            patch.object(gui, "BrailleFrame", return_value=frame),
            patch.object(gui, "start_client_init_background"),
        ):
            app = gui.BrailleApp()
            self.assertTrue(app.OnInit())

        cleanup.assert_called_once_with(paths.dual_view)

    def test_app_reports_startup_cleanup_failure_before_runtime(self) -> None:
        paths = Mock()
        paths.dual_view = Path("C:/DotExpress/dual_view")
        cause = PermissionError("locked")

        with (
            patch.object(gui, "prepare_application_directories", return_value=paths),
            patch.object(gui, "cleanup_dual_view_html", side_effect=cause),
            patch.object(gui, "build_default_translation_runtime") as build_runtime,
            patch.object(gui.wx, "MessageBox") as message_box,
        ):
            app = gui.BrailleApp()
            result = app.OnInit()

        self.assertFalse(result)
        build_runtime.assert_not_called()
        self.assertIn(str(paths.dual_view), message_box.call_args.args[0])

    def test_app_exit_logs_cleanup_failure_and_still_closes_runtime(self) -> None:
        runtime = Mock()
        app = gui.BrailleApp()
        app.translation_runtime = runtime
        error = OSError("locked")

        with (
            patch.object(gui, "cleanup_dual_view_html", side_effect=error),
            patch.object(gui.logger, "exception") as log_exception,
        ):
            result = app.OnExit()

        self.assertEqual(result, 0)
        log_exception.assert_called_once_with("Failed to clean up dual-view HTML")
        runtime.close.assert_called_once_with()
```

Update every earlier successful `OnInit` test to return an object with a `dual_view` path. In particular, change the Task 3 ordering patch to:

```python
paths = Mock(dual_view=Path("C:/DotExpress/dual_view"))
patch.object(
    gui,
    "prepare_application_directories",
    side_effect=lambda: (order.append("paths"), paths)[1],
),
patch.object(gui, "cleanup_dual_view_html"),
```

Change `test_app_builds_runtime_and_passes_it_to_frame` to patch:

```python
patch.object(
    gui,
    "prepare_application_directories",
    return_value=Mock(dual_view=Path("C:/DotExpress/dual_view")),
),
patch.object(gui, "cleanup_dual_view_html"),
```

Wrap the pre-existing successful `OnExit` tests, including the no-runtime case, with `patch.object(gui, "cleanup_dual_view_html")` so unit tests never clean the real development directory.

- [ ] **Step 5: Run lifecycle tests and verify cleanup is not wired**

Run:

```bash
cd client
python3 -m unittest tests.test_gui_document_flows.BrailleAppLifecycleTest -v
```

Expected: cleanup tests FAIL because startup and shutdown do not call `cleanup_dual_view_html`.

- [ ] **Step 6: Integrate cleanup into startup and shutdown**

Replace the `BrailleApp` lifecycle with the following final form, keeping repository tab indentation:

```python
class BrailleApp(wx.App):
    def OnInit(self):
        try:
            paths = prepare_application_directories()
            cleanup_dual_view_html(paths.dual_view)
        except ApplicationDataError as error:
            _show_application_data_error(error)
            return False
        except OSError as cause:
            error = ApplicationDataError(paths.dual_view, cause)
            _show_application_data_error(error)
            return False

        self.translation_runtime = build_default_translation_runtime()
        self.frame = BrailleFrame(None, runtime=self.translation_runtime)
        self.frame.Show()
        start_client_init_background()
        return True

    def OnExit(self):
        try:
            cleanup_dual_view_html()
        except OSError:
            logger.exception("Failed to clean up dual-view HTML")
        runtime = getattr(self, "translation_runtime", None)
        if runtime is not None:
            runtime.close()
        return 0
```

- [ ] **Step 7: Run all focused GUI and dual-view tests**

Run:

```bash
cd client
python3 -m unittest \
  tests.test_gui_document_flows \
  tests.test_dual_view_browser \
  tests.test_dual_view_files \
  tests.test_dual_view_frame \
  tests.test_dual_view_html -v
```

Expected: all tests PASS, including unchanged embedded viewer tests.

- [ ] **Step 8: Commit GUI integration**

```bash
git add \
  client/gui.py \
  client/tests/test_gui_document_flows.py
git commit -m "feat: open dual view in external browser"
```

---

### Task 7: Localize errors and run complete regression verification

**Files:**
- Modify: `client/locales/dotexpress.pot`
- Modify: `client/locales/zh_TW/LC_MESSAGES/dotexpress.po`
- Regenerate: `client/locales/zh_TW/LC_MESSAGES/dotexpress.mo`
- Modify: `client/tests/test_config.py:139-197`

**Interfaces:**
- Consumes: the English source strings introduced in Tasks 3 and 6.
- Produces: active Traditional Chinese translations for `Startup Error`, the unwritable application-data message, and `Failed to open dual view: {error}`.
- Produces: a compiled MO whose values match the PO catalog.

- [ ] **Step 1: Add a failing compiled-catalog regression test**

Add to `ConfigTest` in `client/tests/test_config.py`:

```python
    def test_zh_tw_catalog_contains_application_data_and_dual_view_errors(self) -> None:
        with open(
            Path(__file__).resolve().parents[1]
            / "locales"
            / "zh_TW"
            / "LC_MESSAGES"
            / "dotexpress.mo",
            "rb",
        ) as mo_file:
            translation = gettext.GNUTranslations(mo_file)

        self.assertEqual(translation.gettext("Startup Error"), "啟動錯誤")
        self.assertEqual(
            translation.gettext(
                "DotExpress cannot write to its application data directory:\n"
                "{path}\n\nChoose a writable installation or execution location.\n\n{error}"
            ),
            "DotExpress 無法寫入應用程式資料目錄：\n"
            "{path}\n\n請選擇可寫入的安裝或執行位置。\n\n{error}",
        )
        self.assertEqual(
            translation.gettext("Failed to open dual view: {error}"),
            "無法開啟雙視檢視：{error}",
        )
```

- [ ] **Step 2: Run the catalog test and verify the MO is stale**

Run:

```bash
cd client
python3 -m unittest tests.test_config.ConfigTest.test_zh_tw_catalog_contains_application_data_and_dual_view_errors -v
```

Expected: FAIL because the new messages are absent from the compiled catalog.

- [ ] **Step 3: Regenerate POT, merge PO, and add exact Traditional Chinese translations**

On a Windows development environment with gettext available, run:

```bat
scripts\generate-pot.bat
msgmerge --update client\locales\zh_TW\LC_MESSAGES\dotexpress.po client\locales\dotexpress.pot
```

Ensure the active PO entries are exactly:

```po
msgid "Startup Error"
msgstr "啟動錯誤"

msgid ""
"DotExpress cannot write to its application data directory:\n"
"{path}\n"
"\n"
"Choose a writable installation or execution location.\n"
"\n"
"{error}"
msgstr ""
"DotExpress 無法寫入應用程式資料目錄：\n"
"{path}\n"
"\n"
"請選擇可寫入的安裝或執行位置。\n"
"\n"
"{error}"

#, python-brace-format
msgid "Failed to open dual view: {error}"
msgstr "無法開啟雙視檢視：{error}"
```

- [ ] **Step 4: Validate and compile the PO catalog**

Run:

```bash
msgfmt --check \
  --output-file=client/locales/zh_TW/LC_MESSAGES/dotexpress.mo \
  client/locales/zh_TW/LC_MESSAGES/dotexpress.po
```

Expected: exit code 0 and an updated `dotexpress.mo`.

- [ ] **Step 5: Run focused tests for every changed responsibility**

Run:

```bash
cd client
python3 -m unittest \
  tests.test_app_paths \
  tests.test_log \
  tests.test_config \
  tests.test_dictionary_manager \
  tests.test_document_workspace \
  tests.test_dual_view_files \
  tests.test_dual_view_browser \
  tests.test_dual_view_frame \
  tests.test_dual_view_html \
  tests.test_gui_document_flows -v
```

Expected: all focused tests PASS. Existing non-Windows skips remain skips; no real browser is launched.

- [ ] **Step 6: Run the full client suite**

Run:

```bash
cd client
python3 -m unittest discover -s tests -v
```

Expected: all available tests PASS. Report exact Windows-only skips or dependency failures rather than treating them as feature failures.

- [ ] **Step 7: Verify document and repository hygiene**

Run:

```bash
git diff --check
git status --short
rg -n "~/.DotExpress/config.json|client/documents/workspace|log/(init|translation|math|dual_view)\.log" client --glob '*.py'
```

Expected: `git diff --check` has no output; status lists only intended files; `rg` has no production-code matches for the removed locations.

- [ ] **Step 8: Commit localization and verification changes**

```bash
git add \
  client/locales/dotexpress.pot \
  client/locales/zh_TW/LC_MESSAGES/dotexpress.po \
  client/locales/zh_TW/LC_MESSAGES/dotexpress.mo \
  client/tests/test_config.py
git commit -m "fix: localize application data errors"
```
