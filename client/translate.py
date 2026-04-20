import os
import string
from typing import Sequence, Tuple, TypeVar

import louisHelper
from char import build_language_blocks, language_has_char, language_has_all


TranslationResult = Tuple[str, str, Sequence[int], Sequence[int]]
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TABLES_DIR = os.path.join(BASE_DIR, "louis", "tables")
BRAILLE_UNICODE_PATTERNS_START = 0x2800


class TranslationResult:
	def __init__(self, raw, braille, braille_to_raw_pos, raw_to_braille_pos):
		self.raw = raw
		self.braille = braille
		self.braille_to_raw_pos = braille_to_raw_pos
		self.raw_to_braille_pos = raw_to_braille_pos

		self.LEFT_PUNCT_HALF = set("([{")
		self.RIGHT_PUNCT_HALF = set(")]}")
		self.MIDDLE_SENTENCE_PUNCT_HALF = set(",;:%")
		self.END_SENTENCE_PUNCT_HALF = set(".!?")

		self.LEFT_PUNCT_FULL = set("‘“「『〈《【〔〖（")
		self.RIGHT_PUNCT_FULL = set("’”」』〉》】〕〗）")
		self.MIDDLE_SENTENCE_PUNCT_FULL = set("，；：、％")
		self.END_SENTENCE_PUNCT_FULL = set("。！？")

		self.LEFT_PUNCT = self.LEFT_PUNCT_HALF | self.LEFT_PUNCT_FULL
		self.RIGHT_PUNCT = self.RIGHT_PUNCT_HALF | self.RIGHT_PUNCT_FULL
		self.MIDDLE_SENTENCE_PUNCT = self.MIDDLE_SENTENCE_PUNCT_HALF | self.MIDDLE_SENTENCE_PUNCT_FULL
		self.END_SENTENCE_PUNCT = self.END_SENTENCE_PUNCT_HALF | self.END_SENTENCE_PUNCT_FULL

		self.lang_blocks = build_language_blocks({"ja", "zh", "ko"})

	def __add__(self, other):
		if not isinstance(other, TranslationResult):
			raise TypeError("not TranslateResult object")

		raw_offset = len(self.raw)
		braille_offset = len(self.braille)

		raw = self.raw + other.raw
		braille = self.braille + other.braille
		braille_to_raw_pos = (
			list(self.braille_to_raw_pos)
			+ [pos + raw_offset for pos in other.braille_to_raw_pos]
		)
		raw_to_braille_pos = (
			list(self.raw_to_braille_pos)
			+ [pos + braille_offset for pos in other.raw_to_braille_pos]
		)

		return TranslationResult(raw, braille, braille_to_raw_pos, raw_to_braille_pos)

	def __eq__(self, other):
		result = True
		result &= (self.raw == other.raw)
		result &= (self.braille == other.braille)
		result &= (self.braille_to_raw_pos == other.braille_to_raw_pos)
		result &= (self.raw_to_braille_pos == other.raw_to_braille_pos)
		return result

	def bind_word_tokens(self):
		"""
		將 self.raw（list[str]，每個元素為單一字元）重新切成「詞級 token」，並重建對應表：
		  1) 只有連續 ASCII 英文/數字（A–Z a–z 0–9）會合併為單一 token（例："C","o","s" → "Cos"）。
		  2) CJK（中/日/韓：含漢字、假名、Hangul、注音等）不合併：每個字元是獨立 token，
			 但可參與「尾隨/開頭標點」的綁定。
		  3) '\n' 保留為獨立 token（硬換行）。
		  4) 連續「尾隨標點」會併到前一個「字母 token」（ASCII 字/數字詞 或 單一 CJK 字）。
		  5) 連續「開頭標點」會併到後一個「字母 token」（不與 '\n' 或空白綁定）。
	
		CJK 判斷使用 language_has_all(lang, ch, lang_blocks)：
		  - 只要屬於 ("ja","zh","ko") 任一語系的區塊即視為 CJK 字母字元（但不合併成詞）。
		若未提供 self.lang_blocks，則僅依 ASCII 與標點規則處理。
	
		最後將對應表從「字元級」升級為「token 級」：
		  - self.raw_to_braille_pos：token_index → 該 token 第一個字元的 braille 起始索引
		  - self.braille_to_raw_pos：braille_index → token_index
		"""

		# 取得語系對應 blocks

		lang_blocks = getattr(self, "lang_blocks", None)

		# ---- 判斷是否為 CJK/假名/注音/韓文等字母字元（不合併成詞，但可吃標點）----
		def is_cjk_word_char(ch: str) -> bool:
			if not lang_blocks:
				return False
			for _lang in ("ja", "zh", "ko"):
				if language_has_all(_lang, ch, lang_blocks):
					return True
			return False

		# ---- ASCII 英數集合（可合併成詞）----
		ASCII_ALNUM = set(string.ascii_letters + string.digits)

		# 會併到「前一個字母 token」的尾隨標點（避免出現在行首）
		TRAIL_PUNCT = self.RIGHT_PUNCT | self.MIDDLE_SENTENCE_PUNCT | self.END_SENTENCE_PUNCT
		# 會併到「後一個字母 token」的開頭標點（避免出現在行尾）
		LEAD_PUNCT = set(self.LEFT_PUNCT) | set("—")

		chars = self.raw  # list[str]（每元素一字元）
		n_chars = len(chars)

		# ---- Pass 1：產生基礎 tokens ----
		# 規則：
		#   - 連續 ASCII 英數 → 合併為一個 token
		#   - CJK/假名/注音/韓文 → 單字一 token（不合併）
		#   - 其他（空白/標點/符號…）→ 單字一 token
		#   - '\n' → 獨立 token
		tokens: list[str] = []
		token_char_spans: list[tuple[int, int]] = []  # (char_start, char_end_exclusive)

		i = 0
		while i < n_chars:
			ch = chars[i]
			if ch == "\n":
				tokens.append("\n")
				token_char_spans.append((i, i + 1))
				i += 1
				continue

			if ch in ASCII_ALNUM:
				j = i + 1
				while j < n_chars and chars[j] in ASCII_ALNUM:
					j += 1
				tokens.append("".join(chars[i:j]))
				token_char_spans.append((i, j))
				i = j
				continue

			if is_cjk_word_char(ch):
				tokens.append(ch)
				token_char_spans.append((i, i + 1))
				i += 1
				continue

			# 其他：空白/標點/符號等，單字元 token
			tokens.append(ch)
			token_char_spans.append((i, i + 1))
			i += 1

		# ---- 定義「字母 token」：可被尾隨/開頭標點綁定的 token ----
		#   A) 含任一 ASCII_ALNUM 的 ASCII 詞
		#   B) 長度為 1 且為 CJK 字母字元
		def is_word_token(tok: str) -> bool:
			if any(c in ASCII_ALNUM for c in tok):
				return True
			return len(tok) == 1 and is_cjk_word_char(tok)

		# ---- Pass 2：尾隨標點鏈併入前一個字母 token ----
		merged_tokens: list[str] = []
		merged_spans: list[tuple[int, int]] = []
		t = 0
		while t < len(tokens):
			tok = tokens[t]
			span_start, span_end = token_char_spans[t]

			if is_word_token(tok):
				u = t
				trailing_text = ""
				trailing_end = span_end
				# 貪婪吸收連續尾隨標點
				while (
					u + 1 < len(tokens)
					and len(tokens[u + 1]) == 1
					and tokens[u + 1] in TRAIL_PUNCT
				):
					u += 1
					trailing_text += tokens[u]
					trailing_end = token_char_spans[u][1]
				if trailing_text:
					tok = tok + trailing_text
					span_end = trailing_end
					t = u  # 跳過吃掉的尾隨標點

			merged_tokens.append(tok)
			merged_spans.append((span_start, span_end))
			t += 1

		tokens = merged_tokens
		token_char_spans = merged_spans

		# ---- Pass 3：開頭標點鏈併到下一個字母 token ----
		# 不與 '\n' 或空白（含全形空白等 .isspace()）綁定
		merged_tokens2: list[str] = []
		merged_spans2: list[tuple[int, int]] = []
		t = 0
		while t < len(tokens):
			tok = tokens[t]
			span_start, span_end = token_char_spans[t]

			if len(tok) == 1 and tok in LEAD_PUNCT and t + 1 < len(tokens):
				u = t
				lead_text = tok
				lead_start = span_start
				lead_end = span_end

				# 收集連續的開頭標點
				while (
					u + 1 < len(tokens)
					and len(tokens[u + 1]) == 1
					and tokens[u + 1] in LEAD_PUNCT
				):
					u += 1
					lead_text += tokens[u]
					lead_end = token_char_spans[u][1]

				# 嘗試與下一個可綁定的「字母 token」合併
				if u + 1 < len(tokens):
					next_tok = tokens[u + 1]
					if next_tok != "\n" and not (len(next_tok) == 1 and next_tok.isspace()):
						if is_word_token(next_tok):
							merged_tokens2.append(lead_text + next_tok)
							merged_spans2.append((lead_start, token_char_spans[u + 1][1]))
							t = u + 2
							continue

				# 無法綁定則保留開頭標點鏈
				merged_tokens2.append(lead_text)
				merged_spans2.append((lead_start, lead_end))
				t = u + 1
				continue

			# 其他情況原樣輸出
			merged_tokens2.append(tok)
			merged_spans2.append((span_start, span_end))
			t += 1

		tokens = merged_tokens2
		token_char_spans = merged_spans2

		# ---- 從「字元級」對應表升級為「token 級」對應表 ----
		old_r2b = self.raw_to_braille_pos		# 字元級：char_idx -> braille_start_pos
		old_b2r = self.braille_to_raw_pos		# 字元級：braille_pos -> char_idx
		braille_len = len(self.braille)

		# 防禦：長度不一致時維持原狀（避免 IndexError）
		if not old_r2b or n_chars == 0 or len(old_b2r) != braille_len:
			return

		# token → braille 起始（取 token 第一個字元的起點）
		new_raw_to_braille_pos: list[int] = [old_r2b[c_start] for (c_start, _c_end) in token_char_spans]

		# 字元索引 → token 索引
		char_to_token_idx = [0] * n_chars
		for t_idx, (c_start, c_end) in enumerate(token_char_spans):
			for c in range(c_start, c_end):
				char_to_token_idx[c] = t_idx

		# braille 索引 → token 索引（從舊的字元級映射轉換）
		new_braille_to_raw_pos: list[int] = []
		for bpos in range(braille_len):
			char_idx = old_b2r[bpos]
			if 0 <= char_idx < n_chars:
				new_braille_to_raw_pos.append(char_to_token_idx[char_idx])
			else:
				new_braille_to_raw_pos.append(0)

		# ---- 覆寫為 token 級結構 ----
		self.raw = tokens
		self.raw_to_braille_pos = new_raw_to_braille_pos
		self.braille_to_raw_pos = new_braille_to_raw_pos

	def insert_token(self, idx: int, text: str, braille):
		"""
		在 token 級別插入一個新 token 與其對應的點字片段。
		- idx: 以 token 為單位的插入位置（0..len(self.raw)）
		- text: 插入到 self.raw 的單一 token 文字
		- braille: 對應點字。可為 str（會以 list(braille) 拆成一格一格）或 list[str]
		"""
		if not (0 <= idx <= len(self.raw)):
			raise IndexError(f"idx out of range: {idx}")

		# 正規化 braille 片段型態為 list[str]
		braille_cells = list(braille)
		ins_b_len = len(braille_cells)

		# 計算點字插入位置（braille-index）。
		# 若插在中間，使用該 token 的起始點字索引；
		# 若插在尾端，等於目前點字長度。
		if idx < len(self.raw):
			b_ins = self.raw_to_braille_pos[idx]
		else:
			b_ins = len(self.braille)

		# 1) 實際插入 self.raw 與 self.braille
		self.raw = self.raw[:idx] + [text] + self.raw[idx:]
		self.braille = self.braille[:b_ins] + braille_cells + self.braille[b_ins:]

		# 2) 更新 raw_to_braille_pos（token_index -> 該 token 的點字起始位置）
		old_r2b = self.raw_to_braille_pos
		new_r2b = [0] * len(self.raw)
		#   - idx 之前：不變
		for i in range(idx):
			new_r2b[i] = old_r2b[i]
		#   - 新插入位置：就是 b_ins
		new_r2b[idx] = b_ins
		#   - idx 之後：舊的起點要右移 ins_b_len
		for i in range(idx + 1, len(self.raw)):
			# 舊的對應 token 是 i-1
			new_r2b[i] = old_r2b[i - 1] + ins_b_len
		self.raw_to_braille_pos = new_r2b

		# 3) 更新 braille_to_raw_pos（braille_index -> token_index）
		old_b2r = self.braille_to_raw_pos
		#   - b_ins 前：不變
		left = old_b2r[:b_ins]
		#   - 新插入的點字段落：全部指向新 token idx
		mid = [idx] * ins_b_len
		#   - b_ins 之後：原本 >= idx 的 token 索引要 +1（因為前面多了一個 token）
		right = [(t + 1) if t >= idx else t for t in old_b2r[b_ins:]]
		self.braille_to_raw_pos = left + mid + right

	def reclean_token(self):
		"""
		若相鄰兩個 token 構成：前一 token 以 RIGHT_PUNCT 結尾、下一 token 以 LEFT_PUNCT 開頭，
		則在它們之間插入一個空白 token 與對應的點字空格。
		"""
		blank_cell = chr(BRAILLE_UNICODE_PATTERNS_START)
		i = 1
		# 以 while 迴圈處理，因為過程會動態插入 token、改變長度
		while i < len(self.raw):
			prev_tok = self.raw[i - 1]
			curr_tok = self.raw[i]

			# 防禦：空字串不處理
			if prev_tok and curr_tok:
				prev_last = prev_tok[-1]
				curr_first = curr_tok[0]

				if (prev_last in self.RIGHT_PUNCT) and (curr_first in self.LEFT_PUNCT):
					# 插入空白 token 與點字空格
					self.insert_token(i, " ", blank_cell)
					i += 1  # 跳過剛插入的空白

			i += 1

	def reclean_braille_endspace(self):
		"""
		逐一檢查每個 token：
		  - 當該 token 的點字段長度 > 1，且尾端為空白點字方（U+2800），
			才移除尾端連續的空白點字方（但至少保留 1 格，避免把純空白 token 洗掉）。
		同步更新：
		  - self.braille
		  - self.braille_to_raw_pos
		  - self.raw_to_braille_pos（後續 token 起點左移）
		不移除 self.raw 的 token。
		"""
		if not self.raw or not self.braille:
			return
		if not self.braille_to_raw_pos or not self.raw_to_braille_pos:
			return

		blank = chr(BRAILLE_UNICODE_PATTERNS_START)
		n_tokens = len(self.raw)

		for t_idx in range(n_tokens):
			start = self.raw_to_braille_pos[t_idx]
			end = self.raw_to_braille_pos[t_idx + 1] if t_idx + 1 < len(self.raw_to_braille_pos) else len(self.braille)
			if start >= end:
				continue

			seg_len = end - start
			# 只處理「長度 > 1」且「尾端為空白點字方」的情形
			if seg_len <= 1 or self.braille[end - 1] != blank:
				continue

			# 從尾端開始移除連續空白，但至少保留一格（避免把空白 token 洗掉）
			new_end = end
			while new_end - start > 1 and self.braille[new_end - 1] == blank:
				new_end -= 1

			remove_count = end - new_end
			if remove_count <= 0:
				continue

			# 1) 刪除 braille 與 b2r 的尾端空白區段 [new_end, end)
			del self.braille[new_end:end]
			del self.braille_to_raw_pos[new_end:end]

			# 2) 調整 raw_to_braille_pos：從 t_idx+1 起的 token 起點左移 remove_count
			for k in range(t_idx + 1, len(self.raw_to_braille_pos)):
				self.raw_to_braille_pos[k] -= remove_count

		# 保守收尾：避免任何 raw_to_braille_pos 超出長度
		blen = len(self.braille)
		for k in range(len(self.raw_to_braille_pos)):
			if self.raw_to_braille_pos[k] > blen:
				self.raw_to_braille_pos[k] = blen

	def wrap(self, width: int) -> tuple[str, str]:
		blank = chr(BRAILLE_UNICODE_PATTERNS_START)
		width = max(1, int(width or 1))
		current_len = 0

		raw_lines: list[list[str]] = []
		current_raw_parts: list[str] = []

		braille_lines: list[list[str]] = []
		current_braille_parts: list[str] = []

		raw_len = len(self.raw)

		# line_start_blank 是為了分辨是原文就在開頭的空白與後續因點字規則需要而插入的空白
		line_start_blank = True
		full_line_break = False

		for i, token in enumerate(self.raw):
									# Treat explicit newline in source as a hard line break.
			if token == "\n":
				if current_len < width and current_len > 0 or current_len == 0 and not full_line_break:
					current_raw_parts.append("")
					current_braille_parts.append(blank * (width - current_len))

				# 不能與上面條件相同，要移除 current_len < width 因為這樣如果單一 token 超過寬度雖然會爆版，但仍能顯示
				if current_len > 0 or current_len == 0 and not full_line_break:
					raw_lines.append(current_raw_parts)
					braille_lines.append(current_braille_parts)
					current_raw_parts = []
					current_braille_parts = []
					current_len = 0

				line_start_blank = True
				full_line_break = False
				continue
			elif token == " ":
				if current_len == 0 and not line_start_blank:
					continue

			if token != " ":
				line_start_blank = False

			full_line_break = False
			start = self.raw_to_braille_pos[i]
			end = self.raw_to_braille_pos[i + 1] if i + 1 < raw_len else len(self.braille)
			seg_len = end - start

			if current_len + seg_len > width and current_len > 0:
				current_raw_parts.append("")
				current_braille_parts.append(blank * (width - current_len))
				raw_lines.append(current_raw_parts)
				braille_lines.append(current_braille_parts)
				current_raw_parts = []
				current_braille_parts = []
				current_len = 0

			if seg_len:
				current_raw_parts.append(token)
				current_braille_parts.append("".join(self.braille[start:end]))
				current_len += seg_len

			if current_len < width:
				next_token = self.raw[i + 1] if i + 1 < len(self.raw) else None
				if token[-1] in self.RIGHT_PUNCT_FULL | self.END_SENTENCE_PUNCT_FULL \
					and next_token is not None and next_token not in set(" ") \
					and current_braille_parts[-1][-1] != blank\
				:
					current_raw_parts[-1] += " "
					current_braille_parts[-1] += blank
					current_len += len(blank)

			if current_len == width:
				raw_lines.append(current_raw_parts)
				braille_lines.append(current_braille_parts)
				current_raw_parts = []
				current_braille_parts = []
				current_len = 0
				full_line_break = True

		if current_len > 0 or not braille_lines:
			current_raw_parts.append("")
			current_braille_parts.append(blank * (width - current_len))
			raw_lines.append(current_raw_parts)
			braille_lines.append(current_braille_parts)

		# raw_lines = [i for i in raw_lines if i != []]
		# braille_lines = [i for i in braille_lines if i != []]

		braille_lines_str = ["".join(item) for item in braille_lines]
		raw_lines_str = ["".join(item) for item in raw_lines]

		return "\n".join(braille_lines_str), "\n".join(raw_lines_str)


