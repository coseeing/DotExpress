# 共用 wx 測試 Stub（P0-4）設計

## 目標

把 `client/tests/` 中所有手寫的假 `wx` 移到同一個共用模組 `client/tests/wx_stub.py`，並讓每個 GUI 測試模組安裝 stub 的方式不會洩漏到其他測試模組。這是 roadmap 任務 P0-4（`storage/refactor.md` 第 6.1 節；問題記錄在第 5 節「wx stub 測試骨架」）。P0-5 與 P1 的 GUI 拆分都會以此為基礎。

這是只動測試的重構。不改任何正式程式檔、使用者可見字串、翻譯或建置輸入。每個模組與整個測試套件中既有測試的數量不變，每個既有測試的結果也不變，沒有任何斷言被放寬。唯一的數量變化是新增的 `client/tests/test_wx_stub.py`（16 個測試共用輔助工具的測試；見測試策略）。

## 方法與基準（2026-10-08 於 `refactor/p0-4-wx-test-stub`、HEAD `8404088` 驗證，P0-1/P0-2/P0-3 已合併）

1. 執行 `grep -lw wx client/tests/*.py` 並逐一閱讀結果。共有七個模組用到假 `wx`。正式程式中 import `wx` 的只有 `gui.py`、`dialog.py`、`settings/dialogs.py` 與 `ui/dual_view.py`（`ui/__init__.py` 是空檔）。其他測試模組都不 import 它們。
2. 先讓 64 個測試模組各自在獨立行程中單獨執行，再用 `discover` 跑完整套件，最後以打亂的模組順序執行。打亂順序時用了一個模擬 `discover -s tests` 的小工具：把 `client/` 與 `client/tests/` 放進 `sys.path`，依指定順序先用 `TestLoader.loadTestsFromName` import 所有模組（import 時拋出的 `SkipTest` 與 `discover` 一樣算成一個略過的測試），然後一次執行整個套件。這個工具是用完即丟的檔案，不屬於本次變更。
3. 依 `discover` 的順序 import 這些模組後，檢查 `sys.modules` 與各模組的全域變數。

基準（venv Python 3.14.4，在 `client/` 下執行）：

- `python -m unittest discover -s tests` 結果為 `Ran 450 tests`、`FAILED (failures=1, skipped=7)`。唯一的失敗是已知的 P2-5 案例 `test_conversion_service ... test_translate_with_language_does_not_duplicate_existing_spaces_around_math`。
- 每個模組單獨執行：除了同一個 P2-5 失敗外全部通過，各模組的測試數加總為 450。
- 七個 wx 模組單獨執行（`python -m unittest tests.<module>`），全部 `OK`：`test_dialog_display` 5、`test_dialog_validation` 8、`test_dictionary_management_dialog` 8、`test_dual_view_frame` 6、`test_gui_document_flows` 61、`test_settings_dialogs` 27、`test_speech_symbols_dialog` 21，合計 136。
- roadmap 的指令 `python -m unittest tests.test_gui_document_flows tests.test_settings_dialogs tests.test_speech_symbols_dialog tests.test_dictionary_management_dialog -v` 結果為 `Ran 117 tests`、`OK`。

## 現況

### 清單

