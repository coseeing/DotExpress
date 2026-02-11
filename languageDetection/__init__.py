# -*- coding: utf-8 -*-

from collections import defaultdict
from io import StringIO
from typing import Optional
import config

# import config
# from synthDriverHandler import getSynth

from .blocks import BLOCKS, BLOCK_RSHIFT
# from .._speechcommand import WVLangChangeCommand

BASIC_LATIN = [
    u"en", u"ha", u"so", u"id", u"la", u"sw", u"eu",
    u"nr", u"zu", u"xh", u"ss", u"st", u"tn", u"ts"
]
EXTENDED_LATIN = [
    u"cs", u"af", u"pl", u"hr", u"ro", u"sk", u"sl", u"tr", u"hu", u"az",
    u"et", u"sq", u"ca", u"es", u"gl", u"fr", u"de", u"nl", u"it", u"da", u"is", u"nb", u"sv",
    u"fi", u"lv", u"pt", u"ve", u"lt", u"tl", u"cy", u"vi", "no"
]
ALL_LATIN = BASIC_LATIN + EXTENDED_LATIN

CYRILLIC = [u"ru", u"uk", u"kk", u"uz", u"mn", u"sr", u"mk", u"bg", u"ky"]
ARABIC = ["ar", "fa", "ps", "ur"]
CJK = ["zh", "ja", "ko"]

SINGLETONS = {
	"Armenian": "hy",
	"Hebrew": "he",
	"Bengali": "bn",
	"Gurmukhi": "pa",
	"Greek and Coptic": "el",
	"Gujarati": "gu",
	"Oriya": "or",
	"Tamil": "ta",
	"Telugu": "te",
	"Kannada": "kn",
	"Malayalam": "ml",
	"Sinhala": "si",
	"Thai": "th",
	"Lao": "lo",
	"Tibetan": "bo",
	"Myanmar": "my",
	"Georgian": "ka",
	"Mongolian": "mn",   # ← 改成純語言碼
	"Khmer": "km",
}

# Config keys to get languages to revert to, when in dobt
_configKeys = {'CJK Unified Ideographs': 'CJKCharactersLanguage'}
for charset in ('Basic Latin', 'Extended Latin', 'Latin Extended-B'):
	_configKeys[charset] = 'latinCharactersLanguage'

charsetMaps = {
	"latinCharactersLanguage": "en",
	"CJKCharactersLanguage": "zh",
	"arabicCharactersLanguage": "ar",
}

class LangChangeCommand:
	"""A command to switch the language within speech."""

	def __init__(self, lang: Optional[str]):
		"""
		@param lang: the language to switch to: If None then the NVDA locale will be used.
		"""
		self.lang = lang
		self.isDefault = not lang

	def __repr__(self):
		return "LangChangeCommand (%r)" % self.lang


