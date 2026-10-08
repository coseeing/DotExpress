# 轉換結果結構整理（P1-5）設計

## 目標

在不改變任何輸出的前提下，讓對位值物件與 Dual View 的交接變得便宜且沒有循環依賴。本任務是 `storage/refactor.md`（6.2 節）路線圖的 P1-5，涵蓋：

- S-2（第一與第三點）與 5.6 節：`TranslationResult.__init__` 每個實例都重建 12 個標點集合與 CJK 語言區塊表；`conversion/wrapping.merge_translation_results` 是 O(n^2)。
- D-3（P1-5 負責的部分）：`conversion/wrapping.py` 與 `conversion/preprocessing/literal_braille.py` 中函式內的 `from translate import TranslationResult`。
- D-4：`conversion <-> dual_view` 依賴迴圈（`conversion/service.py` 從 `dual_view.model` import `DualViewSegment`，而 `dual_view.model` 又 import `conversion.math_service`）。
- L-1：`TranslationResult.__eq__` 遇到非 `TranslationResult` 的運算元時拋出 `AttributeError`。
- P0 階段審查的 M-1：`tests/test_translation_result_core.py` 重新 import `translate`，只要它先執行，`tests/test_conversion_service.py` 就有 8 個測試出錯。

具體而言：

- 標點集合與 CJK 語言區塊改為 `TranslationResult` 的不可變類別屬性（import 時建立一次）。實例只保存四個資料欄位。
- `TranslationResult.concat(results)` 一次走訪合併任意數量的結果。`merge_translation_results` 與 `TranslationResult.__add__` 都改用它。
- `DualViewSegment` 移到 `conversion/output.py`，與 `ConversionOutput` 放在一起。`conversion` 不再 import `dual_view`。
- `build_dual_view_model(segments, *, mathml_converter)` 的轉換器改為必填的關鍵字參數。`gui.py` 與 `documents/formats.py` 傳入 `conversion.math_service.latex_to_mathml`。`dual_view` 在執行期不再 import `conversion`（也不再 import `config`）。
- `TranslationResult.__eq__` 對其他型別回傳 `NotImplemented`，類別明確設定 `__hash__ = None`。
- `tests/test_translation_result_core.py` 的 import 隔離檢查改在子行程執行，`translate` 不會再被從 `sys.modules` 移除。完成後，打亂順序的全套測試不再出現任何順序相依的失敗。

這是保持行為不變的重構。對任何輸入，點字文字、原文換行、token 對位、Dual View 模型與 HTML 都與 `main` 的 `7095265` 逐位元組相同。使用者可見字串不變。

不屬於本任務（P2-5）：把 tokenizer（`bind_word_tokens`）與換行器（`wrap`）從 `TranslationResult` 拆出、把 `TranslationResult` 移到 `conversion/alignment.py`，以及已知失敗的測試 `test_translate_with_language_does_not_duplicate_existing_spaces_around_math`。

## 現況（2026-10-08 於 `refactor/p1-5-translation-result-layout`、HEAD `7095265` 驗證，P0-1..P0-6 與 P1-1..P1-4 已合併）

縮排：`translate.py`、`gui.py` 與 `dual_view/model.py`（`DualViewSegment` 類別除外，它用 4 個空白）使用 tab。`conversion/wrapping.py`、`conversion/output.py`、`conversion/service.py`、`conversion/preprocessing/literal_braille.py`、`documents/formats.py` 與 `dual_view/__init__.py` 使用 4 個空白。測試：`test_translation_result.py`、`test_dual_view_model.py`、`test_dual_view_html.py` 使用 tab；本任務會動到的其他測試使用 4 個空白。

### `TranslationResult`（`client/translate.py`，527 行）

- `__init__`（第 11-32 行）保存 `raw`、`braille`、`braille_to_raw_pos`、`raw_to_braille_pos`，接著建立 12 個 `set` 屬性（`LEFT_PUNCT_HALF` ... `END_SENTENCE_PUNCT`）以及 `self.lang_blocks = build_language_blocks({"ja", "zh", "ko"})`（型別為 `dict[str, list[str]]`）。每個實例約 6 微秒；每次 adapter 呼叫、每一步合併、每個字面點字片段都會建立一個。
- 這些集合只被讀取：`bind_word_tokens`（第 142、144 行，以及第 127 行的 `getattr(self, "lang_blocks", None)`）、`reclean_token`（第 376 行）與 `wrap`（第 499 行）。`translate.py` 以外沒有任何地方讀取它們（`grep -rn "PUNCT\|lang_blocks" client --include=*.py`）。沒有任何程式 pickle、複製或檢查結果的 `vars()`。
- `__add__`（第 34-52 行）遇到非 `TranslationResult` 運算元時拋出 `TypeError("not TranslateResult object")`，並回傳四個 list 都是新物件的結果（絕不與任一運算元共用 list）。
- `__eq__`（第 54-60 行）直接讀 `other.raw` 等屬性。遇到其他型別會拋出 `AttributeError`。以探針跑完整套測試，沒有任何測試呼叫它。
- `reclean_braille_endspace` 會就地修改 `braille`、`braille_to_raw_pos` 與 `raw_to_braille_pos`（`del`、索引指派）。

