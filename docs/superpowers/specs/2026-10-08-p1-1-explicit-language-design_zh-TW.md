# 明確傳遞轉換語言（P1-1）設計

## 目標

讓轉換流程不再從全域 `config` 模組讀取轉換語言與「字元集 → 語言」對應表。由 UI 層（`BrailleFrame`；CLI 示範則為 `main.py`）讀取這兩個值、放進 `ConversionRequest`，下層一律以參數接收。本項對應 `storage/refactor.md` 第 6.2 節路線圖的 P1-1，涵蓋發現 D-1（3.5 節，DIP）。

具體而言：

- `ConversionRequest` 新增 `lang` 與 `charset_maps`。
- `LanguageDetector` 的建構子接收 `default_lang` 與 `charset_maps`。
- `MathCATAdapter.get_braille_for_mathml(..., language=...)` 明確接收語言，呼叫它的數學翻譯鏈也一樣。
- `braille/tables/__init__.py` 的 `getDefaultTableForCurLang` 接收 `lang`。
- `conversion/text/pipeline.py`、`languageDetection/__init__.py`、`conversion/mathcat_adapter.py`、`braille/tables/__init__.py` 不再 import `config`。

這是保持行為不變的重構。在相同的 `config.json`、`TEXT2BRAILLE_LANG` 與輸入文字下，程式產生的點字與先前相同。使用者可見字串不變。

## 現況（2026-10-08 於 `refactor/p1-1-explicit-language`、HEAD `7f0d127` 驗證，P0-1..P0-6 已合併）

縮排：`languageDetection/__init__.py`、`conversion/mathcat_adapter.py`、`conversion/math_service.py`、`braille/tables/__init__.py`、`gui.py` 使用 tab。`conversion/text/pipeline.py`、`conversion/output.py`、`conversion/service.py`、`adapters/translation/*.py`、`main.py` 與大多數測試使用 4 個空白。僅限 Windows 的測試 `test_language_detection_translation.py` 與 `test_translation_language_result.py` 使用 tab。

### 值如何產生（`client/config.py`）

- `get_lang()`（第 141 行）依序回傳：`_runtime_lang`（只由 `set_lang` 設定）、環境變數 `TEXT2BRAILLE_LANG`、`config.json` 頂層的 `"language"`，否則為 `"zh_TW"`。每次呼叫都會讀 `config.json`。回傳值保持原樣（可能是 `"zh_TW"`、`"zh-TW"` 或 `"en"`）。
- `get_charset_maps()`（第 152 行）每次呼叫都從 `config.json` 讀 `language_detection.charset_maps`，並合併到 `DEFAULT_CHARSET_MAPS` 之上。結果一定包含三個鍵（`latinCharactersLanguage`、`CJKCharactersLanguage`、`arabicCharactersLanguage`）。
- `set_lang()`（第 160 行）沒有正式程式碼呼叫，只有 `tests/test_mathcat_adapter.py` 使用。
- UI 中沒有任何地方寫入 `"language"` 或 `charset_maps`。設定對話框（`settings/dialogs.py`）沒有語言選項；與語言相關的只有各語言的翻譯表，而翻譯表已經透過 `ConversionRequest.translation_tables` 傳遞。因此這兩個值只有在有人手動編輯 `config.json`（或測試呼叫 `set_lang`）時才會在執行期間改變。`TEXT2BRAILLE_LANG` 來自行程環境變數，在程式內不會改變。

### 所有讀取語言或字元集對應的位置（`grep -rn "get_lang\|get_charset_maps\|TEXT2BRAILLE_LANG\|set_lang" client --include=*.py`）

| 位置 | 讀取內容 | 何時求值 |
| --- | --- | --- |
| `conversion/text/pipeline.py:4, 64` | `config.get_lang().replace("-", "_").split("_", 1)[0]` 決定起始翻譯表。 | 每個純文字片段一次，在 worker thread 上。 |
| `languageDetection/__init__.py:6, 183` | `add_detected_language_commands` 中的 `defaultLang = config.get_lang()`。 | generator 開始時，每個片段一次。 |
| `languageDetection/__init__.py:340` | `find_language_for_charset` 中的 `config.get_charset_maps()[configKey]`。 | 每當字元切換到目前語言未涵蓋的拉丁或 CJK Unified Ideographs 區塊時。每次都重讀 `config.json`。 |
| `languageDetection/__init__.py:349, 357` | `_preferred_full_lang` 中包在 `try/except Exception` 內的 `pref = config.get_lang()`（docstring 也有提到）。 | 每次語言切換。 |
| `conversion/mathcat_adapter.py:9, 72` | `_configure_runtime` 中的 `get_lang().replace("_", "-").lower()`，接著用於 `SetPreference("Language", ...)` 與語音風格查詢。第 9 行也從 `config` import `DEFAULT_MATH_BRAILLE_TABLE` 與 `MATH_BRAILLE_TABLES`。 | 每個數學片段，在 worker thread 上（僅 Windows；其他平台不載入 MathCAT）。 |
| `braille/tables/__init__.py:25, 117` | `getDefaultTableForCurLang` 中的 `config.get_lang()`。 | 從不：整個儲存庫沒有呼叫者。但第 25 行的 `import config` 會在每次 import `braille.tables`（設定對話框、liblouis provider）時執行。 |
| `client_init.py:14, 149` | 以 `get_lang` 作為伺服器初始化的 locale provider。 | 不在範圍內（D-1 認為合理）。不變。 |
| `tests/test_language_detection_char_langinfo.py:18-49`、`tests/test_conversion_text_pipeline.py:141`、`tests/test_mathcat_adapter.py:48-53` | patch `languageDetection.config.*`、`conversion.text.pipeline.config.get_lang`，或呼叫 `config.set_lang`。 | 測試。 |

