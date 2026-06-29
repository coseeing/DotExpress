# Task 0 程式碼審閱報告

## 審閱範圍

- 完成資訊：`docs/superpowers/finish_task0.md`
- 設計規格：`docs/superpowers/specs/2026-06-27-translation-menu-settings-design.md`
- 實作計畫：`docs/superpowers/plans/2026-06-27-translation-menu-settings-implementation-plan.md`
- 文件列出的 commit：
  1. `078f2b2298998ecdd645d83e47c67944c4607eb8` — `feat: move translation controls to menu`
- 比較基準：`09e7a5a890976352cae2b8ce491855411f61a5dc`

`finish_task0.md` 只列出一個 commit，因此依 commit 時間由舊到新審閱時，實際審閱順序即為 `078f2b2`。未將其他 commit 納入本次審閱。

## Findings

### [P1] 字典管理動作不應直接改變目前的轉譯字典

**位置：**

- `client/gui.py:1195`
- `client/gui.py:1228`
- `client/gui.py:1263`
- `client/gui.py:1307`
- `client/gui.py:485-495`

`add_dictionary()`、`delete_dictionary_from_dialog()`、`rename_dictionary_from_dialog()` 與 `import_dictionary_from_dialog()` 成功後，都以管理清單的目標名稱呼叫 `_refresh_dictionary_names()`。該函式除了重載清單，也會：

1. 重建 `self.translation_settings`
2. 將 `selected_dictionary` 設為傳入的 preferred name
3. 呼叫 `set_selected_dictionary()` 寫入設定檔

因此會出現以下可重現行為：

- Translation Settings 目前選擇 `default`
- 開啟 Dictionary Management
- 新增 `math` 字典
- 未開啟 Translation Settings、也未按下其 `OK`
- 目前轉譯字典已被改成 `math`

重新命名或匯入字典也會把管理目標變成目前轉譯字典。刪除非目前使用中的字典時，則可能把目前轉譯字典改成 `plan_dictionary_delete()` 選出的 fallback。

這違反 spec 的狀態邊界：

- 字典選擇是 `Translation Settings...` 的 staged setting
- staged settings 只應在使用者按下 `OK` 後套用
- `Dictionary Management...` 負責字典生命週期，不應把管理清單選取混同為轉譯設定

**建議修正：**

- 將「重載字典名稱」與「變更目前轉譯字典」拆成兩個操作。
- Add、Import 成功後只更新管理清單的選取項目，不改變 active translation setting。
- Rename 僅在被重新命名的字典原本就是 active dictionary 時，將 active name 更新為新名稱。
- Delete 僅在被刪除的字典原本就是 active dictionary 時，才套用既有 fallback 規則；刪除其他字典時保留 active dictionary。
- 補上涵蓋上述四種情況的回歸測試。

在修正前，不建議將此功能視為符合已核准 spec。

### [P2] F6 的測試沒有覆蓋主視窗實際使用的導覽順序

**位置：**

- `client/ui/section_navigation.py:6-16`
- `client/tests/test_section_navigation.py:12-23`
- `client/gui.py:111-116`
- `client/gui.py:417-419`
- `client/gui.py:1119-1129`

`test_section_navigation.py` 驗證的是 `ui.section_navigation.SECTION_ORDER` 與 `get_adjacent_section()`，但 `BrailleFrame` 沒有使用這兩者。`gui.py` 另外定義了 `VISIBLE_SECTION_ORDER` 與 `_get_adjacent_visible_section()`。

目前兩份順序剛好相同，所以功能可依靜態檢查判定符合 spec；但測試通過不能證明主視窗的 F6 行為正確。未來只要其中一份順序改變，測試仍可能全部通過，而實際 UI 已產生不同結果。

**建議修正：**

- 讓 `BrailleFrame` 直接使用 `ui.section_navigation.SECTION_ORDER` 與 `get_adjacent_section()`。
- 不要在 `gui.py` 維護第二份 section order。
- 若保留 frame wrapper，測試至少應確認 wrapper 委派到共用 helper。

### [P2] 新增的核心 UI 流程缺少自動化回歸測試

**位置：**

- `client/tests/test_translation_menu.py:1-20`
- `client/tests/test_translation_settings.py:1-66`
- `client/dialog.py:537-789`
- `client/gui.py:1138-1165`
- `client/gui.py:1174-1332`

目前新增測試只驗證：

- 四個選單 descriptor 的固定順序
- translation settings 純資料的正規化與持久化
- section navigation 純函式

