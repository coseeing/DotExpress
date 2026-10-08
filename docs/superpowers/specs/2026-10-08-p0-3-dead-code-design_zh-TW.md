# 死碼移除（P0-3）設計

## 目標

刪除 `storage/refactor.md` 第 5.4 節列出的死碼與死 API，並調整只為這些 API 存在的測試。本項是路線圖（第 6.1 節）的 P0-3。先刪掉它們，可縮小 P1 各項需要拆分或搬移的範圍。

這是保持行為不變的清理。使用者可見行為、字串、翻譯、持久化資料及建置輸入均不變。

## 方法（2026-10-08 於 `refactor/p0-3-dead-code`、HEAD `e5fa59a` 驗證，P0-1 與 P0-2 已合併）

對 5.4 節中的每個名稱，以及刪除後會連帶變成孤兒的同層輔助函式：

1. 以 `grep -rn` 搜尋 `client/`（正式程式與測試）、`scripts/`（含 `scripts/tests/`）與 `server/` 下的 `*.py`、`*.bat`、`*.spec`、`*.toml`、`*.cfg`、`*.txt`。
2. 動態查找：檢查 `client/` 與 `scripts/` 中所有 `getattr`、`importlib`、`__import__`。沒有任何一處指到下列項目，它們只讀取 `sys.frozen`、wx/pdf/os 屬性、`ctypes.WINFUNCTYPE` 與 `libmathcat_py`。
3. 打包：repo 內沒有 PyInstaller `.spec`。`scripts/build-dotexpress.bat` 執行 `pyinstaller ... gui.py`，只帶 `--add-data` 與 `--collect-data latex2mathml`，沒有 `--hidden-import`。打包內容依 `gui.py` 的 import 決定，所以沒人 import 的模組（例如 `dictionaries/import_flow.py`）目前本來就不會被打包。
4. 意圖：對每個只有測試在用的項目執行 `git log -S<name>`，區分遺留物與刻意預備的 API。

分類：**(a)** 任何地方都沒有呼叫者，刪除。**(b)** 只有測試呼叫，逐項決定。**(c)** 實際在用，保留並註明 review 判斷有誤。

基線：完整 client 測試 `Ran 449 tests`、`FAILED (failures=1, skipped=7)`。唯一的失敗是已知的 P2-5 案例 `test_conversion_service ... test_translate_with_language_does_not_duplicate_existing_spaces_around_math`。

## 項目清單與決策

行號以 HEAD `e5fa59a` 為準。

### `client/gui.py`（tab 縮排）

| 項目 | 證據 | 分類 | 決策 |
| --- | --- | --- | --- |
| `IMPORT_WILDCARDS` 149-155 | 只有定義處符合。匯入對話框用的是 `ui.import_dialog.build_import_wildcard(_)`（`gui.py:1168`）。是 `df01017` 的遺留物。 | a | 刪除。 |
| `PDF_WILDCARD`、`DOCX_WILDCARD`、`EPUB_WILDCARD` 144-146 | 只有 `IMPORT_WILDCARDS` 使用它們。 | a（因上一項刪除而變成孤兒） | 刪除。 |
| `_get_txt_wildcard` 761-762 與 `TXT_WILDCARD` 143 | 不在 5.4 清單中。正式程式與測試都沒有呼叫者，`TXT_WILDCARD` 也沒有其他使用處。 | a（額外發現） | 刪除。 |
| `_get_import_wildcard` 764-766 | 只有定義處符合。review O-2 也確認它從未被呼叫。 | a | 刪除。`get_format` import 保留，因為還有 5 處使用。 |
| `_create_labeled_group` 554-559 | 只有定義處符合。翻譯控制項移到選單（`e4af249`）、改用設定對話框（`064e01d`）之後，最後一個使用者就消失了。 | a | 刪除。 |
| `_rename_dual_view_result` 538-540、`_delete_dual_view_result` 542-543 | 只有 `tests/test_gui_document_flows.py:988-995`（`test_rename_and_delete_keep_alignment_cache_consistent`）使用。`DocumentController.rename_document`/`delete_document`（`documents/controller.py:82-83, 89`）已取代它們，該取代路徑由 `tests/test_document_controller.py` 的 `test_rename_updates_names_and_dual_view_cache`（75）、`test_delete_open_document_prefers_neighbor_and_removes_dual_view_cache`（94）、`test_rename_document_moves_dual_view_cache_entries`（148）、`test_delete_document_removes_dual_view_cache_entry_and_preserves_preferred_selection`（161）涵蓋。 | b | 刪除這兩個方法與那個測試。該測試只驗證死方法，實際路徑已有 4 個 controller 測試。 |

