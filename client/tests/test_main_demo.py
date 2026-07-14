import unittest
from unittest.mock import Mock, patch

import main
from conversion.service import ConversionOutput


class MainDemoTest(unittest.TestCase):
    def test_demo_uses_alignment_conversion_output(self) -> None:
        runtime = Mock()
        output = ConversionOutput("braille", (), ())
        with (
            patch.object(main, "build_default_translation_runtime", return_value=runtime),
            patch.object(main, "convert_text_with_alignment", return_value=output) as convert,
            patch("builtins.print") as print_mock,
        ):
            main.run_demo("source")

        self.assertEqual(convert.call_args.args[0].raw_text, "source")
        print_mock.assert_called_once_with("braille")
        runtime.close.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