目前的後果：

- 一次轉換可能讀取 `config.json` 很多次；若檔案在工作途中被改，理論上同一次轉換可能混用兩種語言。
- `ConversionRequest`（`conversion/output.py:12-18`）並不自足：同一個 request 在不同的 `TEXT2BRAILLE_LANG` 或 `config.json` 下會產生不同點字。
- 沒有 patch 全域的測試（例如 `tests/test_language_detection_unicode_braille.py` 與 `tests/test_conversion_service.py` 的大部分）會受開發者實際環境與 `config.json` 影響。

### 需要這些值的呼叫鏈

- **文字：** `gui._build_conversion_request`（`gui.py:697-705`）或 `main.run_demo`（`main.py:19-29`）-> `ConversionRequest` -> `ConversionJobRunner`（worker thread）-> `conversion.service.convert_text_with_alignment` -> `conversion.output.convert_text_with_alignment` -> `translate_segments(...)`（`output.py:63`）-> `service.translate_with_language_dual_view_segments` -> `pipeline.translate_plain_text_segment` -> `LanguageDetector`。
- **數學：** `service.translate_with_language_dual_view_segments` -> `runtime.math_translator.translate(source, braille_code=...)`（`service.py:63`）-> `MathCATMathTranslator.translate`（`adapters/translation/mathcat.py:12`）-> `math_service.translate_math_segment` -> `mathml_to_nemeth_braille` -> `MathCATAdapter.get_braille_for_mathml`。`FallbackMathTranslator`（`adapters/translation/fallback.py:30`）實作同一個協定（`adapters/translation/contracts.py:25` 的 `MathSegmentTranslator`）。
- 其他呼叫 `translate_with_language*` 的地方：`tests/test_conversion_service.py`（約 10 處）與僅限 Windows 的 `tests/test_translation_language_result.py`。後者已經多傳了一個目前簽章不接受的位置參數（`"zh-tw.ctb"`），所以現在就會拋出 `TypeError`。
- `LanguageDetector(...)` 只在 `pipeline.py:61` 與測試中建立。`ConversionRequest(...)` 在 `gui.py:698`、`main.py:19` 與測試（`test_conversion_service.py` 8 處、`test_conversion_text_pipeline.py`、`test_conversion_jobs.py`）中建立。
- `dual_view/model.py` 只用 `latex_to_mathml`（與語言無關）。`documents/` 的匯出經由 `BrailleFrame._start_conversion`，所以使用同一個 request 建構方法。

### 不得編輯的檔案

`braille/tables/__tables.py` 與 `braille/liblouis/` 是 NVDA 衍生或 vendored 的檔案。`scripts/sync-nvda.py` 只寫入 `vendor/nvda/`，不會重新產生 `client/braille/tables/__init__.py`，因此這個第一方膠水檔可以編輯。

### 基準

- HEAD `7f0d127` 的完整測試（Linux venv）：554 個測試，`failures=1`（已知的 P2-5 `test_translate_with_language_does_not_duplicate_existing_spaces_around_math`），`skipped=7`。
- 在 Linux 上，路線圖的聚焦指令會在載入時中止：`tests.test_language_detection_translation` 在 import 時拋出 `unittest.SkipTest`，以名稱載入它會讓整次執行停止。Linux 上的驗證必須排除這兩個僅限 Windows 的模組（見驗收標準）。

## 設計

### 值與命名

