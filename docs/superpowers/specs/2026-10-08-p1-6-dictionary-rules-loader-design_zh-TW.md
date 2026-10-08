# 字典規則載入器（P1-6）設計

## 目標

每次轉換只讀取一次使用者字典與注音規則檔，而不是每個語言片段讀一次，且不改變任何輸出。本任務為 `storage/refactor.md`（6.2 節）路線圖的 P1-6，涵蓋 5.6 節前兩點與 4.3 節的 Repository 列：

- `dictionary_rules.apply_dictionary` 每次呼叫都開啟並解析兩個 CSV（所選字典與 `data/Bopomofo2Braille.csv`），而 `pipeline.translate_plain_text_segment` 對語言偵測產生的每個純文字項目都呼叫一次。一份中英混排文件會重讀字典 N 次。
- `char_maps._load_char_mapping` 每次轉換讀取 `data/BopomofoChar2Braille.csv` 與 `data/Braille2Ascii.csv`。

具體而言：

- `conversion/text/dictionary_rules.py` 新增 `LoadedDictionaryRules`：不可變的值物件，保存解析後的 raw 規則與 replacement 規則（及其編譯好的比對 trie），由 `LoadedDictionaryRules.from_paths(dictionary_path, bopomofo_path, *, processing)` 建立，以 `.apply(text)` 套用。
- 以轉換為範圍的 `DictionaryRulesLoader` 在第一次需要時建立它，之後回傳同一個物件。`conversion/service.translate_with_language_dual_view_segments` 每次呼叫建立一個 loader，並傳給每一次 `translate_plain_text_segment` 呼叫，因此一次轉換對每個字典檔最多讀一次。
- `apply_dictionary` 保留簽章與輸出，改為 `from_paths(...).apply(...)` 的薄包裝。
- 字元對照表目前每次轉換本來就對每個檔案最多讀一次；程式碼不變，另加讀取次數防護測試。
- 目前 `unittest` 從未執行的 pytest 風格 `tests/test_conversion_text_dictionary_rules.py` 改寫為 `unittest` 模組。

這是保持行為不變的重構。對任何輸入，點字文字、ASCII 輸出、對位資料與雙視窗片段都與 `main` 的 `cdae2f1` 逐位元組相同。P1-5 的黃金測試資料 `client/tests/fixtures/translation_golden.json`（sha256 `e67d95a1ae001d928b657f16468494d0e98beeea5a6425283090b34030211ccd`）不得變動。不更動任何使用者可見字串。

本規格已納入實作計畫（`docs/superpowers/plans/2026-10-08-p1-6-dictionary-rules-loader.md`，「Spec Corrections and Refinements」一節）的更正與細化：驗收條件 6 改用遞迴搜尋（`grep -rn`），因為對目錄執行 `grep -n` 什麼都不印、等於沒有檢查；新測試數固定為 35 個（783 -> 818）；新增兩個 pipeline 測試，固定單獨呼叫 `translate_plain_text_segment` 的讀取次數，以及傳入的 loader 優先於路徑參數；轉換測試與規則檔測試各自共用不含測試的 fixture 基底類別；規則矩陣有 11 個案例、錯誤表有 10 個；步驟 4 的紅燈執行透過模組存取新名稱，因此顯示真實的逐項讀取；步驟 2 的檢查以 5,000 個隨機案例與已提交的拆分前程式碼比對；計時條件改為「至少快 10 倍」且顯示長度相同。

不在本任務內：每個片段建立一個 `LanguageDetector`（5.6 節第三點）、前處理腳本的讀取（本來就每次轉換一次）、`_translate_plain_text_segment` 這個 monkeypatch 別名（5.5 節）、`pipeline.py` 中的函式內 import、任何跨轉換快取，以及更改 CSV 編碼或驗證規則（例如接受 BOM）。

## 現況（2026-10-08 於 `refactor/p1-6-dictionary-rules-loader` 驗證，HEAD `cdae2f1`，已合併 P0-1..P0-6 與 P1-1..P1-5）

縮排：本任務觸及的所有檔案（`conversion/text/*.py`、`conversion/service.py`、`conversion/output.py` 及下列測試模組）皆使用 4 個空白。

### 呼叫路徑與各自讀取的檔案

`ConversionPresenter._start` 在 UI 執行緒上建立 `ConversionRequest`（`gui._build_conversion_request`：`dictionary_path = dictionary_path_for_name(selected_dictionary, dictionary_dir)`、`data_dir = resource_path("data")`）。路徑固定在 request 中；UI 執行緒不開啟任何檔案。接著 `ConversionJobRunner._run_job` 在 daemon 背景執行緒上呼叫 `conversion.service.convert_text_with_alignment(request, runtime=...)`，下列所有讀檔都發生在該執行緒。`ConversionStageError` 透過 `call_after` 交回 UI；其他例外 runner 不攔截。