### 合併（`client/conversion/wrapping.py`，17 行）

```python
def merge_translation_results(translations):
    from translate import TranslationResult
    if not translations:
        return TranslationResult([], [], [], [])
    merged = TranslationResult([], [], [], [])
    for segment in translations:
        merged = merged + segment
    return merged
```

每一步都複製目前已合併的全部內容並建立新實例。在本機以每段 10 個 token 量測：1,000 段 0.18 秒、2,000 段 0.70 秒、4,000 段 3.2 秒、8,000 段 15.3 秒。合併之後，`wrap_translation_results` 的其餘步驟（`reclean_braille_endspace`、`bind_word_tokens`、`reclean_token`、`wrap`）處理 8,000 段約 0.3 秒，所以對這種輸入形狀而言合併是主要成本。（`reclean_braille_endspace` 在大量 token 以空白點字方結尾時另有平方成本，見已知缺陷 3。）每次語言切換、字典括號、字面點字、數學區塊與邊界空白都會產生一段，所以匯入的長篇 PDF/EPUB 會有數千段。

`wrap_translation_results` 會修改合併後的結果（`reclean_braille_endspace`）。因為合併會複製，各段的結果保持不變，而這些物件正是文件的 Dual View 快取（`ConversionOutput.dual_view_segments`）。新的合併必須維持這個保證。

呼叫端：`wrap_translation_results`（同檔案）與 `conversion/service.translate_with_language`（第 110 行）。僅限 Windows 的 `tests/test_language_detection_translation.py` 以 `+` 合併。

### 函式內的 `translate` import

`conversion/wrapping.py:2` 與 `conversion/preprocessing/literal_braille.py:6`。它們源自 `translate.py` 還會載入原生 liblouis helper 的時期（commit `c6474cb`）。如今 `translate.py` 只 import `string` 與 `languageDetection.unicode_blocks`，而且 `adapters/translation/contracts.py:6` 已在模組層級 import 它；`conversion.text.pipeline` import `contracts`，所以這兩個模組執行時 `translate` 早已載入。沒有循環；這兩個函式內 import 只是遺跡。

`conversion/text/pipeline.py:58-59` 的函式內 import（`text.zhuyin`、`languageDetection`）也不是循環造成的，但與 `TranslationResult` 或 `dual_view` 無關。維持原狀（pipeline 屬於 P1-6）。

### Dual View 模型（`client/dual_view/model.py`，90 行）

- 第 4 行：`from conversion.math_service import latex_to_mathml`（它會 import `config` 與 `log`）。
- 第 7-10 行：`DualViewSegment(result: object, source_kind: str)`，frozen dataclass。
- 第 44 行：`build_dual_view_model(segments, *, mathml_converter=latex_to_mathml)`。`"math"` 段的每個原文 token 呼叫一次轉換器；文字段從不呼叫。
- `dual_view/__init__.py` 重新匯出 `DualViewSegment`。沒有正式程式碼從套件 import 它；所有使用者都 import `dual_view.model`。

使用情形：

| 符號 | 正式程式碼 | 測試 |
| --- | --- | --- |
| `DualViewSegment` | `conversion/service.py:18`（在第 50、63、65、72 行建立；第 35、129 行用於型別註記） | `test_conversion_service.py`、`test_document_formats.py`、`test_gui_document_flows.py`、`test_dual_view_model.py`、`test_dual_view_html.py`（全部 `from dual_view.model import DualViewSegment`） |
| `build_dual_view_model` | `gui.py:332`（`_render_dual_view_for_open_document`）、`documents/formats.py:106`（`_write_html`，經由 `ExportCoordinator` 呼叫） | 20 處未傳轉換器（`test_dual_view_model.py`、`test_dual_view_html.py`、`test_gui_document_flows.py` 第 1364、1369、1398、1402 行），2 處傳入假轉換器（`test_dual_view_html.py`） |

