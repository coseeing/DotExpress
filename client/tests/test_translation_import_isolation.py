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


if __name__ == "__main__":
    unittest.main()