不動：`_MENU_TRANSLATION_MARKERS`（`gui.py` 約 220-226）仍列有 wildcard 字面字串 `_("Text files (*.txt)|*.txt")`、`_("PDF files ...")` 等。這些是 gettext 擷取標記，所以 `dotexpress.po` 的條目保留，不需改 `.po`/`.mo`。是否清理這些標記屬於 P1-2/P0-5（O-1）。

### `client/config.py`

| 項目 | 證據 | 分類 | 決策 |
| --- | --- | --- | --- |
| `set_view_font_size`、`set_view_scheme`、`set_braille_font` | P0-1 已移除，並由 `tests/test_config.py:153` 的 `test_unused_single_view_setters_are_removed` 守護。`gui.py:847` 的 `_set_view_font_size` 是另一個仍在使用的 frame 方法。 | 已完成 | 不需處理。 |

### `client/conversion/text/`（4 空白縮排）

| 項目 | 證據 | 分類 | 決策 |
| --- | --- | --- | --- |
| `dictionary_rules.translate__mapping_string` 111-140 | 只有定義處符合。`2026-07-08-conversion-text-processing` 計畫以「若仍有使用」為條件搬移它，而它並沒有被使用。 | a | 刪除。`csv`、`Path`、`mapping` 在檔案其他地方仍有使用。 |
| `char_maps.preprocess_bopomofo_characters` 64-70、`char_maps.map_braille_to_ascii` 73-79 | 只有定義處符合。同一份計畫把它們列為可選的具名包裝（「若能減少重複的路徑處理」）。`aec3331` 加入了它們，但始終沒有寫出呼叫者。 | a | 刪除。 |
| `char_maps.translate__mapping_char` 49-61 | 它是 `conversion/service.py:113` 與 `conversion/output.py:45` 的 `map_char` 預設值，`tests/test_conversion_text_char_maps.py` 也測了 5 次。 | c（review 稱「只是別名」） | **保留**，它在使用中。把別名併入 `map_characters` 屬於更名，不是死碼移除，不在範圍內。 |
| `pipeline.apply_plain_text_rules` 49-61 | 只有 `tests/test_conversion_text_pipeline.py`（`test_apply_plain_text_rules_returns_bracketed_raw_and_replacement` 與 `test_atomic_flags_remain_paired_before_runtime_translation`）使用。它只是把參數原樣轉給 `apply_dictionary`，而 `translate_plain_text_segment` 直接呼叫的就是 `apply_dictionary`。 | b | 刪除這層包裝。兩個測試**改指向** `conversion.text.dictionary_rules.apply_dictionary`，參數與斷言不變。它們驗證的是 pipeline 實際執行的程式碼的括號配對行為，因此仍有價值。第一個測試更名為 `test_apply_dictionary_returns_bracketed_raw_and_replacement`。 |

### `client/languageDetection/__init__.py`（tab 縮排）

| 項目 | 證據 | 分類 | 決策 |
| --- | --- | --- | --- |
| `LanguageDetector.process_for_spelling` 396-442 | 任何地方都沒有呼叫者。它自初始 commit `75ddcde`（2025-11-11，移植自 WorldVoice）就存在，從未被使用。 | a | 刪除。`find_language_for_charset` 與 `_preferred_full_lang` 保留，因為 `add_detected_language_commands` 會用到。`config` import 保留，因為第 183、365、382 行在用。 |
| `add_detected_language_commands` 內的 `if False and (...)` 區塊 262-284 | 這個分支不可能執行，裡面還有 WorldVoice 的 `config.conf[...]` 註解。 | a | 刪除該區塊。同時刪除因此變成無用寫入的 `prevInIgnore = False`（204 與 287）。被刪除的區塊（271、275）是唯一讀取或設定 `prevInIgnore` 的地方。`rule`、`charset` 等其他區域變數保留。 |