| 模組（縮排） | Stub 行數 | 如何建立 `wx` | 何時、如何安裝 | 其他 stub | 執行期是否以名稱查找綁定 wx 的模組？ |
| --- | --- | --- | --- | --- | --- |
| `test_gui_document_flows`（4 空白） | 12-319 | `_install_stub_modules()`。若已有 `sys.modules.get("wx")` 就**沿用**並修改它。完整的 widget 組（見下）。 | import 時。安裝 `wx`、`wx.html2`、`wx.lib`、`wx.lib.scrolledpanel`，從不還原。接著 import `gui` 與 `settings.dialogs`。 | `dialog` stub 與 `braille.louis_helper` stub，**僅在不存在時**安裝 | 否。只用 `patch.object(gui, ...)` 與 `patch.object(gui.wx, ...)`。 |
| `test_settings_dialogs`（4 空白） | 10-291 | `_install_stub_modules()`。每次都建立**全新**模組。會記錄狀態的 widget 組（見下）。 | import 時。無條件取代 `wx`、`wx.lib`、`wx.lib.scrolledpanel`，從不還原。`test_layout_uses_headerless_list_ctrl_and_explicit_categories_name`（565）會再呼叫一次以取得全新的 `wx`，但只還原那 3 個 wx 名稱。 | `braille` 與 `braille.tables`，**無條件**取代（`braille` stub 不是套件，沒有 `__path__`） | 是：函式內的 `from settings.dialogs import ...` 共 15 處、`import settings.dialogs as dialogs_module`，以及 8 個 `patch("settings.dialogs. ...")` 字串目標。 |
| `test_dual_view_frame`（tab） | 7-53 | 沿用並修改 `sys.modules.get("wx")`。自帶最小的 `_Widget`（`__init__` 不做事）、會記錄 `init_args`/`init_kwargs` 的 `Frame`、`BoxSizer`，以及**沒有** `FindFocus` 的 `Window`。 | import 時。安裝 `wx`、`wx.html2`，從不還原。import `ui.dual_view`。 | 無 | 是：`patch("ui.dual_view. ...")`（3 處），以及對自己的 `wx` 做 `patch.object(wx.Window, "FindFocus", create=True)`。 |
| `test_dialog_validation`（4 空白） | 6-12 | 一般的 `ModuleType`，只有 `Dialog`、`ListCtrl`、`Window`、`CommandEvent`。不存在的屬性會引發 `AttributeError`。 | import 時，**僅在 `wx` 不存在時**安裝。接著 `from dialog import ...` 會把真正的 `dialog` 模組留在 `sys.modules`，從不還原。 | 無 | 否。 |
| `test_dialog_display`（tab） | 9-46 | `_AutoModule`：不存在的屬性會變成一個新類別並快取在模組上。常數 `NOT_FOUND`=-1、`ID_OK`/`ID_CANCEL`/`ID_APPLY`/`ID_CLOSE` = 1/2/3/4、`OK`/`CANCEL`/`APPLY`/`CLOSE` = 4/8/16/32。 | 有範圍：先快照整個 `sys.modules`，以 `_dialog_display_test` 的名稱載入 `dialog.py`，再移除**所有**新模組並還原快照。本來就已隔離。 | 無 | 否。 |
| `test_speech_symbols_dialog`（4 空白） | 13-121 | 另一種 `_AutoModule`：不存在的屬性會變成一個**子模組**並註冊為 `sys.modules["wx.<name>"]`，`__or__`/`__ror__` 回傳自身。常數 `NOT_FOUND`=-1、`OK`=1、`ICON_ERROR`=2，`MessageBox` 不做事，類別有 `Dialog`、`ListCtrl`、`Window`、`CommandEvent`、`ListEvent`。 | 有範圍：以 `_speech_symbols_dialog_under_test` 的名稱載入 `dialog.py`，移除 `_SCOPED_RESTORE_ROOTS`（`wx`、`dialog`、`dictionaries`、`documents`、`braille`、`translation`、`Bopomofo` 與各文件格式函式庫）底下的新模組，其餘還原。`DialogModuleIsolationTest` 會測試這個載入器。 | 無 | 否。 |
| `test_dictionary_management_dialog`（tab） | 無 | 從 `tests.test_speech_symbols_dialog` import `dialog`。 | 在 `discover` 下，這會以 `tests.test_speech_symbols_dialog` 的名稱再執行一次 `test_speech_symbols_dialog.py`。 | 無 | 否。 |

### widget stub 的逐欄差異

`test_gui_document_flows`（G）、`test_settings_dialogs`（S）與 `test_dual_view_frame`（D）的 widget 基底類別都有一個 `__getattr__`，會回傳一個回傳 `None` 的空函式。P0-2 與 P0-3 已經踩過它的後果：`hasattr(widget, 任何名稱)` 永遠為真，讀取不存在的屬性會拿到函式而不是 `AttributeError`，呼叫不存在的方法會靜默回傳 `None`。連 `title` 的預設值都是那個函式，因為 `__init__` 在 `title` 存在之前就執行 `kwargs.get("title", getattr(self, "title", ""))`。許多 G 的測試依賴這個遮蔽行為（例如 `_make_frame` 不設定 frame 的方法）。除此之外，各 stub 的差異如下：

