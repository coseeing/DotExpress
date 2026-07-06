import importlib
import sys
import types
import unittest
from unittest.mock import Mock, patch

from adapters.translation.contracts import RuntimeUnavailableError
from adapters.translation.fallback import FallbackMathTranslator, FallbackTextTranslator


class TranslationRuntimeProviderTest(unittest.TestCase):
    def test_selects_both_native_adapters(self) -> None:
        from adapters.translation.provider import build_translation_runtime

        text = Mock()
        math = Mock()

        runtime = build_translation_runtime(
            text_factory=Mock(return_value=text),
            math_factory=Mock(return_value=math),
        )

        self.assertIs(runtime.text_translator, text)
        self.assertIs(runtime.math_translator, math)

    def test_falls_back_only_for_unavailable_text(self) -> None:
        from adapters.translation.provider import build_translation_runtime

        math = Mock()

        runtime = build_translation_runtime(
            text_factory=Mock(side_effect=RuntimeUnavailableError("text")),
            math_factory=Mock(return_value=math),
        )

        self.assertIsInstance(runtime.text_translator, FallbackTextTranslator)
        self.assertIs(runtime.math_translator, math)

    def test_falls_back_only_for_unavailable_math(self) -> None:
        from adapters.translation.provider import build_translation_runtime

        text = Mock()

        runtime = build_translation_runtime(
            text_factory=Mock(return_value=text),
            math_factory=Mock(side_effect=RuntimeUnavailableError("math")),
        )

        self.assertIs(runtime.text_translator, text)
        self.assertIsInstance(runtime.math_translator, FallbackMathTranslator)

    def test_falls_back_for_both_unavailable_capabilities(self) -> None:
        from adapters.translation.provider import build_translation_runtime

        runtime = build_translation_runtime(
            text_factory=Mock(side_effect=RuntimeUnavailableError("text")),
            math_factory=Mock(side_effect=RuntimeUnavailableError("math")),
        )

        self.assertIsInstance(runtime.text_translator, FallbackTextTranslator)
        self.assertIsInstance(runtime.math_translator, FallbackMathTranslator)

    def test_unexpected_factory_error_propagates(self) -> None:
        from adapters.translation.provider import build_translation_runtime

        with self.assertRaisesRegex(ValueError, "defect"):
            build_translation_runtime(
                text_factory=Mock(side_effect=ValueError("defect")),
                math_factory=Mock(),
            )

    def test_close_is_idempotent_and_closes_initialized_adapters(self) -> None:
        from adapters.translation.provider import build_translation_runtime

        text = Mock()
        math = Mock()
        runtime = build_translation_runtime(
            text_factory=Mock(return_value=text),
            math_factory=Mock(return_value=math),
        )

        runtime.close()
        runtime.close()

        text.close.assert_called_once_with()
        math.close.assert_called_once_with()

    def test_create_default_text_translator_rejects_non_windows(self) -> None:
        from adapters.translation import provider

        with self.assertRaises(RuntimeUnavailableError):
            provider.create_default_text_translator(platform="linux")

    def test_create_default_math_translator_rejects_non_windows(self) -> None:
        from adapters.translation import provider

        with self.assertRaises(RuntimeUnavailableError):
            provider.create_default_math_translator(platform="linux")

    def test_default_text_factory_propagates_unexpected_initialize_errors(self) -> None:
        from adapters.translation import provider

        braille_module = types.ModuleType("braille")
        louis_helper = types.ModuleType("braille.louis_helper")
        louis_helper.initialize = Mock(side_effect=ValueError("defect"))
        tables_module = types.ModuleType("braille.tables")
        tables_module.TABLES_DIR = "/tables"

        with patch.dict(
            sys.modules,
            {
                "braille": braille_module,
                "braille.louis_helper": louis_helper,
                "braille.tables": tables_module,
            },
            clear=False,
        ):
            with self.assertRaisesRegex(ValueError, "defect"):
                provider.create_default_text_translator(platform="win32")

    def test_default_text_factory_normalizes_initialize_load_errors(self) -> None:
        from adapters.translation import provider

        braille_module = types.ModuleType("braille")
        louis_helper = types.ModuleType("braille.louis_helper")
        tables_module = types.ModuleType("braille.tables")
        tables_module.TABLES_DIR = "/tables"

        for error in (ImportError("missing package"), OSError("missing DLL")):
            with self.subTest(error_type=type(error).__name__):
                louis_helper.initialize = Mock(side_effect=error)
                with patch.dict(
                    sys.modules,
                    {
                        "braille": braille_module,
                        "braille.louis_helper": louis_helper,
                        "braille.tables": tables_module,
                    },
                    clear=False,
                ):
                    with self.assertRaisesRegex(RuntimeUnavailableError, str(error)):
                        provider.create_default_text_translator(platform="win32")

    def test_default_text_factory_normalizes_native_adapter_import_error(self) -> None:
        from adapters.translation import provider

        with patch.dict(
            sys.modules,
            {"adapters.translation.liblouis": None},
            clear=False,
        ):
            with self.assertRaises(RuntimeUnavailableError):
                provider.create_default_text_translator(platform="win32")

    def test_default_math_factory_normalizes_native_adapter_import_error(self) -> None:
        from adapters.translation import provider

        with patch.dict(
            sys.modules,
            {"adapters.translation.mathcat": None},
            clear=False,
        ):
            with self.assertRaises(RuntimeUnavailableError):
                provider.create_default_math_translator(platform="win32")

    def test_default_math_factory_propagates_unexpected_initialize_errors(self) -> None:
        from adapters.translation import provider

        with patch.object(provider, "get_shared_mathcat_adapter") as get_adapter:
            get_adapter.return_value.initialize.side_effect = ValueError("defect")
            with self.assertRaisesRegex(ValueError, "defect"):
                provider.create_default_math_translator(platform="win32")


if __name__ == "__main__":
    unittest.main()
