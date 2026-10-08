# 應用程式路徑注入（P2-6）設計

## 目標

不再透過模組層級的預設值來解析應用程式資料位置。這是 `storage/refactor.md`（第 6.3 節）的路線圖任務 P2-6，對應發現 D-7（「`app_paths` 以 service-locator 風格被各模組呼叫」），並一併處理 P1 階段審查的 M-1（`conversion/presenter.py` 讓 `conversion` 套件反向依賴 `documents`）。

完成後：

- `BrailleApp.OnInit` 是唯一的組裝根（composition root）。它建立一個 `ApplicationPaths`，驗證**這個**物件，清理**它的** `dual_view/`，建立一個 `config.ConfigStore(paths.config)`，並把兩者傳給 `BrailleFrame`（store 也傳給 client init）。主視窗不再向任何模組詢問目錄。
- `config.py` 有一個擁有設定檔路徑的 `ConfigStore` 類別。`CONFIG_PATH` 與模組層級的設定 IO 函式全部移除。
- `app_paths` 的五個 `get_*_directory(path=None)`／`get_config_path` 輔助函式移除；`dictionaries/manager.py`、`dictionaries/name_prompt.py`、`documents/workspace.py`、`dual_view/files.py` 中每個 `dictionary_dir`／`workspace_dir`／`directory` 參數都改為必填。
- `log.py` 仍以隱含方式解析其目錄（理由見決策 D10），但只透過一個私有輔助函式。
- `ConversionPresenter` 從 `conversion/presenter.py` 搬到 `ui/conversion_presenter.py`，並以守門測試確保 `conversion` 不 import `documents`、`ui`、`gui` 與其他較高層。

這是純重構。每個檔案的落點與現在相同，啟動檢查順序與錯誤對話框相同，寫入 `config.json` 的位元組相同，log 檔與訊息相同，沒有新增顯示或朗讀內容，msgid 不變（353 個，集合相同）。黃金 fixture `client/tests/fixtures/translation_golden.json`（sha256 `e67d95a1ae001d928b657f16468494d0e98beeea5a6425283090b34030211ccd`）與 `client/tests/fixtures/dictionary_entries_trace.json`（sha256 `f493da52376c8eac32a50c33b7f11870451360bed4bf26c1db339ccd2c66c2cf`）不變。不需要任何使用者可見的變更，因此沒有需要上報的決策。

規劃後修正：計畫 `docs/superpowers/plans/2026-10-08-p2-6-application-paths.md`（「Spec Corrections and Refinements」一節）修正了三項事實（AC6 的 presenter grep 若不跳脫 `.`，也會匹配 `_conversion_presenter` 與 `ui.conversion_presenter`；`config` 保留 import 進來的 `get_logger`，所以形狀守門只檢查定義在 `config` 內的函式；一次轉換請求讀取 `config.json` 兩次，而不是一次），並細化了測試計畫（28 個新測試、A 部分額外的斷言、主視窗接線輔助函式使用誘餌根目錄、`gui.py` 何時停止 import `get_dictionary_directory`、以突變檢查證明一出現就綠燈的守門、位元組測試、兩個生命週期測試改用真的路徑、AC7 的應用程式資料快照）；這些變更已併入下文。

## 沿用 2026-07-20 的契約

`docs/superpowers/specs/2026-07-20-external-dual-view-and-app-data-paths-design.md` 是路徑契約。本任務改變的是「誰持有路徑」，不是契約本身：

- 根目錄：封裝版為 `Path(sys.executable).resolve().parent`（PyInstaller `--onefile`，因此是 `DotExpress.exe` 所在資料夾，不是 `_MEIPASS` 解壓資料夾）；否則為 `client/` 資料夾。`get_application_root()` 不動。
- 結構：`<root>/config.json`、`dictionary/`、`workspace/`、`log/`、`dual_view/`。`build_application_paths()` 不動。
- 啟動順序：先驗證根目錄與每個受管資料夾（mkdir + 探測檔），再以附加模式開啟既有的 `config.json`，再移除殘留的 `dual-view-*.html`，之後才建立翻譯 runtime 與主視窗。任何失敗都顯示在地化的「無法寫入應用程式資料目錄」錯誤（含失敗路徑），並在建立 runtime 之前停止。不使用替代位置。
- Logger：import 模組不會建立資料夾也不會開檔（`FileHandler(delay=True)`）；log 檔位於 `<root>/log/`。
- 結束：移除自有的 `dual-view-*.html`；失敗時記 log，仍會關閉 runtime。
- 唯讀的封裝資源（`i18n.resource_path`、`braille/tables/__tables.py`、`conversion/mathcat_adapter.py`、`main.BASE_DIR / "data"`）不是應用程式資料，維持在 `ApplicationPaths` 之外。

## 現況（2026-10-08 於 `refactor/p2-6-application-paths` 驗證，HEAD `f1ff5b3`，已合併 P0-*、P1-*、P2-1..P2-4）

縮排：`gui.py` 與 `dictionaries/name_prompt.py` 使用 tab。`app_paths.py`、`config.py`、`log.py`、`main.py`、`client_init.py`、`settings/*.py`、`dictionaries/manager.py`、`documents/*.py`、`dual_view/files.py`、`conversion/presenter.py` 與所有會動到的測試模組使用 4 個空白。

基準：`cd client && $PY -m unittest discover -s tests` 得到 `Ran 1043 tests`、`FAILED (failures=1, skipped=9)`；唯一失敗是 P2-5 的 `test_conversion_service ... test_translate_with_language_does_not_duplicate_existing_spaces_around_math`。shuffle seed 1 與 2 得到同樣的單一失敗。Msgid 掃描（`cd /workspace/DotExpress && $PY $SP/p12/tools/msgid_scan.py client`）回報 `source msgids: 353`。跑完套件後 `client/config.json` 與 `client/workspace/` 不存在（沒有測試寫入真實的應用程式資料）。（`$PY` = `$SP/venv/bin/python`，`$SP` = 本次工作階段的 scratchpad。）

`storage/refactor.md` 的行號早於 P0–P2-4。以下為目前行號。

### `app_paths.py`

- `ApplicationPaths`（11-22）：frozen dataclass `root, config, dictionary, workspace, log, dual_view` 與 `writable_directories`。
- `get_application_root()`（32-35）、`build_application_paths(root=None)`（38-47）。
- `get_config_path`、`get_dictionary_directory`、`get_workspace_directory`、`get_log_directory`、`get_dual_view_directory`（50-67）：皆為 `return Path(path) if path is not None else build_application_paths().<field>`。
- `prepare_application_directories(paths=None, *, probe_factory)`（70-89）：`paths or build_application_paths()`；把所有 `OSError` 包成 `ApplicationDataError`。

