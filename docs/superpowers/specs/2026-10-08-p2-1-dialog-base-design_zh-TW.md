# 對話框基底與型別化名稱錯誤（P2-1）設計

## 目標

移除在 `client/dialog.py` 與 `client/settings/dialogs.py` 之間複製的對話框樣板，並以型別化的錯誤取代對名稱驗證錯誤的字串比對。這是 `storage/refactor.md`（6.3 節）路線圖任務 P2-1，涵蓋發現 P-2（singleton 實作了兩次）、5.1 節 `__enter__/__exit__` 一列（七份複本）、4.3 節的 Mixin/Template 與 Typed error 兩列，以及 P1 審查建議（`docs/superpowers/history/2026-10-08-02-refactor-p1/review_task.md`，P2 第 2 點）把 `ConvertingDialog` 移出 `gui.py`。

具體而言：

- 新增不依賴 wx 的模組 `client/ui/dialog_base.py`，含三個基底：`ContextManagedDialog`（`__enter__` 回傳對話框、`__exit__` 銷毀它）、`NameDialogBase`（兩個名稱對話框共用的 `_on_ok`／`_validate_name` 骨架；子類只提供 normalizer 與訊息）、`SingletonDialogMixin`（兩個設定對話框「只開一個實例」的邏輯）。
- `client/shared/name_validation.py` 新增 `NameValidationError(ValueError)`，帶 `code` 欄位（`"empty"`、`"invalid"`、`"too_long"`、`"reserved"`）。`normalize_base_name` 改丟這個錯誤而非單純的 `ValueError`；`str(error)` 維持同樣的英文文字。
- `dialog.py` 拿掉七組 `__enter__/__exit__` 與 `_normalize_dialog_name`（它重做了一半的驗證，並以 `"exceed" in str(exc)` 猜錯誤類型）。兩個名稱對話框改以 `error.code` 對應到各自的訊息。
- `settings/dialogs.py` 拿掉兩份 `_destroy`、`_is_destroyed_window_error` 與 `show_singleton` 本體；每個對話框只保留一個轉送建構參數的 `show_singleton`。
- `ConvertingDialog` 原封不動地從 `gui.py` 移到 `dialog.py`。

這是保持行為不變的重構。每個對話框顯示相同的文字、相同的順序、相同的焦點與相同的結果。msgid 不變：原始碼 msgid 掃描維持 353，`client/locales` 不變。調查中發現的怪異行為以測試釘住，不修正（見「保留的既有怪異行為」）。

## 現況（2026-10-08 於 `refactor/p2-1-dialog-base` 驗證，HEAD `000239b`，已合併 P0-1..P0-6、P1-1..P1-6 與 P1 審查修正）

縮排：`dialog.py` 與 `gui.py` 用 tab；`settings/dialogs.py`、`shared/name_validation.py`、P1 新增的 `ui/` 模組與下文提到的測試模組用 4 個空白。

基準：`cd client && $PY -m unittest discover -s tests` 得到 `Ran 818 tests`、`FAILED (failures=1, skipped=9)`；唯一的失敗是 P2-5 的 `test_conversion_service ... test_translate_with_language_does_not_duplicate_existing_spaces_around_math`。路線圖指令 `$PY -m unittest tests.test_dialog_validation tests.test_dialog_display tests.test_settings_dialogs` 跑 40 個測試，全綠。msgid 掃描（`$SP/p12/tools/msgid_scan.py client`）：原始碼 353 個 msgid；`.pot` 只多出 4 個已知的孤兒匯入 wildcard。

### 對話框清單

client 中所有 `wx.Dialog` 子類（`ui/*` 與 `about.py` 沒有定義任何對話框；「關於」視窗是 `gui.on_about` 以 `with` 使用的 `wx.MessageDialog`）：

| 類別 | 檔案:行 | Context manager | 其他共用邏輯 |
| --- | --- | --- | --- |
| `ConvertingDialog` | `gui.py:108` | 無（非 modal；`gui.close_converting_dialog` 解除 `EVT_CLOSE` 綁定並呼叫 `Destroy()`） | `CanVeto()` 時否決 `EVT_CLOSE` |
| `AddSymbolDialog` | `dialog.py:89` | `185-189` | - |
| `DictionaryNameDialog` | `dialog.py:192` | `253-257` | `_on_ok` 225-240、`_validate_name` 242-251 |
| `DocumentNameDialog` | `dialog.py:260` | `316-320` | `_on_ok` 290-304、`_validate_name` 306-314 |
| `InvalidWorkspaceFilesDialog` | `dialog.py:323` | `356-360` | - |
| `FileIssuesDialog` | `dialog.py:363` | `378-382` | - |
| `SpeechSymbolsDialog` | `dialog.py:404` | `417-421` | - |
| `DictionaryManagementDialog` | `dialog.py:651` | `870-874` | - |
| `SettingsDialog` | `settings/dialogs.py:82` | 無 | 基底；`EVT_CLOSE` -> `on_cancel` |
| `TextProcessingDialog` | `settings/dialogs.py:107` | 無 | singleton：`_instance` 108、`_destroy` 168-171、`_is_destroyed_window_error` 173-185、`show_singleton` 187-208 |
| `MultiCategorySettingsDialog` | `settings/dialogs.py:211` | 無 | 基底 |
| `DotExpressSettingsDialog` | `settings/dialogs.py:718` | 無 | singleton：`_instance` 726、`_destroy` 793-796、`_is_destroyed_window_error` 804-816（與 173-185 逐字相同）、`show_singleton` 818-851、`sync_open_font_size` 854-872（P2-4，不動） |