- **基底欄位與方法。** G：`parent`、`label`、`title`、`name`、`size`、`min_size`、`sizer`；`SetLabel`、`SetName`、`GetName`、`SetSize`、`SetMinSize`、`SetSizer`；`Bind` 忽略參數。S 有上述全部，另加 `bound_events`、`focused`、`visible`；它的 `Bind` 會記錄 `bound_events[event] = handler`，並新增 `Show`/`Hide`（設定 `visible`）、`SetFocus`（設定 `focused`）與 `HasFocus`（回傳 `focused`）。在 G 中，這四個方法會落到 `__getattr__`（`HasFocus()` 回傳 `None` 而不是布林值）。D 的基底只有 `__getattr__`，以及一個忽略參數的 `__init__`。
- **類別。** 只有 G 有：`App`、`Menu`、`MenuBar`、`StaticBoxSizer`、`StaticBox`，事件 `CommandEvent`/`CloseEvent`/`KeyEvent`/`MouseEvent`/`ListEvent`/`ContextMenuEvent`，`Font`（帶 `SetFamily` 的 widget），`Colour` 與 `Point`（tuple 子類別），`FileDialog`/`DirDialog`/`MessageDialog`，回傳 `_Timer` 的 `CallLater`，以及回傳 `Mock` 的 `wx.html2.WebView.New`。只有 S 有：會記錄 `children` 清單的 `Sizer`（`BoxSizer`、`GridBagSizer`、`FlexGridSizer` 繼承它）。兩者都有但行為不同：`Choice`（G 全部走 `__getattr__`；S 的 `GetSelection` 回傳 -1）、`SpinCtrl` 與 `TextCtrl`（S 會保存值；G 的 `TextCtrl` 只保存 `Font`；S 的字型是會記錄 `family` 的一般 `_Font`）、`ListCtrl`（G 是空的；S 會記錄欄位、項目、選取與焦點，並提供 `ItemCount`）、`Accessible`（G 是一般 widget；S 的 `__init__(window=None)` 只設定 `self.Window`，不呼叫基底 `__init__`）、`ScrolledPanel`（G 是 `Window`，`SetupScrolling`/`SetSizer`/`Fit`/`Layout` 都不做事，掛在 `wx.lib.ScrolledPanel`；S 是一般 `Panel`，掛在 `wx.lib.scrolledpanel`）。
- **模組屬性。** 兩者相同：`__path__ = []`、每次存取都回傳**新**類別 `type(name, (), {})` 的模組 `__getattr__`（D 也是）、會帶參數轉呼叫的 `CallAfter`、`PyDeadObjectError`、`ID_ANY`=-1、`NOT_FOUND`=-1、`OK`=4、`ICON_ERROR`=512、`ACC_OK`=0、`ROLE_SYSTEM_PROPERTYPAGE`=38、`FONTFAMILY_TELETYPE`=1。值不同的有：`ID_OK`（G 2、S 5100）、`VERTICAL`（4096 / 1）、`HORIZONTAL`（8192 / 2）、`ALL`（16384 / 16）、`EXPAND`（131072 / 32），以及 `LEFT`、`RIGHT`、`BOTTOM`、`ALIGN_RIGHT`、`ALIGN_CENTER_VERTICAL`、`TE_MULTILINE`、`TE_RICH2`、`TE_DONTWRAP`、`RESIZE_BORDER`、`DEFAULT_DIALOG_STYLE`。`DefaultPosition`/`DefaultSize` 在 G 是 `Point()`，在 S 是 `(0, 0)`。`MessageBox` 在 G 是回傳 `wx.OK` 的 lambda，在 S 是一個共用的 `Mock()`。`EVT_*` 在 S 是整數，在 G 則每次存取都是新類別。只有 G 有 `YES`、`NO`、`YES_NO`、`NO_DEFAULT`、`CANCEL`、`ICON_INFORMATION`、`ICON_WARNING`、`FD_*`、`STAY_ON_TOP`、`CLOSE_BOX`、`ID_ABOUT`、`ALIGN_CENTER_HORIZONTAL`；只有 S 有 `ID_CANCEL`、`ID_APPLY`、`APPLY`、`LC_*`、`SP_*`、`WXK_TAB`、`BORDER_SUNKEN`、`ALIGN_CENTER`、`TOP`。D：`VERTICAL`=1、`EXPAND`=2、`EVT_CLOSE = object()`，以及**不接受**額外參數的 `CallAfter(callback)`。

三個 `dialog.py` 載入器（validation、display、speech）在屬性不存在時的行為也不同：引發 `AttributeError`（validation）、回傳快取的新類別（display），或回傳自動註冊、可吸收 `|` 的子模組（speech）。它們的常數也互相衝突（`OK` 在 display 是 4，在 speech 是 1）。

### 目前的洩漏與順序相依

只有 `test_dialog_display` 與 `test_speech_symbols_dialog` 會自行清理。因為 `discover` 會在執行任何測試前先 import **所有**模組，其他 stub 在 import 階段就混在一起了。依 `discover` 順序 import 七個模組後檢查 `sys.modules`，結果如下：

- `test_dialog_validation` 建立一個最小的 `wx`，把它和綁定它的真正 `dialog` 留在 `sys.modules`。接著 `test_dual_view_frame` 和 `test_gui_document_flows` 沿用並修改同一個 `wx` 物件。
- 因此在 `discover` 下，`gui` import 的是**真正的** `dialog`（validation 留下來的；因為名稱已存在，G 的 `dialog` stub 被跳過），`gui` 的 `DualViewFrame` 繼承的是 D 會記錄參數的 `Frame`，`wx.EVT_CLOSE` 則是 D 的 `object()`。單獨執行時，`gui` 拿到的是 G 的 `dialog` stub 與 G 的 `Frame`。
- 接著 `test_settings_dialogs` 取代 `sys.modules["wx"]`，但 `settings.dialogs` 已經被快取，並綁定在共用的 G 物件上。所以在 `discover` 下，settings 測試跑的是以 **G 的** widget 建出來的 `settings.dialogs`，而測試模組自己的 `wx` 名稱卻是 S 的物件。這些測試仍會通過，只是因為它們比對的常數（`OK | ICON_ERROR`、`ACC_OK`、`ROLE_SYSTEM_PROPERTYPAGE`）剛好相同。
- 所有 import 完成後，`sys.modules` 仍留著 `wx`、`wx.html2`、`wx.lib`、`wx.lib.scrolledpanel`、`dialog`、`gui`、`settings.dialogs`、`ui.dual_view`、G 的 `braille.louis_helper` stub，以及 S 那兩個不是套件的 `braille`、`braille.tables` stub。之後的每個模組都在這種狀態下執行。
- 執行期間，`test_dictionary_management_dialog` 會留下 `sys.modules["wx.ID_EDIT"]`（測試讀取 `dialog.wx.ID_EDIT` 時，speech 風格的 `wx` 自動建立的子模組）。

字母順序剛好讓上述情況全部通過。其他順序目前會失敗：