### 誰以預設值解析路徑

| 呼叫端 | 目前行為 |
| --- | --- |
| `config.py:15` | `CONFIG_PATH = str(get_config_path())`，import 時固定。`_load_from_file`（63-82）與 `_save_to_file`（85-98）在呼叫時讀取這個全域變數。 |
| `log.py:17` | `get_logger` 內的 `get_log_directory() / name`，在各模組 import 時建立 logger 的當下求值。 |
| `gui.py:138` | `self.dictionary_dir = get_dictionary_directory()`（經由 `dictionaries.manager` import，`gui.py:17`）。 |
| `gui.py:147` | `DocumentWorkspaceService(controller, get_workspace_directory())`（經由 `documents.workspace` import，`gui.py:30`）。 |
| `gui.py:334` | `write_dual_view_html(html)` 使用預設資料夾。 |
| `gui.py:1074` | `OnExit`：`cleanup_dual_view_html()` 使用預設資料夾。 |
| `gui.py:1056` | `OnInit`：`paths = prepare_application_directories()`，接著 `cleanup_dual_view_html(paths.dual_view)`；之後 `paths` 就被丟棄。 |
| `main.py:23` | demo：`get_dictionary_directory() / "default.csv"`。 |
| `dictionaries/manager.py:15-101` | `dictionary_path_for_name`、`ensure_default_dictionary`、`list_dictionary_names` 預設 `dictionary_dir=None`；`create/import/rename/export/delete_dictionary` 接受 `Path | None`；全部經過 `get_dictionary_directory(dictionary_dir)`。 |
| `dictionaries/name_prompt.py:33-42` | `rename_dictionary_after_name_prompt(dictionary_dir: Path | None, ...)`。 |
| `documents/workspace.py:37-48, 132` | `ensure_workspace_directory`、`document_package_path_for_name`、`load_workspace_documents` 預設 `workspace_dir=None`。 |
| `dual_view/files.py:17-36` | `write_dual_view_html(content, directory=None, *, token_factory)`、`cleanup_dual_view_html(directory=None)`。 |

除上表之外，所有正式程式的呼叫端都已傳入明確的資料夾（`DictionaryManagementPresenter`、`DocumentWorkspaceService`、`conversion/output.py:62`）。所有測試也都傳入明確資料夾，唯一例外是 `tests/test_app_paths.py:106-115`，它刻意呼叫預設值。

### 誰讀取 `config.py`

- `settings/translation.py`（`get/set_output_mode`、`get/set_conversion_width`、`get/set_selected_dictionary`）、`settings/view.py`（`get_view_font_size`、`get_view_scheme`、`get_braille_font`、`set_view_settings`）、`settings/translation_tables.py`（`get/set_translation_tables`）。它們的 `load_*`／`save_*` 只有 `gui.py` 呼叫（`gui.py:145, 146, 151, 422-424, 557`）。
- `gui.py:433` `set_selected_dictionary`，`gui.py:530-531` 每個轉換請求讀一次 `get_lang()`／`get_charset_maps()`（P1-1 的讀取模式）。
- `client_init.py:14, 147-149`：`run_client_init` 預設 `client_id_provider=get_or_create_client_id`、`locale_provider=get_lang`；兩者都在背景 worker 中執行（`start_client_init_background`，160-173）。
- `main.py:5, 30-31` demo。
- `conversion/service.py`、`conversion/math_service.py` 與許多測試只 import 常數（`DEFAULT_*`、`*_KEY`、`LANG_ENV`）。
- `set_lang`（159-165）沒有正式呼叫者；因此 `_runtime_lang`（47）在應用程式中永遠是 `None`。`tests/test_conversion_language_explicit.py:63-89` 設定 `config._runtime_lang = "ko"`，並把 `config.get_lang`／`config.get_charset_maps` patch 成會 raise，以證明轉換從不讀取設定。
- P0-1 行為：寫入不存在的檔案時，先注入 `{"language_detection": {"charset_maps": DEFAULT_CHARSET_MAPS}}`（88-93）；讀取失敗時，每個路徑、每種不同失敗簽章只記一次 `WARNING`（`_logged_load_failures`，50，以路徑字串為 key）；每次寫入失敗都記 `ERROR`；無法開啟 log 檔的 handler 絕不 raise（`_log_current_exception`，53-60）；所有 IO 的 catch 維持 `except Exception`。

### 在 import 時建立的 logger

`config.py:11`、`client_init.py:17`、`gui.py:103`、`ui/dual_view.py:13`、`adapters/translation/provider.py:13`、`conversion/math_service.py:10`。它們全都在 `OnInit` 執行前就已存在。

### 啟動（`gui.py:1053-1080`）

`OnInit`：`prepare_application_directories()` -> `cleanup_dual_view_html(paths.dual_view)` ->（遇 `ApplicationDataError`：對話框、`return False`；遇其他 `OSError`：`ApplicationDataError(paths.dual_view, cause)`、對話框、`return False`）-> `build_default_translation_runtime()` -> `BrailleFrame(None, runtime=...)` -> `Show()` -> `start_client_init_background()` -> `True`。`OnExit`：`cleanup_dual_view_html()`（`OSError` 時記 log），接著 `runtime.close()`。wx 只在 `OnInit` 回傳 `True` 之後才會呼叫 `OnExit`。

若 `prepare_application_directories` 本身丟出一般 `OSError`，`except OSError` 分支會碰到未綁定的 `paths`（`storage/refactor.md` 5.3）。目前不會發生，因為 `prepare_application_directories` 已把所有 `OSError` 包起來。

### M-1：`conversion` -> `documents`

`conversion/presenter.py:31-32` import `documents.controller.DocumentController` 與 `documents.workspace.Document`；`documents/formats.py:8` import `conversion.math_service`。沒有模組層級的循環，但兩個套件互相依賴。其他 `conversion` 模組都沒有 import `documents`、`ui`、`gui`、`dialog`、`settings`、`dictionaries` 或 `dual_view`（AST 掃描，含函式內 import）。`ConversionPresenter` 由 `gui.py:14`、`tests/test_conversion_presenter.py:7`（其 AST 守門讀取 `PRESENTER_PATH`）、`tests/test_export_coordinator.py:11` import；`documents/export_coordinator.py:40` 與 `gui.py:965` 在 docstring 與註解中提到它。

### patch 路徑或 `CONFIG_PATH` 的測試