| 層 | 名稱 | 型別 | 意義 |
| --- | --- | --- | --- |
| `ConversionRequest` | `lang` | `str` | `config.get_lang()` 回傳的原始值，未正規化（`"zh_TW"`、`"zh-TW"`、`"en"`……）。 |
| `ConversionRequest` | `charset_maps` | `dict[str, str]` | `config.get_charset_maps()` 回傳的完整合併對應表。 |
| 文字 pipeline、service 函式 | `lang`、`charset_maps` | 同上 | 原樣傳遞。 |
| `LanguageDetector` | `default_lang`、`charset_maps` | 同上 | 相同的值。 |
| 數學鏈 | `language` | `str` | 與 `lang` 相同的原始值。 |

原始值原樣往下傳，由各個使用端照現在的方式正規化（pipeline：`replace("-", "_").split("_", 1)[0]`；MathCAT：`replace("_", "-").lower()`；偵測器：直接使用）。在頂層統一正規化會比較乾淨，但對 `"zh-TW"` 形式的值可能改變偵測結果，所以不在本次範圍。

所有新參數都是**必填**（沒有預設值）。預設值等於隱藏的後備語言，正是 D-1 要移除的東西。所有呼叫者都在本儲存庫內，會在同一個變更中一起更新。

### 在哪裡讀取、何時讀取

`BrailleFrame._build_conversion_request` 在 UI thread 上**每個轉換 request 讀取一次**這兩個值，放進 request：

```python
return ConversionRequest(
	...,
	translation_tables=self.translation_tables.copy(),
	lang=get_lang(),
	charset_maps=get_charset_maps(),
)
```

`gui.py` 在既有的 `from config import (...)` 區塊中加入 `get_charset_maps` 與 `get_lang`。

為什麼是每個 request 讀一次，而不是 frame 啟動時讀一次：

- **完全保留現有行為。** 目前在程式執行中手動編輯 `config.json`（`"language"` 或 `charset_maps`），下一次轉換就會生效。若改成啟動時讀一次，就會默默變成需要重新啟動。這仍符合路線圖「由 `BrailleFrame` 讀一次後傳入」的意思：每次轉換只有一個讀取點，位於 `BrailleFrame`，取代 worker thread 上散落各處的多次讀取。
- **設定變更的傳遞不需要新程式碼。** 設定對話框沒有語言選項。翻譯表變更已經透過 `self.translation_tables` 傳到下一個 request（P0-2）。若日後加入語言選項，因為 request 建構方法讀取的是當下的值，下一個 request 會自動取得。
- **成本可忽略：** 每次轉換在 UI thread 上讀兩次小型 JSON；目前則是在 worker thread 上每個片段、每次語言切換各讀一次以上。
- `TEXT2BRAILLE_LANG` 的意義與優先順序不變，因為 `config.get_lang()` 本身不變。

`get_charset_maps()` 每次都回傳新的 dict，所以每個 request 擁有自己的對應表，不會與 frame 或 config 狀態共用參考。

`main.run_demo`（CLI 示範）做法相同：建構 request 時呼叫一次 `get_lang()` 與 `get_charset_maps()`。`main.py` 在既有的 `config` import 中加入這兩個名稱。

### 執行緒

request 是在 UI thread 上建立的 frozen dataclass。worker thread 只讀 `request.lang` 與 `request.charset_maps`。工作執行中變更設定或編輯 `config.json` 不會影響該工作，這比現在更嚴格（現在中途編輯可能改變同一工作後面的片段）。`LanguageDetector` 以 `dict(...)` 複製 `charset_maps`，不與 request 共用 dict。request 以下沒有任何程式會修改這兩個值。

共用的 `MathCATAdapter` 本來就會在每次呼叫時重新套用所有偏好設定（包含 `Language`），因此每次呼叫傳入語言仍維持這個保證。

### `ConversionRequest`（`conversion/output.py`）

```python
@dataclass(frozen=True)
class ConversionRequest:
    raw_text: str
    output_mode: str
    width: int
    dictionary_path: Path
    data_dir: Path
    translation_tables: dict[str, str]
    lang: str
    charset_maps: dict[str, str]
```

`convert_text_with_alignment` 以關鍵字參數往下傳：

```python
translations = translate_segments(
    text,
    request.dictionary_path,
    request.translation_tables,
    request.data_dir / "Bopomofo2Braille.csv",
    runtime=runtime,
    lang=request.lang,
    charset_maps=request.charset_maps,
)
```

`output.py` 仍然不 import `config`。

### Service 函式（`conversion/service.py`）

在 `translate_with_language_dual_view_segments`、`translate_with_language_segments`、`translate_with_language`，以及 `convert_text_with_alignment` 內的 `translate_segments_with_dual_view` closure 中，於 `runtime` 之後加入僅限關鍵字的 `lang: str, charset_maps: dict[str, str]`，並往下傳：

- 傳給 `_translate_plain_text_segment(..., runtime=runtime, lang=lang, charset_maps=charset_maps)`；
- 傳給 `runtime.math_translator.translate(segment["text"], braille_code=math_braille_code, language=lang)`。

