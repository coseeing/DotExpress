from bisect import bisect_right

from conversion import tokenizer
from conversion.line_wrap import wrap_tokens
from conversion.tokenizer import contracted_token_spans, iter_separator_positions, word_token_spans


def _is_well_formed_alignment(raw, braille, braille_to_raw_pos, raw_to_braille_pos):
	"""True when there is one start per token and one token per cell, and the token
	starts never decrease and stay within the braille, as every producer builds them."""
	if len(raw_to_braille_pos) != len(raw) or len(braille_to_raw_pos) != len(braille):
		return False
	previous = 0
	for start in raw_to_braille_pos:
		if start < previous:
			return False
		previous = start
	return previous <= len(braille)


class TranslationResult:
	# The same objects as the tokenizer's constants.
	LEFT_PUNCT_HALF = tokenizer.LEFT_PUNCT_HALF
	RIGHT_PUNCT_HALF = tokenizer.RIGHT_PUNCT_HALF
	MIDDLE_SENTENCE_PUNCT_HALF = tokenizer.MIDDLE_SENTENCE_PUNCT_HALF
	END_SENTENCE_PUNCT_HALF = tokenizer.END_SENTENCE_PUNCT_HALF

	LEFT_PUNCT_FULL = tokenizer.LEFT_PUNCT_FULL
	RIGHT_PUNCT_FULL = tokenizer.RIGHT_PUNCT_FULL
	MIDDLE_SENTENCE_PUNCT_FULL = tokenizer.MIDDLE_SENTENCE_PUNCT_FULL
	END_SENTENCE_PUNCT_FULL = tokenizer.END_SENTENCE_PUNCT_FULL

	LEFT_PUNCT = tokenizer.LEFT_PUNCT
	RIGHT_PUNCT = tokenizer.RIGHT_PUNCT
	MIDDLE_SENTENCE_PUNCT = tokenizer.MIDDLE_SENTENCE_PUNCT
	END_SENTENCE_PUNCT = tokenizer.END_SENTENCE_PUNCT

	lang_blocks = tokenizer.CJK_LANGUAGE_BLOCKS

	__hash__ = None

	def __init__(self, raw, braille, braille_to_raw_pos, raw_to_braille_pos):
		self.raw = raw
		self.braille = braille
		self.braille_to_raw_pos = braille_to_raw_pos
		self.raw_to_braille_pos = raw_to_braille_pos

	@classmethod
	def concat(cls, results):
		raw, braille, braille_to_raw_pos, raw_to_braille_pos = [], [], [], []
		for result in results:
			if not isinstance(result, TranslationResult):
				raise TypeError("not TranslateResult object")
			raw_offset = len(raw)
			braille_offset = len(braille)
			raw.extend(result.raw)
			braille.extend(result.braille)
			braille_to_raw_pos.extend(pos + raw_offset for pos in result.braille_to_raw_pos)
			raw_to_braille_pos.extend(pos + braille_offset for pos in result.raw_to_braille_pos)
		return cls(raw, braille, braille_to_raw_pos, raw_to_braille_pos)

	def __add__(self, other):
		if not isinstance(other, TranslationResult):
			raise TypeError("not TranslateResult object")
		return TranslationResult.concat((self, other))

	def __eq__(self, other):
		if not isinstance(other, TranslationResult):
			return NotImplemented
		result = True
		result &= (self.raw == other.raw)
		result &= (self.braille == other.braille)
		result &= (self.braille_to_raw_pos == other.braille_to_raw_pos)
		result &= (self.raw_to_braille_pos == other.raw_to_braille_pos)
		return result

	def bind_contracted_tokens(self):
		"""Merge adjacent source characters that share one braille-cell start.

		liblouis reports character-level source positions even when a grade-2
		contraction maps several source characters to one braille cell. Merge
		those source characters and rebuild both position maps at token level.
		"""
		if not self.raw or len(self.raw) != len(self.raw_to_braille_pos):
			return
		self._regroup(contracted_token_spans(self.raw_to_braille_pos))

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

		spans = word_token_spans(self.raw, self.lang_blocks)

		# 防禦：長度不一致時維持原狀（避免 IndexError）
		if not self.raw_to_braille_pos or not self.raw or len(self.braille_to_raw_pos) != len(self.braille):
			return
		self._regroup(spans)

	def _regroup(self, spans):
		"""Rebuild the four lists for tokens made of the given spans of the current tokens."""
		old_raw = self.raw
		old_r2b = self.raw_to_braille_pos

		# token → braille 起始（取 token 第一個字元的起點）
		new_raw_to_braille_pos = [old_r2b[span_start] for span_start, _span_end in spans]

		# 字元索引 → token 索引
		char_to_token = [0] * len(old_raw)
		for token_index, (span_start, span_end) in enumerate(spans):
			for char_index in range(span_start, span_end):
				char_to_token[char_index] = token_index

		# braille 索引 → token 索引（從舊的字元級映射轉換）
		new_braille_to_raw_pos = [
			char_to_token[char_index]
			if 0 <= char_index < len(old_raw)
			else 0
			for char_index in self.braille_to_raw_pos
		]

		self.raw = ["".join(old_raw[span_start:span_end]) for span_start, span_end in spans]
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
		blank_cell = chr(0x2800)
		# The original token indices before which a separator goes. The original loop
		# skipped every inserted separator, so it checked exactly these adjacent pairs.
		positions = list(iter_separator_positions(self.raw))
		if not positions:
			return
		if not _is_well_formed_alignment(self.raw, self.braille, self.braille_to_raw_pos, self.raw_to_braille_pos):
			# Malformed maps: insert one by one, exactly as before.
			for offset, index in enumerate(positions):
				self.insert_token(index + offset, " ", blank_cell)
			return

		# One pass: the lists that inserting the separators one by one would give.
		# Separator m goes before original token positions[m], at token index
		# positions[m] + m and braille index raw_to_braille_pos[positions[m]] + m.
		raw_to_braille_pos = self.raw_to_braille_pos
		count = len(positions)
		new_raw: list[str] = []
		new_raw_to_braille_pos: list[int] = []
		inserted = 0
		for t_idx, token in enumerate(self.raw):
			if inserted < count and positions[inserted] == t_idx:
				new_raw.append(" ")
				new_raw_to_braille_pos.append(raw_to_braille_pos[t_idx] + inserted)
				inserted += 1
			new_raw.append(token)
			new_raw_to_braille_pos.append(raw_to_braille_pos[t_idx] + inserted)

		separator_cells = [raw_to_braille_pos[index] for index in positions]
		new_braille: list[str] = []
		new_braille_to_raw_pos: list[int] = []
		inserted = 0
		for b_idx, cell in enumerate(self.braille):
			while inserted < count and separator_cells[inserted] <= b_idx:
				new_braille.append(blank_cell)
				new_braille_to_raw_pos.append(positions[inserted] + inserted)
				inserted += 1
			# One by one, a cell's token index grows at each separator inserted at or
			# before the cell, until the first separator that lies after that token.
			token_idx = self.braille_to_raw_pos[b_idx]
			new_braille.append(cell)
			new_braille_to_raw_pos.append(token_idx + min(inserted, bisect_right(positions, token_idx)))
		while inserted < count:
			new_braille.append(blank_cell)
			new_braille_to_raw_pos.append(positions[inserted] + inserted)
			inserted += 1

		self.raw = new_raw
		self.braille = new_braille
		self.raw_to_braille_pos = new_raw_to_braille_pos
		self.braille_to_raw_pos = new_braille_to_raw_pos

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
		if not _is_well_formed_alignment(self.raw, self.braille, self.braille_to_raw_pos, self.raw_to_braille_pos):
			self._reclean_braille_endspace_stepwise()
			return

		# One pass. Every earlier trim lies before the current token (the starts never
		# decrease) and shifts its start and end by the same amount, so the step-by-step
		# loop sees each token's original cells: the same tokens lose the same cells.
		blank = chr(0x2800)
		braille = self.braille
		braille_to_raw_pos = self.braille_to_raw_pos
		raw_to_braille_pos = self.raw_to_braille_pos
		braille_len = len(braille)
		first_start = raw_to_braille_pos[0]
		new_braille = braille[:first_start]
		new_braille_to_raw_pos = braille_to_raw_pos[:first_start]
		new_raw_to_braille_pos = []
		removed = 0
		for t_idx, start in enumerate(raw_to_braille_pos):
			end = raw_to_braille_pos[t_idx + 1] if t_idx + 1 < len(raw_to_braille_pos) else braille_len
			new_raw_to_braille_pos.append(start - removed)
			new_end = end
			while new_end - start > 1 and braille[new_end - 1] == blank:
				new_end -= 1
			new_braille.extend(braille[start:new_end])
			new_braille_to_raw_pos.extend(braille_to_raw_pos[start:new_end])
			removed += end - new_end
		# Replace the contents, not the lists, as the step-by-step deletions do. No start
		# can exceed the new length here, so the stepwise loop's final clamp is not needed.
		braille[:] = new_braille
		braille_to_raw_pos[:] = new_braille_to_raw_pos
		raw_to_braille_pos[:] = new_raw_to_braille_pos

	def _reclean_braille_endspace_stepwise(self):
		"""The original trim, one token at a time; kept for malformed alignments, whose
		deletions can overlap later tokens."""
		blank = chr(0x2800)
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
		return wrap_tokens(self.raw, self.braille, self.raw_to_braille_pos, width)