### `client/dictionaries/import_flow.py`（整個模組）

| 證據 | 分類 | 決策 |
| --- | --- | --- |
| 只有 `tests/test_dictionary_import_flow.py`（2 個測試）import 它。歷史：`96366f3`（2026-06-29 08:07，「fix: streamline dictionary import prompt」）新增它並接進 `gui.py`。43 分鐘後 `f975aa5`（2026-06-29 08:50，「fix: keep duplicate dictionary dialogs open」）把 `gui.py` 的 import 換成 `dictionaries.name_prompt.prompt_dictionary_name_until_success`，該函式還會在名稱重複時重新詢問。所以這是當天就被新設計取代的程式，不是未完成的預定功能。它的行為在實際路徑上已有涵蓋：`gui.py:1435-1442` 預填 `source_path.stem`，並在 `on_submit` 中呼叫 `import_dictionary`；`tests/test_dictionary_name_prompt.py::test_cancel_returns_none_without_submitting` 涵蓋取消時不匯入。P0-6 的 presenter 會建立在 `name_prompt` 上，而不是 `import_flow`。 | b | 刪除模組與 `tests/test_dictionary_import_flow.py`。`docs/superpowers/plans/2026-06-29-windows-filename-validation-implementation-plan.md` 提到它，但那份計畫是歷史紀錄，不修改。 |

### `client/ui/action_menu.py`（4 空白縮排）

| 項目 | 證據 | 分類 | 決策 |
| --- | --- | --- | --- |
| `build_actions_button_label`、`get_actions_menu_position`、`get_dictionary_action_labels` | 任何地方都沒有呼叫者。它們服務於舊的「Actions ▼」彈出按鈕，該按鈕已被 `e4af249`（「feat: move translation controls to menu」）移除。 | a | 刪除。 |
| `get_document_action_labels`、`get_document_export_format_keys` | 任何地方都沒有呼叫者。 | a | 刪除。 |
| `get_document_menu_items`、`get_document_export_format_labels` | 只有 `tests/test_action_menu.py::test_export_submenus_use_descriptive_formats_in_order` 使用。順序一改就會出錯的 `DOCUMENT_MENU_ITEMS[-2]` 負索引（80、84）會隨之消失。 | b | 刪除。該測試**改寫**為測試 `gui.py:456` 實際使用的 `get_document_menu_descriptors()`（見測試策略）。 |
| `DocumentMenuItem`、`DOCUMENT_MENU_ITEMS`、`get_document_menu_descriptors`、`get_document_menu_enabled_state` | `gui.py:64-67, 456, 463` 與 `_sync_document_menu_state` 使用它們。 | c | 保留，不變。 |

### `client/ui/import_dialog.py`（4 空白縮排）

| 項目 | 證據 | 分類 | 決策 |
| --- | --- | --- | --- |
| `get_import_wildcard_text`、`get_default_import_filter_index` | 任何地方都沒有呼叫者。 | a | 刪除。 |
| `get_import_filter_labels`（36-37） | 不在 5.4 清單中，任何地方都沒有呼叫者。`get_import_filters` 直接使用別名 import `get_format_import_filter_labels`。 | a（額外發現） | 刪除。 |
| `ImportFilter`、`get_import_filters`、`build_import_wildcard`、再匯出的 `ALL_SUPPORTED_FILTER_INDEX` | `gui.py:68, 1168-1177` 使用它們。 | c | 保留。模組內所有 import 都保留：`ALL_SUPPORTED_FILTER_INDEX` 再匯出給 `gui`，其餘由 `get_import_filters`/`build_import_wildcard` 使用。 |

### `client/documents/workspace.py`（4 空白縮排）

