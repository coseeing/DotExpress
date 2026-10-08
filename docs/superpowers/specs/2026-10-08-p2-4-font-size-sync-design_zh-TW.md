# 字體大小同步（P2-4）設計

## 目標

移除反向 classmethod 探針 `DotExpressSettingsDialog.sync_open_font_size`。這是 `storage/refactor.md`（第 6.3 節）路線圖任務 P2-4，對應發現 P-3（「Observer 缺席，改以反向 classmethod 探針替代」）。目前主視窗呼叫一個 classmethod，它透過類別 slot 找到開啟中的設定對話框，以 `isinstance(panel, ViewSettingsPanel)` 翻找面板、讀取面板的 `font_size_dirty` 旗標，並寫入其 spin 控制項。本任務完成後：

- `SingletonDialogMixin`（P2-1，`ui/dialog_base.py`）新增一個公開唯讀存取器 `open_instance()`，取得其 slot 中的對話框。
- `DotExpressSettingsDialog` 新增**實例**方法 `sync_font_size(font_size)`，由它自己尋找自己的 View 面板。
- `ViewSettingsPanel` 新增 `sync_font_size(font_size) -> bool`，由它負責 dirty 旗標規則與自己的 spin 控制項。
- `gui._set_view_font_size` 向類別取得開啟中的對話框，再呼叫該實例的方法。`sync_open_font_size` 刪除。

不新增 event bus 或 `Signal`（決策 D1）。此重構不改變行為：相同的字體大小在相同情況下送到相同的控制項，沒有新增任何顯示或朗讀內容，msgid 不變（353，集合相同）。黃金 fixture `client/tests/fixtures/translation_golden.json`（sha256 `e67d95a1ae001d928b657f16468494d0e98beeea5a6425283090b34030211ccd`）與 `client/tests/fixtures/dictionary_entries_trace.json`（sha256 `f493da52376c8eac32a50c33b7f11870451360bed4bf26c1db339ccd2c66c2cf`）不變。

## 現況（2026-10-08 於 `refactor/p2-4-font-size-sync` 驗證，HEAD `6dd65e3`，已合併 P0-*、P1-*、P2-1、P2-2、P2-3）

縮排：`settings/dialogs.py`、`ui/dialog_base.py` 與所有會動到的測試模組使用 4 個空白；`gui.py` 使用 tab。

基準：`cd client && $PY -m unittest discover -s tests` 得到 `Ran 1023 tests`、`FAILED (failures=1, skipped=9)`。唯一失敗為 P2-5 的 `test_conversion_service ... test_translate_with_language_does_not_duplicate_existing_spaces_around_math`。shuffle harness 種子 1、2 得到同一個失敗。聚焦模組：`tests.test_settings_dialogs` 67 個、`tests.test_dialog_base` 23 個、`tests.test_gui_document_flows` 145 個、`tests.test_view_settings` 5 個，全部 OK。msgid 掃描（`cd /workspace/DotExpress && $PY $SP/p12/tools/msgid_scan.py client`）回報 `source msgids: 353`。（`$PY` = `$SP/venv/bin/python`，`$SP` = 本次工作階段的 scratchpad。）

`storage/refactor.md` 中的行號（`gui.py:855`、`settings/dialogs.py:875-896`）早於 P0-P2-3。以下為目前行號。

### 誰在對話框外改變字體大小

- `gui.py:215, 217` 將兩個編輯區的 `wx.EVT_MOUSEWHEEL` 綁到 `on_editor_mousewheel`（`gui.py:868-873`）。`ui/shortcuts.py:51` `get_font_size_step_from_wheel` 對 Ctrl+滾輪回傳 +1/-1，其他情況回傳 0；為 0 時事件被 Skip。
- `gui.py:552-558` `_set_view_font_size(font_size)`：正規化 `replace(self.view_settings, font_size=font_size)`（以 `VIEW_FONT_SIZE_RANGE` 夾在 8..48）、套用到編輯區、`save_view_settings(...)`，**然後**呼叫 `DotExpressSettingsDialog.sync_open_font_size(self.view_settings.font_size)`。即使夾住後大小沒變，四步仍全部執行。
- 這是唯一的呼叫端。字體大小**沒有**鍵盤快捷鍵（沒有 Ctrl+=/Ctrl+-，已查 `ui/shortcuts.py` 與 `gui.py`）。設定對話框自己的套用/確定走 `apply_settings_from_dialog`（`gui.py:408-425`），不會同步：該變更的來源就是對話框，對話框自行以提交後的快照重新載入面板（`on_apply`，`settings/dialogs.py:698-705`）。
- 雙視窗（`ui/dual_view.py`）不使用檢視字體大小。因此只有一個發布者與一個訂閱者。