| 步驟（背景執行緒） | 程式碼 | 讀取檔案 | 目前每次轉換的讀取次數 |
| --- | --- | --- | --- |
| 前處理腳本 | `output.convert_text_with_alignment` -> `pipeline.preprocess_source_text` -> `execute_preprocessing_script` | `<字典目錄>/preprocessing.py` | 1 |
| 注音字元對照 | `preprocess_source_text` -> `map_char(..., data_dir / "BopomofoChar2Braille.csv")`（`char_maps._load_char_mapping`，5-30 行） | `BopomofoChar2Braille.csv` | 1 |
| 字典規則 | `service.translate_with_language_dual_view_segments`（26-73 行）-> 每個文字片段 `_translate_plain_text_segment`（52 行）-> 每個語言項目 `apply_dictionary`（`pipeline.py:70`、`dictionary_rules.py:111-184`） | 所選字典 CSV 與 `Bopomofo2Braille.csv` | 各自每個純文字項目一次 |
| ASCII 輸出 | `output.convert_text_with_alignment`，僅於 `output_mode == "ascii"`，在折行之後 | `Braille2Ascii.csv` | 0 或 1 |

以計數用的 `Path.open` 包裝器量測黃金輸入（實際的 `client/data`、黃金測試的一列字典）：

| 輸入 | preprocessing.py | BopomofoChar2Braille | Bopomofo2Braille | 字典 | Braille2Ascii（ascii 模式） |
| --- | --- | --- | --- | --- | --- |
| `chinese_prose`（3 個片段） | 1 | 1 | 3 | 3 | 1 |
| `english_math`（6 個片段） | 1 | 1 | 4 | 4 | 1 |
| `long_document`（360 個片段） | 1 | 1 | 240 | 240 | 1 |
| `$x$`（僅數學） | 1 | 1 | 0 | 0 | - |

成本：在本機上，以一列字典轉換 `long_document` 需 0.11 秒，以 2,000 列字典需 2.24 秒。以 profiler 觀察，CSV 解析約占字典時間的 40%，建立比對 trie 約占 35%（`_replace_with_trie` 每次呼叫都重建 trie，`apply_dictionary` 還會對每個 `Bopomofo` 類型的列再建一個）。兩者都隨「片段數 × 列數」成長。

因此字元對照表本來就每次轉換讀一次；熱點是字典與 `Bopomofo2Braille.csv`。

### `apply_dictionary` 的解析與驗證語意（以探測程式確認；全部必須保留）

- `dictionary_path` 以 `Path(...)` 包裝；若檔案不存在，回傳 `{"raw": text, "replacement": text}`，且**不開啟 `Bopomofo2Braille.csv`**（此時注音檔遺失或損壞都不算錯誤）。
- 否則先讀 `Bopomofo2Braille.csv`，再讀字典，兩者皆以 `open("r", newline="", encoding="utf-8")` 與 `csv.DictReader` 讀取。
- 錯誤依序為：注音檔不存在 -> `FileNotFoundError`；沒有標題列（空檔）-> `ValueError("CSV must contain header row.")`；缺欄位 -> `ValueError("CSV must contain columns: Bopomofo, Braille")`，接著字典以 `text, braille, type` 做相同檢查。無效 UTF-8 -> `UnicodeDecodeError`。不會去除 UTF-8 BOM，因此標題列帶 BOM 會在欄位檢查失敗（`ValueError`）。
- 資料列：來源（`text` 或 `Bopomofo`）為空則略過；缺少的儲存格讀為 `""`（字典列沒有 `braille` 時產生空的原子替換 `\[\]`）；多出的儲存格忽略；規則順序為檔案順序，重複來源以第一筆為準（trie）。
- `type == "Bopomofo"`：以 `processing(target)`（正式環境為 `text.zhuyin.normalize_zhuyin_sequence`，純函式，回傳 list）切分目標；若它拋出例外，例外會被吞掉，整個目標視為一個部分。每個部分再經注音規則對照。其他類型以 `@` 切分目標。部分數與來源字元數相同時逐字對齊，否則合併為一個部分，並包上 `\[...\]`。
- `bopomofo_path` 直接以 `bopomofo_path.open(...)` 使用而未經 `Path(...)`，所以傳入 `str` 會拋出 `AttributeError`。所有呼叫者都傳 `Path`。