| 項目 | 證據 | 分類 | 決策 |
| --- | --- | --- | --- |
| `list_document_names` 133-138 | review 說「僅 tests」，但實際上連測試都沒用，任何地方都沒有呼叫者。自 `dd43d6f` 起就存在。 | a | 刪除。`get_workspace_directory` 在 38、48 仍有使用。 |
| `batch_export_documents_to_folder` 184-203 | 只有 `tests/test_document_workspace.py` 的 3 個測試（264、282、301）使用。`85bf669`（2026-06-30）移除了它在 `gui.py` 的呼叫者，GUI 現在透過 `_export_document_with_dialog`/`_export_next_document` 匯出。review O-2 也指出它對 `html` 會寫出空的 dual view，不適合作為 P1-4 的基礎。 | b | 刪除函式與那 3 個測試。它們驗證的行為已由實際使用的單元涵蓋：`test_export_document_brl_writes_plain_braille_text`（BRL writer）與 `test_save_document_package_can_skip_pending_metadata_for_exports`（匯出 DEP 時不含 pending metadata）。衝突與覆寫處理現由 GUI 匯出鏈與 `export_results` 負責。刪除後此模組不再使用 `get_format`，因此從 `documents.formats` 的 import 中移除（沒有測試 patch `documents.workspace.get_format`）。 |
| `prepare_document_for_save(..., auto_convert=None)` 122-130 | 沒有任何呼叫傳入 `auto_convert`：唯一的呼叫者是 `gui.py:887`，兩個測試也沒有傳。`85bf669` 移除了它最後的使用者。函式永遠回傳 `(document, None)`。review S-6 指出這個參數與永遠為 `None` 的錯誤欄位都是自動轉換功能的殘骸。 | a | 移除該參數，**以及**永遠為 `None` 的錯誤欄位，函式改為回傳 `Document`。呼叫端改為 `updated_document = prepare_document_for_save(...)`。這也順帶消除一個隱患：目前的 `updated_document, _ = ...` 會讓 `_` 在 `_save_open_document` 內成為區域變數，蓋掉 gettext 的 `_`。同步更新兩個測試（見測試策略）。 |

### `client/documents/formats.py`（4 空白縮排）

| 項目 | 證據 | 分類 | 決策 |
| --- | --- | --- | --- |
| `get_exportable_formats` 186-187 | 只有 `tests/test_document_formats.py::test_exportable_formats_include_dep_and_brl` 使用。它隨格式 registry 在 `df01017`（「refactor: converge document and conversion boundaries」）加入，與實際在用的 `get_importable_formats` 成對。 | b | **保留**。這是兩行的 registry 查詢，看起來是刻意預備的。它的測試固定了 `gui.py:1493` 依賴的 `exportable` 旗標。P1-2（改由 registry 產生匯出子選單與 wildcard，取代寫死的 `(("dep", ...), ("brl", ...), ("html", ...))` tuple）會自然用到它。 |
| `get_import_wildcard_text` 208-209 | 不在 5.4 清單中，任何地方都沒有呼叫者，且與 `ui/import_dialog.py` 的同名函式重複。 | a（額外發現） | 刪除。 |

### `client/braille/tables/__init__.py`（tab 縮排，衍生自 NVDA）

| 項目 | 證據 | 分類 | 決策 |
| --- | --- | --- | --- |
| `getDefaultTableForCurLang` 105-124 | 任何地方都沒有呼叫者。它是此模組中唯一使用 `config` 的地方（117 行的 `config.get_lang()`）。 | a | **保留，延到 P1-1**。P1-1 列明確負責「移除 `braille/tables` 對 `config` 的 import」，第 3.5 節的建議也是讓此函式改收 `lang` 參數，而不是刪除。此模組是手動改寫的 NVDA `brailleTables`（`scripts/sync-nvda.py` 不會重新產生它）。刪除此函式還會讓 `addTable` 寫入的 `_inputTableForLangs`/`_outputTableForLangs` 變成只寫不讀，擴大與上游的差異。liblouis runtime 只能在 Windows 執行，這裡無法驗證。刪除或參數化由 P1-1 連同其餘 `config` 解耦一起決定。 |