邊界空白的翻譯（`runtime.text_translator.translate(" ", table=default_table, ...)`）不使用語言，維持不變。`service.py` 保留 `from config import DEFAULT_MATH_BRAILLE_TABLE`（不屬於本項任務）。

### 文字 pipeline（`conversion/text/pipeline.py`）

```python
def translate_plain_text_segment(
    text: str,
    dictionary_path: Path,
    translation_tables: dict[str, str],
    bopomofo_path: Path,
    *,
    runtime: TranslationRuntime,
    lang: str,
    charset_maps: dict[str, str],
):
    ...
    language_detector = LanguageDetector(language, default_lang=lang, charset_maps=charset_maps)
    sequence = list(language_detector.add_detected_language_commands([text]))

    default_lang = lang.replace("-", "_").split("_", 1)[0]
```

移除 `import config`（第 4 行）。函式其餘部分不變。

### `LanguageDetector`（`languageDetection/__init__.py`）

```python
def __init__(self, availableLanguages, *, default_lang: str, charset_maps: Mapping[str, str], char_langinfo=None):
	self.default_lang = default_lang
	self.charset_maps = dict(charset_maps)
	...
```

- `add_detected_language_commands`：`defaultLang = self.default_lang`。保留 NVDA 風格、已註解掉的 `# defaultLang = getSynth().language`。
- `find_language_for_charset`：`lang = self.charset_maps.get(configKey)`；若為 truthy 就回傳，否則繼續走到 `return langs[0]`。目前 `config.get_charset_maps()` 一定包含所有鍵，`[configKey]` 不會拋錯。改為注入之後，呼叫者可能傳入不完整的對應表；把缺少的項目視為「沒有設定語言」並走既有路徑，是最自然的解讀，也避免在偵測深處拋出 `KeyError`。正式行為不變，因為程式一定傳入完整合併後的對應表。
- `_preferred_full_lang`：第 2 步改用 `pref = self.default_lang`，並移除 `try/except Exception`（它原本保護的是設定檔 I/O，現在這裡已不做 I/O）。更新 docstring 中提到 `config.get_lang()` 的那一行。
- 移除 `import config`（第 6 行）。第 10 行的 NVDA 註解 `# import config` 可以保留；驗收檢查只看真正的 import 敘述。
- 其他維持原狀：camelCase 命名、NVDA 註解與演算法（refactor.md 第 7 節第 1 點）。在 `typing` import 中加入 `Mapping`。

`default_lang` 與 `charset_maps` 是僅限關鍵字參數，所以既有的位置參數 `availableLanguages` 與選用的 `char_langinfo` 意義不變。

### 數學鏈

- `adapters/translation/contracts.py`：`MathSegmentTranslator.translate(self, source: str, *, braille_code: str, language: str) -> TranslationResult`。
- `adapters/translation/fallback.py`：`FallbackMathTranslator.translate(self, source, *, braille_code, language)`。它忽略 `language`，就像目前忽略 `braille_code` 一樣。
- `adapters/translation/mathcat.py`：`MathCATMathTranslator.translate(self, source, *, braille_code, language)` 呼叫 `self._translate_math(source, braille_code=braille_code, language=language)`。
- `conversion/math_service.py`：
  - `mathml_to_nemeth_braille(mathml_text, braille_code=DEFAULT_MATH_BRAILLE_TABLE, *, language: str)` 呼叫 `get_shared_mathcat_adapter().get_braille_for_mathml(mathml_text, braille_code=braille_code, language=language)`。
  - `translate_math_segment(latex_text, braille_code=DEFAULT_MATH_BRAILLE_TABLE, *, language: str)` 往下傳 `language`。log 訊息與 `MathConversionError` 包裝不變。
  - `math_service.py` 保留 `from config import DEFAULT_MATH_BRAILLE_TABLE`。它不在本次要清理的四個模組之列。
- `conversion/mathcat_adapter.py`：
  - `get_braille_for_mathml(self, mathml_text: str, braille_code: str | None = None, *, language: str) -> str` 呼叫 `self._configure_runtime(libmathcat, braille_code, language)`。
  - `_configure_runtime(self, libmathcat, braille_code: str | None, language: str)` 以 `mathcat_language = language.replace("_", "-").lower()` 開始，其餘與現在相同（相同的偏好設定順序與語音風格查詢）。
  - 移除 `from config import ...`（第 9 行）。它需要的兩個常數改由新的葉模組提供（下一項）。