### 轉換層級的錯誤時機（全部必須保留）

- 所有字典錯誤都以 `ConversionStageError("translation", error)` 呈現（`output.py` 中 `translate_segments` 的 try 區塊）。
- 前處理腳本先執行：即使字典損壞，腳本失敗時階段仍為 `text_processing`。
- 字典在翻譯第一個純文字項目時才開啟。空輸入在讀取任何檔案前就返回；**僅含數學的輸入從不讀字典，因此損壞的字典（或缺少 `Bopomofo2Braille.csv`）不會讓它失敗**（已探測：以沒有標題列的字典轉換 `$x$` 成功）。
- 位於第一個文字片段之前的數學片段，會在字典錯誤拋出前先被翻譯。

### 檔案在轉換期間或轉換之間會不會變動？

- **轉換之間：** 會，而且下一次轉換必須看到變動。字典管理對話框與字典條目對話框會寫入 CSV；所選字典存在設定中，於建立下一個 request 時解析為 `request.dictionary_path`。目前沒有任何地方快取解析後的規則。
- **轉換期間經由本程式：** 不會。`set_conversion_busy(True)` 會停用「檔案」與「翻譯」選單（字典管理在「翻譯」之下）、文件清單（連帶其動作彈出選單）與輸入編輯器，直到工作結束。沒有任何快捷鍵會開啟字典對話框。所選字典路徑已固定在 request 中。
- **轉換期間由外部程式：** 可能（外部編輯器存檔）。目前之後的片段會看到新檔，所以一份文件可能用兩個版本的字典轉換。
- **同時進行的轉換：** `convert_for_export` 會取代正在執行的工作但不停止它（P1-4 已知缺陷 2），因此可能有兩個背景執行緒同時轉換。目前它們不共用任何狀態。

### 目前的測試

- `tests/test_conversion_text_dictionary_rules.py` 是 7 個 pytest 風格的模組函式；`python -m unittest tests.test_conversion_text_dictionary_rules` 顯示 `NO TESTS RAN`，而 pytest 既未安裝也不是專案相依套件。直接呼叫時 7 個全部通過。
- `tests/test_conversion_text_pipeline.py`（13 個測試）與 `tests/test_conversion_text_char_maps.py` 以路徑參數呼叫 `apply_dictionary`、`translate_plain_text_segment` 與 `translate__mapping_char`。沒有測試計算讀取次數。
- `tests/test_removed_dead_code.py` 斷言 `char_maps.translate__mapping_char` 與 `dictionary_rules.apply_dictionary` 存在（P0-3 刻意保留）。
- 黃金測試資料只用一列 `Braille/Unicode` 字典；沒有 `Bopomofo` 或 `@` 列，因此未涵蓋注音分支。
- 基線：完整測試（Linux venv、字母順序）783 個測試，`failures=1`（已知的 P2-5 測試），`errors=0`，`skipped=9`。

## 設計

### `LoadedDictionaryRules`（`conversion/text/dictionary_rules.py`）

```python
@dataclass(frozen=True)
class LoadedDictionaryRules:
    raw_rules: tuple[tuple[str, str], ...] = ()
    replacement_rules: tuple[tuple[str, str], ...] = ()
    _raw_trie: _TrieNode = field(init=False, repr=False, compare=False)
    _replacement_trie: _TrieNode = field(init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "_raw_trie", _build_trie(self.raw_rules))
        object.__setattr__(self, "_replacement_trie", _build_trie(self.replacement_rules))

    @classmethod
    def from_paths(cls, dictionary_path, bopomofo_path, *, processing) -> "LoadedDictionaryRules": ...

    def apply(self, text: str) -> dict[str, str]: ...
```

- `from_paths` 就是目前 `apply_dictionary` 中兩個 `mapping(...)` 呼叫之前的內容，順序與訊息不變：`Path(dictionary_path)`；不存在 -> 回傳 `cls()` 且不碰注音檔；否則解析 `Bopomofo2Braille.csv`、只建一次它的 trie，再逐列解析字典（與目前完全相同），每個 `Bopomofo` 部分都用同一個 trie 對照。回傳 `cls(tuple(raws), tuple(replacements))`。
- `apply(text)` 回傳 `{"raw": _scan_trie(text, self._raw_trie), "replacement": _scan_trie(text, self._replacement_trie)}`。沒有規則時（字典不存在或只有標題列）直接回傳 `{"raw": text, "replacement": text}`，不掃描。以空 trie 掃描本來就回傳原文，因此此捷徑在兩種情況下結果相同。
- 不可變：frozen、欄位為 tuple、沒有 setter。trie 為私有，只在 `__post_init__` 建立一次，之後不再修改。實例即使跨執行緒共用也安全，但沒有任何地方共用。
- `processing` 是必填的關鍵字參數（無預設值），因此本模組仍不 import `text.zhuyin`。
- 接受的放寬：`from_paths` 也會以 `Path(...)` 包裝 `bopomofo_path`，所以傳 `str` 可正常運作，不再拋出 `AttributeError`。沒有呼叫者傳 `str`。