### 探針（`settings/dialogs.py:751-773`）

```python
@classmethod
def sync_open_font_size(cls, font_size: int) -> None:
    instance = cls._instance
    if instance is None:
        return
    normalized_view = normalize_view_settings(
        ViewSettings(font_size, instance.snapshot.view.scheme, instance.snapshot.view.braille_font)
    )
    view_panel = None
    for panel in instance.panel_instances.values():
        if isinstance(panel, ViewSettingsPanel):
            view_panel = panel
            break
    if view_panel is not None and getattr(view_panel, "font_size_dirty", False):
        return
    instance.snapshot = instance.snapshot.with_view(normalized_view)
    if view_panel is not None:
        view_panel.font_size_spin.SetValue(normalized_view.font_size)
        view_panel.font_size_dirty = False
```

它處理的情況：

1. **沒有開啟的對話框**（slot 為 `None`）：什麼都不做。
2. **對話框已開啟，View 面板尚未建立**（面板由 `_get_category_panel` 延遲建立，`settings/dialogs.py:214-220`）：只改對話框快照的字體大小，配色與點字字型取自對話框自己的快照。之後使用者切到 View 類別時，`ViewSettingsPanel.make_settings`（561-598）讀取 `owner.snapshot.view`，顯示同步後的大小；不造訪該面板直接套用，也會提交此大小（`_collect` 從 `self.snapshot` 起算）。
3. **View 面板已建立，沒有待套用的編輯**：更新快照、把 spin 設為該大小，並在 `SetValue` 之後把 `font_size_dirty` 重設為 `False`（以防某平台的 `SetValue` 送出 `EVT_TEXT`；處理器 `_on_font_size_changed` 618-619 只設旗標）。配色與點字字型的選項不動，因此那裡的草稿會保留。
4. **View 面板已建立，使用者改過 spin**（`EVT_SPINCTRL`/`EVT_TEXT` 設定 `font_size_dirty`，596-597）：什麼都不做，連快照也不改。旗標由 `load_snapshot`（600-606）清除，每次套用成功後都會執行。
5. **對話框已關閉**：確定、取消、關閉鈕（`EVT_CLOSE` -> `on_cancel`，95-98）與 Escape（`wx.ID_CANCEL` 按鈕）最後都呼叫 `SingletonDialogMixin._destroy`，清空 slot，因此適用情況 1。
6. **slot 中仍留著已死的視窗**：UI 上無法到達（所有關閉路徑都經過 `_destroy`；主框架被銷毀時應用程式即結束）。探針沒有死視窗處理：會從 `font_size_spin.SetValue` 拋出例外。

slot：`DotExpressSettingsDialog._instance`（648）宣告在類別本身。P2-1 的 mixin 透過 `cls.__dict__` 讀寫它（`ui/dialog_base.py:90-142`），因此子類別看不到父類別的對話框。探針讀的是 `cls._instance`（一般屬性查找）。對 `DotExpressSettingsDialog` 兩者得到同一個物件，因為它宣告了自己的 slot。

它之所以是反向探針：對話框的知識（哪個面板持有字體大小、dirty 規則、spin）住在一個從外部伸手進實例的 classmethod 裡，而主視窗呼叫的是對話框**類別**，不是某個對話框。

### 涉及此區的測試

