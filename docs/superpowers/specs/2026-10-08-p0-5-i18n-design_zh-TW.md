# 共用 i18n 模組（P0-5）設計

## 目標

讓 client 只用一個地方設定翻譯與尋找打包資源：新增 `client/i18n.py`，提供 `_`、`N_` 與 `resource_path`。目前各自建立 `gettext` catalog 或各自定義 `resource_path()` 的模組，都改成從這裡 import。這是 roadmap 任務 P0-5（`storage/refactor.md` 第 6.1 節；問題記錄在第 5 節「gettext 初始化 + `resource_path()` 複製 5 份」）。

範圍：roadmap 該列點名的五份第一方副本。衍生自 NVDA 的 `client/braille/tables/__tables.py` 也有一份，但依決策排除，維持不動（見「已知問題／後續工作」）。

對使用者的影響：不論從打包版或原始碼執行，都完全不變。每個字串的 zh_TW 翻譯和每個資源路徑都維持原樣。`scripts\generate-pot.bat` 擷取出的 msgid 集合維持不變。

## 方法與基準（2026-10-08 於 `refactor/p0-5-i18n`、HEAD `78a2eb2` 驗證，P0-1 至 P0-4 已合併）

1. 對 `client/`（`--include=*.py`）、`scripts/` 與建置腳本執行 `grep -rn "gettext\|resource_path\|_MEIPASS\|N_(\|builtins\|\.install(\|translation("`，並逐一閱讀結果。
2. 閱讀 `client/tests/wx_stub.py`（`StubScope` 與 eviction 策略），以及所有讀取或替換模組 `_` 的測試。
3. 以 AST 掃描（用完即丟的腳本，不提交）收集 `client/**/*.py`（排除 `tests/` 與 `.venv/`）中每個 `_(...)` 與 `N_(...)` 呼叫的第一個字串參數，再與 `client/locales/dotexpress.pot` 的 msgid 及編譯後的 zh_TW catalog 比對。
4. 從原始碼 import `braille.tables`，檢查 `__tables.py` 實際使用的 localedir。

基準（venv Python，在 `client/` 執行）：

- `python -m unittest discover -s tests` 結果為 `Ran 466 tests`、`FAILED (failures=1, skipped=7)`。唯一的失敗是已知的 P2-5 案例（`test_conversion_service ... test_translate_with_language_does_not_duplicate_existing_spaces_around_math`）。
- Roadmap 指令 `python -m unittest tests.test_dialog_validation tests.test_dialog_display -v` 結果為 `Ran 13 tests`、`OK`（8 + 5）。
- `tests.test_config` 25 個 OK、`tests.test_client_init` 7 個 OK、`tests.test_import_fixtures` 5 個 OK。Roadmap 提到的 `lxml` 依賴已裝在 venv。
- AST 掃描：原始碼共 357 個不重複的 msgid，`dotexpress.pot` 也是 357 個，兩個集合相同。除了一個以外都已在 zh_TW `.mo` 中翻譯。例外是 `"Close"`：它在 `dotexpress.po` 的 `msgstr` 是空的。這是既有的缺漏，不在本次範圍。
- 這台主機沒有 `xgettext` 和 `msgfmt`。

## 現況

### 清單

| 位置 | 行號 | `resource_path` 基準（原始碼執行） | 打包處理 | 實際 localedir（原始碼） | 語言 | 求值時機 |
| --- | --- | --- | --- | --- | --- | --- |
| `client/gui.py`（tab） | 147-152 `resource_path`、155-163 catalog | `Path(__file__).resolve().parent` = `client/` | 檢查 `sys.frozen` 與 `sys._MEIPASS`，得到 `_MEIPASS` | `client/locales` | `["zh_TW"]`、`fallback=True` | import 時。執行期也會呼叫 `resource_path`：`resource_path(".")`（558，SimBraille 字型）與 `resource_path("data")`（755，`ConversionRequest.data_dir`）。 |
| `client/dialog.py`（tab） | 31-37、39-47 | `parent` = `client/` | 同上 | `client/locales` | 同上 | import 時。`resource_path` 只用來算 localedir。 |
| `client/settings/dialogs.py`（4 空白） | 31-37、39-47 | **`parents[1]`** = `client/`（此檔多一層目錄） | 同上 | `client/locales` | 同上 | import 時。只用來算 localedir。 |
| `client/dictionaries/entries.py`（tab） | 11-12 `_resource_path`、15-23 | `parents[1]` = `client/` | **沒有** | `client/locales` | 同上 | import 時。模組常數 `ENTRY_TYPE_OPTIONS`/`ENTRY_TYPE_LABELS` 在 import 時呼叫 `_()`。 |
| `client/about.py`（tab） | 1-13 | 直接寫 `Path(__file__).resolve().parent / "locales"` | **沒有** | `client/locales` | 同上 | import 時。`longName`、`description`、`copyright`、`aboutMessage` 在 import 時翻譯。 |
| `client/braille/tables/__tables.py`（tab，衍生自 NVDA、手動改寫） | 13-32 | `parent.parent` = **`client/braille/`** | 同上 | **`client/braille/locales`，這個目錄不存在** | 同上 | import 時（約 690 個 `addTable(..., _("..."))` 呼叫）。 |

