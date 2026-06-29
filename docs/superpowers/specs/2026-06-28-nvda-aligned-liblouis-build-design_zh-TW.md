# DotExpress NVDA 對齊版 liblouis 建置設計

## 摘要

DotExpress 目前是透過上游 Windows `nmake` 流程加上倉庫本地調整來建置 `liblouis`。這條路徑已經和 NVDA 分岔，即使 DotExpress 已經重用 NVDA 衍生的 Python `liblouis` 整合程式碼也是一樣。結果是整合邊界變得脆弱：建置設定、相容性 shim、Python ctypes 綁定，以及執行期點譯表處理，已經不再由同一個單位管理。

這份設計要把 DotExpress 的 `liblouis` 整合調整成與 NVDA 對齊。建置入口會改成 SCons，對應 NVDA 的 `liblouis` 建置模式。NVDA 整合檔案與 Python 包裝檔案會從固定的 NVDA 原始碼 submodule（`include/nvda`）同步，然後凍結到 `vendor/nvda/liblouis/` 供產品使用。DotExpress 會保留 `include/liblouis/` 作為上游 `liblouis` 原始碼 submodule，並維持把執行期成品輸出到 `client/braille/`，而 Python glue 會從 vendor snapshot 重新產生，而不是手動編輯。

第一版刻意縮小範圍：只支援 Windows x64、不做簽章、不做多架構矩陣，也不處理 MathCAT。

## 目標

- 讓 DotExpress 的 `liblouis` 建置行為與 NVDA 的 `liblouis` 建置整合對齊。
- 把建置整合層與 Python 包裝層當成同一個同步單位來管理。
- 以最小化的 DotExpress SCons 入口取代目前的 `nmake` 建置流程，並呼叫與 NVDA 對齊的 `liblouis` 建置邏輯。
- 將用來同步的 NVDA 原始碼固定為 `include/nvda` 這個 Git submodule。
- 清楚區隔：
  - 上游 `liblouis` 原始碼，
  - NVDA 整合原始碼，
  - DotExpress 執行期輸出。
- 透過把同步後的 Python 包裝檔案複製到現有的 `client/braille/` 位置，維持 DotExpress 執行期的 import 路徑不變。
- 讓 `client/braille/louis_helper.py` 與 `client/braille/liblouis/__init__.py` 都由同步後的 vendor snapshot 重新產生。

## 非目標

- 不變更 MathCAT。
- 不嘗試把 NVDA 的完整建置系統整包搬過來重用。
- 第一版不支援 x86、arm64 或 arm64ec。
- 不處理簽章或封裝整合。
- 不從 `vendor/nvda/liblouis/` 直接做執行期 import。
- 不在同步或建置時從網路自動抓 NVDA。
- 不對 DotExpress 的 braille 行為做超出 `liblouis` 整合邊界的大規模重構。

## 動機

DotExpress 已經和 NVDA 的 `liblouis` Python 整合模式綁得很深。如果倉庫只同步 DLL 建置行為，卻讓 ctypes 包裝與 helper 程式碼留在舊 fork 上，當 `liblouis` 的 API 形狀、callback 預期、常數或載入行為改變時，專案仍然會壞掉。因此，正確的同步單位不只是原生建置腳本，而是：

- 原生建置整合，
- Python ctypes 包裝，
- 執行期複製 / 輸出契約。

這個單位應該一起做版本化與升級。

## 高階架構

新的架構分成三層：

1. 上游原始碼層
   - `include/liblouis/`
   - 追蹤上游 `liblouis` 原始碼的 Git submodule。
   - 這仍然是實際編譯時使用的 C 原始碼與點譯表原始碼。

2. NVDA 整合層
   - `include/nvda/`
   - 追蹤固定 NVDA commit 的 Git submodule。
   - 只作為同步來源，不會直接拿來當執行期或直接建置依賴。
   - `vendor/nvda/liblouis/`
   - 保存同步後、凍結起來的 NVDA 衍生整合檔案，供 DotExpress 使用。

3. DotExpress 執行期層
   - `client/braille/`
   - 接收產生出來的 DLL、點譯表，以及同步過來的 Python 包裝檔案。
   - 讓現有 DotExpress 其他部分看到的 runtime / import 結構保持穩定。

建置時會從 `include/liblouis/` 讀上游 `liblouis`，並從 `vendor/nvda/liblouis/` 讀 NVDA 衍生的建置整合。執行期程式碼則繼續從 `client/braille/` 載入。

