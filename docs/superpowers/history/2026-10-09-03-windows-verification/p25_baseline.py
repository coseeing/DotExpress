"""P2-5 baseline on real liblouis/MathCAT (Windows source run).

Usage (repo root): client/.venv/Scripts/python.exe <this file> <out_dir>
Writes p25_unicode.brl / p25_ascii.brl into out_dir and prints:
  A. zh-tw.ctb cells for one call vs split calls
  B. the P2-5 failing-test input through the real pipeline
  C. BRL sha256 and reclean_braille_endspace trims for p25_doc.txt
"""
import hashlib
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CLIENT = HERE.parents[3] / "client"
sys.path.insert(0, str(CLIENT))
OUT = Path(sys.argv[1])
OUT.mkdir(parents=True, exist_ok=True)

from braille import louis_helper  # load the bundled DLL before anything else
from braille.tables import TABLES_DIR
from adapters.translation.provider import build_default_translation_runtime
from config import DEFAULT_CHARSET_MAPS, DEFAULT_TRANSLATION_TABLES
from conversion.service import ConversionRequest, convert_text_with_alignment, translate_with_language
import translate as translate_mod

LANG = "zh_TW"
CHARSET = dict(DEFAULT_CHARSET_MAPS)
NO_DICTIONARY = OUT / "no-such-dictionary.csv"  # missing path -> no dictionary rules
BOPOMOFO = CLIENT / "data" / "Bopomofo2Braille.csv"

louis_helper.initialize()
zh = str(Path(TABLES_DIR) / "zh-tw.ctb")


def cells(text):
	c, b2r, r2b, _ = louis_helper.translate([zh], text, mode=4)
	return "".join(chr(0x2800 + x) for x in c), list(b2r), list(r2b)


print("== A. liblouis one call vs split calls (zh-tw.ctb, mode=4)")
for whole, parts in [(" 的值", [" ", "的值"]), ("  中文", ["  ", "中文"]), ("計算 ", ["計算", " "])]:
	one, b2r, r2b = cells(whole)
	split = "".join(cells(p)[0] for p in parts)
	print(f"{whole!r}: one={one!r} split={split!r} identical={one == split} b2r={b2r} r2b={r2b}")

trims = {}
original = translate_mod.TranslationResult.reclean_braille_endspace


def counting(self):
	blank = chr(0x2800)
	pos = list(self.raw_to_braille_pos)
	total = len(self.braille)
	for t in range(len(self.raw)):
		s = pos[t] if t < len(pos) else total
		e = pos[t + 1] if t + 1 < len(pos) else total
		if e - s > 1 and self.braille[e - 1] == blank:
			trims["which"].append((self.raw[t], "".join(self.braille[s:e])))
	original(self)
	trims["cells_removed"] += total - len(self.braille)


translate_mod.TranslationResult.reclean_braille_endspace = counting

runtime = build_default_translation_runtime()
try:
	print("\n== B. P2-5 failing-test input through the real pipeline")
	result = translate_with_language(
		"計算 $1+2$ 的值", NO_DICTIONARY, dict(DEFAULT_TRANSLATION_TABLES), BOPOMOFO,
		runtime=runtime, lang=LANG, charset_maps=CHARSET,
	)
	print("raw tokens:", result.raw)
	print("braille:", "".join(result.braille))

	print("\n== C. long mixed document (p25_doc.txt, width 40)")
	doc = (HERE / "p25_doc.txt").read_text(encoding="utf-8")
	for mode in ("unicode", "ascii"):
		trims.clear()
		trims.update(which=[], cells_removed=0)
		out = convert_text_with_alignment(
			ConversionRequest(
				raw_text=doc, output_mode=mode, width=40, dictionary_path=NO_DICTIONARY,
				data_dir=CLIENT / "data", translation_tables=dict(DEFAULT_TRANSLATION_TABLES),
				lang=LANG, charset_maps=CHARSET,
			),
			runtime=runtime,
		)
		# Path.write_text on Windows translates \n to \r\n, as the BRL export does.
		brl = out.display_text.replace("\n", "\r\n").encode("utf-8")
		(OUT / f"p25_{mode}.brl").write_bytes(brl)
		print(f"mode={mode} sha256={hashlib.sha256(brl).hexdigest()} trims={len(trims['which'])} cells_removed={trims['cells_removed']}")
		print("  trimmed:", trims["which"])
finally:
	runtime.close()
