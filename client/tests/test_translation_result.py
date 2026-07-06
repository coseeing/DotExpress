from translate import TranslationResult


BLANK = chr(0x2800)


def test_bind_word_tokens_lead_punct() -> None:
	"""開頭字元測試"""
	result = TranslationResult(
		list("「嶼我共視"),
		["⠁", "⠂", "⠃", "⠄"],
		[0, 1, 2, 3],
		[0, 1, 2, 3],
	)
	result.bind_word_tokens()
	assert result.raw == [
		"「嶼",
		"我",
		"共",
		"視",
	]


def test_bind_word_tokens_lead_punct_continue() -> None:
	"""連續開頭字元測試"""
	result = TranslationResult(
		list("「「嶼我共視"),
		["⠁", "⠂", "⠃", "⠄", "⠅"],
		[0, 1, 2, 3, 4],
		[0, 1, 2, 3, 4],
	)
	result.bind_word_tokens()
	assert result.raw == [
		"「「嶼",
		"我",
		"共",
		"視",
	]


def test_bind_word_tokens_tail_punct() -> None:
	"""尾隨字元測試"""
	result = TranslationResult(
		list("嶼我共視」"),
		["⠁", "⠂", "⠃", "⠄", "⠅"],
		[0, 1, 2, 3, 4],
		[0, 1, 2, 3, 4],
	)
	result.bind_word_tokens()
	assert result.raw == [
		"嶼",
		"我",
		"共",
		"視」",
	]


def test_bind_word_tokens_tail_punct_continue() -> None:
	"""連續尾隨字元測試"""
	result = TranslationResult(
		list("嶼我共視。」"),
		["⠁", "⠂", "⠃", "⠄", "⠅", "⠆"],
		[0, 1, 2, 3, 4, 5],
		[0, 1, 2, 3, 4, 5],
	)
	result.bind_word_tokens()
	assert result.raw == [
		"嶼",
		"我",
		"共",
		"視。」",
	]


def test_bind_word_tokens_left_right_continue() -> None:
	"""右符號後接左符號插入空格"""
	result = TranslationResult(
		["「", "嶼", "我", "」", "「", "共", "視", "」"],
		["⠁", "⠂", "⠃", "⠄", "⠅", "⠆", "⠇", "⠈"],
		[0, 1, 2, 3, 4, 5, 6, 7],
		[0, 1, 2, 3, 4, 5, 6, 7],
	)
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
	result = TranslationResult(
		["『嶼", "我』", "「共", "視」"],
		["⠁", "⠂", "⠃", "⠄"],
		[0, 0, 1, 2],
		[0, 2, 3, 4],
	)
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
	result = TranslationResult(
		["「嶼我共視是一個關心數位無障礙」", "\n", "「嶼我共視是一個關心數位無障礙」"],
		[BLANK] * 40,
		[0] * 40,
		[0, 20, 20],
	)
	assert result.wrap(40)[1] == "「嶼我共視是一個關心數位無障礙」\n「嶼我共視是一個關心數位無障礙」"


def test_end_right_end_sentence_blank2() -> None:
	"""右符號/句尾符號加空白"""
	result = TranslationResult(
		["「嶼我共視 是個關心數位無障礙」", "\n", "「嶼我共視 是個關心數位無障礙」"],
		[BLANK] * 38,
		[0] * 38,
		[0, 19, 19],
	)
	assert result.wrap(40)[1] == "「嶼我共視 是個關心數位無障礙」 \n「嶼我共視 是個關心數位無障礙」"


def test_end_right_end_sentence_blank3() -> None:
	"""右符號/句尾符號加空白"""
	result = TranslationResult(
		["「嶼我」", "『共視』"],
		[BLANK] * 8,
		[0] * 8,
		[0, 4],
	)
	assert result.wrap(40)[1] == "「嶼我」 『共視』"


def test_remove_start_line_blank() -> None:
	"""行中的空格在排版後如果在行首需移除"""
	result = TranslationResult(
		["Coseeing is a community dedicated to an", " ", "I see"],
		[BLANK] * 45,
		[0] * 45,
		[0, 39, 40],
	)
	assert result.wrap(40)[1] == "Coseeing is a community dedicated to an\nI see"


def test_remove_start_line_blank2() -> None:
	"""行首的空格在排版後必定在行首，但不能移除"""
	result = TranslationResult(
		[" ", " ", " ", "Coseeing is a community dedicated to", " ", "I see"],
		[BLANK] * 45,
		[0] * 45,
		[0, 1, 2, 3, 40, 41],
	)
	assert result.wrap(40)[1] == "   Coseeing is a community dedicated to\nI see"


def test_bind_word_tokens_complex() -> None:
	result = TranslationResult(
		list("Hello,. We are Coseeing. Coseeing is a community dedicated to championing digital accessibility."),
		["⠁"] * 94,
		list(range(94)),
		list(range(94)),
	)
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