七組 `__enter__/__exit__` 完全相同：`__enter__` 回傳 `self`，`__exit__(exc_type, exc, _tb)` 呼叫 `self.Destroy()` 並回傳 `None`，所以例外會往外傳。真正的 wxPython 4 已經讓 `wx.Dialog` 擁有同樣的 context manager（程式碼對 `wx.FileDialog`、`wx.DirDialog`、`wx.MessageDialog` 就是依賴它），但所有測試 stub 都沒有。目前沒有任何測試呼叫這些類別真正的 `__enter__/__exit__`；gui 與字典管理對話框的測試都以 fake 取代對話框。

### Singleton 邏輯（設定對話框）

`show_singleton`（兩份相同流程）：

1. （僅 `DotExpressSettingsDialog`）若有給 `initial_category` 且不在 `category_classes` 中，先丟 `ValueError("initial_category is not registered")`，此時尚未讀取已開啟的實例。
2. 若 `cls._instance` 不是 `None`：呼叫 `Iconize(False)`，然後（僅 `DotExpressSettingsDialog`，且有給 `initial_category` 時）`select_category(initial_category)`，再 `Raise()`、`SetFocus()`，並回傳該實例。
3. 若第 2 步丟出 `ReferenceError`、`RuntimeError` 或 `wx.PyDeadObjectError`：若 `_is_destroyed_window_error(error)` 為 false 就重新丟出（slot 保留舊實例）；否則設 `cls._instance = None` 並往下走。其他例外類型直接往外傳。
4. 以轉送的關鍵字參數建立 `cls(parent, ...)`，把 `cls._instance` 設為它，再呼叫 `Show()` 並回傳。建構失敗（例如 `load_preprocessing_script` 的 `OSError`，由 `gui.on_open_text_processing` 捕捉）時 slot 不變。

`_is_destroyed_window_error(error)`：若是 `getattr(wx, "PyDeadObjectError", ())` 的實例則為 true；否則只有在 `ReferenceError` 或 `RuntimeError` 的小寫訊息包含 `"wrapped c/c++ object"`、`"has been deleted"`、`"already deleted"` 或 `"destroyed"` 時為 true。

`_destroy()`：若類別的 `_instance` 就是這個對話框（類別名稱寫死：`TextProcessingDialog._instance`、`DotExpressSettingsDialog._instance`），清除它；接著 `Destroy()`。由 `on_ok`（apply 成功後）、`on_cancel`，以及 `SettingsDialog._on_window_close` -> `on_cancel` 呼叫。

呼叫端：`gui.on_open_text_processing`（`gui.py:482`）與 `gui.on_open_settings`（`gui.py:893`）以關鍵字參數呼叫 `show_singleton`；`gui._set_view_font_size` 呼叫 `DotExpressSettingsDialog.sync_open_font_size`（讀 `cls._instance`）。測試會直接讀寫 `TextProcessingDialog._instance` 與 `DotExpressSettingsDialog._instance`，也會繼承 `DotExpressSettingsDialog` 並宣告自己的 `_instance = None`。

潛在問題：`except` tuple 直接寫 `wx.PyDeadObjectError`，而 `_is_destroyed_window_error` 用的是 `getattr(wx, "PyDeadObjectError", ())`。wxPython 4（Phoenix，鎖定 4.2.5）據信沒有定義 `PyDeadObjectError`（已刪除物件改丟 `RuntimeError`）。若是如此，在真 wx 上第 2 步發生任何例外時，評估 `except` 子句會變成 `AttributeError`，已死的實例永遠無法被取代。實務上 slot 不會留著已死的視窗：所有銷毀設定對話框的路徑都經過 `_destroy`，它會先清 slot；唯一的其他銷毀方式是關閉主視窗，而那會結束程式。設定測試的 stub 有定義 `PyDeadObjectError`，所以測試看不到這個問題。見決策 D1。

### 名稱驗證

`shared/name_validation.normalize_base_name(name, *, reserved_names=None)` 丟單純的 `ValueError`：

| 檢查（依序） | 訊息（英文，不是 msgid） |
| --- | --- |
| `not name or not name.strip()` | `Name cannot be empty.` |
| 任一字元小於 U+0020 | `Name contains invalid characters.` |
| （原始名稱）以 `" "` 或 `"."` 結尾 | `Name cannot end with a period or space.` |
| `len(name.strip()) > 32` | `Name cannot exceed 32 characters.` |
| strip 後不是合法的 Windows 檔名（`<>:"/\|?*`、`.`/`..`、結尾 `.`/空白、`CON`、`com1.txt` 等裝置名稱） | `Name contains invalid characters.` |
| strip 後 casefold 等於保留名稱 | `Name '<strip 後的名稱>' is reserved.` |