- `tests/test_settings_dialogs.py:391-398` `ViewSettingsPanelTest.test_view_panel_tracks_font_size_dirty_state`。
- `tests/test_settings_dialogs.py:493-525`：`test_sync_open_font_size_updates_snapshot_before_view_panel_exists` 與 `test_sync_open_font_size_keeps_dirty_view_panel_draft`。兩者都手動指定 `DotExpressSettingsDialog._instance` 並呼叫 classmethod。
- `tests/test_settings_dialogs.py:547-770` singleton 特徵測試（P2-1），以及 `tests/test_dialog_base.py` 中的 `MixinShapeTest`（104）、`SingletonDialogMixinTest`（218-340）與 `DialogBaseImportTest`（342）。
- `tests/test_gui_document_flows.py:907-918` `test_open_settings_uses_singleton_dialog`。框架層沒有任何測試涵蓋 `_set_view_font_size` 或 `on_editor_mousewheel`；`tests/test_input_shortcuts.py:62` 只測滾輪步進函式。

## 設計

### 決策摘要

| # | 決策 | 理由 |
| --- | --- | --- |
| D1 | 不加 `Signal`/event bus。 | 一個發布者（`_set_view_font_size`，只由 Ctrl+滾輪觸發）、一個訂閱者（設定對話框）。雙視窗不使用字體大小，對話框內的套用也不需要通知。bus 需要在 `__init__` 訂閱、在 `_destroy` 取消訂閱，再加上死視窗處理，生命週期管理比既有的 slot 還多。`storage/refactor.md` 4.3 與 7.10 也說只有出現第二個訂閱者時才引入 bus。 |
| D2 | 框架**不**另外持有 `_settings_dialog` 參考；改透過 `open_instance()` 讀取 P2-1 的 slot。 | `refactor.md` P-3 提到的 `_dual_view_frame` 手法需要 `on_closed` 回呼（`gui.py:304-309`）來清除框架的副本。設定對話框是自己關閉的（`on_ok`/`on_cancel` -> `_destroy`），框架的副本會過期，除非 `show_singleton` 與建構子多一個回呼參數。slot 已是唯一事實來源，而 `_destroy` 已會清除它。 |
| D3 | `open_instance()` 讀取 `cls.__dict__.get("_instance")`，與 mixin 其他部分一致。它不 raise、不聚焦、也不探測死視窗。 | 對 `DotExpressSettingsDialog` 而言與現在的 `cls._instance` 是同一個物件（它宣告了自己的 slot）。不做存活探測，因為原探針也沒有，且每條關閉路徑都會清空 slot（情況 6 維持原樣）。 |
| D4 | 對話框以同樣的 `isinstance` 掃描 `panel_instances` 尋找 View 面板，改放在對話框的私有輔助方法 `_view_panel()`。 | 語意與現在相同，包含 `ViewSettingsPanel` 的子類別，以及把面板放在任意索引的測試對話框。改用 `category_classes.index(ViewSettingsPanel)` 的索引查找，會對未註冊該面板的對話框拋出例外。對話框掃描自己的面板是正常的擁有關係，不是探針。 |
| D5 | dirty 規則與 spin 移入 `ViewSettingsPanel.sync_font_size(font_size) -> bool`。 | 只有面板知道 `font_size_dirty` 與 `font_size_spin`；對話框只知道「接受與否」。 |
| D6 | 對話框先正規化，再詢問面板，最後替換快照。 | 現在是先替換快照再 `SetValue`，新順序是先設 spin。差異無法觀察：`normalize_view_settings` 是純函式、`with_view` 不會失敗，而 `SetValue`（以及它可能送出的 `EVT_TEXT`）從不讀取快照。面板為 dirty 時提早返回，仍不動快照。 |
| D7 | 刪除 `sync_open_font_size`，不留別名。 | 本 repo 內只有一個呼叫端。`tests/test_settings_dialogs.py` 中加一行不存在檢查記錄此移除。 |

### `ui/dialog_base.py`（4 個空白）

加到 `SingletonDialogMixin`，位於 `_show_new` 之後：

```python
    @classmethod
    def open_instance(cls):
        """The open dialog of this class, or ``None``. Nothing is raised, focused or checked."""
        return cls.__dict__.get("_instance")
```

模組 docstring 與「無 `__init__`/`__new__`/`__slots__`/metaclass」的形狀不變，import 不變。

### `settings/dialogs.py`（4 個空白）

`ViewSettingsPanel`，位於 `_on_font_size_changed` 之後：