### 拆分 trie 的建立與掃描

`_replace_with_trie(text, replacements)` 拆成 `_build_trie(replacements) -> _TrieNode`（第一個迴圈，含「重複來源以第一筆為準」）與 `_scan_trie(text, root) -> str`（最長前綴掃描）。`_replace_with_trie` 改為 `return _scan_trie(text, _build_trie(replacements))`，因此 `mapping()`（公開、簽章不變）行為與之前完全相同。兩個迴圈只搬移，不修改。

### 保留 `apply_dictionary`

```python
def apply_dictionary(text, dictionary_path, bopomofo_path, processing):
    return LoadedDictionaryRules.from_paths(dictionary_path, bopomofo_path, processing=processing).apply(text)
```

簽章、回傳型別、錯誤與讀取（每次呼叫各檔一次）皆相同。本任務後正式程式碼不再呼叫它；保留它是為了既有測試以及 `tests/test_removed_dead_code.py` 的 P0-3 防護，因此該防護不需修改。

### `DictionaryRulesLoader`（轉換範圍、延遲、最多一次）

```python
class DictionaryRulesLoader:
    """Loads one conversion's dictionary rules on first use and keeps them for that conversion."""

    def __init__(self, dictionary_path, bopomofo_path, *, processing) -> None: ...  # 只保存參數，不讀檔

    def load(self) -> LoadedDictionaryRules:
        if self._rules is None:
            self._rules = LoadedDictionaryRules.from_paths(
                self._dictionary_path, self._bopomofo_path, processing=self._processing
            )
        return self._rules
```

- 刻意採延遲載入。若照路線圖字面在 `convert_text_with_alignment` 開頭立即載入，會改變錯誤行為：損壞的字典會讓目前可成功轉換的純數學輸入失敗，而字典與前處理腳本同時損壞時會回報錯誤的階段。即使改成在翻譯前一刻才立即載入，純數學輸入仍會失敗。延遲載入的讀取時間點與目前第一次呼叫 `apply_dictionary` 相同，因此例外型別、訊息、階段與時機都不變。
- 載入失敗不會被記住：`self._rules` 維持 `None`，例外往外傳（並如同目前一樣中止轉換）。
- 刻意不做執行緒安全：一個 loader 只服務一個背景執行緒上的一次轉換。沒有模組層級狀態、沒有跨轉換快取，因此每次轉換都會重讀檔案，看得到轉換開始前做的修改。

### Pipeline（`conversion/text/pipeline.py`）

```python
def dictionary_rules_loader(dictionary_path, bopomofo_path) -> DictionaryRulesLoader:
    from text.zhuyin import normalize_zhuyin_sequence
    return DictionaryRulesLoader(dictionary_path, bopomofo_path, processing=normalize_zhuyin_sequence)


def translate_plain_text_segment(
    text, dictionary_path, translation_tables, bopomofo_path, *,
    runtime, lang, charset_maps,
    dictionary_rules: DictionaryRulesLoader | None = None,
):
    if dictionary_rules is None:
        dictionary_rules = dictionary_rules_loader(dictionary_path, bopomofo_path)
    ...
            result = dictionary_rules.load().apply(item)
```

- 新關鍵字參數為選填，因此既有的直接呼叫者與測試（只傳路徑）照常運作；單獨呼叫時，每次呼叫對每個檔案最多讀一次，而不是每個項目一次。
- 傳入 loader 時以 loader 為準，不再讀路徑參數。service 以同樣的兩個路徑建立 loader，因此兩者一定一致。
- 函式內的 `text.zhuyin` import 從 `translate_plain_text_segment` 移到 `dictionary_rules_loader`，仍維持函式內 import；`LanguageDetector` 的處理不變。

### Service（`conversion/service.py`）是「每次轉換一次」的邊界

`translate_with_language_dual_view_segments` 簽章不變。在 `text == ""` 的提早返回之後，建立 `dictionary_rules = dictionary_rules_loader(dictionary_path, bopomofo_path)`，並在每次 `_translate_plain_text_segment` 呼叫傳入 `dictionary_rules=dictionary_rules`。

