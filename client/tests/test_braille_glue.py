import ast
import ctypes
import importlib.util
import json
import logging
import os
import subprocess
import sys
import tempfile
import types
import unittest
from collections import ChainMap
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch

import braille
import braille.tables as tables

CLIENT_DIR = Path(__file__).resolve().parents[1]
VENDOR_HELPER = CLIENT_DIR.parent / "vendor" / "nvda" / "liblouis" / "runtime" / "louis_helper.py"
BRAILLE_TABLES_SOURCE = CLIENT_DIR / "braille" / "tables" / "__init__.py"
_MISSING = object()


def install_fake_liblouis() -> types.ModuleType:
    """Bind a stand-in ``braille.liblouis``; the real one needs the Windows DLL."""
    fake = types.ModuleType("braille.liblouis")
    fake.LOG_ALL = 0
    fake.LOG_DEBUG = 10000
    fake.LOG_INFO = 20000
    fake.LOG_WARN = 30000
    fake.LOG_ERROR = 40000
    fake.LOG_FATAL = 50000
    fake.LOG_OFF = 60000
    fake.LogCallback = ctypes.CFUNCTYPE(None, ctypes.c_int, ctypes.c_char_p)
    fake.fileSystemEncoding = "utf-8"
    sys.modules["braille.liblouis"] = fake
    sys.modules["braille"].liblouis = fake
    return fake


def exec_vendor_helper() -> types.ModuleType:
    """Execute the tracked generated helper as ``braille.louis_helper`` (not registered)."""
    spec = importlib.util.spec_from_file_location("braille.louis_helper", VENDOR_HELPER)
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    return helper


def run_fresh(script: str) -> dict:
    """Run ``script`` in a new interpreter from client/ and return the JSON it prints."""
    completed = subprocess.run(
        [sys.executable, "-c", script],
        cwd=CLIENT_DIR,
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        raise AssertionError(completed.stderr)
    return json.loads(completed.stdout)


@contextmanager
def vendor_helper():
    """Load the vendor helper with a fake liblouis, then restore modules and the root logger."""
    root = logging.getLogger()
    saved_handlers = list(root.handlers)
    saved_level = root.level
    package = sys.modules["braille"]
    saved_module = sys.modules.get("braille.liblouis", _MISSING)
    saved_attr = vars(package).get("liblouis", _MISSING)
    try:
        install_fake_liblouis()
        yield exec_vendor_helper()
    finally:
        if saved_module is _MISSING:
            sys.modules.pop("braille.liblouis", None)
        else:
            sys.modules["braille.liblouis"] = saved_module
        if saved_attr is _MISSING:
            vars(package).pop("liblouis", None)
        else:
            package.liblouis = saved_attr
        for handler in list(root.handlers):
            root.removeHandler(handler)
        for handler in saved_handlers:
            root.addHandler(handler)
        root.setLevel(saved_level)


class LouisHelperResolverCharacterizationTest(unittest.TestCase):
    """Pins ``_resolveTableInner`` of vendor/nvda/liblouis/runtime/louis_helper.py."""

    def setUp(self) -> None:
        self.helper = self.enterContext(vendor_helper())
        tables = self.helper.braille_tables
        temp = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.builtin = str(temp / "builtin")
        self.custom = str(temp / "custom")
        os.mkdir(self.builtin)
        os.mkdir(self.custom)
        registered = tables.BrailleTable("custom.ctb", "Custom", source="custom-source")
        self.enterContext(patch.object(tables, "TABLES_DIR", self.builtin))
        self.enterContext(patch.object(tables, "_tables", {"custom.ctb": registered}))
        self.enterContext(
            patch.object(
                tables,
                "_tablesDirs",
                ChainMap({"custom-source": self.custom}, {tables.TableSource.BUILTIN: self.builtin}),
            )
        )

    def _write(self, directory: str, name: str) -> str:
        path = os.path.join(directory, name)
        Path(path).write_text("# table\n", encoding="utf-8")
        return path

    def test_registered_table_resolves_in_its_source_directory(self) -> None:
        self._write(self.builtin, "custom.ctb")
        expected = self._write(self.custom, "custom.ctb")

        self.assertEqual(list(self.helper._resolveTableInner(["custom.ctb"])), [expected])

    def test_unregistered_table_falls_back_to_the_builtin_directory(self) -> None:
        expected = self._write(self.builtin, "plain.ctb")

        self.assertEqual(list(self.helper._resolveTableInner(["plain.ctb"])), [expected])

    def test_base_table_searches_its_own_directory_first(self) -> None:
        self._write(self.builtin, "include.uti")
        expected = self._write(self.custom, "include.uti")
        base = os.path.join(self.custom, "main.ctb")

        self.assertEqual(list(self.helper._resolveTableInner(["include.uti"], base)), [expected])

    def test_missing_table_raises_lookup_error_naming_the_searched_folders(self) -> None:
        with self.assertRaises(LookupError) as raised:
            list(self.helper._resolveTableInner(["custom.ctb"]))

        self.assertEqual(
            str(raised.exception),
            f"Could not resolve table 'custom.ctb', looked in paths: {[self.custom, self.builtin]!r}",
        )


class BrailleGlueLoggingTest(unittest.TestCase):
    def test_importing_braille_tables_leaves_the_root_logger_alone(self) -> None:
        state = run_fresh(
            "import json, logging\n"
            "import braille.tables\n"
            "print(json.dumps({\n"
            "    'root_handlers': len(logging.root.handlers),\n"
            "    'root_level': logging.getLevelName(logging.root.level),\n"
            "    'named_logger': braille.tables.log is logging.getLogger('braille.tables'),\n"
            "}))\n"
        )

        self.assertEqual(state, {"root_handlers": 0, "root_level": "WARNING", "named_logger": True})

    def test_loading_the_louis_helper_leaves_the_root_logger_alone(self) -> None:
        state = run_fresh(
            "import json, logging\n"
            "from tests.test_braille_glue import exec_vendor_helper, install_fake_liblouis\n"
            "install_fake_liblouis()\n"
            "helper = exec_vendor_helper()\n"
            "print(json.dumps({\n"
            "    'root_handlers': len(logging.root.handlers),\n"
            "    'root_level': logging.getLevelName(logging.root.level),\n"
            "    'named_logger': helper.log is logging.getLogger('braille.louis_helper'),\n"
            "    'debug': helper._isDebug(),\n"
            "}))\n"
        )

        self.assertEqual(
            state,
            {"root_handlers": 0, "root_level": "WARNING", "named_logger": True, "debug": False},
        )


class GlueSourceTest(unittest.TestCase):
    def test_glue_modules_never_call_basic_config(self) -> None:
        for path in (BRAILLE_TABLES_SOURCE, VENDOR_HELPER):
            with self.subTest(path=path.name):
                tree = ast.parse(path.read_text(encoding="utf-8"))
                calls = [
                    node.lineno
                    for node in ast.walk(tree)
                    if isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Attribute)
                    and node.func.attr == "basicConfig"
                ]
                self.assertEqual(calls, [])

    def test_louis_helper_reads_no_private_table_directories(self) -> None:
        tree = ast.parse(VENDOR_HELPER.read_text(encoding="utf-8"))
        accesses = [
            node.lineno
            for node in ast.walk(tree)
            if isinstance(node, ast.Attribute) and node.attr == "_tablesDirs"
        ]

        self.assertEqual(accesses, [])