- 在 `setUp` 重新指定 `CONFIG_PATH`：`tests/test_config.py`（3 個 class）、`tests/test_view_settings.py`、`tests/test_translation_tables.py`、`tests/test_translation_settings.py`；`tests/test_app_paths.py:113` 讀回它。
- `patch.object(gui, "get_dictionary_directory" | "get_workspace_directory")`：`tests/test_gui_document_flows.py` 中四個 `_initialize_state` 測試（`test_initialize_state_keeps_the_frame_controller`、`test_initialize_state_creates_service_for_frame_controller`、`_initialize_state_with_loaded_tables`、`test_initialize_state_wires_presenter_to_active_dictionary`）。
- `patch.object(gui, "prepare_application_directories")`：五個 `BrailleAppLifecycleTest` 測試；`test_app_validates_application_data_before_building_runtime` 使用零參數的 `side_effect`。三個 `OnExit` 測試 patch `gui.cleanup_dual_view_html`，其中一個斷言失敗會被記 log。
- `patch.object(gui, "get_lang"/"get_charset_maps"/"set_selected_dictionary"/"save_view_settings"/...)`：`test_conversion_request_copies_frame_translation_tables`、`test_initialize_state_wires_presenter_to_active_dictionary`、P2-4 的六個 `ViewFontSizeSyncCharacterizationTest` 測試（`save.assert_called_once_with(expected)`）、兩個 `apply_settings_from_dialog` 測試。
- `test_dual_view_menu_opens_rendered_html_with_main_window_size` 斷言 `write_html.assert_called_once_with("<html>dual</html>")`。
- `test_dictionary_dialog_helpers_and_imports_are_removed_from_gui` 在其「保留」清單中有 `"get_dictionary_directory"`（P0-6 守門）。
- `DocumentControllerOwnershipTest.test_frame_creates_its_controller_before_building_the_menu_bar` 建構 `gui.BrailleFrame(None, runtime=Mock())`。
- `tests/test_log.py` patch `log.get_logger` 使用的 `get_log_directory`；`tests/test_main_demo.py` patch `main.get_dictionary_directory`、`main.get_lang`、`main.get_charset_maps`。

## 設計

### 決策摘要

| # | 決策 | 理由 |
| --- | --- | --- |
| D1 | `BrailleApp.OnInit` 是組裝根：`paths = build_application_paths()`、`self.paths = paths`，接著是不變的 `try`（驗證 `paths`、清理 `paths.dual_view`），然後 `config_store = ConfigStore(paths.config)`、runtime、`BrailleFrame(None, runtime=..., paths=paths, config_store=config_store)`、`Show()`、`start_client_init_background(config_store)`。 | 驗證過的同一個物件在各處使用，正是 D-7 所要求的。`build_application_paths()` 與 `ConfigStore(...)` 不做 IO，因此可觀察的順序（驗證、清理、runtime、主視窗、顯示、client init）就是 2026-07-20 的順序。在 `try` 之前綁定 `paths` 也順帶消除 `except OSError` 分支的未綁定名稱隱患，且不改變任何可達路徑。 |
| D2 | `config.ConfigStore(path)`：每個現有模組函式對應一個公開方法，名稱、參數、預設值、回傳值與檔案格式都相同。建構子保存 `Path(path)`，不做 IO。每個 getter 仍重新讀檔；不做快取。 | 最小且忠實的模組函式搬移。P1-1 依賴「每個轉換請求讀一次 `get_lang`／`get_charset_maps`」，此點不變。S-5 的 repository 形狀（`load`／`save`／`update`、把 `save_translation_settings` 合併為一次寫入、縮小 catch 範圍）是另一項變更，不在範圍內（P0-1 已將其延後）。 |
| D3 | `_logged_load_failures`、`logger` 與 `_log_current_exception` 留在 `config.py` 模組層級；節流仍以 `str(path)` 為 key。 | P0-1 的規則是「每個 process 中，每個路徑、每種不同失敗只記一次警告」。以路徑為 key 的共用 dict 讓這條規則不論有幾個 store 指向同一檔案（應用程式、demo、測試）都成立。測試仍可 patch `config.logger` 並清空 `config._logged_load_failures`。 |
| D4 | `_runtime_lang` 留在模組層級；`set_lang(lang, persist=False)` 改為 `ConfigStore.set_lang`，內容相同；`get_lang` 維持「runtime 覆寫、`TEXT2BRAILLE_LANG`、檔案 `"language"`、`"zh_TW"`」的順序。 | 覆寫值是 process 狀態，不是路徑狀態。移除 `set_lang`／`_runtime_lang` 屬於 S-5（P0-1 已記錄），且會改動 `tests/test_conversion_language_explicit.py` 的守門。 |
| D5 | 刪除 `CONFIG_PATH` 與所有模組層級的 `get_*`／`set_*` 設定函式，不留別名，不設預設 store。 | 預設 store 正好會保留本任務要移除的模組全域路徑，也會讓測試 patch 一個設定來源、程式卻讀另一個。所有正式呼叫端都在可及範圍內：`gui.py`、`main.py`（兩個組裝根）、`client_init.py` 與三個 `settings` 模組，每處都只是多一個參數。 |
| D6 | settings 函式把 store 放在第一個參數：`load_translation_settings(store, dictionary_names)`、`save_translation_settings(store, settings)`、`load_view_settings(store)`、`save_view_settings(store, settings)`、`load_translation_tables(store)`、`save_translation_tables(store, tables)`。內容以相同順序呼叫相同的 store 方法（翻譯設定三次寫入、檢視一次、翻譯表一次）。 | 資源在前，與 `create_dictionary(dictionary_dir, name)` 一致。同樣的寫入、同樣的順序，代表 `config.json` 位元組相同，包含首次寫入的 `language_detection` 注入。`settings/__init__.py` 重新匯出的名稱不變。 |
| D7 | `start_client_init_background(config_store, *, run_client_init=run_client_init, thread_factory=threading.Thread)`。worker 呼叫 `run_client_init(client_id_provider=config_store.get_or_create_client_id, locale_provider=config_store.get_lang)`。`run_client_init` 的這兩個 provider 改為必填的 keyword-only 參數。`client_init.py` 不再 import `config`。 | client id 與 locale 仍在 worker 執行緒中讀取（id 也仍在那裡建立並儲存），與現在相同。例外仍由 worker 吞掉。 |
| D8 | `BrailleFrame.__init__(self, *args, runtime, paths, config_store, **kwargs)`：三者皆為必填 keyword-only。主視窗在 `_initialize_frame()` 之前、與 `translation_runtime` 並列保存 `self._paths` 與 `self._config_store`。保留 `self.dictionary_dir`（由 `self._paths.dictionary` 設定）。 | 比照審查所指的既有 `runtime` 注入。`dictionary_dir` 被 `on_open_text_processing`、`_get_selected_dictionary_path` 與 14 處測試讀取；保留它可避免大量改動，也不會多出第二個事實來源。 |
| D9 | `app_paths` 保留 `ApplicationPaths`、`ApplicationDataError`、`get_application_root`、`build_application_paths(root=None)` 與 `prepare_application_directories(paths, *, probe_factory)`，其中 `paths` 改為必填。刪除五個 `get_*` 輔助函式。 | 不帶 root 的 `build_application_paths()` 意思是「解析真正的根目錄」。這是唯一正當的隱含呼叫，並以守門測試限制只能出現在 `gui.py`、`main.py` 與 `log.py`。 |
| D10 | `log.py` 維持隱含解析，透過私有的 `_log_directory()` 回傳 `build_application_paths().log`，與現在的 `get_log_directory()` 一樣在 `get_logger` 內求值。 | 有六個模組在 import 時建立 logger，那時任何組裝根都還不存在。若要注入資料夾，就得在 `OnInit` 之後重新指定 handler，或改為延遲建立 logger，這會改變 log 檔綁定的時機與位置，而那正是 2026-07-20 契約所固定的。因為解析函式與 `OnInit` 使用的是同一個，handler 的資料夾等於驗證過的 `paths.log`；以測試固定這點。 |
| D11 | `dictionaries/manager.py`、`dictionaries/name_prompt.py`、`documents/workspace.py`、`dual_view/files.py` 的每個目錄參數都改為必填並標註為 `Path`（呼叫端仍可傳 `str`；內容使用 `Path(x)`）。`write_dual_view_html(content, directory, *, token_factory=...)` 的 `directory` 仍為第二個位置參數。 | 對任何非 `None` 的 `x`，`get_*_directory(x)` 回傳的就是 `Path(x)`，所以結果完全相同。沒有正式程式或測試傳入 `None`。 |
| D12 | `main.run_demo` 是自己的組裝根：`paths = build_application_paths()`、`config_store = ConfigStore(paths.config)`、詞典 `paths.dictionary / "default.csv"`、`lang=config_store.get_lang()`、`charset_maps=config_store.get_charset_maps()`。它仍不驗證資料夾。 | 檔案與讀取都和現在相同。demo 從未執行啟動檢查，現在也不執行。 |
| D13 | M-1：`git mv client/conversion/presenter.py client/ui/conversion_presenter.py`。模組內容不變（docstring 可提到新位置）。`conversion/` 中不留轉發。以 AST 守門禁止 `conversion/**` import `documents`、`ui`、`gui`、`dialog`、`settings`、`dictionaries` 與 `dual_view`。 | presenter 是主視窗的轉換協調者（busy 狀態、轉換中對話框計時器、翻譯後訊息、把結果寫入 `DocumentController`），屬於 UI 側，就像不依賴 wx、且已 import `documents` 的 `ui/menu_builder.py` 與 `ui/action_menu.py`。不建新的 `app/` 套件：它只會有一個模組，且 `server/app` 已使用這個名稱。不放 `documents/`：那會讓 `documents` -> `conversion` 擴大到 jobs、service 與 runtime。不在 `conversion/` 內用 Protocol 反轉：依賴雖會消失，協調者卻仍留在 domain 套件。轉發模組會保留 M-1 所指的那條邊。AST 檢查也能抓到函式內的 import，`sys.modules` 檢查則會漏掉。 |