目前的 import 範圍：`import conversion.service` 會載入 `dual_view`、`dual_view.html` 與 `dual_view.model`；`import dual_view` 會載入 `conversion`、`conversion.math_service`、`conversion.math_braille_codes`、`config`、`log` 與 `app_paths`。`import documents.formats` 經由 `dual_view.model` 取得 `conversion.math_service`。

### M-1：測試順序造成的失敗

`TranslationResultCoreTest.test_import_does_not_import_liblouis_helper` 執行 `sys.modules.pop("translate")` 再重新 import，因而產生第二個 `TranslationResult` 類別。較早 import 的模組（`adapters.translation.*`、該測試模組自己的 `FakeTextTranslator`）建立的結果用舊類別，而 `conversion.wrapping` 在呼叫時才 import 類別，拿到的是新類別。於是 `merged + segment` 的 `isinstance` 檢查失敗：`TypeError: not TranslateResult object`。

- 重現：`cd client && python -m unittest tests.test_translation_result_core tests.test_conversion_service` 得到 23 個測試、`errors=8`（8 個會合併的測試，包含 P2-5 的測試，它此時變成錯誤而非失敗）。
- 打亂順序的全套測試（P0-4 起使用的模組順序 harness，種子 0-19，754 個測試）：種子 0、1、3、4、5、10、12、13 為 `failures=0 errors=8`；其餘 12 個為 `failures=1 errors=0`（只有 P2-5）。所有失敗的種子都是 `test_translation_result_core` 排在 `test_conversion_service` 之前；沒有其他模組牽涉其中。
- P1-1 在 `tests/test_conversion_language_explicit.py` 中繞過了這個問題（假翻譯器在每次呼叫時才 import `TranslationResult`，並附註解說明原因）。`tests/test_conversion_service.py` 仍留有三個為 `sys.modules["translate"]` 替換而寫、已無測試使用的輔助函式：`_fake_translate_module`、`_mutating_translate_module`、`_translation_result`。

### 路線圖列出的安全網比看起來薄弱

- `tests/test_translation_result.py`（13 個測試，涵蓋 `bind_contracted_tokens`、`bind_word_tokens` 與 `wrap`）寫成 pytest 風格的模組函式。`unittest` 一個也收集不到（`python -m unittest tests.test_translation_result` 顯示 `NO TESTS RAN`），而 pytest 不是專案的相依套件。直接呼叫時，目前 8 個通過、5 個失敗（`test_bind_word_tokens_lead_punct` 與 `..._lead_punct_continue` 拋出 `IndexError`；`test_end_right_end_sentence_blank2`、`..._blank3` 與 `test_remove_start_line_blank` 斷言失敗）。它們測的是 tokenizer 與換行器，屬於 P2-5。
- `tests/test_translation_language_result.py` 與 `tests/test_language_detection_translation.py` 僅限 Windows，在此會跳過。後者 import 已不存在的 `translate.translate`，所以在 Windows 上會出錯（既有問題；P1-1 已記錄前者的 `TypeError`）。
- 因此目前實際執行的測試中，沒有任何一個針對真實的混合輸入鎖定合併後的點字、換行或對位。本任務先補上這張安全網。

### 基線

`7095265` 的全套測試（Linux venv，字母順序）：754 個測試，`failures=1`（P2-5）、`errors=0`、`skipped=9`。

## 設計

### `TranslationResult` 常數（`translate.py`）

把 12 個集合改為同名、同成員的類別屬性，型別為 `frozenset`。語言區塊在模組層級建立一次，並以唯讀類別屬性提供：

```python
_CJK_LANGUAGE_BLOCKS = MappingProxyType({
	language: tuple(blocks)
	for language, blocks in build_language_blocks(("ja", "zh", "ko")).items()
})

class TranslationResult:
	LEFT_PUNCT_HALF = frozenset("([{")
	...
	END_SENTENCE_PUNCT = END_SENTENCE_PUNCT_HALF | END_SENTENCE_PUNCT_FULL
	lang_blocks = _CJK_LANGUAGE_BLOCKS
	__hash__ = None

	def __init__(self, raw, braille, braille_to_raw_pos, raw_to_braille_pos):
		self.raw = raw
		...
```