六處（範圍內五處加上 `__tables.py`）都使用相同的 domain `"dotexpress"`、相同的固定語言清單 `["zh_TW"]` 與 `fallback=True`。沒有任何一處讀取 `LANG`/`LANGUAGE`/`config` 來決定介面語言，所以語言與環境無關。它們都只在模組第一次被 import 時建立一次 catalog。

Roadmap 只算了五份。`storage/refactor.md` 把 `__tables.py` 視為「vendored」而排除。`scripts/sync-nvda.py` 不會重新產生它。它是手動改寫的 NVDA 點字表清單（P0-3 對 `braille/tables` 也有相同記錄），上游 NVDA 使用 builtins `_`。**決策（orchestrator）：** 本次重構不修改衍生自 NVDA 的程式碼，所以 `__tables.py` 不納入 P0-5。它保留自己的設定，其錯誤（下一節）記錄為後續工作。

### 發現

- **`parents[1]` 的差異只是目錄深度的修正，基準目錄其實相同。** `settings/dialogs.py` 與 `dictionaries/entries.py` 位於 `client/` 下一層，所以 `parents[1]` 與 `gui.py` 的 `parent` 都指向 `client/`。只要有一個以 `client/i18n.py` 為基準的 `resource_path`，就不需要這個修正。
- **打包版。** `scripts/build-dotexpress.bat` 執行 `pyinstaller --onefile ... --add-data "locales;locales" --add-data "data;data" ... gui.py`。三處明確檢查 `sys._MEIPASS`。`about.py` 與 `dictionaries/entries.py` 沒有檢查，但打包版仍然找得到 catalog：PyInstaller 會把打包進 PYZ 封存的模組的 `__file__` 設為 `sys._MEIPASS/<套件路徑>.pyc`，所以 `Path(__file__).resolve().parent`（或 `parents[1]`）本來就等於 `_MEIPASS`。在打包版中兩種基準一致。`i18n.py` 保留明確的 `_MEIPASS` 分支，因為那是 PyInstaller 文件記載的做法，也是多數位置採用的寫法。
- **`__tables.py` 的潛在錯誤（本次不修正）。** 它的 `resource_path` 只往上到 `client/braille/`。從原始碼執行時找不到 catalog，但因為 `fallback=True` 而不報錯，所以每個 `BrailleTable.displayName` 都維持英文。已確認：`resource_path("locales")` 是 `/workspace/DotExpress/client/braille/locales`，這個目錄不存在，且 `listTables()[0].displayName` 是 `'Afrikaans grade 1'`。打包版走 `_MEIPASS` 分支找得到 catalog，所以名稱是中文（`'南非文一級'`）。唯一的使用者是 `settings/dialogs.py:623-625`，它會再呼叫一次 `_(table.displayName)`，所以設定對話框顯示的名稱在兩種模式下都是中文。不過 `listTables()` 依 `strxfrm(displayName)` 排序，所以 196 個輸出點字表的順序在原始碼執行（英文順序）與打包版（翻譯後名稱的順序）之間不同。
- **沒有 builtins `_`。** 沒有任何程式呼叫 `gettext.install()` 或設定 `builtins._`（`builtins` 只出現在 `tests/test_main_demo.py` 替換 `print`，以及 NVDA 子模組中）。每個模組都使用模組全域的 `_`。
- **測試如何使用 `_`。** `tests/test_dialog_display.py`（45-50、60-65、76-85 行）把 `dialog_module._` 換成某個 dict 的 `.get`，之後再還原。這行得通，是因為函式在被呼叫時才查找模組全域的 `_`。`tests/test_gui_document_flows.py` 呼叫 `gui._("...")` 來產生預期字串（207、230-231、296-300、412-413、463、493-494 行）。`tests/test_dialog_validation.py` 驗證 `dialog.py` 產生的真實 zh_TW 訊息。`tests/test_config.py` 與 `tests/test_import_fixtures.py` 直接用 `gettext` 開啟 `.mo` 檔，不經過任何模組。沒有測試讀取或替換任何模組的 `resource_path`、`LOCALE_DOMAIN`、`LOCALE_LANGUAGES` 或 `_translation`。
- **目前還沒有 `N_`。** `gui.py:167-217` 有一個 `_MENU_TRANSLATION_MARKERS`，是由 48 個 `_("...")` 呼叫組成的 tuple，唯一用途是讓 `xgettext` 看得到在別處動態翻譯的標籤（`ui/action_menu.py` 的選單標籤、檔案萬用字元等）。沒有程式讀取這個 tuple。
- **擷取腳本。** 檔名是 `scripts/generate-pot.bat`（連字號）。`AGENTS.md`、`readme.md` 與較早的 plan 寫的是 `generate_pot.bat`。它執行 `xgettext --language=Python --keyword=_ --files-from=<client 下所有 *.py，排除 .venv 與 tests> --output=locales\dotexpress.pot`。`N_` 不在 xgettext 預設的 Python keyword 中，必須明確加上。
- **其他以 `__file__` 為基準的路徑**（`app_paths.get_application_root`，可寫入資料放在執行檔目錄；`conversion/mathcat_adapter.py:17`，MathCAT 資源；`main.py` 的 `BASE_DIR`，只用於示範）與 gettext 無關，不在範圍內（見「範圍外」）。

