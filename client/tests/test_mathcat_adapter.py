import unittest
from pathlib import Path
from unittest.mock import patch

from conversion.mathcat_adapter import MathCATAdapter, MathCATError


class MathCATAdapterTest(unittest.TestCase):
    def test_initialize_loads_runtime_once(self) -> None:
        adapter = MathCATAdapter(resource_root=Path("mathcat/assets"))

        with patch.object(adapter, "_load_libmathcat") as load_runtime:
            adapter.initialize()

        load_runtime.assert_called_once_with()

    def test_resolve_speech_style_falls_back_to_simple_speak_when_clearspeak_missing(self) -> None:
        adapter = MathCATAdapter(resource_root=Path("/tmp/mathcat/assets"))

        with patch.object(adapter, "_has_language_style_file", side_effect=lambda language, style: style == "SimpleSpeak"):
            self.assertEqual(adapter._resolve_speech_style("zh-tw"), "SimpleSpeak")

    def test_get_braille_for_mathml_initializes_rules_and_braille_code(self) -> None:
        class FakeLib:
            def __init__(self):
                self.calls = []

            def GetVersion(self):
                return "test"

            def SetRulesDir(self, value):
                self.calls.append(("SetRulesDir", value))

            def SetPreference(self, key, value):
                self.calls.append(("SetPreference", key, value))

            def SetMathML(self, value):
                self.calls.append(("SetMathML", value))

            def GetBraille(self, value):
                self.calls.append(("GetBraille", value))
                return "⠼⠁"

        fake = FakeLib()
        adapter = MathCATAdapter(resource_root=Path("mathcat/assets"))
        with patch.object(adapter, "_load_libmathcat", return_value=fake):
            with patch("conversion.mathcat_adapter.get_lang", return_value="zh_TW"):
                with patch.object(adapter, "_has_language_style_file", side_effect=lambda language, style: style == "SimpleSpeak"):
                    self.assertEqual(adapter.get_braille_for_mathml("<math/>"), "⠼⠁")
        self.assertEqual(fake.calls[0][0], "SetRulesDir")
        self.assertIn(("SetPreference", "BrailleCode", "UEB"), fake.calls)
        self.assertIn(("SetPreference", "Language", "zh-tw"), fake.calls)
        self.assertIn(("SetPreference", "SpeechStyle", "SimpleSpeak"), fake.calls)

    def test_get_braille_for_mathml_uses_selected_braille_code(self) -> None:
        class FakeLib:
            def __init__(self):
                self.calls = []

            def SetRulesDir(self, value):
                self.calls.append(("SetRulesDir", value))

            def SetPreference(self, key, value):
                self.calls.append(("SetPreference", key, value))

            def SetMathML(self, value):
                self.calls.append(("SetMathML", value))

            def GetBraille(self, value):
                self.calls.append(("GetBraille", value))
                return "⠼⠁"

        fake = FakeLib()
        adapter = MathCATAdapter(resource_root=Path("mathcat/assets"))
        with patch.object(adapter, "_load_libmathcat", return_value=fake):
            with patch("conversion.mathcat_adapter.get_lang", return_value="zh_TW"):
                with patch.object(adapter, "_has_language_style_file", side_effect=lambda language, style: style == "SimpleSpeak"):
                    adapter.get_braille_for_mathml("<math/>", braille_code="UEB")

        self.assertIn(("SetPreference", "BrailleCode", "UEB"), fake.calls)

    def test_get_braille_for_mathml_wraps_runtime_failures(self) -> None:
        adapter = MathCATAdapter(resource_root=Path("mathcat/assets"))
        with patch.object(adapter, "_load_libmathcat", side_effect=RuntimeError("load failed")):
            with self.assertRaisesRegex(MathCATError, "load failed"):
                adapter.get_braille_for_mathml("<math/>")

    def test_get_braille_for_mathml_reapplies_runtime_configuration_for_each_call(self) -> None:
        class FakeLib:
            def __init__(self):
                self.calls = []

            def SetRulesDir(self, value):
                self.calls.append(("SetRulesDir", value))

            def SetPreference(self, key, value):
                self.calls.append(("SetPreference", key, value))

            def SetMathML(self, value):
                self.calls.append(("SetMathML", value))

            def GetBraille(self, value):
                self.calls.append(("GetBraille", value))
                return "⠁"

        fake = FakeLib()
        adapter = MathCATAdapter(resource_root=Path("mathcat/assets"))
        with patch.object(adapter, "_load_libmathcat", return_value=fake):
            with patch("conversion.mathcat_adapter.get_lang", return_value="zh_TW"):
                with patch.object(adapter, "_has_language_style_file", side_effect=lambda language, style: style == "SimpleSpeak"):
                    adapter.get_braille_for_mathml("<math><mn>1</mn></math>")
                    adapter.get_braille_for_mathml("<math><mn>2</mn></math>")

        set_rules_dir_calls = [call for call in fake.calls if call[0] == "SetRulesDir"]
        self.assertEqual(len(set_rules_dir_calls), 2)


if __name__ == "__main__":
    unittest.main()
