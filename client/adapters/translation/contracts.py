from __future__ import annotations

# The translation ports belong to their consumer, the conversion package; they are
# re-exported here so that adapters.translation keeps its names.
from conversion.contracts import BrailleTextTranslator, MathSegmentTranslator, TranslationRuntime


class RuntimeUnavailableError(RuntimeError):
    pass


__all__ = [
    "BrailleTextTranslator",
    "MathSegmentTranslator",
    "RuntimeUnavailableError",
    "TranslationRuntime",
]