### 與 `StubScope`（P0-4）的互動

`i18n.py` 只 import 標準函式庫（`gettext`、`sys`、`pathlib`），從不參照 `wx`，所以 `StubScope` 的洩漏防護（R4）不會因它觸發，它也不需要列入任何 `isolate` 清單。依照各 scope 的 eviction 策略，它可能在 scope 內被 import 後留在快取中（`evict_nothing`、speech roots），也可能之後被移除（`load_display_dialog` 的 `evict_everything`）。被移除不會造成問題：已載入的模組保有它 import 進來的 `_` bound method，之後再 import 時會從相同檔案建立等效的 catalog。任何測試都不得依賴不同測試模組之間 `i18n` 模組物件的同一性。

## 設計

### 決策：一個無狀態模組，使用端在 import 時綁定 `_`

考慮過的方案：

1. **像 NVDA 一樣用 `gettext.install()`（builtins `_`）。** 不採用。這會掩蓋漏掉的 import，讓 `_` 變成整個行程的全域狀態（替換 `dialog_module._` 的測試必須改成替換 `builtins`），也會改變每個模組解析 `_` 的方式。
2. **使用端透過模組呼叫 `i18n._(...)`。** 不採用。xgettext 在呼叫處將看不到 `_(`（keyword 必須改成 `i18n._`），替換 `<module>._` 的測試也會失效。
3. **採用：`from i18n import _`（需要時一併 import `N_`、`resource_path`）。** 每個使用端仍有一個模組全域的 `_`，它與 `i18n._` 是同一個 bound method。呼叫處、xgettext keyword，以及現有的 `dialog_module._` / `gui._` 測試寫法都不用改。

### `client/i18n.py`

4 空白縮排（新檔，依 `AGENTS.md`）、ASCII、只用標準函式庫。名稱即契約，plan 只能調整私有細節。

```python
LOCALE_DOMAIN = "dotexpress"
LOCALE_LANGUAGES = ("zh_TW",)
CLIENT_ROOT = Path(__file__).resolve().parent

def resource_path(relative_path: str) -> Path:
    # 打包版（PyInstaller）：Path(sys._MEIPASS) / relative_path
    # 其他情況：             CLIENT_ROOT / relative_path
    ...

def load_translation(localedir: Path | None = None,
                     languages: Sequence[str] = LOCALE_LANGUAGES) -> gettext.NullTranslations:
    # gettext.translation(LOCALE_DOMAIN, localedir=str(localedir or resource_path("locales")),
    #                     languages=list(languages), fallback=True)
    ...

_translation = load_translation()
_ = _translation.gettext

def N_(message: str) -> str:
    """Mark a string for extraction without translating it."""
    return message
```