- `convert_text_with_alignment` 每次轉換恰好呼叫它一次，`translate_with_language` 與 `translate_with_language_segments` 也經過它，因此每個公開入口每次呼叫最多讀一次字典。
- 為何放在這裡而不是 `output.convert_text_with_alignment`（路線圖的字面說法）：這是所有文字翻譯路徑都會經過的單一函式，且 `output.py` 的 `TranslateSegments` 契約、`ConversionRequest` 與 `map_char` 注入點都不必改。若在 `output.py` 載入，就得在 `translate_segments`、service 的內部轉接函式與測試假物件之間多傳一個參數，而公開的 `translate_with_language*` 仍需要後備做法。
- 建立 loader 不讀任何檔案，所以純數學輸入仍不會讀字典。

### 字元對照表：正式程式碼不變

`BopomofoChar2Braille.csv` 與 `Braille2Ascii.csv` 目前每次轉換各最多讀一次，且讀取時間點有各自的錯誤語意（`BopomofoChar2Braille` 在使用者腳本之後、落在通用的 `translation` 處理中；`Braille2Ascii` 只在 ASCII 模式、折行之後讀，階段為 `ascii`）。把它們併入 loader，要嘛移動讀取時間點（改變失敗時機與階段），要嘛重做一套延遲機制卻沒有減少讀取次數，還會破壞四個測試使用的 `map_char` 注入點。因此 `char_maps.py` 與 `output.py` 不變；以讀取次數防護測試鎖定目前「每次轉換一次」的行為。

### 行為上的改變（刻意且有記錄）

- **每次轉換一個字典快照。** 若外部程式在轉換進行中改寫字典或 `Bopomofo2Braille.csv`，整次轉換現在都使用在第一個純文字項目讀到的版本，而不是混用多個版本。經由本程式不可能發生（忙碌時選單已停用）。下一次轉換會讀到新檔。
- `processing` 改為每次轉換對每個 `Bopomofo` 列執行一次，而不是每個項目對每列執行一次。它是純函式，輸出相同。

## 保持不變的部分

- 所有輸入的點字輸出（Unicode 與 ASCII）、原文折行、對位串列與雙視窗片段；黃金測試資料不變。
- `apply_dictionary`、`mapping`、`split_bracket_segments`、`translate_plain_text_segment`（另加一個選填關鍵字）、`translate_with_language*`、兩個 `convert_text_with_alignment`、`preprocess_source_text`、`translate__mapping_char` 與 `map_characters` 的簽章與回傳型別；`ConversionRequest`、`ConversionOutput` 與 `TranslateSegments`。
- 每種損壞或缺少檔案情況的例外型別、訊息、階段，以及拋出的時間點。
- 讀檔仍在轉換背景執行緒上；UI 執行緒仍只解析路徑。
- `dictionaries/manager.py`、`gui.py`、`ConversionJobRunner` 與轉換 presenter 都不變。不更動任何字串、選單、對話框、`.po`/`.mo`、打包、liblouis DLL 或點字表。

## 測試計畫

所有新測試皆為 `unittest`，使用 4 個空白。特性化測試（A 部分）針對未修改的正式程式碼撰寫，在任何正式程式碼變更前即通過。預期字串是從未修改程式碼擷取的字面值，絕不由受測程式碼計算。

### A. 特性化（步驟 1，正式程式碼變更前）