- 所有既有的讀取（`self.RIGHT_PUNCT`、`self.LEFT_PUNCT`、`set(self.LEFT_PUNCT) | set("—")`、`self.RIGHT_PUNCT_FULL | self.END_SENTENCE_PUNCT_FULL`、`getattr(self, "lang_blocks", None)`）透過類別屬性照常運作，成員判斷與聯集結果都相等。`bind_contracted_tokens`、`bind_word_tokens`、`insert_token`、`reclean_token`、`reclean_braille_endspace` 與 `wrap` 的方法本體不修改。
- 使用不可變型別，因為這些值現在由所有實例共用。`language_has_all` 只呼叫 `.get(lang, [])` 並把結果包成 `set(...)`，所以 tuple 組成的 mapping proxy 與 list 組成的 dict 行為完全相同。dict 的鍵順序取決於 set 的走訪順序，但只會以鍵查詢。
- `bind_word_tokens` 內每次呼叫建立的集合（`ASCII_ALNUM`、`TRAIL_PUNCT`、`LEAD_PUNCT`），以及 `wrap` 內每個 token 的聯集與 `set(" ")` 維持原狀：它們位於 P2-5 要改寫的 tokenizer 與換行器本體中。

### 相等比較（L-1）

```python
def __eq__(self, other):
	if not isinstance(other, TranslationResult):
		return NotImplemented
	... 比較內容不變 ...
```

與其他型別比較時，現在得到 `False`（`!=` 得到 `True`），而不是 `AttributeError`。相等的結果仍然相等；`__hash__ = None` 只是明確寫出 Python 原本就隱含的行為。

### 線性合併

在 `TranslationResult` 上新增類別方法，兩條合併路徑都改走它：

```python
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
```

- `__add__` 對非結果運算元仍拋出 `TypeError`，其餘改為 `return TranslationResult.concat((self, other))`。
- `conversion/wrapping.py` 在模組層級 import `TranslationResult`，`merge_translation_results(translations)` 改為 `return TranslationResult.concat(translations or ())`。`None`／空輸入仍回傳空結果。函式保留為呼叫端使用的公開名稱。
- 與逐對合併的算術相同（偏移量是該段之前已合併內容的長度），所以每個 list 都逐元素相等。只建立一個實例，每個元素只複製一次：O(總長度)。
- 即使輸入為零個或一個，結果也擁有四個新的 list，因此對合併結果呼叫 `reclean_braille_endspace` 不會動到快取的 Dual View 段。
- 接受的放寬：`list + x` 要求 `raw` 與 `braille` 必須是 list，`extend` 則接受任何可迭代物件。所有產生者（liblouis、MathCAT 與 fallback adapter、字面點字、測試假物件）都建立 list，所以實際可能的輸入都不受影響。

`conversion/preprocessing/literal_braille.py` 也改為在模組層級 import `TranslationResult`。兩處搬移都不改變任何 import 範圍（理由見上）。

### `DualViewSegment` 移到 `conversion/output.py`（D-4）

- 在 `conversion/output.py` 的 `ConversionOutput` 之上定義 `DualViewSegment`（欄位相同、同樣 `frozen=True`、`result: object`），並把 `ConversionOutput.dual_view_segments` 註記為 `tuple[DualViewSegment, ...] = ()`。`output.py` 不新增任何 import，所以 `test_language_consumers_do_not_import_config` 維持通過。
- `conversion/service.py` 改從 `conversion.output` import，並移除 `from dual_view.model import DualViewSegment`。
- `dual_view/model.py` 刪除該類別，加上 `from __future__ import annotations`，只在 `if TYPE_CHECKING:` 下 import `DualViewSegment` 供 `Iterable[DualViewSegment]` 註記使用。`dual_view/__init__.py` 從 import 與 `__all__` 中移除 `DualViewSegment`。
- `dual_view.model` 不保留相容別名：別名需要執行期 import，而那正是要移除的依賴。五個測試模組在同一個 commit 中改為 `from conversion.output import DualViewSegment`。
- `conversion/output.py` 不是葉節點模組（它 import adapter contracts 與文字 pipeline），但 `dual_view` 只在型別檢查時引用它，而 `conversion.service` 本來就 import 它。曾考慮另建葉節點模組，但已否決：多一個檔案卻沒有執行期效益，也偏離路線圖明確指定的位置。

之後的方向：`conversion` 產生 `DualViewSegment`；`dual_view` 以結構方式使用它（只讀 `.result.raw`、`.result.braille`、`.result.raw_to_braille_pos` 與 `.source_kind`）；`gui` 與 `documents` 負責把兩者接起來。

### 必填的 `mathml_converter`（D-4）

```python
def build_dual_view_model(
	segments: Iterable[DualViewSegment],
	*,
	mathml_converter: Callable[[str], str],
) -> DualViewModel:
```