### 不在範圍內（已檢視，不變更）

- `dialog.py` 的 `DictionaryEntryListCtrl` 別名（第 4.1 節，不在 5.4）。留給 P2-2。
- `_MENU_TRANSLATION_MARKERS` 與 `.po` 中過時的條目（O-1，P1-2/P0-5）。
- `translate__mapping_char` 的命名（在使用中）。
- `documents/formats.get_format_keys(importable=None)` 分支（未列入，且屬於 registry）。

## 測試策略（TDD）

刪除沒有新行為可以驅動，所以紅燈步驟改用**守護測試**：死名稱仍存在時失敗，刪除後通過。P0-1 用過同樣的做法（`test_unused_single_view_setters_are_removed`）。測試變更依序如下：

1. **新增 `client/tests/test_removed_dead_code.py`**（4 空白縮排、`unittest`）。每個非 GUI 區域一個守護測試，每個名稱一個 `subTest`：
   - `test_dictionary_import_flow_module_is_removed`：`importlib.util.find_spec("dictionaries.import_flow") is None`。
   - `test_dead_conversion_text_helpers_are_removed`：`dictionary_rules.translate__mapping_string`、`char_maps.preprocess_bopomofo_characters`、`char_maps.map_braille_to_ascii`、`pipeline.apply_plain_text_rules` 都不存在（`hasattr` 為 false），且 `char_maps.translate__mapping_char` 仍存在（守護仍在使用的項目）。
   - `test_dead_language_detection_method_is_removed`：`LanguageDetector` 沒有 `process_for_spelling`。
   - `test_dead_ui_helpers_are_removed`：`ui.action_menu` 的 7 個名稱與 `ui.import_dialog` 的 3 個名稱都不存在，且 `get_document_menu_descriptors`/`get_document_menu_enabled_state`/`get_import_filters`/`build_import_wildcard` 仍存在。
   - `test_dead_document_helpers_are_removed`：`documents.workspace.list_document_names`、`documents.workspace.batch_export_documents_to_folder`、`documents.formats.get_import_wildcard_text` 都不存在，且 `"auto_convert"` 不在 `inspect.signature(prepare_document_for_save).parameters` 中。
2. **`client/tests/test_gui_document_flows.py`**（沿用檔內的 wx stub）。新測試放在 `BrailleAppLifecycleTest`，不放在 `GuiDocumentFlowsTest`：`BrailleAppLifecycleTest` 繼承 `GuiDocumentFlowsTest`，放在基底類別的測試會執行兩次。（被刪除的 `test_rename_and_delete_keep_alignment_cache_consistent` 也在 `BrailleAppLifecycleTest` 中，因此只算一次。）
   - 新增 `test_dead_frame_helpers_are_removed`：模組屬性 `IMPORT_WILDCARDS`、`TXT_WILDCARD`、`PDF_WILDCARD`、`DOCX_WILDCARD`、`EPUB_WILDCARD`，以及 `BrailleFrame` 屬性 `_create_labeled_group`、`_get_import_wildcard`、`_get_txt_wildcard`、`_rename_dual_view_result`、`_delete_dual_view_result` 都不存在。frame 屬性要檢查類別 `gui.BrailleFrame`，不可檢查 frame 實例：stub 的 `wx._Widget.__getattr__` 對任何不存在的實例屬性都回傳空函式，所以在 stub 下 `hasattr(frame, ...)` 永遠為真。
   - 新增 `test_save_open_document_saves_prepared_document`（修正，見下）：在 patch `save_document_package` 的情況下執行 `BrailleFrame._save_open_document`，斷言準備好的 `Document` 取代目前開啟的文件，並寫入 `document_package_path_for_name(...)`。目前沒有任何測試會執行這個呼叫者；少了這個測試，`prepare_document_for_save` 回傳型別變更後即使 `gui.py` 仍在解包 tuple，整套測試也會維持綠燈，但每次儲存都會丟出 `TypeError: cannot unpack non-iterable Document object`。這個測試在目前程式碼下通過，workspace 函式變更後會出現該 `TypeError`，呼叫者更新後再度通過。
   - 刪除 `test_rename_and_delete_keep_alignment_cache_consistent`。它只測被刪除的方法，實際路徑已在 `test_document_controller.py` 涵蓋。