### `app_paths.py`（4 空白）

- 刪除 `get_config_path`、`get_dictionary_directory`、`get_workspace_directory`、`get_log_directory`、`get_dual_view_directory`。
- `prepare_application_directories(paths: ApplicationPaths, *, probe_factory=tempfile.TemporaryFile)`；內容直接使用 `paths`。其餘不變。

### `config.py`（4 空白）

留在模組層級：去掉 `get_config_path` 後的 import、`logger`、所有常數（`DEFAULT_*`、`*_SECTION`、`*_KEY`、`LANG_ENV`、`DEFAULT_FALLBACK`、`DEFAULT_CHARSET_MAPS`、重新匯出的 math 名稱）、`_runtime_lang`、`_logged_load_failures`、`_log_current_exception`、`_coerce_int`、`_get_section`。

新增：

```python
class ConfigStore:
    """config.json at one path. Each getter re-reads the file; nothing is cached."""

    def __init__(self, path: Path | str) -> None:
        self._path = Path(path)

    @property
    def path(self) -> Path:
        return self._path

    def _load(self) -> dict: ...          # body of _load_from_file; key = str(self._path)
    def _save(self, data: dict) -> None: ...  # body of _save_to_file, incl. the first-save injection
    def _set_section_value(self, section, key, value) -> None: ...
    def _get_dict_setting(self, section, key, default) -> dict: ...

    def get_lang(self) -> str: ...
    def get_charset_maps(self) -> dict[str, str]: ...
    def set_lang(self, lang: str, persist: bool = False) -> None: ...   # sets module _runtime_lang
    def get_translation_tables(self) -> dict: ...
    def set_translation_tables(self, tables: dict[str, str]) -> None: ...
    def get_output_mode(self, default: str = DEFAULT_OUTPUT_MODE) -> str: ...
    def set_output_mode(self, output_mode: str) -> None: ...
    def get_conversion_width(self, default: int = DEFAULT_CONVERSION_WIDTH) -> int: ...
    def set_conversion_width(self, width: int) -> None: ...
    def get_selected_dictionary(self, default: str = "default") -> str: ...
    def set_selected_dictionary(self, dictionary_name: str) -> None: ...
    def get_view_font_size(self, default: int = DEFAULT_VIEW_FONT_SIZE) -> int: ...
    def get_view_scheme(self, default: str = DEFAULT_VIEW_SCHEME) -> str: ...
    def get_braille_font(self, default: str = DEFAULT_BRAILLE_FONT) -> str: ...
    def set_view_settings(self, font_size: int, scheme: str, braille_font: str) -> None: ...
    def get_or_create_client_id(self) -> str: ...
```

每個方法的內容就是現有函式內容，只把 `_load_from_file()`／`_save_to_file()`／`CONFIG_PATH` 換成 `self._load()`／`self._save()`／`str(self._path)`。`_save` 仍使用 `os.path.exists`、`os.makedirs(os.path.dirname(...), exist_ok=True)`、`json.dump(data, f, ensure_ascii=False, indent=2)`，並把 `str(self._path)` 傳給 log 呼叫，所以訊息逐字相同。類別放在 `config.py`（路線圖寫的是 `config.ConfigStore`）；`settings/options.py` 關於 `config` -> `settings` import 循環的說明仍然成立。`config.py` 為了 `Path | str` 型別標註加上 `from __future__ import annotations`，與 `app_paths.py`、`dictionaries/manager.py`、`documents/workspace.py`、`dual_view/files.py` 的做法相同（執行時無影響）。

