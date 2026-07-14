import ctypes
import unittest
from pathlib import Path


if not hasattr(ctypes, "WINFUNCTYPE"):
	raise unittest.SkipTest("liblouis bindings require WINFUNCTYPE on this platform")

try:
	from braille import liblouis  # noqa: F401
except Exception as exc:
	raise unittest.SkipTest(f"liblouis bindings unavailable: {exc}") from exc

from adapters.translation.provider import build_default_translation_runtime
from config import DEFAULT_TRANSLATION_TABLES
from conversion.service import translate_with_language


BASE_DIR = Path(__file__).resolve().parents[1]


def test_add_blank_between_language_change() -> None:
	runtime = build_default_translation_runtime()
	try:
		result = translate_with_language(
			"zh-tw.ctb",
			"嶼我I起",
			BASE_DIR / "dictionary" / "default.csv",
			DEFAULT_TRANSLATION_TABLES,
			BASE_DIR / "data" / "Bopomofo2Braille.csv",
			runtime=runtime,
		)
	finally:
		runtime.close()
	assert "".join(result.raw) == "嶼我 I 起"