- 新增 `conversion/math_braille_codes.py`（沒有任何 import）：

  ```python
  MATH_BRAILLE_TABLES = ("UEB", "Nemeth")
  DEFAULT_MATH_BRAILLE_TABLE = "UEB"
  ```

  `mathcat_adapter.py` 從這裡 import 兩者。`config.py` 把原本兩行常數定義改成 `from conversion.math_braille_codes import DEFAULT_MATH_BRAILLE_TABLE, MATH_BRAILLE_TABLES  # noqa: F401  (re-exported)`，因此 `config.MATH_BRAILLE_TABLES`、`config.DEFAULT_MATH_BRAILLE_TABLE`，以及 `service.py`、`math_service.py` 現有的 `from config import DEFAULT_MATH_BRAILLE_TABLE` 都繼續運作，值相同。`conversion/__init__.py` 是空的，所以 `config` import 這個葉模組不會帶來 import 副作用，也不會形成循環。P2-3 之後可以再決定設定選項從哪裡讀這些常數。

  已排除的替代方案：常數留在 `config`（`mathcat_adapter` 仍得 import `config`）；搬進 `mathcat_adapter.py`（`config` 就得 import MathCAT 膠水模組）；複製一份（兩個真相來源）。

### `braille/tables/__init__.py`

```python
def getDefaultTableForCurLang(tableType: TableType, lang: str) -> str:
	"""Gets the file name of the default braille table for C{lang}.
	DotExpress: the caller passes the language; upstream NVDA reads languageHandler.getLanguage().
	...
	"""
```

函式本體把 `lang = config.get_lang()` 換成參數，其餘不變（先完全比對，再比對 `_` 之前的基本語言碼，最後回傳 `DEFAULT_TABLE`）。保留 NVDA 的函式名稱，方便與上游比對；docstring 說明差異。此函式在程式中仍然沒有呼叫者。移除 `import config`（第 25 行）。第 18 行上游留下的註解 `# import config` 保留。`logging.basicConfig` 與其他膠水留給 P2-7。

### 需要更新的呼叫者

| 呼叫者 | 變更 |
| --- | --- |
| `gui.py` `_build_conversion_request` | 加入 `lang=get_lang()` 與 `charset_maps=get_charset_maps()`；兩者從 `config` import。 |
| `main.py` `run_demo` | 同樣兩個欄位；兩者從 `config` import。 |
| `tests/test_conversion_jobs.py` | 其中的 `ConversionRequest(...)` 加上 `lang` 與 `charset_maps`。 |
| `tests/test_language_detection_translation.py`（僅 Windows） | `LanguageDetector(["en", "zh_TW", "ja"], default_lang="zh_TW", charset_maps=<預設對應表>)`。`"zh_TW"` 是該測試先前實際使用的值（沒有任何設定時 `get_lang()` 的後備值）。 |
| `tests/test_translation_language_result.py`（僅 Windows） | 呼叫改為 `translate_with_language(text, dictionary_path, DEFAULT_TRANSLATION_TABLES, bopomofo_path, runtime=runtime, lang="zh_TW", charset_maps=DEFAULT_CHARSET_MAPS)`。這個呼叫本來就必須為新的關鍵字參數改寫；同一處修改中順便移除開頭多餘的 `"zh-tw.ctb"` 位置參數（它讓該測試現在就拋出 `TypeError`）。這是讓呼叫符合簽章所需的最小修正；在 Linux 上無法執行。 |

`client_init.py` 繼續使用 `config.get_lang` 回報 locale。

## 維持不變的部分

- 在相同的 `config.json`、環境與輸入下：偵測器產生的語言指令、每個片段選用的翻譯表、邊界空白、MathCAT 的 `Language`/`SpeechStyle`/`BrailleCode` 偏好設定，以及因此產生的點字輸出與 dual-view 片段。
- `config.get_lang()` 的優先順序（`set_lang` 覆寫、`TEXT2BRAILLE_LANG`、`config.json` 的 `"language"`、`"zh_TW"`）與 `config.get_charset_maps()` 的合併方式。
- 執行期間編輯 `config.json`，仍會影響下一次轉換。
- `config.MATH_BRAILLE_TABLES` 與 `config.DEFAULT_MATH_BRAILLE_TABLE` 仍存在，值相同。
- `client_init.py`、`settings/*`、`conversion/jobs.py`、`dual_view/*`、`documents/*`、`braille/tables/__tables.py` 與 `braille/liblouis/` 不變。
- 沒有 `.po`/`.mo` 變更。

刻意的差異（正常使用下都看不出來）：

- 一次轉換內的所有片段使用同一份語言快照（現在若在工作執行中編輯 `config.json`，可能影響後面的片段）。
- `LanguageDetector` 收到不完整的 `charset_maps` 時，會退回該區塊的第一個語言，而不是拋出 `KeyError`（程式中不會走到）。
- import `braille.tables`、`languageDetection`、`conversion.text.pipeline`、`conversion.output` 或 `conversion.mathcat_adapter` 不再連帶 import `config`（因此也不再建立它的 logger）。

## 測試計畫