回傳 `name.strip()`（Python 的 `str.strip`，所以 U+3000 等 Unicode 空白也會被去掉）。呼叫端：`dictionaries/manager.normalize_dictionary_name`（保留 `{"default"}`；由 `create_dictionary`、`import_dictionary`、`rename_dictionary` 使用）、`documents/workspace.normalize_document_name`（無保留名稱；由 `save_document_package`、`load_document_package`、`load_text_document`、`gui._prompt_for_document_name` 使用），以及 `documents/importers/base.py:23`（以檔名主幹作為文件名稱）。

`dialog._normalize_dialog_name(candidate, normalizer, empty, length, invalid, reserved=None)`（`dialog.py:62-86`）自己重做前四項檢查，再呼叫 `normalizer(candidate.strip())`，遇到 `ValueError` 時猜原因：有給保留訊息且 strip 後名稱 casefold 等於 `"default"` 就給保留訊息；`"exceed" in str(exc)` 就給長度訊息（不可達，長度已先檢查過）；否則給無效訊息。對話框的對應：

| 結果 | `DictionaryNameDialog`（括號內為 zh_TW 顯示） | `DocumentNameDialog`（括號內為 zh_TW 顯示） |
| --- | --- | --- |
| 空白 | `Please enter the dictionary name.`（請輸入字典名稱。） | `Please enter the document name.`（請輸入文件名稱。） |
| 太長 | `Dictionary name must be 1 to 32 characters.` | `Document name must be 1 to 32 characters.` |
| 控制字元、結尾空白／句點、Windows 不合法 | `Dictionary name is not a valid Windows file name.` | `Document name is not a valid Windows file name.` |
| 保留名稱 | `Dictionary name "{name}" is reserved.`，以 `DEFAULT_DICTIONARY_NAME`（`default`）格式化，不論使用者輸入的大小寫 | （不會發生；文件沒有保留名稱） |

`_on_ok(event)`（兩個對話框）：驗證 `name_ctrl.GetValue()`；若有訊息，`wx.MessageBox(message, _("Info"), wx.OK | wx.ICON_INFORMATION, parent=self)`，接著 `name_ctrl.SetFocus()`，不呼叫 `event.Skip()` 直接返回（對話框保持開啟）；否則 `name_ctrl.SetValue(normalized)` 並 `event.Skip()`。`_validate_name(candidate)` 只回傳訊息；只有測試呼叫它。七個訊息字串（字典四個、文件三個）每次呼叫都經 `_()`，所以每個字面值在 `dialog.py` 出現兩次。

名稱錯誤英文訊息（`str(exc)`）的使用者：

- `dictionaries/presenter.py` 的 `add`（第 105 行）與 `rename`（第 149 行）捕捉 `ValueError` 並呼叫 `view.show_info(str(exc))`：顯示未翻譯的英文（P0-6 已知怪異行為，由 `test_add_invalid_name_shows_untranslated_info` 與 `test_rename_invalid_name_shows_untranslated_info` 釘住）。真正的對話框會先驗證，所以從 app 無法觸發。`rename` 必須繼續捕捉所有 `ValueError`：前後有空白的 `" default"` 來源會通過 `is_default_dictionary`，而 `rename_dictionary` 會丟 `ValueError("Default dictionary cannot be renamed.")`。
- `presenter.import_from_file` 把所有 `ValueError`（包括名稱錯誤）都對應成 `Imported file must contain text, braille, and type headers.`（P0-6 怪異行為）。
- `documents/workspace.batch_import_documents` 把任何 loader 例外轉成 `BatchIssue(reason=str(exc))`，由 `FileIssuesDialog` 以 `<檔名>: <原因>` 顯示。匯入 `CON.txt` 或檔名主幹 40 字元的檔案會顯示英文名稱訊息。這個可以觸發。
- `load_workspace_documents` 對每個包捕捉所有例外（列入無效包清單；不顯示訊息）。
- `documents/workspace_service.rename_document` 丟自己的 `ValueError("A document cannot be renamed to its own name.")`，不是名稱錯誤。`gui._prompt_for_document_name` 對已驗證的對話框結果再 normalize 一次，不捕捉例外。

對錯誤文字的字串比對只有 `dialog.py:84`（`"exceed" in str(exc)`），外加 `dialog.py:82` 以 casefold 比對 `"default"` 的猜測。

### `ConvertingDialog`（`gui.py:108-121`）

標題 `_("Info")`，style `(wx.DEFAULT_DIALOG_STYLE & ~wx.CLOSE_BOX) | wx.STAY_ON_TOP`，一個 `wx.StaticText` `_("converting")` 放在垂直 `BoxSizer`，旗標 `wx.ALL | wx.ALIGN_CENTER_HORIZONTAL`、邊距 20，`finalize_dialog_layout`，`Bind(wx.EVT_CLOSE, self._on_close)`；`_on_close` 在 `evt.CanVeto()` 時否決。它是 `gui.py` import `finalize_dialog_layout` 的唯一原因。測試一律 patch `gui.ConvertingDialog`。

### 新程式碼必須能在其下運作的測試 stub