```python
    def sync_font_size(self, font_size: int) -> bool:
        """Show a font size changed in the main window, unless the user has edited it here.

        Returns ``False``, changing nothing, while that edit is pending (until Apply or OK).
        """
        if self.font_size_dirty:
            return False
        self.font_size_spin.SetValue(font_size)
        self.font_size_dirty = False
        return True
```

`font_size_dirty` 改為直接讀取（它在 `make_settings` 中設定），不再用 `getattr(..., False)`。所有真實面板與現有測試中的面板都有此屬性。

`DotExpressSettingsDialog`，取代 `sync_open_font_size`：

```python
    def sync_font_size(self, font_size: int) -> None:
        """Take a font size changed in the main window (Ctrl+wheel).

        A View panel with an unsaved font size edit keeps it, and then the snapshot is left alone too.
        """
        view = normalize_view_settings(
            ViewSettings(font_size, self.snapshot.view.scheme, self.snapshot.view.braille_font)
        )
        view_panel = self._view_panel()
        if view_panel is not None and not view_panel.sync_font_size(view.font_size):
            return
        self.snapshot = self.snapshot.with_view(view)

    def _view_panel(self) -> ViewSettingsPanel | None:
        for panel in self.panel_instances.values():
            if isinstance(panel, ViewSettingsPanel):
                return panel
        return None
```

import 不變（`ViewSettings` 與 `normalize_view_settings` 已匯入）。沒有字串變更。

### `gui.py`（tab）

`_set_view_font_size` 前三個敘述與其順序不變，最後一行改為：

```python
		settings_dialog = DotExpressSettingsDialog.open_instance()
		if settings_dialog is not None:
			settings_dialog.sync_font_size(self.view_settings.font_size)
```

`gui.py` 任何地方都不讀取 `_instance`。import 行（`gui.py:91`）不變。

## 保持不變的部分

對上述情況 1-6 而言：編輯區字型、儲存的 `config.json`、對話框快照、spin 值、dirty 旗標、配色與點字字型草稿、套用與確定所提交的內容、之後才建立的 View 面板所顯示的值。另外 `show_singleton`/`_destroy` 的 singleton 行為、msgid 集合與 fixture 也不變。沒有任何可見或朗讀上的變化，因此不需要截圖。

## 測試計畫

### A. 在現有程式碼上的特徵測試（步驟 1）

這些測試在目前程式碼上就會通過。框架層測試之後永不修改。對話框層測試透過 `tests/test_settings_dialogs.py` 中的一個模組輔助函式 `sync_open_dialog_font_size(dialog_class, font_size)` 觸發同步：步驟 1 中它呼叫 `dialog_class.sync_open_font_size(font_size)`，步驟 3 中改為 `dialog = dialog_class.open_instance()`，非 `None` 時呼叫 `dialog.sync_font_size(font_size)`。這是 A 部分唯一的修改。開啟的對話框一律以 `patch.object(dialog_class, "_instance", dialog)` 放入 slot，絕不直接指定，避免在模組之間洩漏。

1. `tests/test_gui_document_flows.py` 新類別 `ViewFontSizeSyncCharacterizationTest`（gui stub scope；使用 `gui.DotExpressSettingsDialog`，即在該 scope 下載入的真實類別）。框架為 `object.__new__(gui.BrailleFrame)`，帶 `view_settings`、`Mock` 的 `_apply_editor_view_settings`，並 patch `gui.save_view_settings`。開啟的對話框為 `object.__new__(gui.DotExpressSettingsDialog)`，帶 `snapshot`、`panel_instances = {}` 與 `Mock` 的 `Destroy`。事件為具 `GetWheelRotation`、`ControlDown`、`Skip` 的 `SimpleNamespace`。
   - 框架檢視 `ViewSettings(12, "dark", "default")`、對話框檢視 `ViewSettings(12, "light", "simbraille")` 時 Ctrl+滾輪向上：框架變為 `(13, "dark", "default")`，編輯區與 `save_view_settings` 收到它，對話框變為 `(13, "light", "simbraille")`（只有大小會傳過去）。`save_view_settings` 的 side effect 記錄儲存當下對話框的大小：仍為 12，因此對話框是在儲存之後才同步。
   - 從 8 向下與從 48 向上的 Ctrl+滾輪：大小維持夾住的值，仍會儲存，且對話框（快照原為 12）被設為夾住後的大小。
   - 未按 Ctrl 的滾輪：呼叫 `Skip`，不套用、不儲存、不同步。
   - 沒有開啟的對話框：編輯區更新與儲存照常執行，不拋例外。
   - 先以 `dialog.on_cancel()` 關閉對話框：slot 為空，之後的 Ctrl+滾輪不動該對話框的快照。