- `python -m unittest tests.test_gui_document_flows tests.test_dialog_validation`：`FAILED (errors=18)`（8 個測試，計入子測試）。`test_dialog_validation` import 到 G 的 `dialog` stub，所以 `DictionaryNameDialog` 是沒有 `_validate_name` 的 `_Dialog`。
- `python -m unittest tests.test_gui_document_flows tests.test_settings_dialogs tests.test_dual_view_frame`：`FAILED (failures=1, errors=1)`。`ui.dual_view` 已經綁定 G 的 `wx`，所以 `test_initial_geometry_matches_parent` 拿到 G 的 `Frame`（沒有 `init_kwargs`，出現 `'function' object is not subscriptable`），而 `test_raise_without_activating_restores_focus_on_other_platforms` 修補的 `FindFocus` 位在 `ui.dual_view` 沒有使用的那個 `wx` 上。
- 七個模組的 42 組有序配對中有兩組失敗：上面第一組，以及 `python -m unittest tests.test_gui_document_flows tests.test_dual_view_frame`（`FAILED (errors=1)`，`test_initial_geometry_matches_parent`，原因與上面的三模組指令相同）。（更正：先前的草稿說只有第一組失敗；在 `8a89d5e` 重跑全部 42 組，結果是兩組。）七個模組的 40 次固定種子亂序中，17 次弄壞 `test_dialog_validation`，20 次弄壞 `test_dual_view_frame`，其他五個模組從未失敗。
- 完整套件的 20 次固定種子亂序中，除了上述兩個模組，只有在 `test_translation_result_core` 先於 `test_conversion_service` 執行時，`test_conversion_service` 會失敗（8 個錯誤）。這與 wx 無關：`test_translation_result_core` 會移除並重新 import `translate`，使 `TranslationResult` 同時存在兩份（`python -m unittest tests.test_translation_result_core tests.test_conversion_service` 不涉及任何 wx 模組就能重現）。這不在本次範圍內。

### 是否有測試依賴洩漏的 stub？

沒有測試需要靠洩漏才能通過。每個模組單獨執行都會通過（此時沒有任何東西洩漏進來），各模組的測試數加總也等於 `discover` 的數量。不過，目前在 `discover` 下有好幾個模組其實是**對著**洩漏的物件執行（`gui` 用真正的 `dialog` 與 D 的 `Frame`、settings 測試用 G 的 `settings.dialogs`、之後所有模組都看到被 stub 的 `braille`）。本次變更後，每個模組都只會對著自己的 stub 執行，與單獨執行時相同。這就是本規格要保留的參考行為。`discover` 目前造成的混用是意外，本次變更會移除它。

## 設計

### 決策：每個模組各自的 stub 工廠，加上一個範圍輔助工具，而不是單一共用的假模組

考慮過的方案：

1. **所有測試模組共用一個假 `wx` 模組（或一個 `install()`）。** 不採用。各 stub 在常數值上互相衝突（`ID_OK` 可能是 2、5100 或 1；`VERTICAL` 是 4096 或 1；`OK` 是 4 或 1），在 widget 行為上衝突（`Bind`/`SetFocus`/`HasFocus` 是記錄還是忽略；`Choice`/`SpinCtrl`/`TextCtrl`/`ListCtrl` 是保存值還是回傳 `None`），在不存在屬性的語意上也衝突。合併會改變測試所面對的物件。測試也許仍會通過，但那是需要逐一證明的行為變更，不是重構。共用的單例也無法提供 `test_layout_uses_headerless_list_ctrl_and_explicit_categories_name` 目前自行建立的全新 `wx`，而且所有東西都會綁在同一個物件上，這正是洩漏本身。
2. **stub 留在各模組，只補上清理。** 不採用。這能修正洩漏，但約 650 行 stub 程式碼仍散落在各測試模組，而 roadmap 要移除的正是這些。
3. **採用：`client/tests/wx_stub.py` 以工廠函式提供所有 stub，每次呼叫都建立全新物件（目前每種 stub 形狀各一個工廠，用共用元件寫一次），再加上一個範圍輔助工具，負責安裝一組 stub 模組、import 受測程式碼並還原 `sys.modules`。** 每個測試模組保有與現在完全相同的 stub，而且都碰不到其他模組。

收斂各 profile（單一常數表、單一 widget 組）可以在本次完成後另行處理。那是行為變更，不在本次範圍內。

### `client/tests/wx_stub.py` 的內容

使用 4 空白縮排與 ASCII，只用標準函式庫（另加 stub 目前就在用的 `unittest.mock.Mock`）。檔名不符合 `test*.py`，所以 `discover` 不會收集它。它不定義任何 `TestCase`。測試模組以 `from tests import wx_stub` import 它。這在 `python -m unittest tests.<module>` 與從 `client/`（文件規定的工作目錄）執行的 `python -m unittest discover -s tests` 下都可行，而且 `test_dictionary_management_dialog` 現在就已經透過 `tests.` import。單純的 `import wx_stub` 在 `tests.<module>` 下會失敗，在 `discover` 下則可能載入第二份。

以下名稱只表達意圖，計畫可以調整命名，但不能改變行為。