| Factory（`tests/wx_stub.py`） | `wx.Dialog` | 載入 |
| --- | --- | --- |
| `dialog_validation_stubs` | `type("Dialog", (), {})`；模組只有 4 個屬性，其他屬性會丟 `AttributeError` | `dialog`（isolate） |
| `speech_dialog_stubs` | 一般類別；`AutoSubmoduleModule`；evict `dialog`、`dictionaries`、`documents`、`wx` 等，但不 evict `ui`、`shared`、`i18n` | 以私有名稱載入 `dialog.py` |
| `dialog_display_stubs` | 一般類別；`AutoClassModule`（缺的屬性會變成類別）；全部 evict | 以私有名稱載入 `dialog.py` |
| `settings_dialog_stubs` | `RecordingWidget` 子類（遮蔽式 `__getattr__`）；定義 `PyDeadObjectError(RuntimeError)` | `settings.dialogs`（isolate） |
| `gui_frame_stubs` | `Widget` 子類；以 `_GUI_DIALOG_NAMES` 的 fake 取代整個 `dialog` 模組；定義 `PyDeadObjectError` | `gui` |

結論：繼承 `wx.Dialog` 或持有 `wx` 參照的基底，會綁定到最先 import 它的那個 stub，並觸發 `StubScope` 的洩漏檢查（speech scope 不 evict `ui`）。在模組層級存取 `Dialog`、`ListCtrl`、`Window`、`CommandEvent` 以外的任何 `wx` 屬性都會讓 `test_dialog_validation` 失敗。所以新基底必須是不 import `wx` 的單純 mixin。

## 設計

### 決策摘要

- `ui/dialog_base.py` 不依賴 wx、不依賴 gui（4 空白縮排）。只 import 標準函式庫、`i18n._` 與 `shared.name_validation`。基底是沒有 `__init__`、`__new__`、`__slots__` 或 metaclass 的單純 mixin，並放在基底清單最前面（`class X(Mixin, wx.Dialog)`），因此能與真 wx 的 sip 類別及所有 stub 基底組合。
- 基底唯一需要的 wx 呼叫（名稱錯誤的訊息框）是一個 hook，在 `dialog.py` 實作一次；唯一需要的 wx 值（dead-object 例外類型）是一個類別屬性，在 `settings/dialogs.py` 設定。
- `NameValidationError` 繼承 `ValueError`，並以英文訊息作為唯一參數，所以所有既有的 `except ValueError` 與所有使用 `str(exc)` 的地方行為都與以前完全相同。名稱對話框以外的使用者不需修改。

### `NameValidationError`（`shared/name_validation.py`）

```python
NameValidationCode = Literal["empty", "invalid", "too_long", "reserved"]


class NameValidationError(ValueError):
    """``normalize_base_name`` rejected a name: ``code`` says why, ``str(error)`` is the English message."""

    def __init__(self, code: NameValidationCode, message: str) -> None:
        super().__init__(message)
        self.code = code
```

`normalize_base_name` 中每個 `raise ValueError(msg)` 改為 `raise NameValidationError(code, msg)`，訊息與順序不變：空白 -> `"empty"`；控制字元、結尾空白／句點與 Windows 不合法 -> `"invalid"`；長度 -> `"too_long"`；保留 -> `"reserved"`。`error.args == (message,)` 與以前相同。四個 code，依 4.3 節的要求；結尾空白／句點與 `"invalid"` 共用，因為所有使用者都把它當成無效，而它不同的英文訊息仍在 `str(error)` 中。不建立錯誤類別階層。

`dictionaries/manager.py`、`documents/workspace.py`、`documents/importers/base.py`、`dictionaries/presenter.py`、`documents/workspace_service.py` 與 `gui._prompt_for_document_name` 不需修改程式碼：它們的 normalize 函式透過相同路徑改丟 `NameValidationError`，而它們的處理器捕捉的是 `ValueError` 或 `Exception`。presenter 刻意保留 `except ValueError`（上面前後有空白的 default 重新命名情境需要它）。它們的測試會加上對類型與 `code` 的斷言。

### `ui/dialog_base.py`

