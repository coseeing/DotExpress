import ctypes

import pytest


if not hasattr(ctypes, "WINFUNCTYPE"):
	pytest.skip("liblouis bindings require WINFUNCTYPE on this platform", allow_module_level=True)

from translate import translate


def test_bind_word_tokens_lead_punct() -> None:
	"""開頭字元測試"""
	text = (
		"「嶼我共視"
	)
	result = translate("zh-tw.ctb", text)
	result.bind_word_tokens()
	assert result.raw == [
		"「嶼",
		"我",
		"共",
		"視",
	]


def test_bind_word_tokens_lead_punct_continue() -> None:
	"""連續開頭字元測試"""
	text = (
		"「「嶼我共視"
	)
	result = translate("zh-tw.ctb", text)
	result.bind_word_tokens()
	assert result.raw == [
		"「「嶼",
		"我",
		"共",
		"視",
	]


def test_bind_word_tokens_tail_punct() -> None:
	"""尾隨字元測試"""
	text = (
		"嶼我共視」"
	)
	result = translate("zh-tw.ctb", text)
	result.bind_word_tokens()
	assert result.raw == [
		"嶼",
		"我",
		"共",
		"視」",
	]


def test_bind_word_tokens_tail_punct_continue() -> None:
	"""連續尾隨字元測試"""
	text = (
		"嶼我共視。」"
	)
	result = translate("zh-tw.ctb", text)
	result.bind_word_tokens()
	assert result.raw == [
		"嶼",
		"我",
		"共",
		"視。」",
	]


def test_bind_word_tokens_left_right_continue() -> None:
	"""右符號後接左符號插入空格"""
	text = (
		"「嶼我」「共視」"
	)
	result = translate("zh-tw.ctb", text)
	# result.bind_word_tokens()
	result.reclean_token()
	assert result.raw == [
		"「",
		"嶼",
		"我",
		"」",
		" ",
		"「",
		"共",
		"視",
		"」",
	]


def test_bind_word_tokens_left_right_continue2() -> None:
	"""右符號後接左符號插入空格"""
	text = (
		"『嶼我』「共視」"
	)
	result = translate("zh-tw.ctb", text)
	result.bind_word_tokens()
	result.reclean_token()
	assert result.raw == [
		"『嶼",
		"我』",
		" ",
		"「共",
		"視」",
	]


def test_end_right_end_sentence_blank() -> None:
	"""右符號/句尾符號加空白"""
	# testcase1: 剛好填滿，不加空白
	text = (
		"「嶼我共視是一個關心數位無障礙」\n「嶼我共視是一個關心數位無障礙」"
	)
	result = translate("zh-tw.ctb", text)
	result.bind_word_tokens()
	result.reclean_token()
	assert result.wrap(40)[1] == "「嶼我共視是一個關心數位無障礙」\n「嶼我共視是一個關心數位無障礙」"


def test_end_right_end_sentence_blank2() -> None:
	"""右符號/句尾符號加空白"""
	# testcase2: 剛好差一格，加空白
	text = (
		"「嶼我共視 是個關心數位無障礙」\n「嶼我共視 是個關心數位無障礙」"
	)
	result = translate("zh-tw.ctb", text)
	result.bind_word_tokens()
	result.reclean_token()
	assert result.wrap(40)[1] == "「嶼我共視 是個關心數位無障礙」 \n「嶼我共視 是個關心數位無障礙」"


def test_end_right_end_sentence_blank3() -> None:
	"""右符號/句尾符號加空白"""
	# testcase3: 
	text = (
		"「嶼我」『共視』"
	)
	result = translate("zh-tw.ctb", text)
	result.bind_word_tokens()
	result.reclean_token()
	assert result.wrap(40)[1] == "「嶼我」 『共視』"


def test_remove_start_line_blank() -> None:
	"""行中的空格在排版後如果在行首需移除"""
	text = (
		"Coseeing is a community dedicated to an I see"
	)
	result = translate("en-ueb-g1.ctb", text)
	result.bind_word_tokens()
	result.reclean_token()
	assert result.wrap(40)[1] == "Coseeing is a community dedicated to an\nI see"


def test_remove_start_line_blank2() -> None:
	"""行首的空格在排版後必定在行首，但不能移除"""
	# 
	text = (
		"   Coseeing is a community dedicated to I see"
	)
	result = translate("en-ueb-g1.ctb", text)
	result.bind_word_tokens()
	result.reclean_token()
	assert result.wrap(40)[1] == "   Coseeing is a community dedicated to\nI see"


def test_bind_word_tokens_complex() -> None:
	text = (
		"Hello,. We are Coseeing. Coseeing is a community dedicated to "
		"championing digital accessibility."
	)
	result = translate("zh-tw.ctb", text)
	result.bind_word_tokens()
	assert result.raw == [
		"Hello,.",
		" ",
		"We",
		" ",
		"are",
		" ",
		"Coseeing.",
		" ",
		"Coseeing",
		" ",
		"is",
		" ",
		"a",
		" ",
		"community",
		" ",
		"dedicated",
		" ",
		"to",
		" ",
		"championing",
		" ",
		"digital",
		" ",
		"accessibility.",
	]


def test_addition_concatenates_results() -> None:
	t1 = translate("zh-tw.ctb", "我們透過開發創新工具")
	t2 = translate("zh-tw.ctb", "我們透過舉辦推廣活動")
	t3 = translate("zh-tw.ctb", "我們透過開發創新工具我們透過舉辦推廣活動")

	assert t1 + t2 == t3