- 必填且只能以關鍵字傳入，沒有預設值、也不接受 `None`：預設值正是要移除的隱性依賴，而 `None` 只會把失敗延後到第一個數學 token。
- `dual_view/model.py` 移除 `from conversion.math_service import latex_to_mathml`。import `dual_view` 不再載入 `conversion`、`config`、`log` 或 `app_paths`。
- `gui.py`：在模組層級 `from conversion.math_service import latex_to_mathml`；`_render_dual_view_for_open_document` 呼叫 `build_dual_view_model(results, mathml_converter=latex_to_mathml)`。
- `documents/formats.py`：同樣在模組層級 import；`_write_html` 傳入它。`documents.formats` 今天就已（經由 `dual_view.model`）載入 `conversion.math_service`，所以它的 import 範圍不變。`ExportContext` 不變：把轉換器放進 context，會讓一個接線決定散布到 `ExportCoordinator`、`formats` 與它們的測試，沒有好處。
- 行為完全相同：兩個呼叫端先前都使用預設的 `latex_to_mathml`。

### M-1：測試隔離

- `tests/test_translation_result_core.py`：`test_import_does_not_import_liblouis_helper` 改用 `subprocess.run([sys.executable, "-c", script], ...)` 在全新的直譯器中檢查，沿用 `tests/test_translation_import_isolation.py` 已有的寫法。腳本 import `translate`，斷言 `braille.louis_helper` 與 `braille.liblouis` 未載入、`TranslationResult` 存在、`translate` 與 `translate_as_single_token` 不存在。測試不再碰 `sys.modules`。全新直譯器也是更可靠的檢查：行程內的版本只能移除其他測試已載入的模組。
- `tests/test_conversion_language_explicit.py`：兩個假翻譯器改在模組層級 import `TranslationResult`，並移除繞道用的註解。這是污染已消失的回歸證明。
- `tests/test_conversion_service.py`：刪除三個無用的輔助函式，以及隨之不再使用的 `ModuleType` import。它們模擬的是 `sys.modules["translate"]` 替換，而 `wrapping` 改為模組層級 import 後，這種替換已沒有意義。
- 移除重新 import、且 `wrapping` 在 import 時就綁定類別之後，每個行程只會有一個 `TranslationResult` 類別。沒有其他測試移除或 reload `translate`（`grep -rn "sys.modules.pop\|importlib.reload" client/tests`；使用 `StubScope` 的測試不會在 scope 內 import `translate`）。

### 遷移步驟（每一步都是一個全綠的 commit；細節由計畫決定）

1. `test: run the translate import check in a subprocess`（M-1，加上 explicit-language 的假翻譯器與刪除無用輔助函式）。20 個種子的打亂測試除了 P2-5 之外全部乾淨。
2. `test: characterize translation and dual-view output`（測試計畫 A 部分全部，包括在未修改的正式程式碼上產生的 golden fixture）。
3. `refactor: share TranslationResult constants`（常數與 `__hash__`；B 部分測試）。
4. `fix: compare TranslationResult only with results`（L-1；C 部分測試）。
5. `refactor: merge translation results in one pass`（`concat`、`__add__`、兩處模組層級 import；D 部分測試）。
6. `refactor: move DualViewSegment to conversion output`（E 部分中針對 `conversion` 的守衛）。
7. `refactor: inject the MathML converter into the dual-view model`（E 部分中針對 `dual_view` 的守衛、測試呼叫處更新）。

golden fixture 只在步驟 2 寫入一次，之後不得改變。

## 維持不變的部分

- 任何輸入與寬度下的點字輸出（Unicode 與 ASCII）、原文換行、合併後的對位 list、後處理後的對位、每個 Dual View 段，以及 Dual View HTML（視窗與匯出）。
- `merge_translation_results`、`wrap_translation_results`、`translate_with_language*` 與 `convert_text_with_alignment` 的簽名與回傳型別。
- 合併非結果物件時的 `TypeError("not TranslateResult object")`。
- `TranslationResult` 的屬性名稱；`__init__`、`__add__` 與 `__eq__` 以外的方法本體。
- `ExportContext`、`ExportCoordinator`、`DocumentController` 與轉換 presenter。
- 沒有任何字串、選單、對話框、`.po`/`.mo` 或打包變更。

## 測試計畫

所有新測試都是 `unittest`。golden 預期值擷取自未修改的正式程式碼（步驟 2），之後的步驟不得重新產生。

### A. 特性化測試（步驟 2，任何正式程式碼變更之前）

