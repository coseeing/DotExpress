from __future__ import annotations

import logging
import sys
from collections.abc import Callable

from adapters.translation.contracts import RuntimeUnavailableError, TranslationRuntime
from adapters.translation.fallback import FallbackMathTranslator, FallbackTextTranslator
from conversion.mathcat_adapter import MathCATError, get_shared_mathcat_adapter
from log import get_logger


logger = get_logger("dotexpress.translation", "log/translation.log", level=logging.WARNING)


def _close_callback(adapter) -> Callable[[], None] | None:
    callback = getattr(adapter, "close", None)
    return callback if callable(callback) else None


def _log_runtime_fallback(capability: str, error: RuntimeUnavailableError) -> None:
    logger.warning(
        "Translation runtime fallback enabled | capability=%s | reason=%s",
        capability,
        error,
        exc_info=True,
    )


def build_translation_runtime(
    *,
    text_factory: Callable[[], object],
    math_factory: Callable[[], object],
) -> TranslationRuntime:
    callbacks = []
    try:
        text = text_factory()
    except RuntimeUnavailableError as error:
        _log_runtime_fallback("text", error)
        text = FallbackTextTranslator()
    else:
        callback = _close_callback(text)
        if callback is not None:
            callbacks.append(callback)

    try:
        math = math_factory()
    except RuntimeUnavailableError as error:
        _log_runtime_fallback("math", error)
        math = FallbackMathTranslator()
    else:
        callback = _close_callback(math)
        if callback is not None:
            callbacks.append(callback)

    return TranslationRuntime(
        text_translator=text,
        math_translator=math,
        close_callbacks=tuple(callbacks),
    )


def create_default_text_translator(
    *,
    platform: str | None = None,
):
    if (platform or sys.platform) != "win32":
        raise RuntimeUnavailableError("bundled liblouis requires Windows")

    try:
        from adapters.translation.liblouis import LiblouisTextTranslator
        from braille import louis_helper
        from braille.tables import TABLES_DIR

        louis_helper.initialize()
    except (ImportError, OSError) as error:
        raise RuntimeUnavailableError(str(error)) from error

    return LiblouisTextTranslator(
        helper=louis_helper,
        tables_dir=TABLES_DIR,
    )


def create_default_math_translator(
    *,
    platform: str | None = None,
):
    if (platform or sys.platform) != "win32":
        raise RuntimeUnavailableError("bundled MathCAT requires Windows")

    try:
        from adapters.translation.mathcat import MathCATMathTranslator
        from conversion.math_service import translate_math_segment

        get_shared_mathcat_adapter().initialize()
    except (ImportError, OSError, MathCATError) as error:
        raise RuntimeUnavailableError(str(error)) from error

    return MathCATMathTranslator(translate_math=translate_math_segment)


def build_default_translation_runtime() -> TranslationRuntime:
    return build_translation_runtime(
        text_factory=create_default_text_translator,
        math_factory=create_default_math_translator,
    )
