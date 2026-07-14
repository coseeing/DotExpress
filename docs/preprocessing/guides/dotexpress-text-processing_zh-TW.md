# DotExpress 文字處理腳本指南

「文字處理」會在轉譯前執行一段 Python。它適合做可預期的來源文字正規化，例如標點轉換、字元替換或以正規表示式清理文字。

## 必要契約

腳本必須在最上層定義**恰好一個**同步的 `main`，有且只有一個位置參數，並回傳 `str`：

```python
def main(text: str) -> str:
    return text
```

- 參數名稱與型別標註可自行調整；但不得再加入其他位置參數、keyword-only 參數、`*args` 或 `**kwargs`。
- 可以定義 helper、常數和 `import`；執行時會以新的 namespace 載入，勿依賴前一次轉譯留下的全域狀態。
- `main` 回傳非字串，或在執行時發生例外，該次轉譯會以「文字處理失敗」結束。

## 資料流與影響範圍

```text
來源文字 -> main(text) -> Bopomofo 字元映射 -> 語言偵測、字典、點字轉譯
```

因此 `main` 的輸出才是實際轉譯和 dual view 對齊所使用的文字。刪除、插入、重排文字都會改變顯示與對齊來源；請讓改寫規則保持小而可預測。

空白來源文字維持空白輸出，不會執行腳本。

## 換行與整段文字

`text` 是完整文件文字，不是逐行呼叫。若只是使用 `replace`、`re.sub` 或逐字加入輸出，`\n` 和 Windows 的 `\r\n` 都會原樣保留。

```python
def main(text: str) -> str:
    return text.replace("\u00a0", " ")
```

只有你呼叫 `splitlines()`、`split()`，或自行以 `"\n".join(...)` 重組內容時，才可能改變換行格式、移除尾端換行，或使標點判定不再跨行。

## 建議模式

### 單純取代

```python
def main(text: str) -> str:
    return text.replace("……", "…")
```

### 正規表示式正規化

```python
import re


def main(text: str) -> str:
    return re.sub(r"[ \t]+", " ", text)
```

不要使用 `r"\s+"` 取代成空白，除非你刻意要把換行也刪掉。

### 依相鄰文字轉換標點

掃描整段字串時，請明確決定換行是否可跨越。例如 `character.isspace()` 會把空白、定位字元和換行都視為空白；若略過它們，開關引號可由跨行的下一個或上一個文字決定語境。

## 點字、字典與語言

- 一般輸出仍會經過 Bopomofo 字元映射、語言偵測、字典規則與翻譯表；不要假設任意 Unicode 點字字元都會跳過後續處理。
- 字典 replacement 本身若是 Unicode 點字，DotExpress 有專用的直通處理；這和文字處理腳本回傳的內容是不同路徑。
- 若腳本需插入 Unicode 點字或語言切換記號，請以實際使用的翻譯表、字典與 dual view 測試輸出，而非只測試 Python 字串。

## 避免的做法

文字處理程式以目前使用者權限執行，並未 sandbox。技術上可以讀檔、寫檔、連網或啟動程序，但這些操作不適合放入轉譯前處理：

- 不要使用 wxPython、檔案選擇器或其他 GUI；腳本在 conversion worker 中執行。
- 不要修改來源檔、設定檔或字典檔；轉譯可能重複執行，副作用難以預期。
- 不要進行網路請求、長時間運算、無限迴圈或等待使用者輸入；它們會讓該 conversion worker 無法完成。
- 不要在 module top level 做有副作用的操作；每次轉譯載入腳本都會執行頂層程式碼。

## 貼入前檢查

1. `main` 是否為最上層同步函式，且只有一個位置參數？
2. 每條路徑是否都回傳 `str`？
3. 是否刻意保留或改變 `\n`／`\r\n`？
4. 是否避免 I/O、GUI、網路與不受控制的耗時操作？
5. 是否以實際文件測試中文、英文、標點、換行、字典 replacement 與 dual view？

可在 `client/` 以現行執行器先驗證一份腳本：

```bash
python3 - <<'PY'
from pathlib import Path
from conversion.preprocessing.user_script import execute_preprocessing_script

print(execute_preprocessing_script(Path("/path/to/preprocessing.py"), "測試 text\r\n第二行"))
PY
```

這會檢查腳本的 `main` 契約、載入方式與回傳型別；實際點字結果仍應在 DotExpress 中確認。