3. **`client/tests/test_action_menu.py`**：把 `test_export_submenus_use_descriptive_formats_in_order` 改寫為以 `get_document_menu_descriptors()` 為基礎的同名測試。以 `label` 找出 `Export` 與 `Export All` 兩項，分別斷言 `kind == "submenu"`、`action` 為 `"export"`/`"export_all"`，以及 `formats == (("dep", "Package DEP"), ("brl", "Braille BRL"), ("html", "Dual View HTML"))`。移除對已刪除函式的 import。4 個 `get_document_menu_enabled_state` 測試不變。
4. **`client/tests/test_conversion_text_pipeline.py`**：改從 `conversion.text.dictionary_rules` import `apply_dictionary`，取代 `apply_plain_text_rules`，並以相同的關鍵字參數呼叫。第一個測試依上述更名，斷言不變。
5. **`client/tests/test_document_workspace.py`**：刪除 3 個 `batch_export_documents_to_folder_*` 測試與對應 import。2 個 `prepare_document_for_save` 測試改為 `prepared = prepare_document_for_save(...)`，移除 `assertIsNone(auto_error)`，並去掉測試名稱中的 `_without_auto_conversion` 後綴。在目前程式碼下它們會紅燈，因為函式回傳的是 tuple。
6. **刪除 `client/tests/test_dictionary_import_flow.py`。**

不可達的 `if False` 區塊與無用的 `prevInIgnore` 寫入無法寫守護測試。現有語言偵測測試（`tests.test_language_detection_translation`、`tests.test_language_detection_char_langinfo`、`tests.test_language_detection_unicode_braille`，以及會執行 `add_detected_language_commands` 的 pipeline 測試）必須在不修改的情況下維持綠燈。下方的驗收 grep 確認區塊已移除。

預期數量：449 − 2（`test_dictionary_import_flow`）− 1（gui rename/delete）− 3（批次匯出）+ 5（`test_removed_dead_code`）+ 1（gui 守護）+ 1（gui 儲存測試）= **450**。（修正：原本的算式得到 449，漏算了上方新增的儲存呼叫者測試。）

## 驗收標準

1. 在 `client/` 以 venv 的 Python 執行 `python -m unittest discover -s tests -p "test_*.py"`，結果為 `Ran 450 tests`、`FAILED (failures=1, skipped=7)`。唯一的失敗是已知的 P2-5 `test_conversion_service` 案例，沒有新增的失敗或錯誤。
2. 聚焦測試通過：`python -m unittest tests.test_removed_dead_code tests.test_action_menu tests.test_conversion_text_pipeline tests.test_conversion_text_char_maps tests.test_conversion_text_dictionary_rules tests.test_document_workspace tests.test_document_formats tests.test_document_controller tests.test_dictionary_name_prompt tests.test_gui_document_flows tests.test_language_detection_char_langinfo tests.test_language_detection_unicode_braille -v`（預期 `Ran 132 tests`、`OK`）。另外，在非 Windows 平台執行 `python -m unittest discover -s tests -p "test_language_detection*.py" -v`，結果為 `Ran 7 tests`、`OK (skipped=1)`。（修正：在非 Windows 平台上，`tests.test_language_detection_translation` 因 liblouis 需要 `WINFUNCTYPE`，會在 import 時丟出 `unittest.SkipTest`；明確指名該模組時，`unittest` 的 loader 不會攔截，整個指令會在任何測試執行前中止。`discover` 則會把它記為一個 skip。在 Windows 上，請把 `tests.test_language_detection_translation` 加回聚焦指令。）
3. 在 repo 根目錄執行下列 grep，只會命中 `client/tests/test_removed_dead_code.py` 與 `client/tests/test_gui_document_flows.py` 中的守護字串：
   `grep -rnE 'IMPORT_WILDCARDS|PDF_WILDCARD|DOCX_WILDCARD|EPUB_WILDCARD|TXT_WILDCARD|_create_labeled_group|_get_import_wildcard|_get_txt_wildcard|_rename_dual_view_result|_delete_dual_view_result|translate__mapping_string|preprocess_bopomofo_characters|map_braille_to_ascii|apply_plain_text_rules|process_for_spelling|import_flow|build_actions_button_label|get_actions_menu_position|get_document_menu_items|get_dictionary_action_labels|get_document_action_labels|get_document_export_format_|get_default_import_filter_index|get_import_wildcard_text|list_document_names|batch_export_documents_to_folder|auto_convert' client scripts --include='*.py' --include='*.bat' --exclude-dir=.venv`
   （`--exclude-dir=.venv` 避免被 git 忽略的 `client/.venv` 造成誤判；目前該目錄沒有任何命中。）
   另外，`grep -n "get_import_filter_labels" client/ui/import_dialog.py` 只會印出一行：別名 import `get_import_filter_labels as get_format_import_filter_labels,`。實際在用的 `documents.formats.get_import_filter_labels` 保留其定義。