LIBLOUIS_BINDING = "braille.liblouis"


def _is_liblouis_binding(module: str | None) -> bool:
    return module == LIBLOUIS_BINDING or (module or "").startswith(LIBLOUIS_BINDING + ".")


def direct_liblouis_imports(source: str | bytes) -> list[int]:
    """Line numbers where ``source`` imports ``braille.liblouis`` itself instead of ``braille.louis_helper``."""
    lines = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            hit = any(_is_liblouis_binding(alias.name) for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            hit = node.level == 0 and (
                _is_liblouis_binding(node.module)
                or (node.module == "braille" and any(alias.name == "liblouis" for alias in node.names))
            )
        elif isinstance(node, ast.Call):
            func = node.func
            name = func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", None)
            hit = (
                name in {"import_module", "__import__"}
                and bool(node.args)
                and isinstance(node.args[0], ast.Constant)
                and isinstance(node.args[0].value, str)
                and _is_liblouis_binding(node.args[0].value)
            )
        else:
            continue
        if hit:
            lines.append(node.lineno)
    return sorted(lines)


class LiblouisImportGuardTest(unittest.TestCase):
    """Tests load the binding only through ``braille.louis_helper`` (W-1).

    The generated binding loads ``liblouis.dll`` by bare name. Imported on its own on
    Windows 11 it gets the older System32 DLL, fails on a missing export, and that DLL
    stays loaded, so every later load in the process (the helper's too) gets it again.
    The helper adds the bundled DLL's directory first.
    """

    def test_detector_flags_every_direct_import_form(self) -> None:
        flagged = [
            ("from braille import liblouis", 1),
            ("from braille import tables, liblouis as louis", 1),
            ("import braille.liblouis", 1),
            ("import os, braille.liblouis as louis", 1),
            ("from braille.liblouis import translateString", 1),
            ("import importlib\nimportlib.import_module('braille.liblouis')", 2),
            ("__import__('braille.liblouis')", 1),
            ("try:\n\tfrom braille import liblouis\nexcept Exception:\n\tpass", 2),
        ]
        for source, line in flagged:
            with self.subTest(source=source):
                self.assertEqual(direct_liblouis_imports(source), [line])
        not_imports = [
            "from braille import louis_helper",
            "from braille.louis_helper import louis",
            "from adapters.translation.liblouis import LiblouisTextTranslator",
            "import braille.tables",
            "import sys\nsys.modules['braille.liblouis'] = object()",
            "assert 'braille.liblouis' not in sys.modules",
        ]
        for source in not_imports:
            with self.subTest(source=source):
                self.assertEqual(direct_liblouis_imports(source), [])

    def test_test_modules_load_liblouis_only_through_louis_helper(self) -> None:
        found = [
            f"{path.name}:{line}"
            for path in sorted((CLIENT_DIR / "tests").glob("*.py"))
            for line in direct_liblouis_imports(path.read_bytes())
        ]

        self.assertEqual(found, [], "import braille.louis_helper and use louis_helper.louis instead")


class TableDirectoryTest(unittest.TestCase):
    def test_builtin_source_is_the_tables_dir(self) -> None:
        self.assertEqual(tables.get_table_directory(tables.TableSource.BUILTIN), tables.TABLES_DIR)

    def test_unknown_source_has_no_directory(self) -> None:
        self.assertIsNone(tables.get_table_directory("no-such-source"))

    def test_source_from_a_child_map_is_found(self) -> None:
        with patch.object(tables, "_tablesDirs", tables._tablesDirs.new_child({"addon": "/addon/tables"})):
            self.assertEqual(tables.get_table_directory("addon"), "/addon/tables")
            self.assertEqual(tables.get_table_directory(tables.TableSource.BUILTIN), tables.TABLES_DIR)


if __name__ == "__main__":
    unittest.main()