- **`resource_path`** 完全沿用現行規則：只有在 `getattr(sys, "frozen", False)` **且** `hasattr(sys, "_MEIPASS")` 時才用 `_MEIPASS`，否則用 `i18n.py` 所在目錄（從原始碼執行時是 `client/`，打包時如前所述是 `_MEIPASS`）。判斷在**呼叫時**進行，所以測試可以用 `patch.object(sys, ..., create=True)` 替換 `sys.frozen`/`sys._MEIPASS`。
- **Import 時機。** catalog 只在 `i18n` 第一次被 import 時載入一次，localedir 取當下的 `resource_path("locales")`。這與現況相同：每個位置都在 import 時載入，而 PyInstaller 會在任何應用程式碼執行前設好 `sys.frozen`/`_MEIPASS`。使用端在模組層級翻譯的常數（`ENTRY_TYPE_OPTIONS`、`about.aboutMessage`）仍在那些模組被 import 時求值，求值順序不變。
- **語言。** 與現況相同，固定 `("zh_TW",)` 加 `fallback=True`，不跟隨 `LANG`/`LANGUAGE`。catalog 不存在或無法讀取時不會拋出例外，`_` 會直接回傳 msgid。讓介面語言可設定不在範圍內。
- **`load_translation`** 設為公開，讓測試可以用暫存目錄驗證 fallback 路徑。正式程式只在 `i18n` 內呼叫它一次。
- **替換規則。** 測試繼續替換使用端的全域名稱（`dialog_module._ = ...`）。使用端 import 之後再替換 `i18n._`，不會影響該使用端。模組 docstring 會寫明這點。
- **不提供 `ngettext`/`pgettext`**，因為沒有程式使用（YAGNI）。不定義 `__all__`，因為使用端都明確 import 名稱。

### `N_` 與 `scripts/generate-pot.bat`

- `scripts/generate-pot.bat`：把 `--keyword=_` 改為 `--keyword=_ --keyword=N_`，其他都不變（檔案清單、輸出路徑，不加 `--from-code`，不加 `--add-comments`）。
- `gui.py`：`_MENU_TRANSLATION_MARKERS` 的 48 個項目從 `_("...")` 改為 `N_("...")`。tuple 與其註解留在 `gui.py`。把這些標記搬到 `ui/action_menu.py` 的標籤旁屬於 O-1 / P1-2（以 action 為 key 的選單），不在這裡做。tuple 的值會變成未翻譯的字串，而沒有程式讀取它。這樣 `N_` 在新增 keyword 的同一個 commit 就有實際的呼叫者，兩項變更不會單獨存在。
- **「.pot 不變」的意思。** 擷取出的 **msgid 集合**相同（因此 `dotexpress.po` 中每組 msgid/msgstr 也相同）：以 keyword `_` 與 `N_` 進行 AST 掃描，變更前後都得到同樣的 357 個字串。xgettext 依字串內容決定格式旗標（`python-format`、`python-brace-format`），與 keyword 無關，所以旗標也相同。下次執行腳本時，`#:` 來源參照與 `POT-Creation-Date` **會**改變（每個遷移過的檔案行號都會位移）。與 P0-2 相同，本任務不手動修改 `dotexpress.pot`、`dotexpress.po` 或 `.mo`。這些參照會在下次於 Windows 執行 `generate-pot.bat` 時更新。

### 各模組遷移

每個使用端刪除自己的 `resource_path`/`_resource_path`、`LOCALE_DOMAIN`、`LOCALE_LANGUAGES`、`_translation` 與 `_ = ...`，以及因此不再使用的 import（`gettext`；`sys`/`Path` 只在沒有其他用途時才刪），然後與其他第一方 import 放在一起加入 `i18n` 的 import。縮排維持各檔原樣。