def translate(table_file: str, text: str, raw: str) -> TranslationResult:
	# Use absolute path for the first table so includes resolve relative to it.
	table_path = os.path.join(TABLES_DIR, table_file)
	braille_cells, braille_to_raw_pos, raw_to_braille_pos, _ = louisHelper.translate(
		[table_path], text, mode=4
	)
	if not raw == text:
		print(f"text: {repr(text)}")
		print(f"raw: {repr(raw)}")
	raw = [s for s in text]
	braille = [chr(b + BRAILLE_UNICODE_PATTERNS_START) for b in braille_cells]

	return TranslationResult(raw, braille, braille_to_raw_pos, raw_to_braille_pos)


def translate_as_single_token(table_file: str, text: str, raw: str) -> TranslationResult:
	"""
	Translate with liblouis but force the entire input text to be one token.
	"""
	table_path = os.path.join(TABLES_DIR, table_file)
	braille_cells, _braille_to_raw_pos, _raw_to_braille_pos, _ = louisHelper.translate(
		[table_path], text, mode=4
	)

	braille = [chr(b + BRAILLE_UNICODE_PATTERNS_START) for b in braille_cells]
	if text:
		raw = [raw]
		braille_to_raw_pos = [0] * len(braille)
		raw_to_braille_pos = [0]
	else:
		raw = []
		braille_to_raw_pos = []
		raw_to_braille_pos = []

	return TranslationResult(raw, braille, braille_to_raw_pos, raw_to_braille_pos)


if __name__ == '__main__':
	tr = translate("zh-tw.ctb", "我「們這，一家")
	print(tr.raw)
