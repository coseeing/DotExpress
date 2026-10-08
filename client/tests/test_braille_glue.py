import ctypes
import importlib.util
import logging
import os
import sys
import tempfile
import types
import unittest
from collections import ChainMap
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch

import braille

CLIENT_DIR = Path(__file__).resolve().parents[1]
VENDOR_HELPER = CLIENT_DIR.parent / "vendor" / "nvda" / "liblouis" / "runtime" / "louis_helper.py"
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


if __name__ == "__main__":
    unittest.main()