先在現有程式碼上寫特性測試（characterization tests），讓預期值來自目前的行為。接著修改程式碼，測試只更新呼叫形式。

### 更新的測試

- `tests/test_language_detection_char_langinfo.py`：把每個 `patch("languageDetection.config.get_lang", return_value="en")` 改為在建構子傳入 `default_lang="en"` 與 `charset_maps=<預設對應表>`。`test_charset_map_is_loaded_from_config` 改名為 `test_charset_map_comes_from_constructor`，把 `CJKCharactersLanguage: "ja"` 的對應表傳給建構子。預期序列不變。
- `tests/test_language_detection_unicode_braille.py`：傳入 `default_lang="zh_TW"` 與預設對應表（即它先前隱含使用的值）。
- `tests/test_conversion_text_pipeline.py`：`test_plain_text_translation_uses_current_language_when_no_language_command` 改為傳入 `lang="en"` 與預設對應表，不再 patch。`test_alignment_output_entry_applies_source_preprocessing_once` 加上兩個 request 欄位。
- `tests/test_conversion_service.py`：每個 `ConversionRequest(...)` 加上 `lang="zh_TW"` 與預設對應表；每個 `translate_with_language*` 呼叫加上 `lang="zh_TW", charset_maps=<預設對應表>`（使用模組層級常數 `LANG`/`CHARSET_MAPS`）。`FakeMathTranslator.translate` 接收 `language` 並記錄 `(source, braille_code, language)`。`test_translate_with_language_passes_selected_math_braille_code` 預期 `[("1", "UEB", "zh_TW")]`。已知的 P2-5 失敗維持原狀。
- `tests/test_mathcat_adapter.py`：移除 `config` import 與呼叫 `config.set_lang` 的 `setUp`/`tearDown`；每個 `get_braille_for_mathml` 呼叫傳入 `language="zh_TW"`。預期的偏好設定不變（`("SetPreference", "Language", "zh-tw")`）。
- `tests/test_math_service.py`：`translate_math_segment(r"\frac{2}{", language="zh_TW")`。
- `tests/test_math_translation_adapter.py`：假的 `translate_math` 接收 `language`；呼叫傳入 `language=...`；記錄的呼叫包含它。
- `tests/test_translation_fallback.py`：`FallbackMathTranslator().translate(..., braille_code="Nemeth", language="zh_TW")`。
- `tests/test_conversion_jobs.py`、`tests/test_language_detection_translation.py`、`tests/test_translation_language_result.py`：見上方呼叫者表格。
- `tests/test_gui_document_flows.py`：兩個既有的 `_build_conversion_request` 測試（`test_conversion_request_copies_frame_translation_tables`、`test_applied_settings_tables_reach_next_conversion_request`）patch `gui.get_lang` 與 `gui.get_charset_maps`，不再讀開發者實際的 `config.json`。

### 新增的測試

