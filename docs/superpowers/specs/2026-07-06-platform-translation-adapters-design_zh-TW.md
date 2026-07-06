# DotExpress 平台翻譯適配器設計

## 摘要

DotExpress 目前在匯入 `braille.louis_helper` 時就會載入內建的 Windows liblouis 執行環境，並且由 `gui.py` 直接初始化它。數學翻譯則會依需要載入 Windows 版的 MathCAT `.pyd` 與其相依 DLL。這些原生相依性會讓完整的轉換流程無法在不支援的平台上可靠地匯入與測試。

這份設計將文字與數學翻譯隔離在小型適配器之後。Windows 仍然使用 liblouis 與 MathCAT。若任一能力不可用，則只有該能力會退回到可預測的字元層級翻譯：每個非空白、非換行的來源字元都會變成 `⣿`，每個來源空白會變成點字空白 `⠀`（`U+2800`），而換行則維持換行。

這項變更保留目前的轉換編排、換行包裝、語言偵測、字典處理與 Windows 原生輸出。它不會引入外掛探索、依賴注入框架，或新的原生後端。

## 目前問題

平台邊界分散在以下路徑：

- `client/braille/louis_helper.py` 在模組匯入時就會匯入並載入內建的 liblouis 執行環境。
- `client/translate.py` 在模組匯入時就會匯入 `braille.louis_helper`。
- `client/gui.py` 會匯入、初始化並終止 `braille.louis_helper`。
- `client/conversion/mathcat_adapter.py` 會載入 `libmathcat_py.pyd` 與相關 DLL。
- `client/conversion/service.py` 會呼叫具體的文字與數學翻譯函式。

這會造成四個具體問題：

1. 匯入原本與平台無關的轉換模組時，可能會載入 Windows 二進位檔。
2. 文字與數學無法在只有一個原生執行環境不可用時，分別降級。
3. 非 Windows 測試無法端到端驗證轉換、換行包裝與雙視檢視對齊。
4. 未來若要新增後端，服務層或 GUI 程式碼會需要更多平台判斷。

另外有兩個 Windows 專屬行為已經是獨立且可降級的：

- `client/ui/font_support.py` 會保護 `AddFontResourceExW`，在非 Windows 平台直接回傳 `False`。
- `client/ui/dual_view.py` 只在 Windows 上使用 `SetWindowPos(..., SWP_NOACTIVATE, ...)`，而在其他平台則在 `Raise()` 後還原焦點。

它們不屬於翻譯適配器的階層，這次變更不需要重構它們。

## 目標

- 將原生執行環境的匯入、載入、初始化與關閉都留在翻譯適配器內。
- 讓文字與數學能力可以獨立選擇。
- 讓轉換入口依賴 `TranslationRuntime`，而不是依賴 Windows 模組。
- 保留目前 Windows 原生翻譯與錯誤行為。
- 提供可預測的降級結果，且具備有效的 `TranslationResult` 對應。
- 在不支援的平台上仍能測試轉換、換行包裝與雙視檢視。
- 保留未來新增 Linux 或 macOS 適配器的明確擴充點。

## 非目標

- 實作真正的 Linux 或 macOS liblouis 或 MathCAT 後端。
- 新增後端探索、註冊表、使用者可選後端，或 DI 容器。
- 重寫 `TranslationResult`、語言偵測、字典處理、換行包裝，或雙視檢視。
- 在原生適配器已成功初始化後，若稍後翻譯失敗，改為靜默降級。
- 讓非 Windows 的焦點行為與 Windows 的 `SWP_NOACTIVATE` 行為完全一致。
- 重構不相關的 GUI、文件或設定程式碼。

## 評估過的方案

### A. 在既有函式中加上平台判斷

在 `translate.py`、`math_service.py` 與轉換函式中加入 `sys.platform` 分支。

這樣初期改動較少，但會把平台與降級策略散落到整個應用程式。它也會讓模組匯入持續綁定原生實作。

### B. 新增翻譯適配器與小型執行環境提供器

定義獨立的文字與數學協定，實作原生與 fallback 策略，並在單一提供器中集中做能力選擇。

這樣可以建立可測試的邊界，同時保留目前的編排與結果模型。它只會增加兩個既有原生整合所需要的抽象層。

### C. 以外掛系統重建翻譯