```python
class ContextManagedDialog:
    """``with Dialog(...) as dialog:`` destroys the dialog on exit and never swallows an exception."""

    def __enter__(self: _DialogT) -> _DialogT:
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.Destroy()


@dataclass(frozen=True)
class NameDialogMessages:
    """Untranslated msgids (marked with ``N_`` where defined); translated when shown."""

    empty: str
    too_long: str
    invalid: str
    reserved: str | None = None   # may contain "{name}"
    reserved_name: str = ""       # value for "{name}"

    def message_for(self, code: str) -> str:
        if code == "empty":
            return _(self.empty)
        if code == "too_long":
            return _(self.too_long)
        if code == "reserved" and self.reserved is not None:
            return _(self.reserved).format(name=self.reserved_name)
        return _(self.invalid)


class NameDialogBase(ContextManagedDialog):
    """``_on_ok``/``_validate_name`` of a dialog with a ``name_ctrl`` text box.

    Subclasses set ``normalize_name`` (a staticmethod) and ``name_messages`` and implement
    ``_show_name_error``.
    """

    name_messages: ClassVar[NameDialogMessages]

    @staticmethod
    def normalize_name(name: str) -> str:
        raise NotImplementedError

    def _check_name(self, candidate: str) -> tuple[str | None, str | None]:
        try:
            return self.normalize_name(candidate), None
        except NameValidationError as error:
            code = error.code
        except ValueError:
            code = "invalid"
        return None, self.name_messages.message_for(code)

    def _validate_name(self, candidate: str) -> str | None:
        return self._check_name(candidate)[1]

    def _on_ok(self, event) -> None:
        normalized, message = self._check_name(self.name_ctrl.GetValue())
        if message:
            self._show_name_error(message)
            self.name_ctrl.SetFocus()
            return
        self.name_ctrl.SetValue(normalized)
        event.Skip()

    def _show_name_error(self, message: str) -> None:
        raise NotImplementedError


class SingletonDialogMixin:
    """At most one open dialog per class; ``show_singleton`` raises it or builds a new one.

    The open dialog lives in the class's own ``_instance`` (read through ``cls.__dict__``,
    so a subclass never sees its parent's dialog).
    """

    dead_window_error_types: ClassVar[tuple[type[BaseException], ...]] = ()

    @classmethod
    def _raise_existing(cls, prepare=None):
        instance = cls.__dict__.get("_instance")
        if instance is None:
            return None
        try:
            instance.Iconize(False)
            if prepare is not None:
                prepare(instance)
            instance.Raise()
            instance.SetFocus()
            return instance
        except (ReferenceError, RuntimeError, *cls.dead_window_error_types) as error:
            if not cls._is_destroyed_window_error(error):
                raise
            cls._instance = None
            return None

    @classmethod
    def _show_new(cls, instance):
        cls._instance = instance
        instance.Show()
        return instance

    def _destroy(self) -> None:
        owner = type(self)
        if owner.__dict__.get("_instance") is self:
            owner._instance = None
        self.Destroy()

    @classmethod
    def _is_destroyed_window_error(cls, error: BaseException) -> bool:
        if isinstance(error, cls.dead_window_error_types):
            return True
        if not isinstance(error, (ReferenceError, RuntimeError)):
            return False
        message = str(error).lower()
        return (
            "wrapped c/c++ object" in message
            or "has been deleted" in message
            or "already deleted" in message
            or "destroyed" in message
        )
```

為何名稱檢查直接以原始文字呼叫 normalizer：`normalize_base_name` 本來就以相同順序、對相同的原始文字做了對話框的四項預檢，然後才 strip，所以 `normalizer(candidate)` 與舊的「預檢後再 `normalizer(candidate.strip())`」得到相同的正規化名稱與相同的失敗檢查。以一次性腳本比較舊 `_normalize_dialog_name` 與新對應，跑 3,431 個產生的名稱（15 個關鍵字元組成的所有長度 3 以內字串，加上裝置名稱、三種大小寫的 `default`、31-34 字元名稱、U+3000/U+00A0/U+0085 填充），兩個對話框的訊息與正規化名稱皆無差異。`except ValueError` 的 fallback 保留舊的捕捉範圍：normalizer 丟出的其他 `ValueError` 仍代表「無效」。

### `dialog.py`

- `from ui.dialog_base import ContextManagedDialog, NameDialogBase, NameDialogMessages`。
- `AddSymbolDialog`、`InvalidWorkspaceFilesDialog`、`FileIssuesDialog`、`SpeechSymbolsDialog`、`DictionaryManagementDialog` 改為 `class X(ContextManagedDialog, wx.Dialog)` 並拿掉各自的 `__enter__/__exit__`。其他部分不變。
- 兩個名稱對話框的私有 wx 基底：

```python
class _NameDialog(NameDialogBase, wx.Dialog):
	def _show_name_error(self, message: str) -> None:
		wx.MessageBox(message, _("Info"), wx.OK | wx.ICON_INFORMATION, parent=self)
```

- `DictionaryNameDialog(_NameDialog)` 設 `normalize_name = staticmethod(normalize_dictionary_name)` 與 `name_messages = NameDialogMessages(empty=N_("Please enter the dictionary name."), too_long=N_("Dictionary name must be 1 to 32 characters."), invalid=N_("Dictionary name is not a valid Windows file name."), reserved=N_('Dictionary name "{name}" is reserved.'), reserved_name=DEFAULT_DICTIONARY_NAME)`。`DocumentNameDialog(_NameDialog)` 設 `normalize_document_name` 與它的三個訊息（沒有保留訊息）。兩者拿掉 `_on_ok`、`_validate_name`、`__enter__`、`__exit__`。建構子、`get_dictionary_name`、`get_document_name` 與 `_apply_initial_name` 不變。
- 刪除 `_normalize_dialog_name`；拿掉 `MAX_DICTIONARY_NAME_LENGTH` 的 import（常數留在 `dictionaries/manager.py`，此後沒有使用者；見範圍外）。
- 新增 `ConvertingDialog`，類別本體原樣複製（兩個檔案都用 tab）。

### `settings/dialogs.py`