1. **Golden 輸出**（`tests/test_translation_golden.py`，新檔，4 個空白；fixture 為 `tests/fixtures/translation_golden.json`）：
   - 執行環境：真正的 `LiblouisTextTranslator` 搭配確定性的假 helper（其 `translate(tables, text, mode=4)` 以 liblouis 的方式回傳點字方、`braille_to_raw` 與 `raw_to_braille`）。假 helper 讓 ASCII 字母對應一格、數字兩格（數符）、CJK 字三格並在每段 CJK 連續字的結尾多一個空白點字方（讓 `reclean_braille_endspace` 修剪）、其他符號一或兩格；表名含 `en` 時，把 `the`/`and`/`ing` 對應為一格（讓 `bind_contracted_tokens` 合併）。數學使用真正的 `MathCATMathTranslator` 搭配確定性的假 `translate_math`。如此可在不需原生程式碼的情況下，涵蓋 adapter、pipeline、語言切換、邊界空白、字面點字、合併、token 綁定與換行。
   - 資料：真正的 `client/data` CSV（字元對應、注音、點字轉 ASCII）；暫存字典含一列 `Braille/Unicode`（`台灣` -> `⠞⠺`）；`translation_tables = {"default": "zh-tw.ctb", "en": "en-ueb-g2.ctb", "zh": "zh-tw.ctb", "math": "Nemeth"}`；`lang="zh_TW"`；`charset_maps=DEFAULT_CHARSET_MAPS`。
   - 輸入（至少）：夾有英文詞與全形標點的中文段落；含行內數學、數學後緊接逗號、以及中文詞的英文句；數學前後有空白的文字（P2-5 的情形，依目前行為鎖定）、硬換行、相鄰的 `）（` 與 `」『`（讓 `reclean_token` 插入空白）；跳脫的錢號、分數、前後無空白的數學、`Testing, (one) [two]!`；含空行與前導空白的字典字面點字；以及由上述組成、至少 300 段的長文件。
   - 每個短輸入以寬度 1、10、24、40 的 `unicode` 模式，以及寬度 24 的 `ascii` 模式執行；長文件以寬度 40 執行。
   - 每次執行的快照：`display_text`；`wrap_translation_results(...)`（兩個字串）；合併結果的四個 list；經過 `reclean_braille_endspace`、`bind_word_tokens` 與 `reclean_token` 後的四個 list；`translate_with_language(...)` 的四個 list；每個 Dual View 段的 `source_kind` 與四個 list（在轉換之後讀取，證明換行沒有修改它們）；`build_dual_view_model(..., mathml_converter=<確定性假轉換器>)` 每個 `AlignmentItem` 的所有欄位；以及該模型 `render_dual_view_html` 的 SHA-256。使用假轉換器讓 fixture 不受 `latex2mathml` 版本影響；真正的轉換器由 A3 鎖定。
   - fixture 為 JSON，使用 `ensure_ascii=False`、排序鍵與縮排，diff 易讀。模組有 `__main__` 進入點可重寫 fixture，只在步驟 2 執行一次。此 harness 的原型在 `7095265` 上以 `PYTHONHASHSEED` 0-3 執行，快照完全相同。
2. **合併語意**（`tests/test_translation_result_core.py`）：合併 `[]` 與 `None` 得到四個空 list；合併單一結果得到相等的結果，且 list 不是輸入的 list；修改合併後的 list（或對它呼叫 `reclean_braille_endspace`）不影響任何輸入；合併三個手動建立的結果得到預期的偏移；非結果項目拋出訊息不變的 `TypeError`；`a + b` 得到與今天相同的四個 list。
3. **真正的 MathML 接線**：在 `tests/test_gui_document_flows.py` 中，frame 對含數學段（`x^2`）的快取結果呼叫 `_render_dual_view_for_open_document()`，結果等於 `render_dual_view_html(build_dual_view_model(results, mathml_converter=latex_to_mathml), empty_message=...)` 且包含 `latex_to_mathml("x^2")`；同一份結果經由 `ExportCoordinator.write_document(..., "html")` 匯出時寫入完全相同的位元組。（`build_dual_view_model` 已接受該關鍵字參數，所以這些測試在變更前後都會通過。）
4. **常數值**（`tests/test_translation_result_core.py`）：結果的 12 個標點屬性等於今天的字面集合，且 `{k: list(v) for k, v in result.lang_blocks.items()} == build_language_blocks({"ja", "zh", "ko"})`。

### B. 共用常數（步驟 3）

- `vars(TranslationResult([], [], [], []))` 恰好只有四個資料鍵。
- 建立結果時不會呼叫 `translate.build_language_blocks`（以 `Mock` patch）。
- 12 個屬性都是 `frozenset`，且無法對 `lang_blocks` 指派項目（`TypeError`）。

