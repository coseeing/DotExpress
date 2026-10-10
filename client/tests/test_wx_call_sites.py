"""Source scans that keep the wx calls F-7 replaced out of the production code (F-W9).

The scan covers every ``.py`` file under ``client/`` except the tests, the virtual
environment, the build output and the vendored or generated trees. A hit is reported as
``<file>:<class>.<function>`` so that a failure names the call site.
"""

import ast
import unittest
from collections.abc import Callable, Iterator
from pathlib import Path

CLIENT = Path(__file__).resolve().parents[1]
EXCLUDED_FOLDERS = {".venv", "tests", "build", "dist", "mathcat"}


def production_sources() -> list[Path]:
    paths = []
    for path in sorted(CLIENT.rglob("*.py")):
        parts = path.relative_to(CLIENT).parts
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


def find_in_production(predicate: Callable[[ast.AST], bool]) -> list[str]:
    """``<file>:<scope>`` of every node of the production code for which ``predicate`` is true."""
    found = []
    for path in production_sources():
        tree = ast.parse(path.read_text(encoding="utf-8"))
        name = path.relative_to(CLIENT).as_posix()
        found.extend(f"{name}:{scope}" for scope in _matches(tree, predicate, ""))
    return found


def is_attribute(name: str) -> Callable[[ast.AST], bool]:
    return lambda node: isinstance(node, ast.Attribute) and node.attr == name


def is_wx_call(name: str) -> Callable[[ast.AST], bool]:
    """A call of ``wx.<name>(...)``."""
    return lambda node: (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == name
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "wx"
    )


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
        # load; ui.message_box.message_box sets the translated label (F-7, F-W9).
        self.assertEqual(find_in_production(is_wx_call("MessageBox")), [])

    def test_message_dialogs_are_the_helper_or_set_every_label(self) -> None:
        # F-5's close dialog sets all three of its labels itself.
        self.assertEqual(
            find_in_production(is_wx_call("MessageDialog")),
            ["gui.py:BrailleFrame._ask_after_close_save_failure", "ui/message_box.py:message_box"],
        )


if __name__ == "__main__":
    unittest.main()