### `log.py`（4 空白）

```python
from app_paths import build_application_paths


def _log_directory() -> Path:
    return build_application_paths().log
```

`get_logger` 使用 `_log_directory() / Path(filename).name`。簽章、`delay=True`、層級、formatter 與 `propagate = False` 都不變。

### `gui.py`（tab）

- import：`from app_paths import ApplicationDataError, ApplicationPaths, build_application_paths, prepare_application_directories`；`from config import ConfigStore, DEFAULT_TRANSLATION_TABLES`；`from dictionaries.manager import dictionary_path_for_name`；步驟 3 移除 `get_workspace_directory`、`get_lang`、`get_charset_maps`、`set_selected_dictionary`。步驟 3 不再呼叫 `get_dictionary_directory` 但仍保留其 import，因為 P0-6 守門 `test_dictionary_dialog_helpers_and_imports_are_removed_from_gui` 把它列為保留；步驟 4 一併移除該 import 與守門中的這一項；`from ui.conversion_presenter import ConversionPresenter`（步驟 5）。
- `BrailleFrame.__init__` 依 D8。
- `_initialize_state`：`self.dictionary_dir = self._paths.dictionary`；`load_translation_settings(self._config_store, names)`；`load_translation_tables(self._config_store)`；`DocumentWorkspaceService(self._document_controller, self._paths.workspace)`；`load_view_settings(self._config_store)`。順序與現在相同。
- `_open_dual_view_in_browser`：`write_dual_view_html(self._render_dual_view_for_open_document(), self._paths.dual_view)`。
- `apply_settings_from_dialog` 與 `_set_view_font_size`：`save_*(self._config_store, ...)`，順序相同。
- `_set_active_dictionary`：`self._config_store.set_selected_dictionary(selected_name)`。
- `_build_conversion_request`：`lang=self._config_store.get_lang()`、`charset_maps=self._config_store.get_charset_maps()`。
- `BrailleApp.OnInit` 依 D1。兩個 `except` 分支與 `_show_application_data_error` 不變。
- `BrailleApp.OnExit`：`paths = getattr(self, "paths", None)`；不為 `None` 時，在同樣的 `try`／`except OSError`／`logger.exception("Failed to clean up dual-view HTML")` 中執行 `cleanup_dual_view_html(paths.dual_view)`；接著照舊關閉 runtime。在產品中 `self.paths` 一定已設定（wx 只在 `OnInit` 成功後呼叫 `OnExit`）；`None` 的情況只存在於對裸 app 呼叫 `OnExit` 的測試。
- `# --- ConversionView (conversion/presenter.py)` 註解改指向 `ui/conversion_presenter.py`。

### 其他模組

- `settings/translation.py`、`settings/view.py`、`settings/translation_tables.py`：依 D6；為了型別標註 import `ConfigStore`，並繼續 import 常數。
- `client_init.py`：依 D7。
- `main.py`：依 D12；import `build_application_paths` 與 `ConfigStore`。
- `dictionaries/manager.py`、`dictionaries/name_prompt.py`、`documents/workspace.py`、`dual_view/files.py`：依 D11；移除 `app_paths` 的 import。
- `documents/export_coordinator.py:40`：docstring 改為 `ui.conversion_presenter.ConversionPresenter`。

## 保持不變的部分

每個檔案位置（根目錄、`config.json`、四個資料夾、log 檔、雙視 HTML 檔名）。啟動流程、執行哪些檢查、什麼會停止啟動，以及錯誤對話框文字。結束時的清理與其 log 行。每個 setter 之後 `config.json` 的確切內容，包含首次寫入的 `language_detection` 注入、key 順序、`ensure_ascii=False` 與 `indent=2`。讀寫的 log 記錄、其層級、訊息、`exc_info`、節流，以及 log 資料夾損壞時絕不 raise。`get_lang` 在各情況的回傳值。client id 何時建立、在哪個執行緒。每次轉換讀取設定檔的次數。msgid 集合與 fixture。沒有可見或朗讀上的變化，因此不需要截圖。

## 測試計畫

### A. 對現有程式碼做特性測試（步驟 1）

這些測試在現在的程式碼上就會通過。每一組都透過一個小的測試輔助函式觸及受測程式。步驟 3–4 只修改輔助函式，永不修改斷言。輔助函式把一切指向一個暫存根目錄：在現有程式碼上，patch `app_paths.get_application_root`（它會改變每次 `get_*_directory()` 呼叫，因為它們在呼叫時才解析根目錄）以及 `config.CONFIG_PATH`（import 時固定）；切換之後則建立 `build_application_paths(root)` 與 `ConfigStore(root / "config.json")` 並傳入。從步驟 3 起，主視窗接線輔助函式還會把 `app_paths.get_application_root`（以及在步驟 4 刪除之前的 `config.CONFIG_PATH`）指向根目錄旁一個空的誘餌資料夾：仍以隱含方式解析資料夾的回歸會落在誘餌中、讓根目錄斷言失敗，且永遠不會寫進 `client/`。client init 與 demo 的輔助函式在步驟 3 移除對 `CONFIG_PATH` 的 patch，因此退回模組函式的回歸會在那裡失敗，而不會被遮蔽。

1. `tests/test_gui_document_flows.py` 新增 class `ApplicationPathsWiringCharacterizationTest`：
   - 對 `object.__new__` 建立的主視窗執行 `_initialize_state`（真的 `DictionaryManagementPresenter`、真的 settings 載入函式，`_register_output_font` 以 mock 取代）：`frame.dictionary_dir == root / "dictionary"`、`root/dictionary/default.csv` 存在、`frame._workspace_service.workspace_dir == root / "workspace"`，且預先寫入 `root/config.json` 的設定會被載入（輸出模式、寬度、選定詞典、檢視設定、翻譯表）。
   - 在全新的根目錄上 `_set_active_dictionary("點字")`（zh_TW 名稱）會寫出 `root/config.json`，其第一個 key 是 `language_detection`，`conversion.selected_dictionary` 為 `"點字"`；測試比對檔案的確切文字（`json.dumps(..., ensure_ascii=False, indent=2)`），因此名稱不會被跳脫。
   - patch `open_html_in_browser` 後執行 `_open_dual_view_in_browser`，會在 `root/dual_view` 下寫入一個 `dual-view-*.html`，並把該路徑傳給瀏覽器輔助函式。
   - 從環境移除 `TEXT2BRAILLE_LANG`，在 `root/config.json` 寫入 `{"language": "en", "language_detection": {"charset_maps": {...}}}` 後執行 `_build_conversion_request`：`request.lang == "en"`，charset maps 與現在一樣合併。在未設定 `TEXT2BRAILLE_LANG` 且沒有執行期覆寫時，一次請求讀檔兩次（先 `get_lang`，再 `get_charset_maps`），所以兩次請求讀檔四次（由輔助函式安裝一個只計算設定檔路徑的 `open` 計數包裝）；兩次請求之間會改寫檔案，第二次請求看到新的語言，證明沒有快取。