## 目錄配置

### 上游原始碼

- `include/liblouis/`
  - 上游 `liblouis` Git submodule。

### NVDA 原始碼

- `include/nvda/`
  - 固定的 NVDA Git submodule。
  - 作為同步時的本地來源。

### 凍結後的 vendor 整合

- `vendor/nvda/liblouis/build/`
  - 從 `include/nvda/` 複製過來的 NVDA `liblouis` 建置整合檔案。

- `vendor/nvda/liblouis/python/`
  - 從 `include/nvda/` 複製過來的 NVDA `liblouis` Python 包裝 / helper 檔案。
  - `python/__init__.py.in` 是用來產生 `client/braille/liblouis/__init__.py` 的模板來源。

- `vendor/nvda/liblouis/runtime/`
  - 從 `include/nvda/` 複製過來的 NVDA `louisHelper.py`。
  - 這是用來產生 `client/braille/louis_helper.py` 的來源。

- `vendor/nvda/liblouis/SOURCE.json`
  - 記錄 NVDA 原始來源與同步檔案清單的中繼資料。

### DotExpress 執行期輸出

- `client/braille/liblouis.dll`
- `client/braille/liblouis/tables/`
- `client/braille/louis_helper.py`
- `client/braille/liblouis/__init__.py`

這些執行期檔案都應該視為同步 / 建置流程的輸出，而不是手動維護的邏輯。

## 同步契約

### 同步來源

同步會讀取 `include/nvda/`，而這個 submodule 的內容會由 Git 子模組狀態固定在某個 commit。

### 同步目標

同步只會把固定白名單內的檔案複製到 `vendor/nvda/liblouis/`。

### 白名單：原生建置整合

複製到 `vendor/nvda/liblouis/build/`：

- `nvdaHelper/liblouis/sconscript`
- `nvdaHelper/liblouis/config.h`
- `nvdaHelper/liblouis/strings.h`

這些檔案的重要性在於：

- `sconscript` 定義 NVDA 的建置行為與編譯器 / 工具預期。
- `config.h` 和 `strings.h` 提供 NVDA 用來成功編譯 `liblouis` 的 Windows 相容性 shim。

### 白名單：Python 包裝整合

複製到 `vendor/nvda/liblouis/python/`：

- NVDA 的 `louisHelper.py`
- NVDA 的 `liblouis` Python ctypes 綁定原始碼（也就是用來產生 DotExpress 的 `client/braille/liblouis/__init__.py` 的那份來源）

NVDA 實際檔案路徑可能會隨 revision 改變，但同步單位必須永遠包含：

- ctypes 綁定層，
- 點譯表 resolver / helper 層。

這個要求是語意上的，不只是路徑上的：如果 NVDA 改名或重組這些檔案，sync script 仍然必須擷取對應的邏輯元件。

### 同步中繼資料

`vendor/nvda/liblouis/SOURCE.json` 會記錄：

- 原始碼倉庫，
- 原始碼 submodule 路徑，
- 實際 commit，
- 同步檔案清單。

範例如下：

```json
{
  "source_repo": "https://github.com/nvaccess/nvda.git",
  "source_path": "include/nvda",
  "source_commit": "b493fe7e1f361a8d549f17a3353d826f6fe32334",
  "files": [
    "build/config.h",
    "build/sconscript",
    "build/strings.h",
    "python/__init__.py.in",
    "python/louisHelper.py",
    "runtime/louis_helper.py"
  ]
}
```

## 建置系統設計

### 建置系統選擇

DotExpress 會改用 SCons 來做 `liblouis` 的建置協調。這不只是把 `.bat` 換成 SCons 呼叫而已，而是刻意對齊 NVDA 的建置契約。

### 為什麼用 SCons

NVDA 的 `liblouis` 整合預期會用到：

- `clang-cl`
- `m4`
- Windows / MSVC 的連結環境
- 特定的 CPP define
- 特定的 include shim
- 特定的點譯表處理方式

如果用另一條自訂的 `nmake` 流程重新實作這些行為，就會保留導致目前問題的同一種維護分岔。採用 SCons 可以讓 DotExpress 盡可能保留 NVDA 的建置邏輯。

### DotExpress 根層 SCons 環境