更換結果模型與轉換流程，並加入後端探索與依賴注入。

這超出目前需求，且在還沒有多個實際後端之前，會增加回歸風險。

### 決策

採用方案 B。這是能移除平台中立模組中原生匯入、支援文字與數學各自降級，並且允許明確測試注入的最小設計。

## 設計原則

- Adapter 會包裝 liblouis 與 MathCAT 的呼叫慣例。
- Strategy 讓原生與 fallback 實作可互換。
- 小型提供器負責建立與選擇兩種策略。
- SRP 將原生載入、轉換編排與結果行為分離。
- OCP 讓未來後端可以不修改 `conversion/service.py`。
- LSP 要求每個實作都回傳有效的 `TranslationResult`。
- ISP 讓文字與數學契約分開。
- DIP 讓轉換依賴協定與執行環境組合。

## 必要檔案結構

```text
client/
├── adapters/
│   ├── __init__.py
│   └── translation/
│       ├── __init__.py
│       ├── contracts.py
│       ├── fallback.py
│       ├── liblouis.py
│       ├── mathcat.py
│       └── provider.py
├── conversion/
│   ├── math_service.py
│   └── service.py
├── gui.py
└── translate.py
```

職責如下：

- `contracts.py`：協定、`RuntimeUnavailableError` 與 `TranslationRuntime`。
- `fallback.py`：可預測的文字與數學 fallback 適配器。
- `liblouis.py`：延遲匯入、生命週期，以及對 `braille.louis_helper` 的呼叫。
- `mathcat.py`：MathCAT 能力初始化與數學結果建構。
- `provider.py`：獨立建構與 fallback 選擇。
- `conversion/service.py`：片段解析、字典／語言編排、結果組合與包裝。
- `translate.py`：只保留 `TranslationResult` 及其結果／映射操作。
- `gui.py`：應用程式組裝；取得、傳遞並關閉單一執行環境。

## 契約

### 文字翻譯

```python
class BrailleTextTranslator(Protocol):
    def translate(
        self,
        text: str,
        *,
        table: str,
        raw: str,
        single_token: bool = False,
    ) -> TranslationResult:
        ...
```

`text` 是套用字典後送給原生後端的輸入。`raw` 是在對齊輸出中代表來源的文字。`single_token=True` 會保留既有的原子字典行為。

原生適配器會重現目前的 `translate()` 與 `translate_as_single_token()` 行為。fallback 適配器則會根據 `raw` 產生輸出，而不是依據替換後的 `text`，因為字典替換可能會改變長度，而降級輸出必須維持每個來源字元對應一個點字格。

### 數學翻譯

```python
class MathSegmentTranslator(Protocol):
    def translate(
        self,
        source: str,
        *,
        braille_code: str,
    ) -> TranslationResult:
        ...
```

MathCAT 適配器保留目前行為：整段數學來源會被當作單一原始 token，而每個原生點字 cell 都會對應到該 token。fallback 數學適配器則會回傳每個來源字元一個原始 token，並提供一對一陣列，讓所有不支援的數學字元都能保持可對齊。

### 執行環境組合

```python
@dataclass
class TranslationRuntime:
    text_translator: BrailleTextTranslator
    math_translator: MathSegmentTranslator
    close_callbacks: tuple[Callable[[], None], ...] = ()

    def close(self) -> None:
        ...
```

`close()` 必須具備冪等性，且只會關閉已成功初始化的原生適配器。

## 執行環境選擇

文字與數學能力會分開選擇：

| 文字 | 數學 | 文字適配器 | 數學適配器 |
| --- | --- | --- | --- |
| 可用 | 可用 | liblouis | MathCAT |
| 可用 | 不可用 | liblouis | fallback |
| 不可用 | 可用 | fallback | MathCAT |
| 不可用 | 不可用 | fallback | fallback |

原生工廠會把已知的載入失敗統一轉成 `RuntimeUnavailableError`。不支援的平台、缺少二進位檔、缺少相依 DLL，以及由原生套件造成的匯入失敗，都屬於能力不可用的情況。

提供器只會捕捉 `RuntimeUnavailableError`。其他未預期的缺陷會直接冒出，不會被偽裝成不支援的能力。

能力探測會在應用程式組裝時主動進行：