### C. 相等比較（步驟 4）

`result == object()` 為 `False`、`result != "x"` 為 `True`、`result.__eq__(42) is NotImplemented`、兩個相等的結果比較為相等，且 `hash(result)` 拋出 `TypeError`。

### D. 線性合併守衛（步驟 5）

- **結構性（主要、確定性）：** 合併 500 個結果只建立一個 `TranslationResult`（以包裝函式計算 `__init__` 呼叫次數），且從不呼叫 `__add__`（以 `side_effect=AssertionError` patch）。逐對合併的迴圈會建立 501 個實例並呼叫 `__add__` 500 次，所以舊程式碼不需任何計時就會失敗。
- **規模後盾：** 合併 20,000 個單 token 結果，結果等於以單純偏移算術建立的參考值，且在 5 秒內完成（`time.perf_counter`）。新程式碼預期只需數十毫秒；舊程式碼需要遠超過一分鐘（由 8,000 段的量測外推），超過 100 倍的餘裕讓它在慢機器上也不會不穩定。

### E. 依賴守衛（步驟 6 與 7，`tests/test_translation_import_isolation.py`，與既有測試一樣使用子行程）

- `import conversion.service, conversion.output, conversion.wrapping` 不載入任何 `dual_view` 模組。
- `import dual_view, dual_view.model, dual_view.html` 不載入任何 `conversion` 模組，也不載入 `config`。
- 未傳 `mathml_converter` 呼叫 `build_dual_view_model([])` 會拋出 `TypeError`（`tests/test_dual_view_model.py`）。

### F. 更新的測試

- 五個模組把 `DualViewSegment` 的 import 改為 `conversion.output`。
- 20 處未傳轉換器的 `build_dual_view_model` 呼叫改為傳入轉換器。純文字測試傳入一個會拋出 `AssertionError` 的模組輔助函式（文字段不得呼叫轉換器）；`test_gui_document_flows.py` 的匯出比對傳入 `latex_to_mathml`，與正式接線一致。
- `tests/test_translation_result.py` 不在此轉換或修正（P2-5）。作為手動檢查，直接呼叫其 13 個函式，變更前後都得到相同的 8 個通過與相同的 5 個失敗（例外型別相同）。

## 驗收條件

1. 路線圖驗證在 Linux 上通過：`cd client && python -m unittest tests.test_translation_result tests.test_translation_result_core tests.test_dual_view_model tests.test_dual_view_html tests.test_conversion_service -v`（`test_translation_result` 貢獻 0 個測試，見上文；只剩 P2-5 失敗）。另外 `tests.test_translation_golden tests.test_translation_import_isolation tests.test_conversion_language_explicit tests.test_document_formats tests.test_gui_document_flows tests.test_export_coordinator tests.test_conversion_text_pipeline`。
2. `git diff <步驟 2 的 commit> HEAD -- client/tests/fixtures/translation_golden.json` 為空，且之後每個 commit 上 `tests.test_translation_golden` 都通過。
3. `python -m unittest tests.test_translation_result_core tests.test_conversion_service` 只回報 P2-5 失敗（沒有錯誤），反向順序亦同。
4. 全套測試（字母順序）：754 + 新增測試，`failures=1`（只有 P2-5）、`errors=0`、`skipped=9`。
5. 打亂順序的全套測試，種子 0-19（以 `random.Random(seed)` 打亂模組順序、單一行程、`unittest.TextTestRunner`；即 P0-4 起使用的 harness）：每個種子執行的測試數相同，皆為 `failures=1 errors=0`，唯一失敗的測試是 `test_translate_with_language_does_not_duplicate_existing_spaces_around_math`。
6. `grep -rnE "(from|import) dual_view" client/conversion` 沒有輸出，且 `grep -rnE "(from|import) conversion" client/dual_view` 只輸出 `dual_view/model.py` 中的 `TYPE_CHECKING` import。E 部分的子行程守衛才是具約束力的檢查。
7. `grep -rn "^\s\+from translate import" client --include=*.py | grep -v tests/` 沒有輸出。
8. `grep -n "self\.\(LEFT\|RIGHT\|MIDDLE\|END\)_[A-Z_]* = \|self.lang_blocks = " client/translate.py` 沒有輸出。
9. `git diff main --stat -- client/locales scripts client/braille` 為空；沒有使用者可見字串變更。

## 風險