```python
_DEAD_WINDOW_ERROR_TYPES = tuple(
    error_type for error_type in (getattr(wx, "PyDeadObjectError", None),) if error_type is not None
)


class TextProcessingDialog(SingletonDialogMixin, SettingsDialog):
    _instance: "TextProcessingDialog | None" = None
    dead_window_error_types = _DEAD_WINDOW_ERROR_TYPES
    ...
    @classmethod
    def show_singleton(cls, *, parent, script_path: Path | str) -> "TextProcessingDialog":
        existing = cls._raise_existing()
        if existing is not None:
            return existing
        return cls._show_new(cls(parent, script_path=script_path))
```

`DotExpressSettingsDialog(SingletonDialogMixin, MultiCategorySettingsDialog)` 做法相同，仍先做 `initial_category` 檢查，且只有在 `initial_category is not None` 時傳入 `prepare=lambda instance: instance.select_category(initial_category)`。兩者拿掉 `_destroy` 與 `_is_destroyed_window_error`；`on_ok`／`on_cancel` 仍呼叫 `self._destroy()`。`show_singleton` 的簽章不變。`sync_open_font_size` 不動（P2-4）。

### `gui.py`

移除 `ConvertingDialog`，改從 `dialog` import；移除 `finalize_dialog_layout` 的 import（沒有其他使用者）。`show_converting_dialog`／`close_converting_dialog` 不變。`tests/wx_stub.py` 在 `_GUI_DIALOG_NAMES` 加入 `"ConvertingDialog"`，讓 stub 的 `dialog` 模組提供它；測試繼續 patch `gui.ConvertingDialog`。

為何放 `dialog.py` 而非新的 `ui/` 模組：`dialog.py` 是 wx 對話框類別與 `finalize_dialog_layout` 的所在，且 gui 測試 scope 本來就整個取代它。新的、會 import wx 的 `ui/` 模組必須加入 gui scope 的 isolate 名單，也會破壞「P1 的 `ui/` 模組不依賴 wx」的慣例。

### 行為決策

- **D1（dead-window 例外類型，在 app 中觀察不到）。** mixin 以 `getattr` 取得 `PyDeadObjectError`（與 `_is_destroyed_window_error` 原本的做法一致），而不是在 `except` tuple 中直接寫 `wx.PyDeadObjectError`。wx 有定義該類型時（所有測試 stub）沒有任何改變。沒有定義時（據信：真正的 wxPython 4.2.5），在喚起既有對話框時發生的例外現在會依程式原意處理（已死 -> 重建；其他 -> 重新丟出原本的錯誤），而不是變成 `AttributeError`。這條路徑在 app 中無法到達（見現況）。被否決的替代方案：用 classmethod hook 延遲存取 `wx.PyDeadObjectError`，刻意保留 `AttributeError`。Windows 檢查列於下方。
- **D2（`_destroy` 的擁有者）。** `_destroy` 清的是 `type(self)` 的 slot，而非寫死的類別。對兩個正式類別而言是同一個類別；只有子類會不同，此時子類清的是它自己的 slot（也就是 `show_singleton` 設定的那個），而不是父類的。
- **D3（normalizer 的綁定）。** `normalize_name` 在類別定義時綁定，而非每次呼叫時以模組全域名稱查找。沒有任何地方 patch `dialog.normalize_dictionary_name` 或 `dialog.normalize_document_name`。
- **D4（翻譯時機）。** 七個名稱對話框訊息以 `N_()` 定義一次，顯示時以 `_()` 翻譯。同一個 catalog、同樣的文字、同樣的 msgid 集合（353）。

## 維持不變的部分

- 每一種名稱輸入下，使用者看得到的每一個字串（英文與 zh_TW）；保留訊息不論輸入大小寫都仍顯示 `default`。
- `_on_ok` 的順序：訊息框、然後焦點、不 `Skip`；或 `SetValue(normalized)` 然後 `Skip`。
- 每個名稱錯誤的 `str()` 與 `args`；每個 `except ValueError` 與 `except Exception` 處理器；presenter 的未翻譯 info 文字；匯入時的 header 對應；檔案問題的原因。
- `show_singleton` 的呼叫順序（`Iconize(False)`、[`select_category`]、`Raise`、`SetFocus`）、在 `Show` 之前設定 slot、未註冊類別在讀取 slot 之前丟 `ValueError`、非 dead 錯誤重新丟出且 slot 保留、建構失敗時 slot 不變。
- `with` 語意：回傳同一個物件、`Destroy` 恰好一次、例外往外傳。
- `ConvertingDialog` 的建構與否決。
- `client/locales`、`scripts/`、`client/dictionaries/`、`client/documents/`、`client/conversion/` 沒有 diff。

## 測試計畫

特徵化優先：A 部分在任何正式程式碼修改之前提交，之後不再修改；唯一例外是在搬移 commit 中，把以 `gui.ConvertingDialog` 作為受測類別的測試改指向 `dialog.ConvertingDialog`。

### A. 特徵化（第 1 步）