| 模組 | 從 `i18n` import | 不再使用的 import | 備註 |
| --- | --- | --- | --- |
| `gui.py` | `_`、`N_`、`resource_path` | `gettext`（`sys` 與 `Path` 仍在使用） | `gui._` 與 `gui.resource_path` 仍是模組屬性，`test_gui_document_flows` 需要 `gui._`。標記改用 `N_`。 |
| `dialog.py` | `_` | `gettext`、`sys`（`Path` 仍用於 429、690 行） | `dialog.resource_path` 消失。模組外沒有呼叫者（已確認）。 |
| `settings/dialogs.py` | `_` | `gettext`、`sys`（`Path` 仍用於 131 行） | `parents[1]` 的特殊寫法消失。625 行的 `_(table.displayName)` 保留（見下文）。 |
| `dictionaries/entries.py` | `_` | `gettext`（`Path` 仍用於函式簽名） | 透過委派取得 `_MEIPASS` 處理，打包版結果相同。 |
| `about.py` | `_` | `gettext`、`Path` | `client_init.py` 也 import `about`。`i18n` 除了標準函式庫外不增加任何依賴。 |

`i18n` 不 import 任何 client 模組，所以這次變更不可能造成 import 循環。

`client/braille/tables/__tables.py` 不遷移（見「範圍」）。它的 gettext 區塊、`resource_path`，以及透過不存在的 `client/braille/locales` 查找 catalog 的行為都維持原樣。因此沒有任何行為改變，從原始碼執行時也一樣。

### Commit 順序（plan 會再細化）

1. `client/i18n.py` 與 `client/tests/test_i18n.py`（先寫核心測試並確認失敗）。
2. 遷移 `dialog.py`、`settings/dialogs.py`、`dictionaries/entries.py` 與 `about.py`。
3. 遷移 `gui.py`、標記改用 `N_`、在 `scripts/generate-pot.bat` 加上 `--keyword=N_`，並加入「沒有重複設定」的防護測試。

## 測試策略

新增 `client/tests/test_i18n.py`（4 空白、`unittest`、不用 `wx`，所以不需要 `StubScope`）。預計約 9 個案例：

1. 沒有 `frozen` 時，`resource_path` 回傳 `<client>/<relative>`，且 `resource_path("locales") / "zh_TW" / "LC_MESSAGES" / "dotexpress.mo"` 存在。
2. `sys.frozen = True` 且 `sys._MEIPASS = <tmp>`（以 `create=True` 替換）時，回傳 `<tmp>/<relative>`。
3. `sys.frozen = True` 但沒有 `_MEIPASS` 時，退回 client 根目錄（現行的 `and hasattr` 規則）。
4. `_("General") == "一般"` 且 `_("Startup Error") == "啟動錯誤"`（這些 msgid 已由 `test_config` 固定）。
5. 未知的 msgid 原樣回傳。
6. `load_translation(localedir=<空的暫存目錄>)` 回傳一個 `gettext` 為恆等函式的 `NullTranslations`，且不拋出例外。
7. `N_(s)` 回傳同一個物件 `s`，即使該 msgid 有翻譯也一樣（`N_("General") == "General"`）。
8. 語言不跟隨環境：以 `cwd=client/`、`LANGUAGE=en_US`、`LANG=C`、`LC_ALL=C` 啟動子行程，執行 `from i18n import _; print(_("General"))`，得到 `一般`（以 `PYTHONIOENCODING` 強制 UTF-8 輸出）。
9. 沒有重複設定：靜態掃描 `client/**/*.py`（排除 `tests/`、`.venv/`、`__pycache__/`、`i18n.py` 與範圍外的 `braille/tables/__tables.py`），找不到 `gettext.translation(`、`import gettext`、`_MEIPASS`、`def resource_path` 或 `def _resource_path`。所有遷移完成前它都會失敗，所以跟最後一個遷移 commit 一起提交。

既有測試是安全網，且不得修改：`test_dialog_validation`（透過 `dialog._` 驗證真實 zh_TW 訊息）、`test_dialog_display`（替換 `dialog_module._`）、`test_gui_document_flows`（`gui._`）、`test_settings_dialogs`、`test_speech_symbols_dialog`、`test_dictionary_management_dialog`、`test_dual_view_frame`、`test_wx_stub`、`test_config`、`test_client_init`、`test_import_fixtures`。