class LanguageDetector(object):
	""" Provides functionality to add guessed language commands to NVDA speech sequences.
	Unicode ranges and user configuration are used to guess the language."""
	def __init__(self, availableLanguages, speechSymbols=None):
		self.speechSymbols = speechSymbols
		# 保留原始語言清單（含地區碼），供輸出時還原完整語系
		self.availableLanguagesFull = tuple(availableLanguages)
		# 偵測時僅使用語言碼（兩碼）
		availableLanguagesBase = frozenset(l.split("_")[0] for l in self.availableLanguagesFull)
		# Cache what are the unicode blocks supported by each language.
		# Only cache for languages we have available
		languageBlocks = defaultdict(lambda: [])

		# And japonese.
		if "ja" in availableLanguagesBase:
			languageBlocks["ja"].extend([
				"Kana",
				"Kana Supplement",
			])

		# Chinese (I have some dobts here).
		if "zh" in availableLanguagesBase:
			languageBlocks["zh"].extend([
				"Bopomofo",
				"Bopomofo Extended",
			])

		# If we have korian, store its blocks.
		if "ko" in availableLanguagesBase:
			languageBlocks["ko"].extend([
				"Hangul Syllables",
				"Hangul Jamo",
				"Hangul Compatibility Jamo",
				"Hangul Jamo Extended-A",
				"Hangul Jamo Extended-B",
			])

		# Same for greek.
		if "el" in availableLanguagesBase:
			languageBlocks["el"].extend([
				"Greek and Coptic",
				"Greek Extended",
			])

		# Basic latin and extended latin are considered the same... → 擴充一下拉丁相關
		for l in (set(ALL_LATIN) & availableLanguagesBase):
			languageBlocks[l].extend([
				"Basic Latin",
				"Extended Latin",			  # Latin-1 + Extended-A（你原本就有）
				"Latin Extended-B",
				"Latin Extended-C",
				"Latin Extended-D",
				"Latin Extended Additional",
				"IPA Extensions",
				"Spacing Modifier Letters",
				"Phonetic Extensions",
				"Phonetic Extensions Supplement",
			])

		# For arabic.
		for l in (set(ARABIC) & availableLanguagesBase):
			languageBlocks[l].extend([
				"Arabic",
				"Arabic Supplement",			# ← 新增
				"Arabic Presentation Forms-A",
				"Arabic Presentation Forms-B",
			])

		# For cjk.
		for l in (set(CJK) & availableLanguagesBase):
			languageBlocks[l].extend([
				"CJK Symbols and Punctuation",
				"CJK Unified Ideographs",
				"CJK Unified Ideographs Extension A",
				"CJK Unified Ideographs Extension B",
				"CJK Unified Ideographs Extension C",
				"CJK Unified Ideographs Extension D",
				"CJK Compatibility Ideographs",
				"CJK Compatibility Ideographs Supplement",
				"Halfwidth and Fullwidth Forms",
			])

		# Cyrillic
		for l in (set(CYRILLIC) & availableLanguagesBase):
			languageBlocks[l].extend([
				"Cyrillic",
				"Cyrillic Supplement",
				"Cyrillic Extended-B",
			])

		# Ad singletone languages (te only language for the range)
		for blockName, langCode in SINGLETONS.items():
			if langCode in availableLanguagesBase:
				languageBlocks[langCode].append(blockName)

		for k, v in languageBlocks.items():
			# Preserve order while dedup
			languageBlocks[k] = list(dict.fromkeys(v))

		self.languageBlocks = languageBlocks

		# cache a reversed version of the hash table too.
		blockLanguages = defaultdict(lambda: [])
		for k, v in languageBlocks.items():
			for i in v:
				blockLanguages[i].append(k)
		self.blockLanguages = blockLanguages

	def add_detected_language_commands(self, speechSequence):
		availableLanguagesBase = frozenset(l.split("_")[0] for l in self.availableLanguagesFull)
		yield LangChangeCommand(config.get_lang())
		sb = StringIO()
		charset = None
		# defaultLang = getSynth().language
		defaultLang = config.get_lang()
		curLang = defaultLang
		tmpLang = curLang.split("_")[0]
		for command in speechSequence:
			if isinstance(command, LangChangeCommand):
				if command.lang is None:
					curLang = defaultLang
				else:
					curLang = command.lang
				tmpLang = curLang.split("_")[0]
				yield command
				charset = None # Whatever will come, reset the charset.
			elif isinstance(command, str):
				sb = StringIO()
				command = str(command)
				prevInIgnore = False
				rule = False
				for c in command:
					if self.speechSymbols and c in self.speechSymbols.symbols:
						rule = True
						block = ord(c) >> BLOCK_RSHIFT
						try:
							newCharset = BLOCKS[block]
						except IndexError:
							newCharset = None
						charset = newCharset
						symbol = self.speechSymbols.symbols[c]
						c = symbol.replacement if symbol.replacement and c not in [str(i) for i in range(10)] else c
						if symbol.mode == 1:
							newLang = symbol.language
						else:
							newLang = tmpLang
						newLangFirst = newLang.split("_")[0]
						if newLangFirst == tmpLang:
							# Same old...
							sb.write(c)
							continue
						# Change language
						# First yield the string we already have.
						if sb.getvalue():
							yield sb.getvalue()
							sb = StringIO()
						tmpLang = newLangFirst
						charset = None
						# 以偏好的完整語系輸出（例如 zh -> zh_TW）
						target = self._preferred_full_lang(newLangFirst, curLang)
						yield LangChangeCommand(target)
						yield c
						continue

					# For non-alphanumeric characters, revert to  the currently set language if in the ASCII range
					block = ord(c) >> BLOCK_RSHIFT
					if c.isspace():
						sb.write(c)
						continue
					if False and (c.isdigit() or (not c.isalpha() and block <= 0x8)):
						# if config.conf["WorldVoice"]['autoLanguageSwitching']['ignoreNumbersInLanguageDetection'] and c.isdigit():
						if c.isdigit():
							sb.write(c)
							continue
						# if config.conf["WorldVoice"]['autoLanguageSwitching']['ignorePunctuationInLanguageDetection'] and not c.isdigit():
						if not c.isdigit():
							sb.write(c)
							continue
						if prevInIgnore and not rule:
							# Digits and ascii punctuation. We already calculated
							sb.write(c)
							continue
						prevInIgnore = True
						charset = None # Revert to default charset, we don't care here and  have to recheck later
						if tmpLang != curLang.split("_")[0]:
							if sb.getvalue():
								yield sb.getvalue()
								sb = StringIO()
							yield LangChangeCommand(curLang)
							tmpLang = curLang.split("_")[0]
						sb.write(c)
						continue

					# Process alphanumeric characters.
					prevInIgnore = False
					try:
						newCharset = BLOCKS[block]
					except IndexError:
						newCharset = None
					if not rule:
						if newCharset == charset:
							sb.write(c)
							continue
						charset = newCharset
						if charset in self.languageBlocks[tmpLang]:
							sb.write(c)
							continue
					else:
						charset = newCharset
					rule = False
					# Find the new language to use
					newLang = self.find_language_for_charset(charset, curLang)
					newLangFirst = newLang.split("_")[0]
					if newLangFirst == tmpLang:
						# Same old...
						sb.write(c)
						continue
					# Change language
					# First yield the string we already have.
					if sb.getvalue():
						yield sb.getvalue()
						sb = StringIO()
					tmpLang = newLangFirst
					# 以偏好的完整語系輸出（例如 zh -> zh_TW）
					target = self._preferred_full_lang(newLangFirst, curLang)
					yield LangChangeCommand(target)
					sb.write(c)
				# Send the string, if we have one:
				if sb.getvalue():
					yield sb.getvalue()
			else:
				yield command

	def find_language_for_charset(self, charset, curLang):
		langs = self.blockLanguages[charset]
		if not langs or curLang.split("_")[0] in langs:
			return curLang
		# See if we have any configured language for this charset.
		if charset in _configKeys:
			configKey = _configKeys[charset]
			lang = charsetMaps[configKey]
			return lang
		return langs[0]

	def _preferred_full_lang(self, base: str, curLang: Optional[str] = None) -> str:
		"""將兩碼語言（例如 zh）映射回偏好的完整語系（例如 zh_TW）。

		優先順序：
		1) 若 curLang 與 base 符合且含地區碼，回傳 curLang。
		2) 若 config.get_lang() 與 base 符合，回傳該完整值。
		3) 在初始化傳入的 availableLanguages 中尋找以 base_ 開頭的第一個；找不到則回傳 base 或與 base 完全相等者。
		"""
		# 1) 目前語系（含地區碼）優先
		if curLang and curLang.split("_")[0] == base and "_" in curLang:
			return curLang
		# 2) 全域設定偏好
		try:
			pref = config.get_lang()
			if pref and pref.split("_")[0] == base:
				return pref
		except Exception:
			pass
		# 3) 從可用清單中選擇最佳匹配
		best = None
		for lang in self.availableLanguagesFull:
			if lang.startswith(base + "_"):
				return lang
			if lang == base and best is None:
				best = base
		return best or base

	def process_for_spelling(self, text, locale=None):
		if locale is None:
			# defaultLang = getSynth().language
			defaultLang = config.get_lang()
		else:
			defaultLang = locale
		# 以完整語系作為目前語言（避免僅保留兩碼）
		curLang = defaultLang
		charset = None
		sb = StringIO()
		for c in text:
			block = ord(c) >> BLOCK_RSHIFT
			if c.isspace() or c.isdigit() or (not c.isalpha() and block <= 0x8):
				charset = None
				if curLang == defaultLang:
					sb.write(c)
				else:
					if sb.getvalue():
						yield sb.getvalue(), curLang
					curLang = defaultLang
					sb = StringIO()
					sb.write(c)
				continue
			try:
				newCharset = BLOCKS[block]
			except IndexError:
				newCharset = None
			if charset is None or charset != newCharset:
				tmpLang = curLang.split("_")[0]
				if newCharset in self.languageBlocks[tmpLang]:
					sb.write(c)
					continue
				base = self.find_language_for_charset(newCharset, tmpLang)
				charset = newCharset
				if base == tmpLang:
					sb.write(c)
					continue
				if sb.getvalue():
					yield sb.getvalue(), curLang
					sb = StringIO()
				sb.write(c)
				# 以偏好規則將兩碼 base（如 zh）還原為完整語系（如 zh_TW）
				curLang = self._preferred_full_lang(base, defaultLang)
			else: # same charset
				sb.write(c)
		if sb.getvalue():
			yield sb.getvalue(), curLang