2. 同一檔案，`BrailleAppLifecycleTest` 新增 `test_app_startup_runs_steps_in_contract_order`：以記錄用的假物件取代 `prepare_application_directories`、`cleanup_dual_view_html`、`build_default_translation_runtime`、`BrailleFrame`（及其 `Show`）與 `start_client_init_background`，得到 `["prepare", "cleanup", "runtime", "frame", "show", "client_init"]`，且不顯示錯誤對話框。以及 `test_app_stops_before_cleanup_when_validation_fails`：遇到 `ApplicationDataError` 時不清理、不建 runtime、不建主視窗、不啟動 client init，且錯誤對話框指出失敗的路徑。假物件接受任何參數，因此測試在新簽章下仍成立。
3. `tests/test_client_init.py` 新增 `ClientInitConfigCharacterizationTest`：使用同步的 `thread_factory` 與假的 `opener`，對空的根目錄啟動背景 client init 會建立 UUID client id、存入 `root/config.json` 並送出；第二次啟動送出同一個 id；檔案中的 `"language": "ja"` 以 `locale` 送出；worker 執行緒是 daemon；以永不執行的執行緒啟動 client init 時不會建立 client id（`test_no_client_id_is_created_before_the_worker_runs`），因此 id 永遠不會在 UI 執行緒上建立。輔助函式在現在包裝 `start_client_init_background(run_client_init=partial(run_client_init, opener=fake))`（並 patch `CONFIG_PATH`），之後改為 `start_client_init_background(ConfigStore(...), run_client_init=partial(...))`。
4. `tests/test_log.py`：`test_default_log_directory_follows_the_application_root`：把 `app_paths.get_application_root` patch 成暫存根目錄後，新 logger 的 `baseFilename` 為 `root/log/<name>`（測試傳入 `"nested/sample.log"`，以釘住 `Path(filename).name`），不會建立 `root/log`，且在同一 patch 下等於 `build_application_paths().log / <name>`。不需修改即可延續。
5. `tests/test_main_demo.py`：`test_demo_reads_dictionary_and_language_from_the_application_root`：根目錄被 patch 且 `root/config.json` 含 `{"language": "en"}` 時，請求的 `dictionary_path` 為 `root/dictionary/default.csv`，`lang == "en"`。
6. `tests/test_config.py` 新增 `ConfigLanguageOverrideCharacterizationTest`（3 個測試）：`get_lang()` 依序取 `TEXT2BRAILLE_LANG`、檔案的 `"language"`、`"zh_TW"`；`set_lang("ja")` 讓 `get_lang()` 回傳 `"ja"`，優先於 `TEXT2BRAILLE_LANG` 與檔案，且不寫檔；`set_lang("en", persist=True)` 寫入頂層 `"language": "en"`，並帶首次寫入注入。以 `addCleanup` 還原 `_runtime_lang`。透過 `make_store(path)` 輔助函式觸及（步驟 1：一個轉接物件，其方法在呼叫模組函式前後 patch `config.CONFIG_PATH`；步驟 2 起：`config.ConfigStore(path)`）。

一個用完即丟的突變執行器（不提交）會對 `client/` 的副本套用單點破壞（主視窗詞典資料夾改由 `Path.cwd()` 取得、雙視 HTML 寫到 workspace 資料夾、在驗證前清理、在清理前建 runtime、在 UI 執行緒讀 client id、移除 `language_detection` 注入、快取 `get_lang`、logger 資料夾由 `Path.cwd()` 解析），並證明 A 部分能抓到每一個：步驟 1 對現有程式碼有 26 個突變。步驟 3 再加 22 個新接線的突變（由六個受影響的模組抓到），步驟 4 加 8 個守門的突變。一出現就綠燈的守門（`test_client_init_does_not_import_config`，因為 client init 在步驟 3 就不再 import `config`；以及改寫後的 `test_consumers_use_the_common_application_root`）以突變證明會失敗（例如在 client init 加入 `import config`）。確切的突變清單由計畫列出。

### B. `ConfigStore`（步驟 2，純新增）

`tests/test_config.py` 新增 `ConfigStoreTest`：
- 對父資料夾不存在的路徑，建構子不建立檔案或資料夾，也不記 log（`patch.object(config, "logger")`，`mock_calls == []`）。
- 不論傳入 `str` 或 `Path`，`store.path == Path(given)`。
- 兩個 store 指向同一個損毀檔案，總共只記一次警告；指向兩個不同損毀檔案的 store 各記一次（D3）。
- `test_store_writes_the_documented_config_bytes`：從不存在的檔案開始，一串 setter（包含 zh_TW 詞典名稱 `點字`）寫出的內容與預期的字面文字完全相同；模組函式仍存在時（步驟 2–3）它們也必須產生相同位元組，步驟 4 移除這一半。兩個節流測試把兩個 store 都存在變數中，因此以實例為鍵的節流不會因 `id()` 重用而通過。

步驟 2 中，模組函式改為一行委派給在呼叫時建立的 `ConfigStore(CONFIG_PATH)`，因此每個既有的 `CONFIG_PATH` 測試不用改就能對 store 程式碼執行。

### C. 切換與守門（步驟 3–5）

