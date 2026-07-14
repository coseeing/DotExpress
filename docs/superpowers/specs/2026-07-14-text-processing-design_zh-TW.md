# 文字處理自訂 Python 前處理設計

## 目標

在「轉譯」選單提供全域的「文字處理」設定。使用者可撰寫不受限制的 Python 程式，定義 `main` 函式，在任何文字轉譯開始前改寫來源文字。

這項功能取代目前屬於非標準規則的 `conversion/preprocessing/punctuation.py` 標點處理。轉譯與 dual view 一律以使用者 `main()` 回傳的處理後文字為來源。

## 範圍

包含：

- 新增「轉譯」選單的「文字處理」項目與獨立 dialog。
- 保存單一全域 Python script。
- 在所有實際轉譯入口的既有背景 conversion worker 中執行 script。
- 將 script 輸出串入共用 source preprocessing pipeline。
- 移除 punctuation token 化與其標點規則。
- 移除未使用的 `convert_text_for_output()` API，以及只剩 demo／舊測試使用的 `translate_and_wrap_both()` 輸出路徑，讓 `convert_text_with_alignment()` 成為唯一轉譯輸出流程。
- 保留字典 replacement 直接輸出 Unicode 點字的能力。

不包含：

- Python sandbox、能力限制、網路／檔案限制或 timeout。
- 多份 script、每文件 script、script profile 管理或 script 測試按鈕。
- 將原始輸入文字與任意處理後文字做字元級 dual-view 對齊。

## 使用者介面與持久化

「轉譯」選單在「Dual View」之後、「Dictionary Management...」之前新增直接項目「文字處理」。點選後開啟獨立、可調整大小的 modeless singleton dialog；重複點選時帶回既有 dialog，而不建立第二個 instance：

- title 固定為「文字處理」。
- 初始大小為 `720 × 440`，與既有設定 dialog 相同。
- 主要控制項為多行、等寬字型的 Python 程式編輯區，具備清楚的無障礙名稱。
- 沿用 `OK`、`Cancel`、`Apply`：`Apply` 與 `OK` 儲存，`Cancel` 放棄目前未保存編輯。

首次使用的預設內容為：

```python
def main(input: str) -> str:
    return input
```

script 儲存在既有字典目錄（`get_dictionary_directory()`）的 `preprocessing.py`，與 `default.csv` 等字典檔位於相同資料夾。檔案不存在時，dialog 顯示預設 identity script；首次 `Apply` 或 `OK` 才以 UTF-8 建立檔案。保存採同目錄暫存檔加 `os.replace()` 的原子替換，避免中斷寫入留下半份 script。它是唯一的全域 script，套用至所有文件、主畫面轉換，以及單筆／批次匯出因缺少點字快取而觸發的轉換；匯出既有點字快取時維持目前不重新轉譯的行為。

## Script 契約與驗證

使用者可在 script 中定義任意 helper function、常數及 import。唯一的入口契約是頂層 `main`：

- 必須恰好定義一個頂層、同步的 `def main(...)`；巢狀函式與 `async def main(...)` 不符合契約。
- 必須定義恰好一個位置參數，且不得有額外的位置、keyword-only、`*args` 或 `**kwargs` 參數；該唯一參數名稱不限制。
- 型別標註 `str -> str` 是預設模板與文件契約，不強制使用相同標註文字。
- 實際呼叫的回傳值必須是 `str`。

保存時只解析與編譯程式碼，並以 AST 驗證恰好一個符合此精確參數形狀的頂層 `def main(...)`。保存流程不執行 `exec()`，因此不會意外執行 module-level 程式碼。原本有效的已儲存 script 在新 script 驗證失敗時保持不變。

實際轉換時，conversion worker 在執行前才讀取 `preprocessing.py`，因此外部檔案修改會套用至下一次轉換，且讀檔與執行都不會阻塞 wxPython UI thread。每次建立含 `__name__` 與 `__file__` 的新 namespace，執行 script，取得 `main` 後呼叫 `main(raw_text)`；不保留前一次轉換的全域變數狀態。Python 能力不受限制，程式碼以目前使用者權限執行；沒有 timeout，無限迴圈會使該 conversion worker 持續執行，但不阻塞 wxPython 前景 UI。

## 轉譯與 dual view 資料流

```text
原始來源文字
  -> main(raw_text)
  -> 處理後文字
  -> Bopomofo 字元映射
  -> 語言偵測、字典規則與一般點字轉譯
  -> 點字輸出與 dual view
```

