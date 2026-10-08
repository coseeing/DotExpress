import ast
import gettext
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import i18n


CLIENT_ROOT = Path(__file__).resolve().parents[1]
LEGACY_SETUP_FUNCTIONS = {"resource_path", "_resource_path"}
LEGACY_SETUP_GLOBALS = {"LOCALE_DOMAIN", "LOCALE_LANGUAGES", "_translation", "_"}


def _module_tree(relative_path: str) -> ast.Module:
    path = CLIENT_ROOT / relative_path
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


class ResourcePathTest(unittest.TestCase):
    def test_resource_path_defaults_to_client_root(self) -> None:
        self.assertEqual(i18n.CLIENT_ROOT, CLIENT_ROOT)
        self.assertEqual(i18n.resource_path("data"), CLIENT_ROOT / "data")
        catalog = i18n.resource_path("locales") / "zh_TW" / "LC_MESSAGES" / "dotexpress.mo"
        self.assertTrue(catalog.is_file(), catalog)

    def test_resource_path_uses_meipass_when_frozen(self) -> None:
        with tempfile.TemporaryDirectory() as bundle_dir:
            with patch.object(sys, "frozen", True, create=True), patch.object(sys, "_MEIPASS", bundle_dir, create=True):
                self.assertEqual(i18n.resource_path("locales"), Path(bundle_dir) / "locales")

    def test_resource_path_ignores_frozen_without_meipass(self) -> None:
        self.assertFalse(hasattr(sys, "_MEIPASS"))
        with patch.object(sys, "frozen", True, create=True):
            self.assertEqual(i18n.resource_path("locales"), CLIENT_ROOT / "locales")


class TranslationTest(unittest.TestCase):
    def test_translates_known_msgids_to_zh_tw(self) -> None:
        self.assertEqual(i18n.LOCALE_DOMAIN, "dotexpress")
        self.assertEqual(i18n.LOCALE_LANGUAGES, ("zh_TW",))
        self.assertIsInstance(i18n.load_translation(), gettext.GNUTranslations)
        self.assertEqual(i18n._("General"), "一般")
        self.assertEqual(i18n._("Startup Error"), "啟動錯誤")

    def test_unknown_msgid_is_returned_unchanged(self) -> None:
        self.assertEqual(i18n._("No such msgid in the DotExpress catalog"), "No such msgid in the DotExpress catalog")

    def test_load_translation_falls_back_without_catalog(self) -> None:
        with tempfile.TemporaryDirectory() as empty_dir:
            translation = i18n.load_translation(localedir=Path(empty_dir))

        self.assertIs(type(translation), gettext.NullTranslations)
        self.assertEqual(translation.gettext("General"), "General")

    def test_n_returns_message_unchanged(self) -> None:
        message = "General"

        self.assertIs(i18n.N_(message), message)
        self.assertEqual(i18n.N_("General"), "General")

    def test_language_does_not_follow_environment(self) -> None:
        env = dict(os.environ, LANGUAGE="en_US", LANG="C", LC_ALL="C", PYTHONIOENCODING="utf-8")
        env.pop("PYTHONSAFEPATH", None)

        result = subprocess.run(
            [sys.executable, "-c", "from i18n import _; print(_('General'))"],
            cwd=CLIENT_ROOT,
            env=env,
            capture_output=True,
            encoding="utf-8",
            check=False,
            timeout=60,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "一般")


class SharedSetupConsumerTest(unittest.TestCase):
    def assert_uses_shared_i18n(self, relative_path: str, expected_names: set[str]) -> None:
        tree = _module_tree(relative_path)
        from_i18n = {
            alias.asname or alias.name
            for node in tree.body
            if isinstance(node, ast.ImportFrom) and node.module == "i18n" and node.level == 0
            for alias in node.names
        }
        plain_imports = {
            alias.name
            for node in ast.walk(tree)
            if isinstance(node, ast.Import)
            for alias in node.names
        }
        functions = {node.name for node in tree.body if isinstance(node, ast.FunctionDef)}
        assigned = {
            target.id
            for node in tree.body
            if isinstance(node, ast.Assign)
            for target in node.targets
            if isinstance(target, ast.Name)
        }

        self.assertEqual(from_i18n, expected_names, f"{relative_path} must import {sorted(expected_names)} from i18n")
        self.assertNotIn("gettext", plain_imports, f"{relative_path} still imports gettext")
        self.assertEqual(functions & LEGACY_SETUP_FUNCTIONS, set(), f"{relative_path} still defines its own resource path")
        self.assertEqual(assigned & LEGACY_SETUP_GLOBALS, set(), f"{relative_path} still builds its own catalog")

    def test_dialog_uses_shared_i18n(self) -> None:
        self.assert_uses_shared_i18n("dialog.py", {"_"})


if __name__ == "__main__":
    unittest.main()
