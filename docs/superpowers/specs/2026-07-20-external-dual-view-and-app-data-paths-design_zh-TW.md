# 外部雙視檢視與應用程式資料路徑統一設計

## 目標

將「轉譯」選單的「雙視檢視」從內嵌 `wx.html2.WebView` 改為在系統上可用的瀏覽器開啟，同時讓新視窗的目標尺寸等同 DotExpress 主視窗。雙視 HTML 會寫入 DotExpress 應用程式目錄下的 `dual_view/`，而不是系統暫存目錄。

同一項變更會統一 DotExpress 所管理檔案的根目錄策略，讓設定、字典、文件 workspace、日誌與雙視 HTML 都位於應用程式根目錄。

## 範圍

### 包含

- 由「轉譯」選單的「雙視檢視」產生 HTML 檔並開啟外部瀏覽器。
- 依序嘗試 Chrome、Microsoft Edge、Firefox；都無法啟動時才以 `os.startfile()` 開啟 HTML 檔。
- 對已知瀏覽器傳入獨立視窗與主視窗寬高的啟動參數。
- 保留既有 `DualViewFrame`、`wx.html2.WebView`、`_show_dual_view()` 與相關刷新程式碼，不由此選單事件呼叫。
- 建立單一 application-root 路徑來源，並統一設定、字典、workspace、日誌與雙視 HTML 的位置。
- 啟動時明確驗證所有應用程式管理目錄的可寫性；不可寫時顯示錯誤並停止啟動。
- 將啟動與雙視檢視的使用者可見錯誤同步至 gettext catalog 與編譯後的繁體中文 catalog。

### 不包含

- 控制系統預設瀏覽器或以 Windows API 強制調整外部瀏覽器視窗。
- 將使用者透過匯出對話框選擇的輸出檔案搬到應用程式目錄。
- 保留、讀取或遷移舊的 `~/.DotExpress/config.json`。
- 刪除或重構既有 wx.html 雙視檢視功能。

## 應用程式資料位置

application root 的解析規則：

- 打包版：`Path(sys.executable).resolve().parent`，即 `DotExpress.exe` 所在目錄。
- 開發版：`client/` 目錄。

所有由 DotExpress 管理的可寫入資料使用下列結構：

```text
<application-root>/
  config.json
  dictionary/
  workspace/
  log/
  dual_view/
```

`dictionary/` 中的字典與預處理腳本、`workspace/` 中的 DEP 文件、`log/` 中的日誌，以及 `dual_view/` 中的暫時 HTML 都依此根目錄解析。原本相對於目前工作目錄的日誌位置不再使用；開發模式中原先落在 `client/documents/workspace/` 的 workspace 也改為 `client/workspace/`。

設定檔固定為 `<application-root>/config.json`。程式不再讀取或遷移 `~/.DotExpress/config.json`。

程式啟動時先建立必要目錄，並在 application root 與每個受管理子目錄中建立及移除探測檔，以驗證可寫性，再初始化會產生檔案的服務。若 `config.json` 已存在，也要以不變更內容的附加模式開啟該檔，偵測檔案本身的唯讀權限。File logger 必須延後至驗證完成後才開啟檔案；單純匯入模組不得建立 `log/` 或日誌檔。若根目錄、既有設定檔或任何必要目錄不可寫，顯示包含失敗路徑的本地化錯誤，在建立轉譯 runtime 或主視窗之前停止啟動，且不退回使用者家目錄或其他隱藏位置。

## 外部雙視檢視流程

當使用者啟動「雙視檢視」時：

