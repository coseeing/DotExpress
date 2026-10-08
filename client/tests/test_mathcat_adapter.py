import unittest
from pathlib import Path

from conversion.mathcat_adapter import MathCATAdapter, MathCATError


class FakeLib:
    def __init__(self, braille: str = "⠼⠁") -> None:
        self.braille = braille
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
        return self.braille


class TestMathCATAdapter(MathCATAdapter):
    def __init__(self, *, fake_lib=None, load_error: Exception | None = None) -> None:
        super().__init__(resource_root=Path("mathcat/assets"))
        self.fake_lib = fake_lib or FakeLib()
        self.load_error = load_error
        self.load_calls = 0

    def _load_libmathcat(self):
        self.load_calls += 1
        if self.load_error is not None:
            raise self.load_error
        return self.fake_lib

    def _has_language_style_file(self, language: str, style: str) -> bool:
        return style == "SimpleSpeak"


class MathCATAdapterTest(unittest.TestCase):
    def test_initialize_loads_runtime_once(self) -> None:
        adapter = TestMathCATAdapter()

        adapter.initialize()

        self.assertEqual(adapter.load_calls, 1)

    def test_resolve_speech_style_falls_back_to_simple_speak_when_clearspeak_missing(self) -> None:
        adapter = TestMathCATAdapter()

        self.assertEqual(adapter._resolve_speech_style("zh-tw"), "SimpleSpeak")

    def test_get_braille_for_mathml_initializes_rules_and_braille_code(self) -> None:
        fake = FakeLib()
        adapter = TestMathCATAdapter(fake_lib=fake)

        self.assertEqual(adapter.get_braille_for_mathml("<math/>", language="zh_TW"), "⠼⠁")

        self.assertEqual(fake.calls[0][0], "SetRulesDir")
        self.assertIn(("SetPreference", "BrailleCode", "UEB"), fake.calls)
        self.assertIn(("SetPreference", "Language", "zh-tw"), fake.calls)
        self.assertIn(("SetPreference", "SpeechStyle", "SimpleSpeak"), fake.calls)

    def test_get_braille_for_mathml_uses_selected_braille_code(self) -> None:
        fake = FakeLib()
        adapter = TestMathCATAdapter(fake_lib=fake)

        adapter.get_braille_for_mathml("<math/>", braille_code="UEB", language="zh_TW")

        self.assertIn(("SetPreference", "BrailleCode", "UEB"), fake.calls)

    def test_get_braille_for_mathml_wraps_runtime_failures(self) -> None:
        adapter = TestMathCATAdapter(load_error=RuntimeError("load failed"))
        with self.assertRaisesRegex(MathCATError, "load failed"):
            adapter.get_braille_for_mathml("<math/>", language="zh_TW")

    def test_get_braille_for_mathml_reapplies_runtime_configuration_for_each_call(self) -> None:
        fake = FakeLib("⠁")
        adapter = TestMathCATAdapter(fake_lib=fake)
        adapter.get_braille_for_mathml("<math><mn>1</mn></math>", language="zh_TW")
        adapter.get_braille_for_mathml("<math><mn>2</mn></math>", language="zh_TW")

        set_rules_dir_calls = [call for call in fake.calls if call[0] == "SetRulesDir"]
        self.assertEqual(len(set_rules_dir_calls), 2)

    def test_language_preference_is_lowercase_with_hyphen(self) -> None:
        fake = FakeLib()
        adapter = TestMathCATAdapter(fake_lib=fake)

        adapter.get_braille_for_mathml("<math/>", language="en_US")

        self.assertIn(("SetPreference", "Language", "en-us"), fake.calls)

    def test_each_call_sets_its_own_language(self) -> None:
        fake = FakeLib()
        adapter = TestMathCATAdapter(fake_lib=fake)

        adapter.get_braille_for_mathml("<math/>", language="zh_TW")
        adapter.get_braille_for_mathml("<math/>", language="en")

        self.assertEqual(
            [call[2] for call in fake.calls if call[:2] == ("SetPreference", "Language")],
            ["zh-tw", "en"],
        )

    def test_language_is_required(self) -> None:
        adapter = TestMathCATAdapter()

        with self.assertRaises(TypeError):
            adapter.get_braille_for_mathml("<math/>")


if __name__ == "__main__":
    unittest.main()
