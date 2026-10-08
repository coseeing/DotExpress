import sys
import types
import unittest
from contextlib import contextmanager
from functools import partial
from unittest.mock import patch

from adapters.translation.contracts import RuntimeUnavailableError
from adapters.translation.fallback import FallbackMathTranslator, FallbackTextTranslator
from conversion.math_service import latex_to_mathml
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


class RecordingMathCATAdapter:
    def __init__(
        self,
        cells: str = "\u283c\u2801",
        initialize_error: Exception | None = None,
        events: list[str] | None = None,
    ) -> None:
        self.cells = cells
        self.initialize_error = initialize_error
        self.events = events if events is not None else []
        self.initialize_calls = 0
        self.close_calls = 0
        self.braille_calls = []

    def initialize(self) -> None:
        self.initialize_calls += 1
        self.events.append("mathcat.initialize")
        if self.initialize_error is not None:
            raise self.initialize_error

    def get_braille_for_mathml(self, mathml_text, braille_code=None, *, language):
        self.events.append("mathcat.translate")
        self.braille_calls.append((mathml_text, braille_code, language))
        return self.cells

    def close(self) -> None:
        self.close_calls += 1
        self.events.append("mathcat.close")


@contextmanager
def default_math_translator(adapter):
    """Build the default math translator for "win32" around ``adapter``."""
    from adapters.translation import provider

    yield provider.create_default_math_translator(platform="win32", adapter_factory=lambda: adapter)


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

        failing_adapter = RecordingMathCATAdapter(initialize_error=MathCATError("missing MathCAT runtime"))

        with self.assertRaisesRegex(RuntimeUnavailableError, "missing MathCAT runtime"):
            provider.create_default_math_translator(platform="win32", adapter_factory=lambda: failing_adapter)

        self.assertEqual(failing_adapter.close_calls, 1)

    def test_default_math_translator_initializes_once_and_translates_through_the_adapter(self) -> None:
        adapter = RecordingMathCATAdapter()

        with default_math_translator(adapter) as translator:
            self.assertEqual(adapter.events, ["mathcat.initialize"])
            result = translator.translate("1", braille_code="Nemeth", language="en")

        self.assertEqual(adapter.initialize_calls, 1)
        self.assertEqual(adapter.braille_calls, [(latex_to_mathml("1"), "Nemeth", "en")])
        self.assertEqual(result.raw, ["1"])
        self.assertEqual(result.braille, ["\u283c", "\u2801"])
        self.assertEqual(result.raw_to_braille_pos, [0])
        self.assertEqual(result.braille_to_raw_pos, [0, 0])

    def test_unexpected_math_initialize_error_closes_the_adapter_and_propagates(self) -> None:
        from adapters.translation import provider

        adapter = RecordingMathCATAdapter(initialize_error=ValueError("defect"))

        with self.assertRaisesRegex(ValueError, "defect"):
            provider.create_default_math_translator(platform="win32", adapter_factory=lambda: adapter)

        self.assertEqual(adapter.close_calls, 1)

    def test_each_default_math_translator_gets_its_own_adapter(self) -> None:
        from adapters.translation import provider

        adapters = [RecordingMathCATAdapter("\u2801"), RecordingMathCATAdapter("\u2803")]
        factory = iter(adapters).__next__

        first = provider.create_default_math_translator(platform="win32", adapter_factory=factory)
        second = provider.create_default_math_translator(platform="win32", adapter_factory=factory)

        self.assertEqual(first.translate("1", braille_code="UEB", language="en").braille, ["\u2801"])
        self.assertEqual(second.translate("1", braille_code="UEB", language="en").braille, ["\u2803"])
        first.close()
        self.assertEqual([adapter.initialize_calls for adapter in adapters], [1, 1])
        self.assertEqual([adapter.close_calls for adapter in adapters], [1, 0])

    def test_default_adapter_factory_builds_a_fresh_bundled_adapter(self) -> None:
        from adapters.translation import provider
        from conversion.mathcat_adapter import MathCATAdapter, get_default_mathcat_resource_root

        first = provider._create_mathcat_adapter()
        second = provider._create_mathcat_adapter()
        recorded = RecordingMathCATAdapter()
        with patch.object(provider, "_create_mathcat_adapter", return_value=recorded):
            provider.create_default_math_translator(platform="win32")

        self.assertIsInstance(first, MathCATAdapter)
        self.assertEqual(first.resource_root, get_default_mathcat_resource_root())
        self.assertIsNot(first, second)
        self.assertEqual(recorded.initialize_calls, 1)

    def test_runtime_close_closes_mathcat_before_liblouis(self) -> None:
        from adapters.translation import provider

        events = []
        adapter = RecordingMathCATAdapter(events=events)
        louis_helper = InitializerModule("braille.louis_helper")
        louis_helper.terminate = lambda: events.append("louis.terminate")
        tables_module = types.ModuleType("braille.tables")
        tables_module.TABLES_DIR = "/tables"

        with ModuleBindings(
            {
                "braille": types.ModuleType("braille"),
                "braille.louis_helper": louis_helper,
                "braille.tables": tables_module,
            }
        ):
            runtime = provider.build_translation_runtime(
                text_factory=partial(provider.create_default_text_translator, platform="win32"),
                math_factory=partial(
                    provider.create_default_math_translator,
                    platform="win32",
                    adapter_factory=lambda: adapter,
                ),
            )
        runtime.close()
        runtime.close()

        self.assertEqual(events, ["mathcat.initialize", "mathcat.close", "louis.terminate"])
        self.assertEqual(adapter.close_calls, 1)
        self.assertEqual(louis_helper.calls, 1)


if __name__ == "__main__":
    unittest.main()
