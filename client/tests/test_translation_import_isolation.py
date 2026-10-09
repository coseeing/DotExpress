import ast
import subprocess
import sys
import unittest
from pathlib import Path

CLIENT_DIR = Path(__file__).resolve().parents[1]
HIGHER_LAYERS = {"adapters", "documents", "ui", "gui", "dialog", "settings", "dictionaries", "dual_view"}


class TranslationImportIsolationTest(unittest.TestCase):
    def test_platform_neutral_modules_do_not_load_native_modules(self) -> None:
        script = """
import sys
import translate
import conversion.service
assert "braille.louis_helper" not in sys.modules
assert "libmathcat_py" not in sys.modules
"""
        completed = subprocess.run(
            [sys.executable, "-c", script],
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)

    def test_language_consumers_do_not_import_config(self) -> None:
        script = """
import sys
import languageDetection
import conversion.text.pipeline
import conversion.output
import conversion.mathcat_adapter
import braille.tables
assert "config" not in sys.modules, "config was imported"
"""
        completed = subprocess.run(
            [sys.executable, "-c", script],
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)

    def test_client_init_does_not_import_config(self) -> None:
        script = """
import sys
import client_init
assert "config" not in sys.modules, "config was imported"
"""
        completed = subprocess.run(
            [sys.executable, "-c", script],
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)

    def test_conversion_does_not_import_dual_view(self) -> None:
        script = """
import sys
import conversion.service
import conversion.output
import conversion.wrapping
loaded = sorted(name for name in sys.modules if name == "dual_view" or name.startswith("dual_view."))
assert not loaded, f"dual_view modules were imported: {loaded}"
"""
        completed = subprocess.run(
            [sys.executable, "-c", script],
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)

    def test_conversion_package_imports_no_higher_layer(self) -> None:
        found = []
        for path in sorted((CLIENT_DIR / "conversion").rglob("*.py")):
            for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
                if isinstance(node, ast.Import):
                    names = [alias.name for alias in node.names]
                elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                    names = [node.module]
                else:
                    continue
                for name in names:
                    if name.split(".")[0] in HIGHER_LAYERS:
                        found.append(f"{path.relative_to(CLIENT_DIR).as_posix()}:{node.lineno} {name}")

        self.assertEqual(found, [])

    def test_adapter_contracts_reexport_the_conversion_ports(self) -> None:
        import adapters.translation
        import adapters.translation.contracts
        import conversion.contracts

        for name in ("BrailleTextTranslator", "MathSegmentTranslator", "TranslationRuntime"):
            with self.subTest(name=name):
                port = getattr(conversion.contracts, name)
                self.assertEqual(port.__module__, "conversion.contracts")
                self.assertIs(getattr(adapters.translation.contracts, name), port)
                self.assertIs(getattr(adapters.translation, name), port)
        error = adapters.translation.contracts.RuntimeUnavailableError
        self.assertEqual(error.__module__, "adapters.translation.contracts")
        self.assertIs(adapters.translation.RuntimeUnavailableError, error)
        self.assertFalse(hasattr(conversion.contracts, "RuntimeUnavailableError"))

    def test_production_modules_do_not_import_translate(self) -> None:
        found = []
        for path in sorted(CLIENT_DIR.rglob("*.py")):
            relative = path.relative_to(CLIENT_DIR)
            if {"tests", ".venv", "__pycache__"} & set(relative.parts) or relative.parts[:2] == ("braille", "liblouis"):
                continue
            if relative.as_posix() == "translate.py":
                continue
            for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
                if isinstance(node, ast.Import):
                    names = [alias.name for alias in node.names]
                elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                    names = [node.module]
                else:
                    continue
                if "translate" in names:
                    found.append(f"{relative.as_posix()}:{node.lineno}")

        self.assertEqual(found, [], "import TranslationResult from conversion.alignment")

    def test_packaged_build_keeps_the_translate_shim(self) -> None:
        # No production module imports translate, so PyInstaller bundles it only when
        # asked; a user preprocessing script run inside the exe may still import it.
        script = (CLIENT_DIR.parent / "scripts" / "build-dotexpress.bat").read_text(encoding="utf-8")

        self.assertIn("--hidden-import translate ^", script)

    def test_alignment_modules_load_no_config_adapters_or_native_code(self) -> None:
        script = """
import sys
import conversion.alignment
import conversion.tokenizer
import conversion.line_wrap
import conversion.contracts
forbidden = ("config", "adapters", "braille", "wx", "dual_view", "libmathcat_py")
loaded = sorted(
    name for name in sys.modules
    if any(name == prefix or name.startswith(prefix + ".") for prefix in forbidden)
)
assert not loaded, f"loaded: {loaded}"
"""
        completed = subprocess.run(
            [sys.executable, "-c", script],
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)

    def test_tokenizer_and_line_wrap_do_not_import_alignment(self) -> None:
        script = """
import sys
import conversion.tokenizer
import conversion.line_wrap
loaded = sorted(name for name in sys.modules if name in {"conversion.alignment", "translate"})
assert not loaded, f"loaded: {loaded}"
"""
        completed = subprocess.run(
            [sys.executable, "-c", script],
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)

    def test_dual_view_does_not_import_conversion_or_config(self) -> None:
        script = """
import sys
import dual_view
import dual_view.model
import dual_view.html
loaded = sorted(
    name for name in sys.modules
    if name in {"conversion", "config"} or name.startswith("conversion.")
)
assert not loaded, f"conversion or config modules were imported: {loaded}"
"""
        completed = subprocess.run(
            [sys.executable, "-c", script],
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)


if __name__ == "__main__":
    unittest.main()