1. **widget 基底**（模組層級，永不修改）：
   - `NoOpAttributes`：只有一個 `__getattr__`，回傳一個回傳 `None` 的空函式。文件說明這是刻意的遮蔽，列出上述後果，以及 P0-3 採用的規則：檢查屬性是否不存在時要檢查類別，絕不檢查 stub 實例。
   - `Widget(NoOpAttributes)`：與 G 的 `_Widget` 完全相同（欄位、方法、`Bind` 忽略參數）。
   - `RecordingWidget(Widget)`：與 S 的 `_Widget` 完全相同。先呼叫 `Widget.__init__`，再設定 `bound_events`、`focused`、`visible`，並覆寫 `Bind`、`Show`、`Hide`、`SetFocus`、`HasFocus`。
2. **stub 工廠。** 每次呼叫都回傳一個以 `sys.modules` 名稱為鍵的新 `dict[str, ModuleType]`，其中安裝的每個類別、`Mock` 與常數都是新建立的。每個工廠都完全重現目前的 stub：相同的類別與方法、相同的常數值、相同的模組 `__getattr__`、相同的子模組連接方式。
   - `gui_frame_stubs()` 供 `test_gui_document_flows` 使用：`wx`、`wx.html2`、`wx.lib`、`wx.lib.scrolledpanel`，加上 `dialog` stub（8 個 dialog 名稱都對應 `_Dialog`，另有 `finalize_dialog_layout`）與 `braille.louis_helper` stub。這兩個現在**一律**安裝，與模組單獨執行時的情況相同。
   - `settings_dialog_stubs()` 供 `test_settings_dialogs` 使用：`wx`、`wx.lib`、`wx.lib.scrolledpanel`、`braille`、`braille.tables`（`listTables` 回傳 `[]`）。
   - `dual_view_stubs()` 供 `test_dual_view_frame` 使用：`wx`、`wx.html2`，採用 D 自己的空操作基底（不是 `Widget`）、會記錄參數的 `Frame`、`CallAfter(callback)`，並且沒有 `FindFocus`。
   - `dialog_validation_stubs()`：只有四個類別的一般 `wx`。
   - `dialog_display_stubs()`：display 那個會快取類別的自動模組與它的常數。
   - `speech_dialog_stubs()`：speech 那個會註冊子模組的自動模組、它的常數與 `|` 支援。
   - 兩種自動模組類別原封不動移到這裡，依行為命名（例如 `AutoClassModule` 與 `AutoSubmoduleModule`）。
3. **`StubScope`**，唯一的安裝與還原機制：
   - 建構時傳入 stub dict、要隔離的名稱（此測試模組要重新 import 的、綁定 wx 的正式模組，例如 `("gui", "settings.dialogs", "ui.dual_view")`），以及一個可選的移除策略，處理在範圍內首次 import 的其他模組。預設策略只處理受管理的名稱（見 R1）。display 傳入「所有新模組」，speech 傳入它目前的根集合，因此兩者的行為完全不變。
   - `loading()` 是給模組層級 import 用的 context manager。它快照受管理的名稱與對應的父套件屬性，移除要隔離的名稱讓它們重新 import，安裝 stub，然後執行區塊內容。離開時記錄產生的模組物件，還原快照（`sys.modules` 條目，以及 `settings.dialogs`、`ui.dual_view` 這類父套件屬性），套用移除策略，並執行洩漏防護（R4）。
   - 一個在 `loading()` 內以私有模組名稱載入檔案的輔助函式（即 display 與 speech 目前用 `spec_from_file_location` 做的事）。`loading()` 離開時會再移除這些私有名稱。
   - 給 `setUpModule` / `tearDownModule` 用的 `activate()` / `deactivate()`。`activate` 重新安裝記錄下來的 stub 模組（包括載入時出現的點號子模組，例如 speech 自動註冊的 `wx.*` 子模組）、被隔離的模組及其父套件屬性，但**不**安裝私有的受測模組名稱（`_speech_symbols_dialog_under_test`、`_dialog_display_test`）：目前測試執行期間這些名稱並不存在，而且 `DialogModuleIsolationTest` 會斷言巢狀載入後 `_MODULE_UNDER_TEST_NAME` 不在 `sys.modules` 中。`deactivate` 還原先前的狀態，並移除任何新出現在 stub 名稱底下的 `sys.modules` 鍵（例如 `wx.ID_EDIT`）。
   - speech 風格的 `dialog.py` 載入器（speech 的 stub、私有名稱 `_speech_symbols_dialog_under_test`、speech 的移除根集合）以單一函式放在這裡，讓 `test_speech_symbols_dialog` 與 `test_dictionary_management_dialog` 共用。它會同時交給呼叫端載入的模組與範圍物件，讓兩個模組都能以該範圍的 `activate`/`deactivate` 作為模組層級 fixture（R3 需要：`test_dictionary_management_dialog` 會在執行期建立 `wx.ID_EDIT`）。display 的載入器採用相同形式：`load_display_dialog()` 同樣回傳 `(module, scope)`。

### 隔離契約