1. **相同 request、不同環境**（新檔 `tests/test_conversion_language_explicit.py`）：建立一個 `ConversionRequest(lang="en", charset_maps=<預設對應表>, ...)`，內容為混合文字與行內數學（例如 `"Hello 中文 $1$"`）。以會記錄呼叫的假文字與數學翻譯器、注入的 `map_char`、暫存的資料與字典檔（與 `test_conversion_service.py` 相同的設定）執行 `conversion.service.convert_text_with_alignment`。執行兩次：一次 `TEXT2BRAILLE_LANG=zh_TW`、一次 `TEXT2BRAILLE_LANG=ja`（`patch.dict(os.environ, ...)`，並把 `config._runtime_lang` 設為第三個值，結束後還原）。兩次都以 `side_effect=AssertionError` patch `config.get_lang` 與 `config.get_charset_maps`。斷言：`display_text` 相同、記錄的文字翻譯器 `(text, table)` 呼叫相同、數學呼叫相同，且每個數學呼叫的 `language == "en"`。
2. **使用 request 的語言**（同一檔案）：在翻譯表 `{"default": ..., "en": ..., "zh": ..., "ja": ...}` 下，文字 `"→"`（它的區塊在 `languageDetection.blocks.BLOCKS` 中對應到 `None`，屬於不參與偵測的字元，因此偵測器不產生語言切換；它不是 Unicode 點字，所以仍會交給 runtime 翻譯器）在 `lang="en"` 時用 `en` 翻譯表、在 `lang="zh_TW"` 時用 `zh` 翻譯表。數字與 ASCII 標點不適用：在 `zh_TW` 下它們會切換到 `en`。在現有程式碼上的特性結果（patch `config.get_lang` 的偵測器）：`"→"` 在 `en` 與 `zh_TW` 下都得到 `["→"]`；`"1+1"` 在 `en` 下得到 `["1+1"]`，在 `zh_TW` 下得到 `["en", "1+1"]`。
3. **使用 request 的 `charset_maps`**（`tests/test_conversion_text_pipeline.py`）：翻譯表 `{"default": ..., "en": ..., "zh": ..., "ja": ...}`、`lang="en"`、文字 `"A中"`：`CJKCharactersLanguage: "zh"` 時 `中` 用 `zh` 翻譯表；`CJKCharactersLanguage: "ja"` 時用 `ja` 翻譯表。
4. **偵測器以 `default_lang` 決定偏好的完整語系**（`tests/test_language_detection_char_langinfo.py`）：`LanguageDetector(["en", "zh"], default_lang="zh_HK", charset_maps=<預設對應表>)` 處理 `[LangChangeCommand("en"), "中"]` 時產生 `["en", "zh_HK", "中"]`（`_preferred_full_lang` 的第 2 步；已在現有程式碼上以 `config.get_lang` patch 成 `"zh_HK"` 確認）。另外：`LanguageDetector(["en", "zh", "ja"], ...)` 處理 `"Hello 中文 "`，在 `default_lang="en"` 時產生 `["Hello ", "zh", "中文 "]`，在 `default_lang="zh_TW"` 時產生 `["en", "Hello ", "zh_TW", "中文 "]`（同樣已在現有程式碼上確認）。
5. **偵測器收到不完整的對應表**（同一檔案）：`charset_maps={}`、`default_lang="zh_TW"`、可用語言 `["en", "zh_TW"]`，文字 `"中A"` 不會拋錯，並產生 `["中", "en", "A"]`（Basic Latin 的第一個語言；目前使用完整預設對應表也得到相同序列）。此案例不要用 CJK 字元：CJK 區塊的 `blockLanguages` 是迭代 `set` 建立的，`langs[0]` 取決於 hash 隨機化。
6. **偵測器建構子必須明確傳值**（同一檔案）：`LanguageDetector(["en"])` 拋出 `TypeError`。
7. **MathCAT 語言逐次指定**（`tests/test_mathcat_adapter.py`）：`get_braille_for_mathml(..., language="en_US")` 設定 `("SetPreference", "Language", "en-us")`；同一個 adapter 先後以 `"zh_TW"`、`"en"` 呼叫兩次，各自套用自己的語言。不傳 `language` 的 `get_braille_for_mathml("<math/>")` 拋出 `TypeError`。
8. **數學 service 往下傳語言**（`tests/test_math_service.py`）：把 `conversion.mathcat_adapter.get_shared_mathcat_adapter` patch 成會記錄呼叫的假物件後，`translate_math_segment("1", braille_code="Nemeth", language="en")` 會呼叫 `get_braille_for_mathml(<mathml>, braille_code="Nemeth", language="en")`。
9. **`getDefaultTableForCurLang` 接收 `lang`**（新檔 `tests/test_braille_tables_default_lang.py`）：`TableType.OUTPUT` 下，`"zh_TW"` -> `"zh-tw.ctb"`、`"ja_JP"` -> `"ja-kantenji.utb"`（退回基本語言碼）、`"xx"` -> `DEFAULT_TABLE`。這些值來自 `__tables.py` 的註冊表（已在 Linux 上確認）。若上游註冊表改變，測試應改從 `_outputTableForLangs` 讀取預期值，而不是寫死。
10. **清理後的模組不 import `config`**（`tests/test_translation_import_isolation.py`，在既有類別中新增測試）：以子行程執行 `import languageDetection, conversion.text.pipeline, conversion.output, conversion.mathcat_adapter, braille.tables`，並斷言 `"config" not in sys.modules`。這同時能抓到直接與間接 import。
11. **Frame 每個 request 讀取語言**（`tests/test_gui_document_flows.py`）：`gui.get_lang` 回傳 `"en"`、`gui.get_charset_maps` 回傳某個對應表時，`_build_conversion_request(...)` 帶有這兩個值。patch 的回傳值改變後建立的第二個 request 帶有新值（執行期間的變更會影響下一次轉換）。兩個 request 不共用同一個 `charset_maps` 物件。
12. **CLI 示範讀取一次語言**（新增小型測試，例如 `tests/test_main_demo.py`）：patch `main.build_default_translation_runtime`、`main.convert_text_with_alignment`、`main.get_lang` 與 `main.get_charset_maps` 後，`run_demo("x")` 建立的 request 帶有 patch 的 `lang`/`charset_maps`，印出輸出並關閉 runtime。

新測試不得依賴開發者的 `config.json` 或環境。

## 驗收標準