- 步驟 3 把 `tests/test_config.py`、`test_view_settings.py`、`test_translation_tables.py`、`test_translation_settings.py` 從重新指定 `CONFIG_PATH` 改為 `self.store = config.ConfigStore(tmp / "config.json")` 並呼叫 store 或 settings 函式；對檔案內容的斷言不變。`test_conversion_language_explicit.py` 改為 patch `config.ConfigStore.get_lang` 與 `config.ConfigStore.get_charset_maps` 使其 raise（同樣的守門，涵蓋任何 store）。`test_gui_document_flows.py` 的主視窗工廠設定 `frame._paths` 與 `frame._config_store`（測試會寫檔時用暫存根目錄上的真 store，其他情況用 `Mock(spec=config.ConfigStore)`）；原本指名被 patch 的模組函式的斷言，改為指名 store（例如 `save.assert_called_once_with(frame._config_store, expected)`、`frame._config_store.set_selected_dictionary.assert_called_once_with("default")`、`write_html.assert_called_once_with("<html>dual</html>", frame._paths.dual_view)`）。`BrailleAppLifecycleTest` patch `gui.build_application_paths` 回傳暫存根目錄的路徑；零參數的 `side_effect` 改為接受 `paths`；`frame_class.assert_called_once_with(None, runtime=runtime, paths=paths, config_store=ANY)`；`OnExit` 測試設定 `app.paths`（必要：在 wx stub 下，缺少的屬性會讀成不做事的函式）。`test_app_cleans_stale_dual_view_html_after_path_validation` 與 `test_app_reports_startup_cleanup_failure_before_runtime` 原本建立 `paths = Mock()`，而 `ConfigStore(Mock().config)` 會在 `Path()` 中 raise `TypeError`，因此改用真的 `ApplicationPaths`（`build_application_paths(Path("C:/DotExpress"))`），由被 patch 的 `gui.build_application_paths` 回傳；斷言不變。
- 步驟 3 新增：`test_app_passes_the_validated_paths_and_one_store`：傳給 `prepare_application_directories` 的物件，就是傳給 `BrailleFrame` 並存為 `app.paths` 的那個；一個 `path == paths.config` 的 `ConfigStore` 同時到達主視窗與 `start_client_init_background`；store 在清理之後、runtime 之前建立。`test_app_exit_cleans_the_validated_dual_view_folder`。`test_frame_requires_paths_and_config_store`（以 `inspect.signature` 確認為 keyword-only 且無預設值）。
- 步驟 4 守門，以允許清單撰寫，因此永遠不會拼出已移除的名稱（P2-4 的教訓）：
  - `tests/test_app_paths.py` `ApplicationPathsApiTest`：`app_paths` 的公開函式恰好是 `{"get_application_root", "build_application_paths", "prepare_application_directories"}`；`prepare_application_directories` 的 `paths` 沒有預設值。
  - 同一 class：對 D11 列出的每個函式，`inspect.signature` 顯示資料夾參數沒有預設值。
  - 同一 class：AST 掃描 `client/**/*.py`（排除 `tests/`、`.venv/`、`braille/liblouis/`、`__pycache__`），不帶參數呼叫 `build_application_paths` 只出現在 `gui.py`、`main.py` 與 `log.py`。
  - `test_consumers_use_the_common_application_root` 改寫為 `build_application_paths(root)`，並檢查由它建立的 store 與主視窗輔助函式。
  - `tests/test_config.py` `ConfigModuleShapeTest`：定義在 `config` 內的函式（`inspect.isfunction(value) and value.__module__ == config.__name__`）沒有任何以 `get_` 或 `set_` 開頭，且沒有任何模組名稱含 `PATH`。（不是「沒有任何屬性」：`config` 從 `log` import 了 `get_logger`，這個屬性會保留。）
  - `tests/test_translation_import_isolation.py`：`test_client_init_does_not_import_config`（subprocess，與相鄰測試相同）。
  - `tests/test_gui_document_flows.py`：`"get_dictionary_directory"` 從 `test_dictionary_dialog_helpers_and_imports_are_removed_from_gui` 的「保留」清單移除（刻意的守門變更，於 commit 訊息中說明）。
  - `tests/test_log.py`：既有測試改為 patch `log._log_directory`。
- 步驟 5（M-1）：`tests/test_conversion_presenter.py` 改從 `ui.conversion_presenter` import，其 `PRESENTER_PATH` 指向 `client/ui/conversion_presenter.py`（wx／gui／dialog 的 AST 守門保留）；`tests/test_export_coordinator.py` 更新 import。新增 `tests/test_translation_import_isolation.py::test_conversion_package_imports_no_higher_layer`：對每個 `client/conversion/**/*.py` 做 AST 掃描，每個 `import`／`from`（絕對 import，任何巢狀層級）的頂層名稱都不得屬於 `{"documents", "ui", "gui", "dialog", "settings", "dictionaries", "dual_view"}`。搬移前為紅燈（會指出 `conversion/presenter.py`），搬移後為綠燈。

新測試共 28 個（1043 -> 1071）：步驟 1 新增 14 個（`ApplicationPathsWiringCharacterizationTest` 4、`BrailleAppLifecycleTest` 2、`ClientInitConfigCharacterizationTest` 3、`test_log` 1、`test_main_demo` 1、`ConfigLanguageOverrideCharacterizationTest` 3），步驟 2 新增 5 個（`ConfigStoreTest`），步驟 3 新增 3 個，步驟 4 新增 5 個（`ApplicationPathsApiTest` 3、`ConfigModuleShapeTest` 1、`test_client_init_does_not_import_config`），步驟 5 新增 1 個。最後各模組：`test_gui_document_flows` 151 -> 160、`test_config` 25 -> 34、`test_client_init` 7 -> 10、`test_app_paths` 7 -> 10、`test_translation_import_isolation` 4 -> 6、`test_log` 1 -> 2、`test_main_demo` 2 -> 3。因此 AC1 的路線圖指令執行 204 個測試。

## 遷移步驟（每一步一個綠燈 commit）

1. `test: characterize application paths wiring`（A 部分，輔助函式使用現有的接縫）。
2. `refactor: add config store behind the config functions`（`ConfigStore`，模組函式在每次呼叫時委派，B 部分）。
3. `refactor: inject application paths and config store at startup`（`OnInit`、`BrailleFrame`、settings 模組、`client_init`、`main`；設定測試改用 store API；A 部分輔助函式切換；步驟 3 的測試）。
4. `refactor: remove implicit application path defaults`（刪除 `app_paths` 輔助函式、`None` 預設值、`CONFIG_PATH` 與模組設定函式；`log._log_directory`；步驟 4 守門）。
5. `refactor: move conversion presenter to ui`（D13 及其守門）。

## 驗收條件