- **R1，載入不留痕跡。** import 一個已遷移的測試模組後，所有受管理名稱（stub 名稱及其點號子名稱、被隔離的名稱、私有的受測模組名稱）在 `sys.modules` 中都不變，被隔離模組的父套件屬性也不變。這裡的「不變」是精確的：如果父套件在 `loading()` 之前沒有該屬性，之後會把該屬性刪除，讓 `from settings import dialogs` 不會拿到過期的副本。載入期間首次 import 的純模組可以留在快取中，就像任何一般 import 之後一樣。採用 display 與 speech 的策略時，它們會像現在一樣被移除。
- **R2，執行期查找看到載入時的物件。** 已遷移模組的測試執行期間，測試透過 `sys.modules` 解析的每個名稱（字串形式的 `patch` 目標、函式內的 import、會讀取父套件屬性的 `import a.b as c`）都解析到該模組在模組層級載入時綁定的同一批模組物件。`test_settings_dialogs` 與 `test_dual_view_frame` 需要這一點。為求一致，七個模組都設定 `setUpModule = scope.activate` 與 `tearDownModule = scope.deactivate`，對其他模組沒有害處。
- **R3，執行不留痕跡。** 已遷移模組的測試結束後，受管理名稱與父套件屬性都回到 `setUpModule` 之前的狀態，且 stub 名稱底下不會留下任何新的鍵。
- **R4，洩漏防護。** `loading()` 離開時，在還原與移除步驟之後，如果有任何在範圍內首次 import、且仍留在 `sys.modules` 中的模組，其模組全域變數指向此範圍的某個 stub 模組物件，就會拋出 `StubLeakError`（`AssertionError` 的子類別），並列出這些 `<模組>.<全域變數>`。這能抓到將來某個正式模組開始 import `wx`、卻沒有加入 `isolate` 的情況。目前防護會通過：只有 `gui.py`、`dialog.py`、`settings/dialogs.py` 與 `ui/dual_view.py` import `wx`，而在模組層級 import `braille.tables` 的只有 `settings/dialogs.py`（`adapters/translation/provider.py` 是在函式內延遲 import `braille`）。

### 各模組的遷移方式

| 模組 | 工廠 | `isolate` | 保留在測試模組的模組層級程式碼 |
| --- | --- | --- | --- |
| `test_gui_document_flows` | `gui_frame_stubs()` | `gui`、`settings.dialogs`、`ui.dual_view` | 放在 `loading()` 內：`gui = importlib.import_module("gui")` 與 `from settings.dialogs import TranslationSettingsPanel`，因為兩者都必須綁定 G 的 stub。純模組的 import（`documents.*`、`settings.state` 等）留在外面。`_make_frame` 與所有測試都不變。 |
| `test_settings_dialogs` | `settings_dialog_stubs()` | `settings.dialogs` | 放在 `loading()` 內：`import wx` 與 `from settings.dialogs import ...` 區塊。`test_layout_uses_headerless_list_ctrl_and_explicit_categories_name` 仍在測試中途建立一組全新的 settings stub，裝進 `sys.modules`，用它修補 `dialogs_module`，然後還原，與現在相同。它留下的東西由 `tearDownModule` 清理（目前會留下重新 stub 過的 `braille`）。 |
| `test_dual_view_frame` | `dual_view_stubs()` | `ui.dual_view` | 放在 `loading()` 內：`from ui.dual_view import DualViewFrame` 與 `import ui.dual_view as dual_view`。模組層級的名稱 `wx` 指向工廠產生的 stub `wx`，因為測試會修補 `wx.Window`。 |
| `test_dialog_validation` | `dialog_validation_stubs()` | `dialog` | 放在 `loading()` 內：`from dialog import DictionaryNameDialog, DocumentNameDialog`。現在一律安裝 stub（目前只在 `wx` 不存在時安裝，而單獨執行時正是如此）。 |
| `test_dialog_display` | `dialog_display_stubs()` | 無（私有名稱 `_dialog_display_test`） | `dialog_module` 透過範圍的私有名稱載入器載入，並採用「移除所有新模組」策略。 |
| `test_speech_symbols_dialog` | `speech_dialog_stubs()` | 無（私有名稱 `_speech_symbols_dialog_under_test`） | `_load_dialog_module()` 保留為包裝共用 speech 載入器的薄層，讓 `DialogModuleIsolationTest` 以相同斷言繼續測試同一份契約。`_SCOPED_STUB_MODULES` 仍提供給該測試使用。 |
| `test_dictionary_management_dialog` | 共用的 speech 載入器 | 無 | 以 `dialog = <共用 speech 載入器>()` 取代 `from tests.test_speech_symbols_dialog import dialog`。它拿到一份內容相同、另外載入的副本，與它目前在 `discover` 下的情況一樣。`discover` 不再把 speech 測試模組執行兩次。 |

所有測試方法、類別、名稱與斷言都保持原樣，只搬移建立與安裝 stub 的程式碼。縮排依各檔案原樣（`test_dual_view_frame`、`test_dialog_display` 與 `test_dictionary_management_dialog` 用 tab，其餘用 4 空白）。

### 刻意保留的行為