這裡無法執行擷取（沒有 `xgettext`）。改用「方法」一節的 AST 掃描代替：keyword 相同（`_`、`N_`），檔案集合也與 `generate-pot.bat` 相同。變更前後各執行一次，預期得到相同的 357 個 msgid，且兩者都等於 `.pot` 的 msgid 集合。

## 驗收條件

所有指令都在 `client/` 以 venv Python（`$PY`）執行。

1. **單一來源。** 在 repo 根目錄執行 `grep -rnE "gettext\.translation\(|^\s*import gettext|_MEIPASS|def _?resource_path|LOCALE_LANGUAGES" client --include=*.py | grep -v -e "/tests/" -e "/.venv/" -e "braille/tables/__tables.py"`，只會印出 `client/i18n.py` 中的行（目前會印出範圍內五個檔案的行）。`git diff main -- client/braille/tables/__tables.py` 沒有輸出。
2. **新測試。** `$PY -m unittest tests.test_i18n -v` 結果為 `OK`。
3. **Roadmap 指令。** `$PY -m unittest tests.test_dialog_validation tests.test_dialog_display -v` 結果為 `Ran 13 tests`、`OK`。
4. **相鄰測試不變。** `$PY -m unittest tests.test_gui_document_flows tests.test_settings_dialogs tests.test_speech_symbols_dialog tests.test_dictionary_management_dialog tests.test_dual_view_frame tests.test_wx_stub tests.test_config tests.test_client_init tests.test_import_fixtures -v` 結果為 `OK`，且 test id 與 `78a2eb2` 相同。
5. **完整套件。** `$PY -m unittest discover -s tests -v`：`Ran 466 + N tests`（N 為 `test_i18n` 的測試數）、`FAILED (failures=1, skipped=7)`，唯一的失敗是 P2-5 案例。排除含 `(test_i18n.` 的行後，排序過的 `<test id> ... <outcome>` 各行與基準完全相同。
6. **順序。** `$PY -m unittest tests.test_dialog_display tests.test_i18n tests.test_dialog_validation tests.test_gui_document_flows` 以及相反順序都是 `OK`（不依賴 `StubScope` eviction 前後 `i18n` 模組物件的同一性）。
7. **msgid 集合。** 變更後 AST 掃描得到 357 個 msgid，與變更前的集合以及 `client/locales/dotexpress.pot` 的 msgid 完全相同。`_MENU_TRANSLATION_MARKERS` 的 48 個項目全部是 `N_(...)` 呼叫。
8. **擷取腳本。** `scripts/generate-pot.bat` 含有 `--keyword=_ --keyword=N_`，其他行都沒有改變。
9. **範圍。** `git diff main --stat` 只涉及 `client/i18n.py`、`client/tests/test_i18n.py`、`client/gui.py`、`client/dialog.py`、`client/settings/dialogs.py`、`client/dictionaries/entries.py`、`client/about.py`、`scripts/generate-pot.bat` 與這些 spec/plan 文件。`.pot`/`.po`/`.mo` 都沒有變更。
10. **Windows（這台主機無法執行，交接時必須說明未經驗證）。** 執行 `scripts\generate-pot.bat`。與已提交的 `.pot` 相比，只能在 `#:` 參照行與 `POT-Creation-Date` 上有差異（例如 `git diff --stat` 會顯示有變更，而 `git diff -U0 client/locales/dotexpress.pot | findstr /r /c:"^[-+]msg" /c:"^[-+]#,"` 不印出任何內容）。接著用 `scripts\build-dotexpress.bat` 建置，確認打包版的選單、對話框按鈕、字典項目類型與關於文字都顯示 zh_TW，且點字表名稱仍有翻譯（這來自 `__tables.py` 自己未變更的 `_MEIPASS` 分支）。

## 範圍外