1. **將 `tests/test_conversion_text_dictionary_rules.py` 改為 `unittest`**：7 個函式成為 `ApplyDictionaryTest` 的方法，斷言不變（`tmp_path` 改為 `setUp` 中的 `TemporaryDirectory`）。它們從此會執行：原本默默未執行的 7 個測試。
2. **規則矩陣**（同模組，類別 `DictionaryRulesCasesTest`）：模組層級表格 `DICTIONARY_CASES`，每筆為（字典列、注音列、輸入、預期 `raw`、預期 `replacement`），涵蓋：以 `@` 切分並對齊的 `Braille` 列；長度不符合併為一個部分；來源重疊（最長者勝、不連鎖替換）；重複來源（第一筆勝）；`text` 為空的列（略過）、沒有 `braille` 儲存格的列（`\[\]`）、多一個儲存格的列；`processing` 回傳 list、拋出例外，以及使用真實 `normalize_zhuyin_sequence` 與真實 `client/data/Bopomofo2Braille.csv` 的 `Bopomofo` 列；輸入字面上含有 `\[` 與 `\]`；空輸入。只有標題列的字典也是一個案例；`text` 為空、缺儲存格與多儲存格的列共用一個字典，重疊與不連鎖替換的規則也共用一個（共 11 個案例）。一個測試以 `subTest` 將每個案例跑過 `apply_dictionary`。
3. **檔案與標題列語意**（類別 `DictionaryFileSemanticsTest`）：字典不存在 -> 原文不變且 `Bopomofo2Braille.csv` 從未被開啟（計數，且該檔不存在時亦然）；字典存在但缺 `Bopomofo2Braille.csv` -> `FileNotFoundError`；兩個檔案各自的空檔、缺欄位與帶 BOM 標題列 -> 精確的 `ValueError` 訊息；無效 UTF-8 -> `UnicodeDecodeError`；兩個檔案都損壞（兩者都缺欄位）-> 注音檔的訊息（順序）。測試輔助函式 `_error_cases()` 回傳此表（10 個案例），供步驟 3 重用；每個 `ValueError` 都比對訊息，`FileNotFoundError` 與 `UnicodeDecodeError` 只檢查型別（其訊息含暫存路徑或位元組位移）。讀取順序（先注音檔）以小型 context manager `OpenRecorder` 記錄 `Path.open` 的檔名來固定；本模組的測試共用不含測試的基底類別 `DictionaryFilesTestCase`（含 `dictionary.csv` 與 `bopomofo.csv` 的暫存目錄）。
4. **轉換層級的錯誤時機**（`tests/test_conversion_service.py`，類別 `DictionaryErrorTimingTest`，建立在與 `DictionarySnapshotTest` 共用、不含測試的基底類別 `DictionaryConversionTestCase` 上：暫存資料目錄內有只含標題列的 `BopomofoChar2Braille.csv` 與 `Bopomofo2Braille.csv`，字典位於 `dictionary/default.csv`；真實 pipeline，沿用該模組既有測試的記錄用假 runtime）：無標題列字典加文字 -> `ConversionStageError`，階段 `translation`，內含 `ValueError`；同一字典加 `$x$` 與加 `""` -> 成功；前處理腳本失敗加損壞字典 -> 階段 `text_processing`；位於第一個文字片段前的數學片段在錯誤前已翻譯（數學翻譯器被呼叫一次）。
5. **轉換之間會重新讀取**（同類別）：轉換、以不同規則改寫字典、再轉換 -> 第二次輸出使用新規則；刪除字典再轉換 -> 不套用字典。

### B. 拆分 trie（步驟 2）

不新增測試：既有測試、A 部分與黃金測試資料已涵蓋。該步驟以一次性檢查（不提交）用 `git show HEAD:` 載入已提交、尚未拆分的模組，在 5,000 組以固定 seed 產生、含標記字元的隨機規則與文字上，確認其 `_replace_with_trie` 與 `mapping(..., marker=True)` 等於新的 `_replace_with_trie`、`_scan_trie(_build_trie(...))` 與 `mapping(..., marker=True)`。（拿 `_scan_trie(_build_trie(...))` 與新的 `_replace_with_trie` 比對是同義反覆，因為後者就定義為前者。）

### C. `LoadedDictionaryRules`（步驟 3，`tests/test_conversion_text_dictionary_rules.py`，類別 `LoadedDictionaryRulesTest`）

- 每個 `DICTIONARY_CASES` 案例經 `LoadedDictionaryRules.from_paths(...).apply(input)` 得到相同的字面預期值。
- 每個 `_error_cases()` 案例由 `from_paths` 拋出相同型別與訊息的例外；字典不存在的案例回傳 `LoadedDictionaryRules()` 且不開啟注音檔。
- 實例不可變：指定 `raw_rules` 會拋出 `FrozenInstanceError`；兩個規則欄位都是依檔案順序的 `(str, str)` tuple。
- `apply` 不讀檔也不建 trie：將 `Path.open` 與 `_build_trie` 換成計數版本後，對同一實例呼叫三次 `apply`，開檔 0 次、建 trie 0 次。
- `LoadedDictionaryRules().apply(text)` 回傳 `{"raw": text, "replacement": text}`。

### D. Loader 與讀取次數（步驟 4）

