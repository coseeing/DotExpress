"""Source scans that keep the wx calls F-7 replaced out of the production code (F-W9).

The scan covers every ``.py`` file under ``client/`` that git does not ignore, except the
tests, the virtual environment, the build output and the vendored or generated trees. A
hit is reported as ``<file>:<class>.<function>`` so that a failure names the call site; a
file that does not parse is named too.
"""

import ast
import shutil
import subprocess
import tempfile
import unittest
from collections.abc import Callable, Iterator
from pathlib import Path

CLIENT = Path(__file__).resolve().parents[1]
EXCLUDED_FOLDERS = {".venv", "tests", "build", "dist", "mathcat"}
# The wx names F-7 replaced or restricted (FindWindowById, MessageBox) or allows only in
# two places (MessageDialog).
REPLACED_WX_NAMES = {"FindWindowById", "MessageBox", "MessageDialog"}


def _python_files(root: Path) -> list[Path]:
    """The ``.py`` files under ``root`` that git does not ignore.

    ``git ls-files --cached --others --exclude-standard`` lists the tracked files and the
    untracked ones that are not ignored: the git-ignored runtime copies (for example
    ``braille/louis_helper.py``) and ignored drafts are skipped, while a new module that
    is not yet added is still scanned. Outside a git work tree (a ``git archive`` copy, or
    no git) every ``.py`` file under ``root`` is scanned.
    """
    command = [
        "git", "-C", str(root), "ls-files", "-z", "--cached", "--others", "--exclude-standard", "--", "*.py",
    ]
    try:
        listed = subprocess.run(command, capture_output=True, check=True).stdout
    except (OSError, subprocess.CalledProcessError):
        return sorted(root.rglob("*.py"))
    paths = {root / name for name in listed.decode("utf-8").split("\0") if name}
    return sorted(path for path in paths if path.is_file())


def production_sources(root: Path = CLIENT) -> list[Path]:
    paths = []
    for path in _python_files(root):
        parts = path.relative_to(root).parts
        if parts[0] in EXCLUDED_FOLDERS or parts[:2] == ("braille", "liblouis"):
            continue
        paths.append(path)
    return paths


def _matches(node: ast.AST, predicate: Callable[[ast.AST], bool], scope: str) -> Iterator[str]:
    for child in ast.iter_child_nodes(node):
        if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            yield from _matches(child, predicate, f"{scope}.{child.name}" if scope else child.name)
            continue
        if predicate(child):
            yield scope or "<module>"
        yield from _matches(child, predicate, scope)


def find_in_production(predicate: Callable[[ast.AST], bool], root: Path = CLIENT) -> list[str]:
    """``<file>:<scope>`` of every node of the production code for which ``predicate`` is true."""
    found = []
    for path in production_sources(root):
        name = path.relative_to(root).as_posix()
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=name)
        except (SyntaxError, ValueError) as error:
            raise AssertionError(f"cannot scan {name}: {error!r}") from error
        found.extend(f"{name}:{scope}" for scope in _matches(tree, predicate, ""))
    return found


def is_attribute(name: str) -> Callable[[ast.AST], bool]:
    return lambda node: isinstance(node, ast.Attribute) and node.attr == name


def hides_wx_names(node: ast.AST) -> bool:
    """``import wx as <alias>``, or ``from wx import`` of a replaced name or of ``*``.

    The other scans find the replaced names as attributes (``wx.MessageBox``); a bare
    name imported from wx would hide a use from them. With ``import wx as _wx`` the
    attribute is still found, but the alias is refused too, so that the code keeps one
    spelling of the module.
    """
    if isinstance(node, ast.Import):
        return any(alias.name == "wx" and alias.asname not in (None, "wx") for alias in node.names)
    if isinstance(node, ast.ImportFrom) and node.module == "wx" and not node.level:
        return any(alias.name in REPLACED_WX_NAMES | {"*"} for alias in node.names)
    return False


class WxCallSitesTest(unittest.TestCase):
    def test_scan_reads_the_production_modules(self) -> None:
        names = {path.relative_to(CLIENT).as_posix() for path in production_sources()}

        self.assertTrue({"dialog.py", "gui.py", "settings/dialogs.py"} <= names, sorted(names))
        self.assertFalse([name for name in names if name.startswith("tests/")])

    def test_no_production_code_searches_windows_by_id_globally(self) -> None:
        # wx.Window.FindWindowById is static: called on a dialog, it still searches every
        # top-level window and can return another dialog's button (F-W9). FindWindow
        # searches the window and its children only.
        self.assertEqual(find_in_production(is_attribute("FindWindowById")), [])

    def test_no_production_module_calls_wx_message_box(self) -> None:
        # wx.MessageBox labels its OK button from wx's own catalog, which DotExpress does not
        # load; ui.message_box.message_box sets the translated label (F-7, F-W9). Any
        # reference counts, called or not (message_box = wx.MessageBox), under any alias.
        self.assertEqual(find_in_production(is_attribute("MessageBox")), [])

    def test_message_dialogs_are_the_helper_or_set_every_label(self) -> None:
        # F-5's close dialog sets all three of its labels itself.
        self.assertEqual(
            find_in_production(is_attribute("MessageDialog")),
            ["gui.py:BrailleFrame._ask_after_close_save_failure", "ui/message_box.py:message_box"],
        )

    def test_the_only_generic_message_dialog_is_the_confirmation_box(self) -> None:
        # F-11: ui.message_box.confirm_box uses wx's generic dialog and sets both labels.
        self.assertEqual(find_in_production(is_attribute("GenericMessageDialog")), ["ui/message_box.py:confirm_box"])

    def test_no_production_module_imports_wx_names_around_the_scans(self) -> None:
        # from wx import MessageBox, or import wx as _wx, would let a use slip past the
        # scans above (F-7 review M-1).
        self.assertEqual(find_in_production(hides_wx_names), [])


class ScanSourcesTest(unittest.TestCase):
    """Which files the scans read, and how they fail (F-7 review M-6)."""

    def test_a_file_that_does_not_parse_is_named(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "settings").mkdir()
            (root / "settings" / "draft.py").write_text("def broken(:\n", encoding="utf-8")

            with self.assertRaisesRegex(AssertionError, "settings/draft.py"):
                find_in_production(is_attribute("MessageBox"), root)

    @unittest.skipUnless(shutil.which("git"), "git is not installed")
    def test_git_ignored_files_are_not_scanned(self) -> None:
        # The worktree holds git-ignored runtime copies (braille/louis_helper.py) that are
        # not DotExpress code; a module that is new and not yet added is still scanned.
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            subprocess.run(["git", "init", "-q", str(root)], check=True, capture_output=True)
            (root / ".gitignore").write_text("ignored.py\n", encoding="utf-8")
            for name in ("added.py", "ignored.py", "new.py"):
                (root / name).write_text("import wx\n", encoding="utf-8")
            subprocess.run(["git", "-C", str(root), "add", "added.py"], check=True, capture_output=True)

            names = [path.name for path in production_sources(root)]

        self.assertEqual(names, ["added.py", "new.py"])


if __name__ == "__main__":
    unittest.main()