- 可設定的介面語言、`ngettext`/`pgettext`，或把 `_` 安裝到 builtins。
- 把 `_MENU_TRANSLATION_MARKERS` 搬到 `ui/action_menu.py`，或以 action 為 key 的選單（O-1 / P1-2）。
- 移除 `settings/dialogs.py` 中多餘的 `_(table.displayName)`（P2-3）。
- `"Close"` 缺少 zh_TW 翻譯。
- 任何對 `client/braille/tables/__tables.py` 的修改（衍生自 NVDA；見「已知問題／後續工作」）。
- 修正 `AGENTS.md`/`readme.md`/文件中 `generate_pot.bat` 的拼法（見「已知問題／後續工作」）。
- `app_paths.get_application_root`（可寫入資料放在執行檔旁，是不同的議題）、`conversion/mathcat_adapter.py` 的資源路徑與 `main.py` 的 `BASE_DIR`。它們之後可以改用 `resource_path`，但不是 gettext 的重複設定。
- 重新產生 `dotexpress.pot` 或 `.po`/`.mo`。
- 永久性地檢查原始碼 msgid 與 catalog 一致的測試。它今天會因 `"Close"` 而失敗，而且會讓每次修改字串都多一個只能在 Windows 執行的重新產生步驟。

## 已知問題／後續工作

- **`__tables.py` 在不存在的目錄中尋找 catalog。** `client/braille/tables/__tables.py:15-20` 以 `Path(__file__).resolve().parent.parent`（即 `client/braille/`）為基準解析 `resource_path("locales")`，所以從原始碼執行時會去找 `client/braille/locales`，而這個目錄不存在。因為 `fallback=True`，查找會靜默失敗，每個 `BrailleTable.displayName` 都維持英文。只影響從原始碼執行：打包版走 `_MEIPASS` 分支，得到中文名稱。設定對話框顯示的名稱在兩種模式下都是中文，因為 `settings/dialogs.py:625` 會再翻譯一次 `displayName`。不同的是 `listTables()` 的順序，它依 `strxfrm(displayName)` 排序：從原始碼執行時是英文順序，打包版是翻譯後名稱的順序。後續工作：等到修改衍生自 NVDA 的程式碼屬於範圍內時（例如已會動到 `braille/tables` 的 P1-1 或 P2-7），讓 `__tables.py` 改用 `i18n._`（或把基準改為 `parents[2]`），再移除多餘的 `_(table.displayName)`（P2-3）。那項後續工作會改變從原始碼執行時的排序，應明確說明。
- **文件中的腳本名稱不一致。** 腳本是 `scripts/generate-pot.bat`，但 `AGENTS.md`（"Regenerate the translation template with `scripts\generate_pot.bat`"）、`readme.md`、`docs/user/en/readme.md`、`docs/user/zh_TW/readme.md` 與幾份較早的 plan 寫的是 `generate_pot.bat`。本任務不修改它們。後續工作：另開文件變更修正（或重新命名腳本）。P0-5 的文件使用實際名稱 `generate-pot.bat`。
- **`"Close"` 沒有 zh_TW 翻譯**（`dotexpress.po` 的 `msgstr` 是空的）。本任務之前就是如此，維持原樣。

## 風險

- **打包版路徑解析**（低，這裡無法驗證）。`gui.py`、`dialog.py` 與 `settings/dialogs.py` 的打包分支不變（`__tables.py` 不動）。對 `about.py` 與 `dictionaries/entries.py` 而言，它取代的是以 `__file__` 為基準、在 PyInstaller 6.21 下本來就解析為 `_MEIPASS` 的路徑。PyInstaller 會從 `gui.py` 的靜態 import 分析找到 `i18n`，不需要 hidden-import 設定。需在 Windows 驗證（條件 10）。
- **使用 `N_` 的擷取**（低，這裡無法驗證）。若有人執行舊版、沒有 `--keyword=N_` 的擷取指令，只出現在標記 tuple 中的字串會從 `.pot` 中消失（例如選單標籤 "Add"、"Edit"、"Delete" 與 "Package DEP"）。keyword 與標記在同一個 commit 修改，條件 10 會檢查結果。
- **測試的替換語意**（低）。替換 `i18n._` 不會影響已經 import `_` 的模組。目前沒有測試這樣做。`i18n` 的 docstring 與 `test_i18n` 會寫明規則：替換使用端的 `_`。
- **`StubScope` eviction**（低）。`i18n` 可能在測試模組之間被移除後重新 import，結果只是重建一個相同的 catalog。條件 6 涵蓋此情況。
- **名稱衝突**（低）。沒有任何已安裝的套件提供頂層 `i18n`（在 venv 中 `find_spec("i18n")` 為 `None`），從原始碼執行時 `client/` 位於 `sys.path` 最前面，而 PyInstaller 建置時也會從 `client/`（腳本所在目錄）解析 `i18n`。