DotExpress 會新增一個倉庫根層的 `sconstruct`，只為 `liblouis` 建置提供最小環境。

第一版只會提供同步後的 NVDA `sconscript` 所需變數，包括：

- `TARGET_ARCH = x86_64`
- `sourceDir`
- `thirdPartyEnv`
- `certFile = ""`
- `apiSigningToken = ""`
- `signExec = no-op 或可省略的占位值`
- `nvdaHelperDebugFlags = []`

根層 `sconstruct` 刻意不會複製 NVDA 的完整根層建置腳本。它只存在於滿足同步後的 `liblouis` 整合層。

### 建置入口

DotExpress 會保留一個很薄的 `scripts/build-liblouis.bat` 入口，但它的角色會改變：

1. 透過 `vcvarsall.bat x64` 載入 Visual Studio 2022 的建置環境
2. 呼叫 `scons`

這個 batch script 只負責 Windows shell bootstrap，真正的建置定義則放在 SCons 裡。

### 編譯器與工具

對齊後的建置需要：

- Visual Studio 2022 C++ tools
- Clang tools for Windows
- Python
- SCons
- `m4.exe`

這些依賴的用途如下：

- Visual Studio 2022 C++ tools 提供：
  - Windows SDK headers，
  - linker，
  - runtime libraries，
  - `vcvarsall.bat`
- Clang tools for Windows 提供：
  - `clang-cl`
- SCons 提供：
  - NVDA 使用的協調模型
- `m4.exe` 提供：
  - `.in` 點譯表檔案的展開

若要採用這種與 NVDA 對齊的建置方式，Visual Studio 與 Clang 都是必要條件。

### `m4` 處理方式

第一版不應該把 NVDA 的整個 `miscDeps` 結構一起搬進來。相反地，DotExpress 應該透過下列其中一種方式提供 `m4.exe`：

- 倉庫本地的一個固定路徑，或
- 明確的環境變數，例如 `M4_EXE`

SCons 環境應該把這個工具映射到同步後的 NVDA `sconscript` 契約上，而不是把依賴面不必要地擴大。

## 執行期輸出契約

同步與建置完成後：

- 原生輸出會複製到：
  - `client/braille/liblouis.dll`
  - `client/braille/liblouis/tables/*`
- 同步過來的 Python 包裝輸出會複製到：
  - `client/braille/louis_helper.py`
  - `client/braille/liblouis/__init__.py`

這兩個 Python 檔案會從同步後的 vendor snapshot 重新產生：

- `client/braille/louis_helper.py` 來自 `vendor/nvda/liblouis/runtime/louis_helper.py`
- `client/braille/liblouis/__init__.py` 來自 `vendor/nvda/liblouis/python/__init__.py.in`，並在產生時替換 liblouis DLL 名稱

這樣可以保留現有 DotExpress 的執行期 import 位置，同時確保它們是從固定的 NVDA 原始碼更新而來。

這比直接從 `vendor/nvda/liblouis/` 做執行期 import 更好，因為：

- 產品程式碼與 vendor 目錄結構保持獨立，
- 執行期路徑保持穩定，
- vendor 內容與執行期輸出之間的邊界更清楚。

## 建置流程

第一版的建置流程如下：

1. 確認 submodule 已初始化：
   - `include/liblouis`
   - `include/nvda`

2. 將 NVDA 整合同步到 vendor：
   - 執行 `scripts/sync_nvda_liblouis.py`
   - 重新產生 tracked 的 runtime Python 檔案

3. 建置 `liblouis`：
   - 執行 `scripts/build-liblouis.bat`
   - 這個腳本會進入 Visual Studio x64 環境後呼叫 SCons

4. SCons 會從下列來源編譯：
   - `include/liblouis` 的上游原始碼
   - `vendor/nvda/liblouis/build` 的 NVDA 整合

5. 建置後步驟會把執行期輸出刷新到 `client/braille/`

## 手動升級流程

因為 NVDA 同步是刻意固定且手動進行的，升級流程會是：

1. 把 `include/nvda` submodule 更新到目標 commit。
2. 執行 `scripts/sync_nvda_liblouis.py`。
3. 重新產生並檢查 `client/braille/` 下的 tracked runtime Python 檔案。
4. 檢查 `vendor/nvda/liblouis/` 下的 diff。
5. 執行 `scripts/build-liblouis.bat`。
6. 執行驗證命令與手動檢查。
7. 提交 submodule pointer 更新、vendor 同步變更、runtime 檔案更新，以及相關的文件 / 測試更新。