4. `grep -n "if False" client/languageDetection/__init__.py` 與 `grep -n prevInIgnore client/languageDetection/__init__.py` 沒有輸出。
5. `client/dictionaries/import_flow.py` 與 `client/tests/test_dictionary_import_flow.py` 已不存在。
6. 刻意保留，每項仍能搜到其定義：`translate__mapping_char`、`get_exportable_formats`、`getDefaultTableForCurLang`、`get_document_menu_descriptors`、`get_document_menu_enabled_state`、`get_import_filters`。
7. `git diff main --stat -- client/locales` 為空。因為沒有使用者可見字串變更，`.po`/`.mo` 不變。
8. 縮排依各檔案原樣（`gui.py` 與 `languageDetection/__init__.py` 用 tab，其餘用 4 空白），不重新排版。
9. 每個 commit 只做一類刪除，例如 gui 輔助函式、conversion text 輔助函式、語言偵測、import flow 模組、action menu 與 import dialog、documents。每個 commit 之後，完整測試除已知的 P2-5 案例外沒有任何失敗或錯誤。

## 風險

- **grep 範圍外的隱藏呼叫者**：已由上述動態查找與打包檢查涵蓋。沒有以字串存取、沒有 `--hidden-import`、沒有 `.spec`。`server/` 沒有 import 這些模組。剩餘風險低。
- **僅限 Windows 的路徑**：被刪除的程式碼中沒有只在 Windows 執行的部分，`braille/tables`（liblouis）也刻意不動。這台 Linux 機器無法執行 Windows 的 PyInstaller 建置。由於 `gui.py` 從未 import `import_flow`，預期不受影響，但交接時必須說明這點未經驗證。
- **`prepare_document_for_save` 回傳型別變更**：它是 `documents/workspace.py` 的公開函式。grep 顯示只有一個正式呼叫者 `gui.py:887` 與兩個測試，全部在同一個 commit 中更新。`test_save_open_document_saves_prepared_document` 守護這個呼叫者，其他測試都不會執行到它。
- **改指向的 pipeline 測試直接呼叫 `apply_dictionary`**：這正是 pipeline 呼叫的函式，對實際路徑的涵蓋不變。
- **移除 `batch_export_documents_to_folder`**：若 P1-4 之後需要純函式的批次匯出輔助，應依統一的 `ExportContext` writer 契約（P1-2）重寫，而不是復活這個會錯誤處理 `html` 的版本。
- **與 review 的差異**：`translate__mapping_char` 在使用中，不是死碼。`list_document_names` 連測試都沒有呼叫者。`get_exportable_formats` 與 `getDefaultTableForCurLang` 刻意保留，另外多刪四項死輔助（`_get_txt_wildcard`/`TXT_WILDCARD`、`ui.import_dialog.get_import_filter_labels`、`documents.formats.get_import_wildcard_text`，以及 `prepare_document_for_save` 永遠為 `None` 的欄位）。以上都已記錄，避免後續任務誤以為漏刪而重新處理。
