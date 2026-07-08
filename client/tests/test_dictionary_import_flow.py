import tempfile
import unittest
from pathlib import Path

import dictionaries.import_flow as import_flow
from dictionaries.manager import DEFAULT_HEADER


class DictionaryImportFlowTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self.dictionary_dir = Path(self._tmpdir.name) / "dictionary"

    def tearDown(self) -> None:
        self._tmpdir.cleanup()

    def _create_source_dictionary(self, name: str = "1.1") -> Path:
        source_path = Path(self._tmpdir.name) / f"{name}.csv"
        source_path.write_text(",".join(DEFAULT_HEADER) + "\nterm,braille,General\n", encoding="utf-8")
        return source_path

    def test_import_dictionary_after_name_prompt_uses_prompted_name(self) -> None:
        source_path = self._create_source_dictionary()
        prompt_calls = []

        def prompt_name(default_name: str) -> str:
            prompt_calls.append(default_name)
            return "edited"

        result = import_flow.import_dictionary_after_name_prompt(
            self.dictionary_dir,
            source_path,
            prompt_name=prompt_name,
        )

        self.assertEqual(result, self.dictionary_dir / "edited.csv")
        self.assertEqual(prompt_calls, ["1.1"])
        self.assertTrue((self.dictionary_dir / "edited.csv").exists())

    def test_import_dictionary_after_name_prompt_returns_none_when_prompt_is_cancelled(self) -> None:
        source_path = self._create_source_dictionary()
        prompt_calls = []

        def prompt_name(default_name: str) -> None:
            prompt_calls.append(default_name)
            return None

        result = import_flow.import_dictionary_after_name_prompt(
            self.dictionary_dir,
            source_path,
            prompt_name=prompt_name,
        )

        self.assertIsNone(result)
        self.assertEqual(prompt_calls, ["1.1"])
        self.assertFalse(self.dictionary_dir.exists())
