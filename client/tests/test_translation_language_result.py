import ctypes

import pytest


if not hasattr(ctypes, "WINFUNCTYPE"):
	pytest.skip("liblouis bindings require WINFUNCTYPE on this platform", allow_module_level=True)

from gui import translate_with_language, translate_and_wrap_both


def test_add_blank_between_language_change() -> None:
	"""在點字系統轉換前加入空白，如果上一片段結尾沒有空白"""
	text = (
		"嶼我I起"
	)
	result = translate_with_language("zh-tw.ctb", text)
	assert "".join(result.raw) == "嶼我 I 起"


def test_blank_on_start_line() -> None:
	"""移除開頭的空白"""
	text = (
		"I am a student. I want to school every day"
	)
	result = translate_and_wrap_both("zh-tw.ctb", text, 40)
	# result.bind_word_tokens()
	# result.reclean_token()
	assert result[1] == "I am a student. I want to school every\nday"