- **隱性輸出漂移**（影響高、可能性低）。緩解：以未修改程式碼對真實混合輸入、多種寬度產生 golden fixture，並在換行之後讀取 Dual View 段；fixture 在步驟 3-7 必須逐位元組不變。
- **新合併的 list 共用**（影響中、可能性低）。若 `concat` 回傳輸入的 list（例如單段捷徑），`reclean_braille_endspace` 會破壞 Dual View 快取。緩解：A2 測試零個、一個輸入與修改的情況；不允許任何捷徑。
- **共用的可變常數**（低）。frozenset 與唯讀 mapping 讓意外修改直接拋出例外，而不是在實例間外洩。
- **相等比較的變更**（低）。結果與其他型別比較時不再拋出例外。沒有呼叫端依賴該例外（全套測試探針）。
- **Stub scope 驅逐**（低）。`test_dialog_display` 以 `evict_everything` 載入 `dialog.py`，會驅逐 `documents.formats`，以及步驟 7 之後它直接 import 的 `conversion.math_service`（之前是經由 `dual_view.model`）。重新 import 只會產生新的模組物件，不會有跨越 `isinstance` 檢查的類別。驗收條件 5 涵蓋此風險。
- **計時後盾不穩定**（低）。超過 100 倍餘裕；結構性測試才是真正的守衛。
- **僅限 Windows 的路徑**（中，在此無法驗證）。liblouis adapter 現在建立的結果其常數為類別屬性、合併為線性；輸出必須一致。見 Windows 驗證待辦。

## 調查中發現的已知缺陷（本任務不修正）

1. `tests/test_translation_result.py` 從未在 `unittest` 下執行，直接呼叫時 13 個函式中有 5 個失敗（P2-5 應轉換它並決定預期行為）。
2. `tests/test_language_detection_translation.py`（僅限 Windows）import 已不存在的 `translate.translate`，在 Windows 上會出錯。
3. **`reclean_braille_endspace` 也是平方複雜度**，與它修剪的 token 數成正比：每次修剪都從兩個 list 中段刪除，並位移之後所有 `raw_to_braille_pos` 項目。在此量測的最壞情況（每個 token 的點字都以空白點字方結尾）：修剪 10,000 個 token 3.8 秒、20,000 個 15.4 秒、40,000 個 62 秒。真正的 liblouis 輸出（例如 `zh-tw.ctb` 處理中文段落）會修剪多少 token，在 Linux 上無法量測。路線圖該列不包含此項，而且這個方法屬於 P2-5 要重整的對位後處理，所以此處維持原狀；本任務的 golden fixture（其假 helper 在每段 CJK 連續字結尾都會觸發修剪）就是 P2-5 或獨立任務修正它時的安全網。
4. `language_has_all` 對 `bind_word_tokens` 檢查的每個字元都建立一個 `set`（常數倍成本，不是平方）。屬 P2-5。

## Windows 驗證待辦

- 在打包版本上，變更前後各做一次：以 `zh-tw.ctb` 與 `en-ueb-g2.ctb` 轉換一份含行內數學的長篇中英混合文件（例如匯入的 PDF 或 EPUB 章節）；點字結果文字、ASCII 輸出模式與匯出的 BRL 必須逐位元組相同，長文件的轉換應明顯變快。同時統計 `reclean_braille_endspace` 對該文件修剪了多少 token（已知缺陷 3），以便排定後續修正的優先順序。
- 對含數學的文件開啟 Dual View 視窗並匯出 HTML；兩者都必須與變更前的輸出一致（原文欄顯示 MathML）。
- 執行僅限 Windows 的模組（`tests.test_liblouis_runtime`、`tests.test_translation_language_result`、`tests.test_language_detection_translation`）並與基線比較（後兩者因上述原因本來就會失敗）。
- 沒有選單、對話框或字串變更，因此不需要截圖，也不需要執行 `generate-pot.bat`。

## 不在範圍內

- tokenizer 與換行器的抽出、把 `TranslationResult` 移到 `conversion/alignment.py`、P2-5 的失敗測試，以及轉換或修正 `tests/test_translation_result.py`（皆屬 P2-5）。
- 把 `bind_word_tokens` 與 `wrap` 內每次呼叫建立的集合提升、`language_has_all` 的效能，以及 `reclean_braille_endspace` 的平方修剪（P2-5 或獨立任務；已知缺陷 3 與 4）。
- `conversion/text/pipeline.py` 的函式內 import，以及字典／字元表的重複載入（P1-6）。
- `documents/formats <-> documents/workspace`（D-5），以及把 `DualViewSegment.result` 或 `ConversionOutput.translation_results` 的型別寫得更精確。
- `ApplicationPaths`（P2-6）與縮排（P2-8）。
