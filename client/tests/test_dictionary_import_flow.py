import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

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
        prompt_name = Mock(return_value="edited")

        original_import_dictionary = import_flow.import_dictionary
        import_flow.import_dictionary = Mock(return_value=self.dictionary_dir / "edited.csv")
        self.addCleanup(setattr, import_flow, "import_dictionary", original_import_dictionary)

        result = import_flow.import_dictionary_after_name_prompt(
            self.dictionary_dir,
            source_path,
            prompt_name=prompt_name,
        )

        self.assertEqual(result, self.dictionary_dir / "edited.csv")
        prompt_name.assert_called_once_with("1.1")
        import_flow.import_dictionary.assert_called_once_with(self.dictionary_dir, source_path, "edited")

    def test_import_dictionary_after_name_prompt_returns_none_when_prompt_is_cancelled(self) -> None:
        source_path = self._create_source_dictionary()
        prompt_name = Mock(return_value=None)

        original_import_dictionary = import_flow.import_dictionary
        import_flow.import_dictionary = Mock()
        self.addCleanup(setattr, import_flow, "import_dictionary", original_import_dictionary)

        result = import_flow.import_dictionary_after_name_prompt(
            self.dictionary_dir,
            source_path,
            prompt_name=prompt_name,
        )

        self.assertIsNone(result)
        prompt_name.assert_called_once_with("1.1")
        import_flow.import_dictionary.assert_not_called()
