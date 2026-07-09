import sys
import types
import unittest
from unittest.mock import patch

from adapters.translation.contracts import RuntimeUnavailableError
from adapters.translation.fallback import FallbackMathTranslator, FallbackTextTranslator
from conversion.mathcat_adapter import MathCATError


class ClosableTranslator:
    def __init__(self) -> None:
        self.close_calls = 0

    def close(self) -> None:
        self.close_calls += 1


class Factory:
    def __init__(self, value=None, error: Exception | None = None) -> None:
        self.value = value
        self.error = error
        self.calls = 0

    def __call__(self):
        self.calls += 1
        if self.error is not None:
            raise self.error
        return self.value


class InitializerModule(types.ModuleType):
    def __init__(self, name: str, error: Exception | None = None) -> None:
        super().__init__(name)
        self.error = error
        self.calls = 0

    def initialize(self):
        self.calls += 1
        if self.error is not None:
            raise self.error
        return "helper"


class RecordingLogger:
    def __init__(self) -> None:
        self.warnings = []

    def warning(self, message, *args, **kwargs) -> None:
        self.warnings.append((message, args, kwargs))


class ModuleBindings:
    def __init__(self, bindings: dict[str, object]) -> None:
        self.bindings = bindings
        self.previous = {}

    def __enter__(self):
        for name, value in self.bindings.items():
            self.previous[name] = sys.modules.get(name)
            sys.modules[name] = value

    def __exit__(self, _exc_type, _exc, _tb):
        for name, value in self.previous.items():
            if value is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = value