1. `tests/test_dialog_validation.py`（dialog-validation stub）：
   - 凍結的 oracle：把現在的 `_normalize_dialog_name` 逐字複製到測試模組（改名，並註明它是 P2-1 之前的參考版本）。對一個產生的語料（同上），兩個對話框的 `_validate_name` 必須等於 oracle 的訊息；並抽樣經由 `_on_ok`（`SetValue`）檢查正規化後的名稱。
   - 明確表格，精確比對 zh_TW 文字：空字串、只有空白、只有 U+3000、控制字元、結尾空白、結尾句點、結尾 U+3000 可接受（`name　` -> `name`）、開頭空白可接受、32 與 33 字元、strip 後 33 字元、`a?b`、`CON`、`con.txt`、`..`、`default`/`Default`/`DEFAULT`（字典：顯示含 `default` 的保留訊息；文件：可接受）。
   - 兩個對話框的 `_on_ok`（以 `create=True` 把 `wx.MessageBox`、`wx.OK`、`wx.ICON_INFORMATION` patch 到 stub 上）：無效輸入恰好記錄 `MessageBox(message, "資訊", OK | ICON_INFORMATION, parent=dialog)`，然後 `SetFocus`，沒有 `SetValue`、沒有 `Skip`；`" name"` 記錄 `SetValue("name")` 然後一次 `Skip`，沒有訊息框。
   - 七個類別的 context manager（以 `object.__new__` 建立實例，`Destroy` 為 `Mock`）：`with` 回傳同一個物件；正常離開與區塊丟例外時 `Destroy` 各呼叫一次；例外往外傳；`__exit__` 回傳 `None`。
2. 新增 `tests/test_name_validation.py`：`normalize_base_name` 的每一項檢查及其精確英文訊息與 `ValueError` 類型、回傳的 strip 後名稱、保留名稱的 casefold、`str(error)`/`args`。
3. `tests/test_settings_dialogs.py`，兩個 singleton 類別都要：新實例路徑（轉送關鍵字參數、`Show` 之前設定 slot、回傳實例）；既有實例路徑的呼叫順序，有與沒有 `initial_category`；已死實例在 `PyDeadObjectError`、含四種片語之一的 `RuntimeError`、以及 `ReferenceError("... has been deleted")` 時重建；不含片語的 `ReferenceError` 與無關的 `RuntimeError` 重新丟出且 slot 保留；`_destroy` 只清自己的實例且一定呼叫 `Destroy`；兩個類別的 slot 互相獨立；未註冊類別在碰觸 slot 之前丟錯；建構子 `OSError` 時 slot 維持 `None`。
4. `ConvertingDialog`：建構參數（parent、title、style 值）、label、sizer 旗標與邊距、`EVT_CLOSE` 綁定、只在 `CanVeto()` 時否決；搬移前在 gui stub 下對 `gui.ConvertingDialog` 執行（記錄 `wx.Dialog.__init__`）。

### B. 型別化錯誤（第 2 步）

`NameValidationError` 是 `ValueError`；每項檢查的 `code`；訊息不變；`normalize_dictionary_name`、`normalize_document_name` 與 importer 基底名稱丟出帶預期 code 的此錯誤；presenter 測試不改且維持綠燈。

### C. `ui/dialog_base.py`（第 3 步，新增 `tests/test_dialog_base.py`，不用 wx、不用 stub scope）

每個基底分別與 (a) 單純的 `type("Dialog", (), {})` 基底、(b) `wx_stub.RecordingWidget` 式的遮蔽基底組合，證明 MRO 與行為：`ContextManagedDialog` 語意；`NameDialogMessages.message_for` 對每個 code、缺保留訊息時的 fallback 與 `{name}` 格式化；以 fake normalizer 測 `NameDialogBase`（型別化 code、單純 `ValueError` -> 無效、`_on_ok` 呼叫順序）；`SingletonDialogMixin` 透過 `cls.__dict__` 隔離 slot（未宣告 `_instance` 的子類看不到父類的實例）、以自訂 `dead_window_error_types` 測喚起／重建／重新丟出路徑。一個 AST 守門測試斷言此模組不 import `wx`、`gui`、`dialog` 或 `settings`。

### D. 遷移（第 4-6 步）

不新增斷言；A 與 B 部分必須不改且維持綠燈。守門設定與它守護的變更在同一個 commit 更新：`_GUI_DIALOG_NAMES` 加入 `ConvertingDialog`。

新測試的確切數量由 plan 決定。

## 遷移步驟（每一步是一個綠燈 commit）

1. `test: characterize dialog lifecycle, name validation and singletons`（A 部分）。
2. `refactor: raise typed NameValidationError for invalid names`（B 部分）。
3. `refactor: add wx-free dialog base mixins`（C 部分；模組尚未被使用）。
4. `refactor: use dialog base mixins in dialog.py`（七個 context manager、兩個名稱對話框、刪除 `_normalize_dialog_name`）。
5. `refactor: use SingletonDialogMixin in settings dialogs`。
6. `refactor: move ConvertingDialog into dialog.py`。

## 驗收標準