- `DictionaryRulesLoaderTest`（`tests/test_conversion_text_dictionary_rules.py`）：建立 loader 不開任何檔；呼叫三次 `load()` 只呼叫一次 `from_paths` 並回傳同一物件；拋出例外的 `load()` 會在下一次 `load()` 重試（呼叫 2 次）。
- `DictionaryReadCountTest`（`tests/test_conversion_text_pipeline.py`），以檔名計數 `pathlib.Path.open`（`dictionary_rules.py` 與 `char_maps.py` 都透過 `Path.open` 開檔；測試會斷言計數的檔名中包含字典，所以若改用其他開檔函式會明確失敗，而不是以 0 次讀取空洞地通過）：
  - 一段含行內數學、會產生至少 8 個純文字項目的中英混排文字（以計數 `LoadedDictionaryRules.apply` 呼叫作為前提斷言）：`unicode` 模式下字典、`Bopomofo2Braille.csv` 與 `BopomofoChar2Braille.csv` 各恰好開啟一次，`Braille2Ascii.csv` 從未開啟；`ascii` 模式下 `Braille2Ascii.csv` 開啟一次。舊程式碼對前兩者是每個項目開一次（測試文字為 12 次），因此此測試在步驟 4 之前為紅燈。
  - 每次轉換 `LoadedDictionaryRules.from_paths` 呼叫一次、`_build_trie` 呼叫三次（注音、raw、replacement），與項目數無關。
  - 純數學輸入既不開字典也不開 `Bopomofo2Braille.csv`。
  - 直接呼叫 `translate_with_language(...)` 時，每個字典檔各開一次。
  - 連續兩次轉換呼叫 `from_paths` 兩次（沒有跨轉換快取）。
  - 單獨呼叫 `translate_plain_text_segment`（未傳 loader）時，不論產生多少項目，每次呼叫每個字典檔各開一次。
  - 傳給 `translate_plain_text_segment` 的 loader 優先於路徑參數：路徑不存在時仍套用 loader 的字典，且兩次呼叫共只開檔一次。
  - 純數學的測試在舊程式碼上已是綠燈；它固定既有行為，若改成預先載入就會失敗。紅燈執行透過模組存取新名稱（`dictionary_rules.DictionaryRulesLoader`），因此顯示真實的逐項讀取，而不是 import 錯誤。
- `DictionarySnapshotTest`（`tests/test_conversion_service.py`）：假的文字翻譯器在第一次被呼叫後改寫字典檔；同一次轉換中之後的所有項目仍使用第一個版本，下一次轉換則使用新版本。此測試記錄刻意的快照行為改變，在舊程式碼上為紅燈。

### E. 不變的測試

13 個 pipeline 測試、字元對照測試、`test_conversion_service`、`test_conversion_language_explicit`、`test_removed_dead_code` 與黃金測試在每個步驟都不需修改即通過（A1 改寫的模組除外）。

## 遷移步驟（每步一個綠燈提交；細節見計畫）

1. `test: characterize dictionary rule loading`（A 部分；同時改寫 pytest 模組）。特性化測試無法先紅；計畫會加入一次性的突變檢查（例如讓字典讀取略過第一列，或讓 `apply_dictionary` 不檢查檔案是否存在），證明新測試能抓到。
2. `refactor: split dictionary trie build and scan`（B 部分）。
3. `refactor: add LoadedDictionaryRules`（`from_paths`、`apply`、`apply_dictionary` 改為包裝；C 部分，因類別尚不存在而先紅）。
4. `refactor: load dictionary rules once per conversion`（`DictionaryRulesLoader`、`dictionary_rules_loader`、pipeline 關鍵字參數、service 接線；D 部分，讀取次數與快照測試先紅）。

本任務中黃金測試資料一律不重新產生。

## 驗收條件

1. 路線圖驗證在 Linux 上通過：`cd client && python -m unittest tests.test_conversion_text_dictionary_rules tests.test_conversion_text_char_maps tests.test_conversion_text_pipeline tests.test_conversion_service -v`，只剩已知的 P2-5 失敗。`tests.test_conversion_text_dictionary_rules` 會回報測試數，而不是 `NO TESTS RAN`。
2. 以下也全綠：`tests.test_translation_golden tests.test_conversion_language_explicit tests.test_removed_dead_code tests.test_conversion_jobs tests.test_conversion_presenter tests.test_main_demo`。
3. `git diff main -- client/tests/fixtures/translation_golden.json` 為空，sha256 仍為 `e67d95a1ae001d928b657f16468494d0e98beeea5a6425283090b34030211ccd`；`tests.test_translation_golden` 在本任務每個提交都通過。
4. 完整測試（字母順序）：783 + 35 個新測試 = 818（步驟 1 有 17 個，含改寫的 7 個；步驟 2 有 0 個；步驟 3 有 6 個；步驟 4 有 12 個），`failures=1`（僅 P2-5），`errors=0`，`skipped=9`。模組順序打亂的測試工具（seed 0-19）每個 seed 都只有同一個失敗。
5. 讀取次數防護（D 部分）通過：每次轉換中字典、`Bopomofo2Braille.csv`、`BopomofoChar2Braille.csv` 與（ASCII 模式）`Braille2Ascii.csv` 各最多開啟一次。
6. `grep -rn "apply_dictionary(" client/conversion` 只顯示其定義（對目錄執行 `grep -n` 什麼都不印，等於沒有檢查）；`grep -n "\.open(" client/conversion/text/dictionary_rules.py` 只顯示 `from_paths` 內的讀取。
7. 實測（回報，非測試）：以 2,000 列字典轉換 `long_document`，比變更前至少快 10 倍，且顯示文字長度相同（計畫中的暫存腳本印出前後數據；本機上變更前 2.24 秒、變更後約 0.07 秒）。
8. `git diff main --stat -- client/locales scripts client/braille client/gui.py client/dictionaries client/conversion/output.py client/conversion/text/char_maps.py` 為空。