class TranslationRuntimeProviderTest(unittest.TestCase):
    def test_selects_both_native_adapters(self) -> None:
        from adapters.translation.provider import build_translation_runtime

        text = ClosableTranslator()
        math = ClosableTranslator()

        runtime = build_translation_runtime(
            text_factory=Factory(text),
            math_factory=Factory(math),
        )

        self.assertIs(runtime.text_translator, text)
        self.assertIs(runtime.math_translator, math)

    def test_falls_back_only_for_unavailable_text(self) -> None:
        from adapters.translation.provider import build_translation_runtime

        math = ClosableTranslator()

        runtime = build_translation_runtime(
            text_factory=Factory(error=RuntimeUnavailableError("text")),
            math_factory=Factory(math),
        )

        self.assertIsInstance(runtime.text_translator, FallbackTextTranslator)
        self.assertIs(runtime.math_translator, math)

    def test_logs_text_runtime_fallback_reason(self) -> None:
        from adapters.translation import provider

        logger = RecordingLogger()

        with patch.object(provider, "logger", logger):
            provider.build_translation_runtime(
                text_factory=Factory(error=RuntimeUnavailableError("text unavailable")),
                math_factory=Factory(ClosableTranslator()),
            )

        self.assertEqual(len(logger.warnings), 1)
        message, args, kwargs = logger.warnings[0]
        self.assertIn("Translation runtime fallback enabled", message)
        self.assertEqual(args[0], "text")
        self.assertEqual(str(args[1]), "text unavailable")
        self.assertIs(kwargs["exc_info"], True)

    def test_falls_back_only_for_unavailable_math(self) -> None:
        from adapters.translation.provider import build_translation_runtime

        text = ClosableTranslator()

        runtime = build_translation_runtime(
            text_factory=Factory(text),
            math_factory=Factory(error=RuntimeUnavailableError("math")),
        )

        self.assertIs(runtime.text_translator, text)
        self.assertIsInstance(runtime.math_translator, FallbackMathTranslator)

    def test_logs_math_runtime_fallback_reason(self) -> None:
        from adapters.translation import provider

        logger = RecordingLogger()

        with patch.object(provider, "logger", logger):
            provider.build_translation_runtime(
                text_factory=Factory(ClosableTranslator()),
                math_factory=Factory(error=RuntimeUnavailableError("math unavailable")),
            )

        self.assertEqual(len(logger.warnings), 1)
        message, args, kwargs = logger.warnings[0]
        self.assertIn("Translation runtime fallback enabled", message)
        self.assertEqual(args[0], "math")
        self.assertEqual(str(args[1]), "math unavailable")
        self.assertIs(kwargs["exc_info"], True)

    def test_falls_back_for_both_unavailable_capabilities(self) -> None:
        from adapters.translation.provider import build_translation_runtime

        runtime = build_translation_runtime(
            text_factory=Factory(error=RuntimeUnavailableError("text")),
            math_factory=Factory(error=RuntimeUnavailableError("math")),
        )

        self.assertIsInstance(runtime.text_translator, FallbackTextTranslator)
        self.assertIsInstance(runtime.math_translator, FallbackMathTranslator)

    def test_unexpected_factory_error_propagates(self) -> None:
        from adapters.translation.provider import build_translation_runtime

        with self.assertRaisesRegex(ValueError, "defect"):
            build_translation_runtime(
                text_factory=Factory(error=ValueError("defect")),
                math_factory=Factory(ClosableTranslator()),
            )

    def test_close_is_idempotent_and_closes_initialized_adapters(self) -> None:
        from adapters.translation.provider import build_translation_runtime

        text = ClosableTranslator()
        math = ClosableTranslator()
        runtime = build_translation_runtime(
            text_factory=Factory(text),
            math_factory=Factory(math),
        )

        runtime.close()
        runtime.close()

        self.assertEqual(text.close_calls, 1)
        self.assertEqual(math.close_calls, 1)

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
        louis_helper = InitializerModule("braille.louis_helper", error=ValueError("defect"))
        tables_module = types.ModuleType("braille.tables")
        tables_module.TABLES_DIR = "/tables"

        with ModuleBindings(
            {
                "braille": braille_module,
                "braille.louis_helper": louis_helper,
                "braille.tables": tables_module,
            }
        ):
            with self.assertRaisesRegex(ValueError, "defect"):
                provider.create_default_text_translator(platform="win32")

    def test_default_text_factory_normalizes_initialize_load_errors(self) -> None:
        from adapters.translation import provider

        braille_module = types.ModuleType("braille")
        tables_module = types.ModuleType("braille.tables")
        tables_module.TABLES_DIR = "/tables"

        for error in (ImportError("missing package"), OSError("missing DLL")):
            with self.subTest(error_type=type(error).__name__):
                louis_helper = InitializerModule("braille.louis_helper", error=error)
                with ModuleBindings(
                    {
                        "braille": braille_module,
                        "braille.louis_helper": louis_helper,
                        "braille.tables": tables_module,
                    }
                ):
                    with self.assertRaisesRegex(RuntimeUnavailableError, str(error)):
                        provider.create_default_text_translator(platform="win32")

    def test_default_text_factory_normalizes_native_adapter_import_error(self) -> None:
        from adapters.translation import provider

        with ModuleBindings({"adapters.translation.liblouis": None}):
            with self.assertRaises(RuntimeUnavailableError):
                provider.create_default_text_translator(platform="win32")

    def test_default_math_factory_normalizes_native_adapter_import_error(self) -> None:
        from adapters.translation import provider

        with ModuleBindings({"adapters.translation.mathcat": None}):
            with self.assertRaises(RuntimeUnavailableError):
                provider.create_default_math_translator(platform="win32")

    def test_default_math_factory_normalizes_native_runtime_errors(self) -> None:
        from adapters.translation import provider

        failing_adapter = InitializerModule("mathcat_adapter", error=MathCATError("missing MathCAT runtime"))

        with patch.object(provider, "get_shared_mathcat_adapter", return_value=failing_adapter):
            with self.assertRaisesRegex(RuntimeUnavailableError, "missing MathCAT runtime"):
                provider.create_default_math_translator(platform="win32")


if __name__ == "__main__":
    unittest.main()
