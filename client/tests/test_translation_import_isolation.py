import subprocess
import sys
import unittest


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