## 風險

- **錯誤時機漂移**（影響中、可能性低）。立即載入會讓字典損壞時的純數學轉換失敗。緩解：延遲載入器與 A4 測試。
- **解析漂移**（影響高、可能性低）。`from_paths` 必須保留讀取順序、略過規則、`processing` 後備行為與訊息。緩解：程式碼是搬移而非重寫；A2/A3 表格對兩個 API 都執行；黃金測試資料涵蓋整條 pipeline。
- **項目之間共用 trie**（低）。同一個 trie 物件現在服務一次轉換的所有項目；掃描只讀取它。`_scan_trie` 不得修改節點（目前也沒有），注音 trie 只在 `from_paths` 內使用。
- **快照語意**（低）。外部修改的檔案改為每次轉換讀一次而非每個項目讀一次。已記錄；下一次轉換會讀到修改；本程式在轉換期間無法編輯。
- **同時進行的轉換**（低）。被取代的匯出工作與新工作各有自己的 loader；沒有可競爭的模組層級快取。
- **讀取次數防護的脆弱性**（低）。它計數 `Path.open`；防護會斷言至少看到字典一次，因此換開檔函式會明確失敗，而不是空洞通過。
- **僅 Windows 的路徑**（低，此處無法驗證）。讀檔是純 Python，但仍應以打包版本搭配真實 liblouis 與真實使用者字典檢查；見驗證債。

## 調查中發現的已知缺陷（本任務不修）

1. 以 UTF-8 BOM 存檔的字典（部分 Windows 編輯器會這樣做）會出現 "CSV must contain columns: text, braille, type" 錯誤，資料檔亦然。`dictionaries.manager.validate_dictionary_csv`（匯入）行為相同。改為接受 `utf-8-sig` 屬於行為變更；應由另一個任務連同匯入驗證一起決定。
2. 損壞的 `Bopomofo2Braille.csv` 只有在字典檔存在且輸入含純文字時才會回報，且 `apply_dictionary` 會默默忽略 `processing` 失敗（整個注音目標變成一個部分）。兩者皆保留。
3. `LanguageDetector` 仍是每個文字片段建立一次（5.6 節第三點），前處理腳本仍是每次轉換編譯一次；兩者都不在 P1-6 範圍內。

## Windows 驗證債

- 在打包版本上，變更前後各做一次：使用含 `Braille`、`Braille/Unicode`（`@` 切分）與 `Bopomofo` 列的大型使用者字典，以 Unicode 與 ASCII 輸出模式轉換一份含行內數學的長篇中英混排文件；點字結果文字與匯出的 BRL 必須逐位元組相同，且轉換應明顯變快。
- 在兩次轉換之間於字典管理中編輯字典，確認第二次轉換使用了修改。
- 執行僅 Windows 的模組（`tests.test_liblouis_runtime`、`tests.test_translation_language_result`、`tests.test_language_detection_translation`）並與基線比較（後兩者已因 P1-1 與 P1-5 記錄的原因失敗）。
- 沒有選單、對話框或字串變更，因此不需要截圖，也不需執行 `generate_pot.bat`。

## 範圍外

- 跨轉換快取解析後的規則（需要在編輯、改名、刪除與切換選擇時做到滴水不漏的失效處理；一旦不再是每個項目讀一次，每次轉換讀一次的成本很低）。
- 將字元對照表改由 loader 載入，或修改 `map_char`、`ConversionRequest`、`TranslateSegments`。
- 重用 `LanguageDetector`、前處理腳本、`_translate_plain_text_segment` 別名與 `service.py` 中其他模組別名（5.5 節），以及把 pipeline 的 import 移到模組層級。
- BOM 處理與其他任何 CSV 驗證變更（已知缺陷 1）。
- `ApplicationPaths`（P2-6）、P2-5 的 tokenizer 工作及其失敗測試，以及縮排（P2-8）。