- G、S、D widget 上會遮蔽屬性的 `__getattr__`，以及每次存取都建立新類別的模組 `__getattr__`。
- 每個 profile 的所有常數值，包括互相衝突的值。
- S 每次工廠呼叫只有一個共用的 `MessageBox` `Mock`（與現在一樣，每次載入模組建立一次）。
- speech 在模組執行期間把自動子模組註冊到 `sys.modules` 的行為。R3 現在會在 teardown 時移除這些鍵。
- `test_settings_dialogs` 在測試中途重新建立 stub 的做法。
- repr 會有些微變化：由模組 `__getattr__` 與工廠建立的類別，其 `__module__` 會變成 `"tests.wx_stub"`，而不是測試模組名稱。沒有測試斷言 `__module__`、`__qualname__` 或 stub 的 repr（已用 grep 確認）。

### 不在範圍內

- 收斂各 profile，或去掉遮蔽用 `__getattr__` 的嚴格模式。可以之後另行處理，兩者都會改變測試的行為。
- `test_translation_result_core` 與 `test_conversion_service` 之間與 wx 無關的順序相依（`translate` 被重新 import）。
- P2-5 的失敗。
- 新增 `client/tests/__init__.py`。這會讓 `discover` 下的所有模組改名，測試 id 也會改變。
- 在七個已遷移模組中新增測試方法。（更正：先前的草稿也排除了 `test_wx_stub.py`，好讓所有數量完全相同。計畫刻意新增 `client/tests/test_wx_stub.py`，讓每個任務都從一個失敗的測試開始；見測試策略。）
- 任何正式程式碼。

## 測試策略

這次只搬移測試骨架，不新增正式程式的行為。（更正：先前的草稿說沒有紅綠步驟，也不新增測試。）`wx_stub.py` 有自己的測試 `client/tests/test_wx_stub.py`：先寫 10 個共用核心（widget 基底類別、自動模組、`StubScope`）的測試，之後每個遷移 commit 各加一個工廠測試，共 16 個，每個都先失敗。已遷移的模組仍是每個工廠重現舊 stub 的主要證據。安全性來自動手前先記錄基準，並在每一步之後比對：

1. 第一個 commit 之前，記錄七個模組各自單獨執行與 `discover` 的逐測試結果（`-v` 輸出排序後），以及亂序工具在固定種子下的結果（七模組亂序與完整套件亂序）。
2. 第一個 commit 加入共用核心（widget 基底類別、兩種自動模組類別、`StubScope`）及其測試。之後每個 commit 遷移一個模組，從最小的 `test_dialog_validation` 開始，接著是 `test_dual_view_frame`、`test_gui_document_flows`、`test_settings_dialogs`、一起處理的 `test_speech_symbols_dialog` 與 `test_dictionary_management_dialog`，最後是 `test_dialog_display`。`wx_stub.py` 每次只增加該 commit 的模組所需的內容（它的工廠）。每個 commit 之後，該模組單獨執行與完整 `discover` 的結果都必須與記錄完全相同，只多出 `test_wx_stub` 的各行。
3. 最後一個 commit 之後，執行驗收標準中的順序檢查、綁定檢查與洩漏檢查。

## 驗收標準

所有指令都在 `client/` 下以 venv 的 Python（`$PY`）執行。

1. **每個模組結果相同。** 七個模組各自執行 `$PY -m unittest tests.<module> -v`，列出的測試 id 與結果都與基準相同，數量分別為 5 / 8 / 8 / 6 / 61 / 27 / 21，全部 `OK`。
2. **完整套件結果相同。** `$PY -m unittest discover -s tests -v`：`Ran 466 tests`（450 個加上 `test_wx_stub` 的 16 個）、`FAILED (failures=1, skipped=7)`。排序後的 `<test id> ... <結果>` 各行去掉含 `(test_wx_stub.` 的行之後與基準完全相同，且恰好有 16 行含 `(test_wx_stub.`，全部是 `... ok`。唯一的失敗是 P2-5 案例。（更正：先前的草稿預期 `Ran 450 tests`，當時還沒有 `test_wx_stub.py`。）
3. **roadmap 指令。** `$PY -m unittest tests.test_gui_document_flows tests.test_settings_dialogs tests.test_speech_symbols_dialog tests.test_dictionary_management_dialog -v` 結果為 `Ran 117 tests`、`OK`。七個模組放在同一個指令中執行，結果為 `Ran 136 tests`、`OK`。
4. **順序無關（七個模組）。** 以下指令以前會失敗，現在必須通過：
   - `$PY -m unittest tests.test_gui_document_flows tests.test_dialog_validation` 結果為 `Ran 69 tests`、`OK`。
   - `$PY -m unittest tests.test_gui_document_flows tests.test_settings_dialogs tests.test_dual_view_frame` 結果為 `Ran 94 tests`、`OK`。
   - `$PY -m unittest tests.test_gui_document_flows tests.test_dual_view_frame` 結果為 `Ran 67 tests`、`OK`。

   用亂序工具執行七個模組的全部 42 組有序配對，以及至少 200 種固定種子的排列（種子 1-200），每次都是 136 個測試，沒有失敗或錯誤。跑完全部 5040 種排列為選用（依序執行約需 25 分鐘）。