1. `grep -nE '^[[:space:]]*(import config\b|from config import)' client/conversion/text/pipeline.py client/languageDetection/__init__.py client/conversion/mathcat_adapter.py client/braille/tables/__init__.py` 沒有輸出。
2. `grep -rnE 'get_lang|get_charset_maps' client --include=*.py | grep -v '^client/tests/'` 只列出 `config.py`（定義）、`client_init.py`、`gui.py`（import 與 `_build_conversion_request`）、`main.py`（import 與 `run_demo`）。
3. `grep -rnE 'languageDetection\.config|pipeline\.config|config\.set_lang' client/tests` 沒有輸出。
4. `git diff main --stat -- client/braille/tables/__tables.py client/braille/liblouis` 為空。
5. 聚焦驗證（Linux；排除兩個在 Linux 上以名稱載入會中止執行的 Windows 專用模組）只剩已知的 P2-5 失敗：
   `cd client && python3 -m unittest tests.test_conversion_text_pipeline tests.test_language_detection_char_langinfo tests.test_language_detection_unicode_braille tests.test_mathcat_adapter tests.test_conversion_service tests.test_translation_import_isolation tests.test_math_service tests.test_math_translation_adapter tests.test_translation_fallback tests.test_conversion_jobs tests.test_translation_runtime_provider tests.test_conversion_language_explicit tests.test_braille_tables_default_lang tests.test_main_demo tests.test_gui_document_flows -v`
6. 完整測試：`cd client && python3 -m unittest discover -s tests -p "test_*.py"` 回報 `failures=1`（只有已知的 P2-5 失敗）、`errors=0`、`skipped=7`，測試數為 554 加上新增的測試。
7. `client/locales/` 下沒有變更。
8. Windows 上（無法在這台 Linux 主機執行；列為驗證待辦）：路線圖指令 `python -m unittest tests.test_conversion_text_pipeline tests.test_language_detection_char_langinfo tests.test_language_detection_translation tests.test_language_detection_unicode_braille tests.test_mathcat_adapter tests.test_conversion_service tests.test_translation_import_isolation -v`，加上 `tests.test_translation_language_result`、`tests.test_liblouis_runtime` 與 `tests.test_translation_runtime_provider`；並手動確認在程式中轉換中英數學混排文字，於 `TEXT2BRAILLE_LANG` 未設定與 `TEXT2BRAILLE_LANG=en` 兩種情況下，點字都與變更前相同。

## 風險

- **語言偵測對語言敏感**（中）：偵測器的輸出在三個地方取決於 `default_lang`。先寫特性測試，並原樣傳遞 `get_lang()` 的原始值，可確保結果相同。刻意不對 `lang` 做任何正規化。
- **Windows 專用路徑無法在此執行**（中）：MathCAT（`libmathcat_py.pyd`）與 liblouis 只在 Windows 載入。MathCAT 的 `Language` 偏好設定由相同字串、以相同運算式算出，假函式庫的測試固定了呼叫順序。Windows 專用測試會更新，但無法在 Linux 上執行。
- **簽章變動**（低）：所有新參數都是必填關鍵字參數，漏改的呼叫者會明確拋出 `TypeError`，不會默默使用預設值。驗收標準的 grep 涵蓋正式呼叫者；完整測試涵蓋測試程式。
- **`config` import `conversion.math_braille_codes`**（低）：新增 `config` 對一個沒有任何 import 的葉模組的相依，不可能形成循環。在 wx 測試 stub（`tests/wx_stub.py` 的 `StubScope`）下，`config` 不會被 stub；葉模組被 evict 後重新 import 也無害。請單獨執行 `tests.test_gui_document_flows`，也在完整測試中執行。
- **gui 測試讀到真實設定**（低）：新增與更新的 gui 測試會 patch `gui.get_lang`/`gui.get_charset_maps`。其他 mock 掉 `_build_conversion_request` 的 gui 測試不受影響。
- **與後續任務重疊**（低）：P1-6（字典 repository）也會改 `translate_plain_text_segment` 的簽章，會在這裡新增的關鍵字參數之外再加參數。P2-3 可能搬動數學選項；葉模組提供一個不依賴 config 的讀取位置。P2-7 會改 `braille/tables/__init__.py` 的 logging 與 `MathCATAdapter` 的注入方式，並保留明確的 `language` 參數。

## 不在範圍內

- 在設定對話框加入語言選項，或透過 `set_lang` 保存 `lang`。
- 在來源端正規化語言字串。
- 修改 `client_init.py` 的 locale provider。
- 移除 `conversion/service.py` 或 `conversion/math_service.py` 對 `config` 的 import（它們只 import 數學表常數）。
- 移除 `logging.basicConfig` 或 `braille/` 中其他 P2-7 的清理。
- 把語言偵測器改為每次轉換建立一次，而非每個片段一次（屬 P1-6 範圍）。
- 編輯 NVDA 衍生或 vendored 檔案（`braille/tables/__tables.py`、`braille/liblouis/`）。