它們沒有驗證下列 spec 核心流程：

- `Translation` 選單項目實際綁定到正確 handler
- Translation Settings 的 `Cancel` 不改變 runtime/config
- Translation Settings 的 `OK` 才提交 staged settings
- Dictionary Management 動作後 list view 立即更新
- Dictionary Management 的 Edit 先關閉管理對話框，再開啟 `SpeechSymbolsDialog`
- 關閉 entry editor 後停留在主視窗
- `Ctrl+Enter` 和選單 Convert 使用同一轉換流程

這個缺口直接使第一項 finding 未被測試發現。wxPython UI 可保留 Windows smoke test，但 handler 的狀態轉換與 callback contract 應透過 mock dialog/callback 做自動化測試，不必依賴完整視窗繪製。

**建議修正：**

- 新增 frame orchestration 測試，mock `TranslationSettingsDialog`、`DictionaryManagementDialog` 與 `SpeechSymbolsDialog`。
- 新增字典管理 callback 測試，分別驗證管理清單 selection 與 active translation selection。
- 將 Windows UI smoke test結果補記於完成文件；目前 `finish_task0.md` 只列出命令，未記錄 spec 要求的手動 UI 驗收。

## Commit-by-commit 審閱

### 1. `078f2b2` — `feat: move translation controls to menu`

**符合規格的部分：**

- 已移除主視窗可見的 Conversion 列。
- 已新增頂層 Translation 選單，四個項目與順序符合 spec。
- Convert 保持第一層命令，`Ctrl+Enter` handler 仍保留。
- 已新增 Translation Settings modal dialog，主視窗只在 `wx.ID_OK` 分支提交設定。
- Translation Tables Setting 繼續使用既有 `TranslationTableDialog`。
- 已新增 Dictionary Management list view 與六個指定按鈕。
- Edit 在 `DictionaryManagementDialog` context 結束後才建立 `SpeechSymbolsDialog`，符合「先關閉管理，再開啟 editor」。
- F6 / Shift+F6 的實際順序已移除 Conversion。
- zh_TW `.po` 與 `.mo` 都包含新增字串。
- 沒有修改 conversion service、CSV 格式或輸出格式，也沒有引入大型 UI framework。

**需要修正的部分：**

- Dictionary Management 與 active translation dictionary 的狀態沒有真正分離，詳見 P1。
- section navigation 存在兩份 source of truth，詳見 P2。
- 新增 UI orchestration 缺少回歸測試，詳見 P2。

## 驗證結果

### 通過

```bash
python3 -m py_compile \
  client/gui.py \
  client/dialog.py \
  client/translation/settings.py \
  client/ui/translation_menu.py \
  client/ui/section_navigation.py \
  client/tests/test_section_navigation.py
```

結果：exit code 0。

```bash
cd client && python3 -m unittest \
  tests.test_translation_settings \
  tests.test_translation_menu \
  tests.test_section_navigation \
  tests.test_config \
  tests.test_dictionary_actions \
  tests.test_dictionary_manager \
  tests.test_input_shortcuts -v
```

結果：34 tests passed。

使用 Python `gettext.GNUTranslations` 讀取已提交的 `.mo`，確認 Translation、Convert、Translation Settings、Translation Tables Setting、Dictionary Management 及六個字典動作均有正確 zh_TW 翻譯。

### 未完全通過

```bash
cd client && python3 -m unittest discover -s tests -v
```

結果：執行 96 tests，3 個 import errors：

- `test_language_detection_translation`：缺少 `liblouis.dll`
- `test_translation_language_result`：module-level `pytest.skip` 被 unittest discovery 視為 import error
- `test_translation_result`：module-level `pytest.skip` 被 unittest discovery 視為 import error

這三項與 `finish_task0.md` 記錄一致，未發現是本 commit 新增的失敗；但此命令的實際 exit code 為 1，因此完成文件不應將它表述為通過的驗證。

環境未安裝 `msgfmt` / `msgunfmt`，無法重跑 plan 中的 gettext catalog 格式檢查。已改以 Python 標準庫成功載入 `.mo` 並驗證新增翻譯，但這不能取代 `msgfmt --check`。

## 整體結論

**審閱結論：需要修改。**

主要 UI 結構與大部分流程符合 spec，但 P1 會讓 Dictionary Management 繞過 Translation Settings 的 `OK` 提交邊界，造成使用者未明確確認就改變目前轉譯字典。應先修正該狀態耦合並加入回歸測試，再進行最終 Windows UI 驗收。