1. Linux 上的路線圖驗證：`cd client && python -m unittest tests.test_dialog_validation tests.test_dialog_display tests.test_settings_dialogs -v` 通過。
2. 也必須綠燈：`tests.test_name_validation tests.test_dialog_base tests.test_dictionary_manager tests.test_document_workspace tests.test_dictionary_presenter tests.test_dictionary_management_dialog tests.test_speech_symbols_dialog tests.test_gui_document_flows tests.test_workspace_service tests.test_i18n tests.test_removed_dead_code tests.test_wx_stub`。
3. 完整測試：818 + 新測試，`failures=1`（只有 P2-5）、`errors=0`、`skipped=9`。shuffle harness（`$SP/shuffle_harness.py`，seed 0-19）每個 seed 都只有同一個失敗；`test_dialog_validation`、`test_dialog_display`、`test_speech_symbols_dialog`、`test_dictionary_management_dialog`、`test_settings_dialogs` 與 `test_gui_document_flows` 單獨執行，以及與 `test_dialog_base` 兩兩以兩種順序執行時也都通過。
4. `grep -n "def __enter__\|def __exit__\|_normalize_dialog_name\|\"exceed\"" client/dialog.py` 無輸出；`grep -n "_is_destroyed_window_error\|def _destroy" client/settings/dialogs.py` 無輸出；`grep -n "raise ValueError" client/shared/name_validation.py` 無輸出；`grep -n "class ConvertingDialog\|finalize_dialog_layout" client/gui.py` 無輸出；`grep -rn "in str(exc)" client --include=*.py --exclude-dir=tests` 無輸出。
5. msgid 掃描：原始碼 353 個 msgid、同樣 4 個只在 pot 的孤兒、沒有只在原始碼的項目；`git diff main --stat -- client/locales scripts` 為空。
6. `git diff main --stat -- client/dictionaries client/documents client/conversion client/about.py client/ui` 只列出 `client/ui/dialog_base.py`（新檔）。
7. `client/ui/dialog_base.py` 通過 AST 守門（不 import `wx`、`gui`、`dialog`、`settings`）。

## 風險

- **真 wx 上的 mixin（此處無法執行）。** 把單純 mixin 放在 sip 類別之前是 wxPython 的標準用法；這些 mixin 不定義 `__init__`、`__new__`、`__slots__` 或 metaclass。只在 Linux 上以 stub 驗證。
- **Stub scope 的類別身分。** 若 `shared.name_validation` 被 evict 並重新 import，而 `ui.dialog_base` 仍持有舊類別，`except NameValidationError` 會漏接，所有錯誤都會顯示無效訊息。在目前的 evict 規則下不會發生（模組只有在該 scope 內首次 import 時才會被 evict，而 `ui.dialog_base` 自己就會 import `shared.name_validation`），且 shuffle 順序下的 oracle 測試會抓到。
- **被移除名稱的隱藏呼叫者。** `_normalize_dialog_name`、`_is_destroyed_window_error` 與各類別的 `__enter__/__exit__` 在被修改的檔案之外沒有呼叫者（grep）；`_validate_name`、`_destroy`、`show_singleton` 保留原名。
- **D1 改變了真 wx 上一條無法到達的路徑**；列入 Windows 驗證。

## 保留的既有怪異行為（以測試釘住，不修正）

1. 字典 presenter 在新增／重新命名遇到名稱錯誤時顯示 `str(exc)`（未翻譯的英文）（P0-6）。從真正的對話框無法觸發。日後可把 `NameValidationError.code` 對應到對話框訊息來修正；那會改變 presenter 的輸出，所以是另一個任務。
2. presenter 把匯入時的名稱錯誤對應成 CSV header 訊息（P0-6）。
3. 匯入的檔案問題原因對 zh_TW 使用者顯示英文名稱訊息（例如 `CON.txt: Name contains invalid characters.`）。可觸發。歸入 P1 的在地化缺陷（P1 審查清單的 defect 4）；型別化的 `code` 讓修正變得很小。
4. 保留名稱訊息永遠顯示 `default`，即使使用者輸入的是 `Default` 或 `DEFAULT`。
5. `_is_destroyed_window_error` 把不含四種片語之一的 `ReferenceError`（例如 `weakly-referenced object no longer exists`）視為未死。

## Windows 驗證待辦

- 在建置機器上執行 `python -c "import wx; print(wx.version(), hasattr(wx, 'PyDeadObjectError'))"`（預期 `4.2.5 ... False`；確認 D1 的前提）。
- 打包版：開關清單中的每個對話框；新增／重新命名字典與新增／重新命名文件時，以空白、33 字元、`CON` 與（字典）`Default` 名稱輸入，顯示相同的 zh_TW 訊息且對話框保持開啟；設定與文字處理開兩次會喚起既有視窗，關閉後可重開；長時間轉換時出現轉換中對話框且無法以 Alt+F4 關閉。不需截圖（無視覺變化）。
- PyInstaller 經由 `dialog.py` 與 `settings/dialogs.py` 的靜態 import 收進 `ui/dialog_base.py`（讀碼確認，未執行）。

## 範圍外

- 統一兩個名稱對話框的建構子（標題處理與 `SetValue` 時機不同）或 `get_*_name` 存取子。
- `AddSymbolDialog` 與 `dictionaries/entries.py` 中已翻譯的領域訊息（4.3 節備註）。
- `sync_open_font_size` 與反向探針（P2-4）；讓設定對話框成為 context manager。
- 修改任何 presenter 或 importer 的錯誤處理，或移除 `MAX_DICTIONARY_NAME_LENGTH`（本任務後無使用者；死碼後續事項）。
- 收斂 `tests/wx_stub.py` 中的 stub profile。