- liblouis 適配器會在自己的 factory 內匯入 `braille.louis_helper` 並呼叫 `initialize()`。
- MathCAT 適配器會在自己的 factory 初始化過程中載入 `.pyd` 與相依 DLL。
- 匯入 `translate`、`conversion.service` 或 `gui` 時，都不會初始化任一原生執行環境。

## Fallback 契約

對於長度為 `n` 的來源字串 `source`：

- 除了空白與換行以外的每個字元，都會變成 `⣿`。
- 每個來源空白都會變成 `⠀`（`U+2800`）。
- 每個換行都會保留為 `\n`。
- `raw == list(source)`。
- `braille` 會包含與來源字元數量相同的輸出字元。
- `raw_to_braille_pos == list(range(n))`。
- `braille_to_raw_pos == list(range(n))`。
- 空輸入會回傳 `TranslationResult([], [], [], [])`。

範例：

| 輸入 | 輸出 |
| --- | --- |
| `我們這一家` | `⣿⣿⣿⣿⣿` |
| `我 們` | `⣿⠀⣿` |
| `1+2` | `⣿⣿⣿` |
| `a\nb` | `⣿\n⣿` |

fallback 是明確的降級模式。它的用途是維持應用程式流程與對齊，而不是宣稱產生語意正確的點字。

`single_token=True` 不會讓 fallback 映射折疊。字元層級的 fallback 對齊優先，因為它的目的就是支援不支援平台的測試。

## 資料流

```text
BrailleApp.OnInit
    |
    +--> build_translation_runtime()
             |
             +--> native text or fallback
             `--> native math or fallback
    |
    `--> BrailleFrame(runtime)
             |
             `--> convert_text_with_alignment(..., runtime=runtime)
                      |
                      +--> dictionary and language segmentation
                      +--> runtime.text_translator.translate(...)
                      +--> runtime.math_translator.translate(...)
                      `--> compose, wrap, dual-view results

BrailleApp.OnExit --> runtime.close()
```

測試會注入包含 fallback 或假物件適配器的 `TranslationRuntime`。它們不會透過修改全域 `sys.platform` 來控制服務行為。

## 錯誤處理

### 能力不可用

這只會在建立原生適配器時發生。原生 factory 會拋出 `RuntimeUnavailableError`，由提供器為該能力選擇 fallback。另一項能力會維持獨立。

### 翻譯失敗

原生適配器已成功初始化，但在某個輸入、表格、LaTeX 表達式或執行環境狀態下翻譯呼叫失敗。此錯誤會沿用現有的 `ConversionStageError("translation", error)` 路徑向上拋出，不會靜默切換到 fallback。

這個區分可以避免真實的 Windows 回歸被誤判成成功的降級輸出。

## UI 平台行為

### 字型註冊

維持 `register_private_font_for_windows()` 不變。它已經會跳過不支援的平台，而且不會阻擋翻譯初始化。

### 雙視檢視視窗

保留 Windows 的不搶焦點最佳化與目前跨平台的焦點還原。非 Windows 的驗收只要求雙視檢視能夠開啟、關閉並渲染 fallback 對齊結果；焦點語意不必與 Windows 完全一致。

## 測試策略

### 結果特性測試

- 將與 liblouis 無關的 `TranslationResult` 測試移出受執行環境保護的模組。
- 在適配器遷移前，先鎖定加法、空結果與字元層級對齊行為。

### Fallback 單元測試

- CJK、ASCII、數字與標點都會變成 `⣿`。
- 空白變成 `⠀`；換行維持 `\n`。
- 混合輸入與空輸入會產生精確陣列。
- 當字典替換長度不同時，文字 fallback 會使用 `raw`。
- 即使 `single_token=True`，文字 fallback 仍維持字元層級。
- 數學 fallback 也遵循相同的字元層級契約。

### 原生適配器測試

- liblouis 適配器會轉交表格、文字與模式，並重現一般與單一 token 的映射。
- liblouis 的初始化與關閉只會執行一次。
- MathCAT 適配器會傳遞選定的 braille code，並回傳目前的單一 token 映射。
- 已知的載入失敗會變成 `RuntimeUnavailableError`。
- 翻譯失敗仍然是翻譯錯誤。

### 提供器測試