1. Linux 上的路線圖驗證：`cd client && $PY -m unittest tests.test_app_paths tests.test_config tests.test_gui_document_flows -v` 通過。下列也須綠燈：`tests.test_log tests.test_main_demo tests.test_client_init tests.test_view_settings tests.test_translation_tables tests.test_translation_settings tests.test_conversion_language_explicit tests.test_conversion_presenter tests.test_export_coordinator tests.test_translation_import_isolation tests.test_dictionary_manager tests.test_dictionary_name_prompt tests.test_document_workspace tests.test_workspace_service tests.test_dual_view_files tests.test_removed_dead_code tests.test_i18n tests.test_wx_stub`。
2. 全套件：`Ran` = 1043 + 28 = 1071，`failures=1`（僅 P2-5 案例），`errors=0`，`skipped=9`。
3. Shuffle harness：`cd client && for s in $(seq 0 19); do $PY $SP/shuffle_harness.py $s; done`，每個 seed 都恰好一個失敗，即 P2-5 案例。`test_config`、`test_gui_document_flows` 與 `test_app_paths` 單獨執行、以及每一對的兩種順序都通過。
4. 從 repo 根目錄執行 msgid 掃描，回報 `source msgids: 353`，與 `main` 集合相同。`git diff main --stat -- client/locales` 為空。
5. 上述兩個 fixture 的 sha256 不變，`git diff main -- client/tests/fixtures` 為空。
6. grep（皆為 `--include=*.py --exclude-dir=.venv`，範圍 `client`）：`CONFIG_PATH` 無輸出；`get_config_path\|get_dictionary_directory\|get_workspace_directory\|get_log_directory\|get_dual_view_directory` 無輸出；`grep -rnE "(_dir|directory|paths): (Path|ApplicationPaths) \| None" client/app_paths.py client/dictionaries client/documents/workspace.py client/dual_view/files.py` 無輸出（唯一保留的可選根目錄 `build_application_paths(root: Path | None = None)` 不會匹配；目前此 grep 有 15 行）；`conversion\.presenter\|conversion/presenter`（跳脫的點：不跳脫的 `.` 也會匹配 `gui.py` 中的 `_conversion_presenter`、`ui.conversion_presenter` 與 `test_conversion_presenter`）無輸出；`grep -rn "documents" client/conversion --include=*.py` 沒有任何 import 行；`client/conversion/presenter.py` 不存在。
7. 跑完全套件後，`client/config.json` 與 `client/workspace/` 仍不存在，且沒有測試寫入真實的應用程式資料。基準套件本來就會附加寫入 `client/log/dual_view.log`、`init.log`、`math.log` 與 `translation.log`（logger 在 import 時綁定真實的 log 資料夾，D10），而 `client/dictionary/` 是 git 忽略的使用者資料，可能存在於工作目錄中，所以這項以快照而非「不存在」來檢查：在完整執行套件前後記錄 `config.json`／`workspace/` 是否存在、`dictionary/` 下每個檔案的 sha256、`dual_view/` 中非原始碼的項目，以及 `log/` 中的檔名，兩份快照必須完全相同。
8. `git diff main --stat` 只動到本規格列出的模組、測試計畫列出的測試模組、兩份規格檔與計畫。

## 風險

- **`test_gui_document_flows.py` 的大量測試修改。** 約 30 處從 patch 模組函式改為設定主視窗屬性。緩解：A 部分先以輔助函式固定行為；`Mock(spec=config.ConfigStore)` 讓拼錯的 store 方法直接失敗。
- **以 `object.__new__` 建立且沒有 `_config_store` 的主視窗。** 任何未設定它就走到儲存或轉換請求的測試會得到 `AttributeError`。兩個主視窗工廠都會設定；全套件與 shuffle 會涵蓋。
- **Stub scope 的類別身分。** 使用 `evict_everything` 的 scope 可能重新 import `config`，產生第二個 `ConfigStore` 類別與第二個 `_logged_load_failures`。正式程式不對 `ConfigStore` 做 `isinstance`；測試 patch 的是它自己 import 的類別。由 shuffle 涵蓋。
- **兩個執行緒上的兩個設定讀取者。** UI 與 client-init worker 共用一個 store。store 只持有不可變的路徑，所以共用與現在的模組函式一樣安全。`get_or_create_client_id` 與 UI 儲存之間既有的 read-modify-write 競態維持不變（不修正，見已知怪癖）。
- **已刪除名稱的隱藏呼叫者。** repo 外 import `config.get_lang` 或 `app_paths.get_*` 的腳本會壞掉。全 repo grep 找不到（`server/` 不 import client 模組；`scripts/sync-nvda.py` 中的 `import config` 是 NVDA 的模組，該腳本會將它移除）。
- **PyInstaller。** 搬移後的 presenter 由 `gui.py` 靜態 import，`--onefile` 會收錄。此處無法建置（Windows 待驗證項目）。

## 保留的已知怪癖（固定或記錄，不修正）

1. 開發模式下 `client/dual_view/` 既是 `dual_view` Python 套件，也是雙視 HTML 資料夾。清理只移除 `dual-view-*.html`，所以原始碼安全。A 部分第 1 項寫入暫存根目錄，不碰它。
2. `get_or_create_client_id`（worker 執行緒）與 UI 儲存都會對 `config.json` 做 read-modify-write，且沒有鎖；若儲存剛好落在兩者之間，可能遺失其中一方的變更。既有問題，未固定（取決於時序）。
3. `set_lang` 沒有正式呼叫者，`_runtime_lang` 在應用程式中永遠為 `None`。保留給 S-5。
4. `save_translation_settings` 仍寫檔三次。保留給 S-5。

## Windows 待驗證項目

此 Linux 環境無法執行：以 `scripts\build-dotexpress.bat` 建置，從可寫入的資料夾執行 exe：`config.json`、`dictionary\`、`workspace\`、`log\` 與 `dual_view\` 和以前一樣出現在 `DotExpress.exe` 旁；設定、選定詞典與文件在重新啟動後仍在；雙視能開啟，其 HTML 在結束時被移除；client init 仍會回報（伺服器 log，或失敗時的 `log\init.log`）。從唯讀資料夾執行（例如未提權的 `Program Files` 下）：出現同樣的在地化啟動錯誤與失敗路徑，且不啟動 runtime。從 `client\` 與其他工作資料夾執行 `python gui.py`：都使用同一個 `client\` 根目錄。

## 範圍外

- S-5 的 repository 形狀（`load`／`save`／`update`）、合併寫入、縮小 `except Exception`，以及移除 `set_lang`／`_runtime_lang`。
- 把 log 資料夾注入 logger（D10），以及 P2-7 在 `braille/` 的 logging 工作。
- 搬移 `documents/export_coordinator.py` 或 `documents/workspace_service.py`，以及重新命名 `tests/test_conversion_presenter.py`。
- 將開發模式的 `dual_view/` 資料夾與套件分開（怪癖 1），以及對 2026-07-20 契約的任何變更。
- 拆分 `tests/test_gui_document_flows.py`（P1 審查 M-2）。
- 更新提到舊名稱的歷史規格、計畫與 `storage/refactor.md`。