2. `tests/test_settings_dialogs.py` 新類別 `FontSizeSyncCharacterizationTest`。對話框為 `make_dialog_without_wx_constructor()`。View 面板是以該對話框為 owner 建立的**真實** `ViewSettingsPanel`，透過 `build_panel` 新增的 `owner=` 關鍵字（預設為目前的 `SimpleNamespace`），並使用記錄用的 `wx.Choice`/`wx.SpinCtrl`。面板放在 `dialog.panel_instances[2]`。
   - slot 中沒有對話框：不拋例外。
   - 尚無 View 面板：快照大小變成 20，配色與點字字型不變。之後以該對話框為 owner 建立的 View 面板，其 spin 顯示 20。99 變成 48，3 變成 8。
   - 已建立且乾淨的面板，配色選項切到深色（草稿）：spin 為 20、`font_size_dirty` 為 false、快照為 20，配色選項仍為深色，快照的配色不變。
   - 待套用的編輯（spin 設為 30 並呼叫 `panel._on_font_size_changed(None)`，即綁到 `EVT_SPINCTRL`/`EVT_TEXT` 的處理器）：spin 維持 30、快照維持 12。接著 `panel.load_snapshot(dialog.snapshot)`（套用時所做的事）：下一次同步又會生效。
   - 面板放在其他索引（0）以及 `ViewSettingsPanel` 的子類別：仍會被找到（D4）。
3. 493-525 的兩個現有測試保留，於步驟 3 改用輔助函式（更名為 `test_sync_font_size_...`）。`test_view_panel_tracks_font_size_dirty_state` 保留。

### B. 新 API（步驟 2，純新增）

`tests/test_dialog_base.py` 的 `SingletonDialogMixinTest` 新增：
- slot 為空時 `open_instance()` 回傳 `None`，否則回傳 slot 中的對話框，且不呼叫 `Iconize`、`Raise`、`SetFocus` 或 `Show`（對話框為 `Mock`；斷言 `mock_calls == []`）。
- 父類別有對話框時，沒有自己 slot 的子類別得到 `None`（與 `_raise_existing` 相同的 `cls.__dict__` 規則）。
- `_destroy` 之後 `open_instance()` 回傳 `None`。

`tests/test_settings_dialogs.py` 新增 `ViewSettingsPanel.sync_font_size` 測試（乾淨時回傳 `True` 並設定 spin；dirty 時回傳 `False` 且不動 spin），針對步驟 2 新增的方法。守護測試 `MixinShapeTest` 不需修改即通過。

### C. 切換（步驟 3）

A 部分只改輔助函式即通過。新增一個斷言：`"sync_open_font_size" not in vars(DotExpressSettingsDialog)`。既有的 singleton 特徵測試（P2-1）不需修改即通過。

## 遷移步驟（每步一個綠色 commit）

1. `test: characterize font size sync`（在目前程式碼上的 A 部分，加上 `build_panel` 的 `owner=` 關鍵字）。
2. `refactor: add open dialog and panel font size hooks`（`SingletonDialogMixin.open_instance`、`ViewSettingsPanel.sync_font_size`、B 部分；除測試外尚無呼叫端）。
3. `refactor: sync font size through the open settings dialog`（`DotExpressSettingsDialog.sync_font_size` 與 `_view_panel`、`gui._set_view_font_size`、刪除 `sync_open_font_size`、C 部分）。

## 驗收標準