5. **順序無關（完整套件）。** 用亂序工具以種子 1-20 執行基準的 64 個模組（打亂前先排除 `test_wx_stub`，讓每個種子產生與基準相同的排列）：每次都是 450 個測試，七個模組中沒有任何失敗或錯誤，其他模組的失敗與同一種子的基準完全相同。那些失敗只會是不在範圍內的 `translate` 重新 import 或 P2-5 造成的 `test_conversion_service` 案例。另外以種子 1-20 執行全部 65 個模組（466 個測試），`test_wx_stub` 與七個模組都沒有任何失敗或錯誤。（更正：比對基準時排除 `test_wx_stub`，因為多一個模組會改變每個種子的排列。）
6. **無洩漏（R1/R3）。** 用一個用完即丟的探測腳本，在全新行程中單獨 import 每個已遷移模組，確認 `sys.modules` 沒有多出先前不存在的 `wx`、`wx.*`、`dialog`、`gui`、`settings.dialogs`、`ui.dual_view` 或 `braille.louis_helper` 鍵，且 `braille` 若存在就是真正的套件。執行完該模組的測試後，同樣成立。對 `test_wx_stub` 執行同一個探測腳本，也不會回報任何變化。
7. **綁定（R2）。** 用一個用完即丟的探測腳本，在 `discover`（先載入所有模組）下分別於 `test_settings_dialogs` 與 `test_dual_view_frame` 內執行，確認測試執行期間 `sys.modules["settings.dialogs"]`（或 `sys.modules["ui.dual_view"]`）與對應的父套件屬性，正是測試模組在載入時綁定的模組，且它的 `wx` 是該模組自己的 stub。這很重要，因為 `test_layout_uses_headerless_list_ctrl_and_explicit_categories_name` 即使面對過期的模組也可能通過。
8. **洩漏防護有效。** 暫時從 `test_gui_document_flows` 的 `isolate` 中拿掉 `"ui.dual_view"`，它的 import 會以防護的訊息失敗。之後改回，不要 commit。
9. **測試模組中不再有 stub 程式碼。** 在 repo 根目錄執行：`grep -nE 'class _Widget|class _AutoModule|def _install_stub_modules|def _make_wx_stub|__getattr__ = lambda|__path__ = \[\]|ModuleType\("wx' client/tests/test_*.py`。目前它在六個模組中比對到 24 行。變更後不輸出任何內容，所有建立假 `wx` 的程式碼都在 `client/tests/wx_stub.py`。這個模式不會比對到 `DialogModuleIsolationTest` 中的 `sentinel_wx = types.ModuleType('wx')`（單引號）。那一行是測試資料而不是 stub，保留不動。
10. `git diff main --stat` 只動到 `client/tests/`（七個模組、`wx_stub.py` 與 `test_wx_stub.py`）以及這些 spec/plan 文件。沒有正式程式檔，也沒有 `.po`/`.mo` 變更。
11. 先以一個 commit 加入共用核心，之後每個 commit 遷移一個模組（speech 與 dictionary 兩個模組一起）。每個 commit 之後，已遷移的模組都符合第 1、2 條。

## 風險

- **過期的父套件屬性**（中）。`import settings.dialogs as x` 與 `from settings import dialogs` 讀的是 `settings` 套件的 `dialogs` 屬性，而不是 `sys.modules`。如果範圍只還原 `sys.modules` 而沒有還原這個屬性，之後的模組可能拿到別的模組的副本，測試卻照樣通過。R1/R2/R3 明確涵蓋這些屬性，並由第 7 條驗收檢查。
- **隱藏地依賴跨模組物件**（低）。單獨執行每個模組（全部通過、數量加總正確）與順序檢查已排除這種可能。在 `discover` 下，`gui` 會改用 G 的 `dialog` stub 而不是真正的 `dialog`，settings 測試會改用 S 的 widget 而不是 G 的。兩者都是目前單獨執行時就會通過的行為。
- **profile 逐漸分歧**（低）。之後的測試可能只在某一個 profile 加 widget。模組 docstring 會說明每個工廠只對應一個使用者，收斂是另一項變更。
- **僅限 Windows 的行為**（此處無法驗證）。目前 S 那個不是套件的 `braille` stub 與 G 的 `braille.louis_helper` stub，會在 `discover` 執行的剩餘期間一直留在 `sys.modules`。在 Windows 上，`test_liblouis_runtime.setUpClass`（`from braille import liblouis, louis_helper`）在所有模組載入後才執行，因此目前可能拿到 G 的 stub `louis_helper`。變更後它會拿到真正的模組。測試數不變，但這些只在 Windows 執行的測試在 Windows 上的結果可能改變，推測是從錯誤變成通過。這台 Linux 主機無法執行它們。交接時必須說明這一點，並請人在 Windows 上於變更前後各執行一次 `py -m unittest discover -s tests`。
- **pytest**（低）。此環境未安裝。pytest 支援 `setUpModule`/`tearDownModule`，並且和 `discover` 一樣先 import 模組再執行，但這點未經驗證。
- **超出 roadmap 列的範圍**（判斷）。該列只列出四個模組。本規格另外遷移 `test_dialog_validation`、`test_dual_view_frame` 與 `test_dialog_display`。前兩者是目前會被洩漏弄壞的模組，第三個是最後一份手寫的假 `wx`。不納入的話，會留下三份 stub 與那些順序失敗。
