"""Time reclean_braille_endspace on real zh-tw.ctb output (Windows source run).

Usage (repo root): client/.venv/Scripts/python.exe <this file> <out_dir> 100 400 1600
"""
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
CLIENT = HERE.parents[3] / "client"
sys.path.insert(0, str(CLIENT))
OUT = Path(sys.argv[1])

from braille import louis_helper  # noqa: F401  load the bundled DLL first
from adapters.translation.provider import build_default_translation_runtime
from config import DEFAULT_CHARSET_MAPS, DEFAULT_TRANSLATION_TABLES
from conversion import wrapping
from conversion.service import translate_with_language_segments
import translate as translate_mod

PARAGRAPH = "第一章　緒論。請說明你的理由，並且（如果可以）提供範例。這是一段用來測試效能的中文段落，包含標點符號。\n"

timing = {}
original = translate_mod.TranslationResult.reclean_braille_endspace


def timed(self):
	start = time.perf_counter()
	original(self)
	timing["reclean"] = time.perf_counter() - start


translate_mod.TranslationResult.reclean_braille_endspace = timed

runtime = build_default_translation_runtime()
try:
	for repeat in (int(arg) for arg in sys.argv[2:]):
		text = PARAGRAPH * repeat
		t0 = time.perf_counter()
		segments = translate_with_language_segments(
			text, OUT / "no-such-dictionary.csv", dict(DEFAULT_TRANSLATION_TABLES),
			CLIENT / "data" / "Bopomofo2Braille.csv",
			runtime=runtime, lang="zh_TW", charset_maps=dict(DEFAULT_CHARSET_MAPS),
		)
		t1 = time.perf_counter()
		wrapping.wrap_translation_results(segments, 40)
		t2 = time.perf_counter()
		print(f"chars={len(text):>7} translate={t1 - t0:6.2f}s wrap={t2 - t1:6.2f}s reclean={timing['reclean']:6.2f}s")
finally:
	runtime.close()
