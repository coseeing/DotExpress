import os

import louisHelper
from brailleTables import listTables
from languageDetection import LanguageDetector
from translate import translate
from gui import translate_with_language, translate_and_wrap_both


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TABLES_DIR = os.path.join(BASE_DIR, "louis", "tables")


## text translate braille
def text2braille(string):
	BRAILLE_UNICODE_PATTERNS_START = 0x2800
	braille_cells, braille_to_raw_pos, raw_to_braille_pos, braille_cursor_pos = louisHelper.translate([os.path.join(TABLES_DIR, "zh-tw.ctb"), "braille-patterns.cti"], string, mode=4)
	braille_cells = [chr(b + BRAILLE_UNICODE_PATTERNS_START) for b in braille_cells]

	print(f"braille_cells: {len(braille_cells)} {braille_cells}")
	print(f"braille_to_raw_pos: {len(braille_to_raw_pos)} {braille_to_raw_pos}")
	print(f"raw_to_braille_pos: {len(raw_to_braille_pos)} {raw_to_braille_pos}")
	if braille_cursor_pos:
		print(f"braille_cursor_pos: {len(braille_cursor_pos)} {braille_cursor_pos}")

# get braille table list
def get_braille_table_list():
	display_names = [i.displayName for i in listTables()]
	print(display_names)

# get_braille_table_list()
language_detector = LanguageDetector(["en", "zh"])
text = "我們 Coseeing　 透過開發創新工具，讓視障者看見更多資訊和可能；透過舉辦推廣活動, 讓大眾看見障礙者面臨的實際挑戰和需求。希望以多元的形式與持續的行動，讓所有人都能共同看見這精采的世界以及獨特的彼此"
text = """  但只要見到你，任誰都得劍拔弩張。
  ──德國劇作家與詩人布希萊特（Bertolt Bercht, 1898-1956）

p.15

    第一章 正義的殿堂
"""

res = language_detector.add_detected_language_commands([text])
# print(list(res))

r = translate_and_wrap_both("zh-tw.ctb", text, 40)
print(r)