- 以注入的 factory 覆蓋四種原生／fallback 組合。
- 驗證只有 `RuntimeUnavailableError` 會導致 fallback。
- 驗證執行環境關閉回呼只包含已初始化的原生適配器，而且具備冪等性。

### 轉換整合測試

- 純文字轉換會完整透過 fallback 完成。
- 含有數學的文字轉換會完整透過 fallback 完成。
- 可以混合原生／假文字與 fallback 數學。
- fallback 結果會正常通過換行包裝。
- `convert_text_with_alignment()` 會回傳可供雙視檢視使用的字元映射。
- 匯入 `translate`、`conversion.service` 與 `gui` 不會載入原生模組。

### 現有平台測試

- 保留 Windows 專屬的 liblouis 與 MathCAT 執行環境測試。
- 保留字型與雙視檢視的平台行為測試。
- 跨平台 fallback 測試絕不能因缺少 Windows 二進位檔而被跳過。

## 遷移順序

1. 先建立目前結果契約的特性測試。
2. 定義協定、執行環境組合與能力錯誤。
3. 實作 fallback 適配器。
4. 把 liblouis 呼叫從 `translate.py` 移出去。
5. 將 MathCAT 轉換包裝成會產生結果的適配器。
6. 加入獨立的提供器選擇與生命週期管理。
7. 透過轉換入口注入執行環境。
8. 在 `BrailleApp` 中組裝並關閉執行環境。
9. 補上跨平台轉換與雙視檢視覆蓋。
10. 執行聚焦的跨平台測試，並保留 Windows 環境下的回歸命令。

## 相容性

- Windows 預設會選擇 liblouis 與 MathCAT，並保留目前的原生輸出。
- 現有的轉換函式名稱會保留，但轉換入口會接收明確的 `runtime` 關鍵字參數。
- `TranslationResult` 的公開行為會保留。
- 語言偵測、字典替換、數學分隔符、邊界空白、換行包裝與 ASCII 輸出仍然屬於服務責任。
- 現有的 `font_support.py` 與 `dual_view.py` 平台保護會維持不變。

## 風險與緩解

### 原生載入仍在匯入時發生

如果只是移動類別，卻沒有移除頂層匯入，失敗狀況仍然會保留。

緩解方式：加入匯入隔離測試，並從 `translate.py` 與 `gui.py` 移除 `braille.louis_helper` 的匯入。

### 字典替換會破壞 fallback 對齊

字典處理後的文字長度可能和來源不同。

緩解方式：文字契約同時攜帶 `text` 與 `raw`；fallback 一律映射 `raw`。

### 數學映射與字元層級 fallback 衝突

目前 MathCAT 的輸出會把整個表達式當成單一 token。

緩解方式：保留原生行為，但明確要求 fallback 數學採用字元層級映射。

### 過度寬鬆的例外處理會掩蓋缺陷

如果把所有初始化例外都當成不可用，可能會掩蓋程式設計錯誤。

緩解方式：原生 factory 只會正規化已知的載入失敗，而提供器只會捕捉 `RuntimeUnavailableError`。

### 執行環境生命週期被重複處理

如果 `gui.py` 保留 `louis_helper.initialize()`，同時適配器也初始化它，就可能重複註冊回呼。

緩解方式：執行環境獨家負責生命週期；GUI 只呼叫 `runtime.close()`。

## 驗收條件

- `translate.py`、`conversion.service` 與 `gui.py` 在匯入時不會初始化 liblouis 或 MathCAT。
- 非 Windows 平台可以透過 fallback 適配器執行文字與數學轉換。
- 不支援的文字與數學能力會分別選擇。
- 每個不支援的非空白／非換行字元都會變成 `⣿`。
- 來源空白會變成 `⠀`，而換行會維持換行。
- fallback 的位置陣列會精確符合字元層級契約。
- 字典替換不能改變 fallback 結果長度或來源對齊。
- fallback 轉換會通過換行包裝與雙視檢視模型生成。
- `conversion/service.py` 不包含任何 OS 判斷或原生二進位載入。
- 原生翻譯失敗會被回報，而不是靜默降級。
- Windows 仍然沿用現有的 liblouis 與 MathCAT 行為。
- 字型註冊與不搶焦點視窗行為仍然是彼此獨立的可選 UI 增強。
- 不會引入外掛系統、DI 容器，或其他無關重構。
