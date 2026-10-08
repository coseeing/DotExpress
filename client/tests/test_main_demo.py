import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import app_paths
import config
import main
from conversion.service import ConversionOutput


class MainDemoTest(unittest.TestCase):
    def test_demo_uses_alignment_conversion_output(self) -> None:
        runtime = Mock()
        output = ConversionOutput("braille", (), ())
        dictionary_directory = Path("C:/Portable/DotExpress/dictionary")
        with (
            patch.object(main, "build_default_translation_runtime", return_value=runtime),
            patch.object(main, "convert_text_with_alignment", return_value=output) as convert,
            patch.object(main, "get_dictionary_directory", return_value=dictionary_directory),
            patch("builtins.print") as print_mock,
        ):
            main.run_demo("source")

        self.assertEqual(convert.call_args.args[0].raw_text, "source")
        self.assertEqual(
            convert.call_args.args[0].dictionary_path,
            dictionary_directory / "default.csv",
        )
        print_mock.assert_called_once_with("braille")
        runtime.close.assert_called_once_with()

    def test_demo_request_carries_language_settings(self) -> None:
        runtime = Mock()
        charset_maps = {"latinCharactersLanguage": "en", "CJKCharactersLanguage": "ja"}
        with (
            patch.object(main, "build_default_translation_runtime", return_value=runtime),
            patch.object(main, "convert_text_with_alignment", return_value=ConversionOutput("braille", (), ())) as convert,
            patch.object(main, "get_lang", return_value="en") as get_lang,
            patch.object(main, "get_charset_maps", return_value=charset_maps) as get_charset_maps,
            patch("builtins.print") as print_mock,
        ):
            main.run_demo("x")

        request = convert.call_args.args[0]
        self.assertEqual(request.lang, "en")
        self.assertEqual(request.charset_maps, charset_maps)
        get_lang.assert_called_once_with()
        get_charset_maps.assert_called_once_with()
        print_mock.assert_called_once_with("braille")
        runtime.close.assert_called_once_with()

    def run_demo_at_root(self, root: Path):
        """Run the demo with its application data under ``root``; return the request.

        P2-6: today the application root and the import-time config path are patched.
        """
        with (
            patch.object(app_paths, "get_application_root", return_value=root),
            patch.object(config, "CONFIG_PATH", str(root / "config.json")),
            patch.dict(os.environ),
            patch.object(config, "_runtime_lang", None),
            patch.object(main, "build_default_translation_runtime", return_value=Mock()),
            patch.object(main, "convert_text_with_alignment", return_value=ConversionOutput("braille", (), ())) as convert,
            patch("builtins.print"),
        ):
            os.environ.pop(config.LANG_ENV, None)
            main.run_demo("x")
        return convert.call_args.args[0]

    def test_demo_reads_dictionary_and_language_from_the_application_root(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "config.json").write_text(
                json.dumps({"language": "en", "language_detection": {"charset_maps": {"CJKCharactersLanguage": "ja"}}}),
                encoding="utf-8",
            )

            request = self.run_demo_at_root(root)

            self.assertEqual(request.dictionary_path, root / "dictionary" / "default.csv")
            self.assertEqual(request.lang, "en")
            self.assertEqual(request.charset_maps, {**config.DEFAULT_CHARSET_MAPS, "CJKCharactersLanguage": "ja"})
            self.assertEqual(sorted(path.name for path in root.iterdir()), ["config.json"])


if __name__ == "__main__":
    unittest.main()
