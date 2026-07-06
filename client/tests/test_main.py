import importlib
import sys
import unittest
from unittest.mock import patch


class MainDevelopmentScriptTest(unittest.TestCase):
    def test_import_does_not_execute_demo(self) -> None:
        sys.modules.pop("main", None)

        with patch("builtins.print") as print_mock:
            module = importlib.import_module("main")

        print_mock.assert_not_called()
        self.assertTrue(callable(module.run_demo))


if __name__ == "__main__":
    unittest.main()