空白來源文字維持既有行為：直接產生空白輸出，不執行 `main()`。

處理後文字是實際送進轉譯器的文字，因此 dual view 以它作為唯一可精準對齊的來源。任意 Python 可用正規表示式、刪除、插入、重排或產生外部內容，僅靠 `main(input) -> str` 無法可靠建立原始文字的逐字對應；本設計不做不可靠的 diff 推測。

目前主畫面轉換，以及缺少點字快取時的單筆／批次匯出，都經由 `ConversionJobRunner` 使用 `convert_text_with_alignment()`。`convert_text_for_output()` 及其客製 `wrap_both` 分支沒有正式呼叫端，僅為舊 API／測試注入點；將其移除。`translate_and_wrap_both()` 仍被 `client/main.py` demo 與舊測試直接呼叫，形成第二條輸出路徑；一併移除此 wrapper 與底層專用 helper，並將 demo 改用 `ConversionRequest` 和 `convert_text_with_alignment()`。需要最終文字的未來呼叫端應取用 `.display_text`，不得建立第二條轉譯流程。

## 移除舊標點規則與保留字典點字 replacement

移除 `conversion/preprocessing/punctuation.py`、`preprocess_punctuation()` 及 service 中依標點 token 分流的邏輯。一般文字片段直接進入既有語言感知轉譯。

`literal_braille.py` 現在還提供兩項與標點無關的能力：`is_unicode_braille()` 和 `build_literal_translation_result()`。字典 replacement 若本身為 Unicode 點字，仍需透過這些能力直通為點字結果並維持 dual-view 對應。因此應保留它們，必要時搬至更貼近文字轉譯的模組；不得因刪除 punctuation 一併移除這項字典能力。

## 錯誤處理

設定期若 syntax error、`main` 數量不是一個，或 `main` 定義不符合單一位置輸入契約，dialog 保持開啟、顯示錯誤並且不保存。讀取既有檔案或原子保存發生 I/O error 時也顯示錯誤，不以預設內容靜默覆蓋既有檔案。

轉換期的讀檔、編譯、script 執行失敗，`main` 在 runtime 不可呼叫，或回傳非字串時，均產生 `ConversionStageError("text_processing", error)`，並以「文字處理失敗：{error}」回報。Python-level `SystemExit` 與 `KeyboardInterrupt` 也需轉為一般 runtime error，確保 worker 一定送回完成 callback；不限制 Python 意味著 `os._exit()` 這類直接終止程序的能力仍無法攔截。不要顯示完整 traceback。失敗不覆寫既有點字輸出。既有的轉譯失敗與 ASCII 轉換失敗仍為獨立錯誤類型。

## 測試

- `preprocessing.py` 不存在時的預設內容、讀取、UTF-8 保存與原子替換。
- dialog 的 title、初始大小、無障礙名稱及 `OK`／`Cancel`／`Apply` 行為。
- 保存期拒絕 syntax error、缺少 `main` 與不符合單一位置輸入的定義，且不覆寫先前設定。
- 轉換期驗證正常文字改寫、helper function 與 import 的使用。
- 驗證 runtime 例外、runtime `main` 不可呼叫及非字串回傳會產生文字處理錯誤。
- 驗證主畫面轉換，以及單筆／批次匯出需要轉譯時，都透過唯一的 `convert_text_with_alignment()` pipeline 套用 script；已有點字快取的匯出不重新轉譯。
- 驗證 dual view 採用處理後文字。
- 驗證移除 punctuation 路徑後，Unicode 點字字典 replacement 仍正常。
- 驗證 `convert_text_for_output()`、`translate_and_wrap_both()`、相關 wrapper／helper 與只針對它們的舊測試均被移除，`client/main.py` demo 改用唯一 pipeline。

## 成功標準

1. 使用者可在「文字處理」dialog 保存單一全域 `main` script。
2. 所有正式轉譯，以及匯出需要轉譯時，都先經 `main()` 處理，且不阻塞前景 UI；已有點字快取的匯出不重跑轉譯。
3. dual view 一致顯示處理後文字。
4. 非標準 punctuation 規則不再影響轉譯。
5. Unicode 點字字典 replacement 行為維持。
6. codebase 不再存在 `convert_text_for_output()` 或 `translate_and_wrap_both()` 第二轉譯入口。
