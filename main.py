import os

import louisHelper
from brailleTables import listTables
from languageDetection import LanguageDetector
from translate import translate
from gui import translate_with_language


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

# text2braille("c我們透過開發創新工具，讓視障者看見更多資訊和可能；透過舉辦推廣活動，讓大眾看見障礙者面臨的實際挑戰和需求。")
# text2braille("我們這一家")
# get_braille_table_list()
language_detector = LanguageDetector(["en", "zh_TW", "ja"])
# res = language_detector.add_detected_language_commands(["我們 Coseeing 透過開發創新工具，讓視障者看見更多資訊和可能；透過舉辦推廣活動，讓大眾看見障礙者面臨的實際挑戰和需求。希望以多元的形式與持續的行動，讓所有人都能共同看見這精采的世界以及獨特的彼此"])
# print(list(res))
text = "我們 Coseeing　 透過開發創新工具，讓視障者看見更多資訊和可能；透過舉辦推廣活動, 讓大眾看見障礙者面臨的實際挑戰和需求。希望以多元的形式與持續的行動，讓所有人都能共同看見這精采的世界以及獨特的彼此"
text = "I am a student. I want to school every day"
res = language_detector.add_detected_language_commands([text])
print(list(res))
r = translate_with_language("ja-rokutenkanji.utb", text)


# item = "我們 Coseeing 透過開發創新工具，讓視障者看見更多資訊和可能。"
# item = "我？！的"
# item = "coseeing.org"
# t = translate("zh-tw.ctb", item)
# print(f"raw: {len(t.raw)} {t.raw}")
# print(f"braille: {len(t.braille)} {t.braille}")
# print(f"braille_to_raw_pos: {len(t.braille_to_raw_pos)} {t.braille_to_raw_pos}")
# print(f"raw_to_braille_pos: {len(t.raw_to_braille_pos)} {t.raw_to_braille_pos}")