1. 沿用既有 `build_dual_view_model()` 與 `render_dual_view_html()` 產生 HTML 字串，包括既有的空資料訊息。
2. 在 `dual_view/` 建立本次執行專用的內容，並將每次開啟寫成唯一、UTF-8 編碼的 `.html` 檔，避免既有分頁讀取到舊內容或快取。
3. 讀取主 wx 視窗目前的像素寬高。
4. 依序尋找並嘗試啟動 Chrome、Microsoft Edge、Firefox。搜尋範圍包含 `PATH`，以及各瀏覽器在 Windows 的標準使用者與 `Program Files` 安裝位置。每一個瀏覽器僅在找不到可執行檔或建立處理程序時引發 `OSError` 才嘗試下一個；瀏覽器處理程序隨即結束不在 launcher 可觀察的成功條件內。
5. Chrome 與 Edge 使用 `--new-window` 與 `--window-size=<width>,<height>`；Firefox 使用 `-new-window`、`-width <width>` 與 `-height <height>`。要求的寬高等於 wx 主視窗目前 `GetSize()` 的結果。瀏覽器可能重用既有處理程序，或因瀏覽器政策、視窗框線與 Windows DPI 縮放調整最終尺寸，因此精確的外部視窗幾何是目標而非保證。
6. 三個指定瀏覽器都不可用或無法啟動時，呼叫 Windows 的 `os.startfile()` 作為最後 fallback。此路徑遵循 Windows 的 HTML 關聯，可能不是瀏覽器，亦無法控制視窗尺寸。非 Windows 系統上的測試會注入 fallback callable，不要求 `os.startfile` 存在。

瀏覽器尋找、命令列建立與 fallback 順序實作為不依賴 wx 的 helper，以利單元測試；GUI 只負責取得 HTML 和主視窗尺寸、呼叫 helper，並以既有風格向使用者回報寫檔或開啟失敗。

## 雙視 HTML 清理

- 啟動路徑驗證完成後，清除 `dual_view/` 內上一次執行遺留、符合 DotExpress 自有 `dual-view-*.html` 命名模式的檔案。
- DotExpress 正常結束時，清除符合相同自有命名模式的檔案。
- 異常結束所留下的檔案，於下一次啟動清除。
- 清理範圍嚴格限定在 application root 下 `dual_view/` 中的自有 HTML 檔，不刪除無關檔案，也不影響 workspace、dictionary、log 或使用者選擇的匯出位置。

## 保留的內嵌 viewer

`DualViewFrame` 及其 `wx.html2.WebView` 的建立、HTML refresh、關閉與焦點處理程式碼保持不變。`_show_dual_view()` 也保留為可用入口；僅「轉譯」選單的事件處理改呼叫外部瀏覽器流程。既有 viewer 測試繼續存在。

## 錯誤處理

- 根目錄不可寫：在 GUI 啟動初期顯示錯誤，停止程式，不使用替代位置。
- 啟動時無法清除前次雙視檢視檔案：以相同的啟動錯誤回報失敗的 `dual_view/` 路徑，並在建立 runtime 或主視窗之前停止。
- 正常結束時無法清除本次雙視檢視檔案：記錄失敗，但繼續關閉轉譯 runtime 與應用程式。
- 產生或寫入雙視 HTML 失敗：記錄詳細錯誤，向使用者顯示既有風格的錯誤訊息，且不改變文件或轉譯資料。
- 指定瀏覽器不可用：依 Chrome、Edge、Firefox 的固定順序繼續嘗試。
- `os.startfile()` 亦失敗：記錄詳細錯誤並顯示開啟失敗訊息。

## 驗證

- application-root 在 frozen 與開發模式的解析測試。
- 設定、dictionary、workspace、log、dual_view 都解析至共同 application root 的測試。
- 必要資料目錄建立，以及目錄或既有唯讀設定檔無法寫入時的初始化錯誤測試。
- Logger 建立時不會在啟動驗證前建立目錄或開啟檔案，且延遲開啟的 file handler 會解析至 `log/` 的測試。
- 雙視 HTML 以 UTF-8、唯一檔名寫入 `dual_view/` 的測試。
- Chrome → Edge → Firefox → `os.startfile()` 的搜尋、啟動與 fallback 順序測試。
- 各瀏覽器命令列包含檔案 URI、新視窗參數與主程式寬高的測試。
- `dual_view/` 僅在啟動／正常結束時清理其自身檔案的測試。
- GUI 選單事件改走外部瀏覽器流程的測試，以及既有 `DualViewFrame` 測試的保留。
- 驗證新增使用者可見錯誤的 gettext template、繁體中文 PO 與重新編譯的 MO 檔。