1. Linux 上的路線圖驗證：`cd client && $PY -m unittest tests.test_settings_dialogs -v` 通過。以下也須為綠：`tests.test_dialog_base tests.test_gui_document_flows tests.test_view_settings tests.test_input_shortcuts tests.test_wx_stub tests.test_removed_dead_code tests.test_i18n`。
2. 全套件（`$PY -m unittest discover -s tests`）：`Ran 1023 + N`（N 為新增的測試數，由 plan 確定）、`failures=1`（僅 P2-5 那一個）、`errors=0`、`skipped=9`。
3. shuffle harness：`cd client && for s in $(seq 0 19); do $PY $SP/shuffle_harness.py $s; done`，20 個種子都恰好只有一個失敗，即 P2-5 那一個。`test_settings_dialogs`、`test_dialog_base` 與 `test_gui_document_flows` 單獨執行及兩兩以兩種順序執行皆通過。
4. 從 repo 根目錄執行 msgid 掃描回報 `source msgids: 353`，集合與 `main` 相同。`git diff main --stat -- client/locales` 為空。
5. 上述兩個 fixture 的 sha256 不變，`git diff main -- client/tests/fixtures` 為空。
6. `grep -rn "sync_open_font_size" client --include=*.py --exclude-dir=.venv` 無輸出。`grep -n "_instance" client/gui.py` 無輸出。`grep -n "isinstance(panel, ViewSettingsPanel)" client/settings/dialogs.py` 只列出 `_view_panel` 中那一行。`grep -n "font_size_dirty\|font_size_spin" client/settings/dialogs.py` 只列出 `ViewSettingsPanel` 內的行。
7. `git diff main --stat` 只動到 `client/gui.py`、`client/settings/dialogs.py`、`client/ui/dialog_base.py`、三個測試模組與文件。

## 風險

- **測試模組間的 slot 洩漏。** 所有新測試都以 `patch.object` 設定 slot。由 shuffle 涵蓋。
- **stub scope 的類別同一性。** `test_gui_document_flows` 必須使用 `gui.DotExpressSettingsDialog`（在 gui scope 下載入、有自己 slot 的類別），絕不在其 scope 外 import `settings.dialogs`。`test_settings_dialogs` 使用自己 scope 中的類別。
- **`SetValue` 與快照寫入的順序（D6）。** 以 stub 無法觀察；依處理器程式碼判讀，真實 wx 亦然。
- **直接讀取 `font_size_dirty`。** 手動建立而缺少此屬性的面板，現在會拋 `AttributeError`，而不是被視為乾淨。所有真實面板都在 `make_settings` 中設定它，以 `object.__new__` 建立面板的測試也都有設定。
- **真實 wx。** 此處一切都只以 stub 檢查（見 Windows 驗證待辦）。

## 保留的已知怪異行為（以測試釘住，不修正）

1. 已在 8 或 48 時的 Ctrl+滾輪仍會儲存並同步對話框。由 A 部分第 1 項釘住。
2. View 面板中有待套用的字體大小編輯時，同步連快照也不改，因此套用會提交使用者的編輯，從對話框角度看滾輪的變更被捨棄（編輯區在套用前維持滾輪設定的大小）。由 A 部分第 2 項釘住。
3. 沒有死視窗處理（情況 6）。目前無法到達，不釘住。

## Windows 驗證待辦

Windows 上的真實 wxPython 搭配 NVDA（此 Linux 環境無法執行）：開啟 設定 > 檢視，在編輯區按 Ctrl+滾輪，字體大小 spin 跟著變。在 spin 中輸入大小後 Ctrl+滾輪，spin 保留輸入的值。套用後再 Ctrl+滾輪，spin 又會跟著變。在「轉譯」類別開啟設定，Ctrl+滾輪後切到「檢視」：顯示新的大小。關閉對話框（確定、取消、關閉鈕、Escape）後 Ctrl+滾輪：不出錯。

## 不在範圍內

- event bus 或 `Signal`（D1），以及雙視窗回應檢視設定。
- 字體大小鍵盤快捷鍵。
- `open_instance` 中的死視窗處理（情況 6）。
- `TextProcessingDialog`（無字體大小）、其他 singleton 內部（P2-1）與選項來源（P2-3）。
- 更新提到 `sync_open_font_size` 的舊 spec 與 plan（它們是歷史紀錄）。
