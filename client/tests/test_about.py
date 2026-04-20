import importlib
import sys
import unittest


class AboutModuleTest(unittest.TestCase):
    def test_about_module_imports_without_gui_translation_context(self) -> None:
        original = sys.modules.pop("about", None)
        try:
            module = importlib.import_module("about")
            self.assertEqual(module.name, "DotExpress")
            self.assertTrue(isinstance(module.longName, str))
            self.assertTrue(isinstance(module.aboutMessage, str))
        finally:
            sys.modules.pop("about", None)
            if original is not None:
                sys.modules["about"] = original


if __name__ == "__main__":
    unittest.main()