這樣可以保有可追溯性，避免因為上游默默移動而讓產品行為突然改變。

## 驗證策略

驗證必須同時涵蓋建置正確性與執行期整合正確性。

### 建置驗證

- SCons 建置成功完成。
- `client/braille/liblouis.dll` 成功重新產生。
- `client/braille/liblouis/tables/` 已刷新。

### 同步驗證

- `scripts/tests/test_sync_nvda_liblouis.py` 會通過。
- `client/braille/louis_helper.py` 已從同步後的 NVDA wrapper 原始碼刷新。
- `client/braille/liblouis/__init__.py` 已從同步後的 NVDA ctypes 綁定原始碼刷新。
- `vendor/nvda/liblouis/SOURCE.json` 反映的是固定的 NVDA commit。
- `client/braille/louis_helper.py` 會和 `vendor/nvda/liblouis/runtime/louis_helper.py` 一致。
- `client/braille/liblouis/__init__.py` 會和 `vendor/nvda/liblouis/python/__init__.py.in` 產生出的結果一致。

### 功能驗證

至少要包含：

- 中文預設表轉譯可用。
- 英文 UEB grade 1 轉譯可用。
- 英文 UEB grade 2 轉譯可用。

### 自動化驗證

至少執行既有、與 braille / liblouis 相關的測試，再加上實作過程中新增的目標測試。確切命令會寫在實作計畫裡，但目標範圍至少應包含：

- 會受 braille runtime 選擇影響的設定測試，
- 直接的 `liblouis` helper 測試，
- 任何 table resolution 測試，
- 新建置 / 同步流程所需的回歸測試。

## 錯誤處理與失敗模式

預期中的硬性失敗應該要明確且儘早發生：

- `include/liblouis` submodule 缺失，
- `include/nvda` submodule 缺失，
- 同步白名單中的某個來源檔缺失，
- `clang-cl` 缺失，
- Visual Studio 建置環境缺失，
- `m4.exe` 缺失，
- SCons 建置失敗，
- 執行期成品複製失敗。

建置與同步腳本應該快速失敗，並顯示清楚、具體的診斷訊息，而不是只留下半成品。

## 限制與取捨

### 為什麼不直接從 `include/nvda` 建置

如果直接在產品建置時消費 `include/nvda`，會讓下列幾個邊界變得模糊：

- 固定的第三方參考來源，
- DotExpress 凍結後的整合來源，
- 產品執行期輸出。

保留 `vendor/nvda/liblouis/` 作為正式建置輸入，可以維持可審查、可控的交接點。

### 為什麼不繼續保留現在的 `nmake` 路徑

目前的路徑本身就已經是分岔點。繼續用另一條自訂 `nmake` 流程去間接重寫 NVDA 行為，只會保留同一種維護風險。這次變更的目的，就是要和 NVDA 選擇的 `liblouis` 整合機制對齊。

### 為什麼不只同步原生建置檔

如果只同步原生建置檔，會讓下列兩者之間產生高風險的 ABI / API 漂移：

- 編譯出來的 DLL 行為，
- Python 包裝行為，
- DotExpress 執行期實際使用方式。

原生建置整合與 Python 包裝整合必須一起移動。

## 實作邊界

實作範圍應該維持精簡：

- 只把 SCons 引入到 `liblouis` 建置對齊這件事上。
- 保持執行期 import 路徑不變。
- 不要做和整合邊界無關的大範圍整理。
- 只新增維持 NVDA 同步版 `liblouis` 建置邏輯所需的最小 DotExpress glue。

## 成功條件

當且僅當下列條件都成立時，這份設計才算成功：

- DotExpress 的 `liblouis` 建置改由 SCons 跑，而不是現在這條自訂 `nmake` 路徑。
- 同步後的 NVDA `liblouis` 建置整合檔存在於 `vendor/nvda/liblouis/`。
- `include/nvda` 是固定的本地同步來源 submodule。
- Python 包裝檔與原生建置檔一起同步。
- 執行期輸出仍然維持在 `client/braille/`。
- Windows x64 建置可在 Visual Studio 2022 C++ tools 加上 Clang tools for Windows 的環境下完成。
- 轉譯與 braille 相關的基本情境與測試在移轉後仍然通過。
