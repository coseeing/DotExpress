# Dialog Display Optimization 完成摘要

本次實作已依照 spec / plan 完成，重點如下：

- 新增 `finalize_dialog_layout()`，統一 custom dialog 的 `Fit + center` 收尾流程。
- `AddSymbolDialog`、`DictionaryNameDialog`、`DocumentNameDialog`、`InvalidWorkspaceFilesDialog`、`FileIssuesDialog`、`TranslationSettingsDialog`、`TranslationTableDialog`、`ConvertingDialog` 都改為使用共用收尾流程。
- 將 `SpeechSymbolsDialog` 的初始化尺寸改成內容驅動，保留三欄 virtual list 與既有互動。
- 抽出共用的 `load_dictionary_entries()` 與 `normalize_entry_type()`，讓 dictionary editor 與 count 顯示共用同一套有效列規則。
- 將 `DictionaryManagementDialog` 改成 two-column virtual list，顯示 `Dictionary` 與 `Entries`，並改成依可視寬度重算欄寬。
- `DictionaryManagementDialog` 的刷新流程改為 `SetItemCount()` / `Refresh()`，並在開啟與刷新時同步計算每個 dictionary 的 entry count。
- 移除 list double-click 直接編輯，維持只有 `Edit` 按鈕進入 entry editor。
- `DualViewFrame` 改為直接採用主視窗目前的 position / size，讓 Dual View 覆蓋主視窗區域。
- 已更新 `dotexpress.pot`、`zh_TW` `.po` 與 `.mo`，補上 `Entries` 的翻譯。

驗證結果：

```bash
cd client && python3 -m unittest \
  tests.test_dialog_display \
  tests.test_speech_symbols_dialog \
  tests.test_dictionary_management_dialog \
  tests.test_dual_view_frame \
  tests.test_gui_document_flows \
  -v
git diff --check
python3 - <<'PY'
import gettext
with open('client/locales/zh_TW/LC_MESSAGES/dotexpress.mo', 'rb') as fp:
    tr = gettext.GNUTranslations(fp)
assert tr.gettext('Entries') == '條目數量'
PY
```

補充：

- 這個環境沒有 `msgfmt`，因此 `.mo` 以 Python fallback 方式重新編譯，並用 `gettext.GNUTranslations` 驗證載入成功。
- `python3 -m unittest discover -s tests -v` 仍有數個與本次變更無關的既有測試環境失敗，主要集中在 importer 測試所使用的 stub / fixture 行為；本次變更相關的 focused tests 已通過。

新增 commit list：

- `feat: optimize dialog display and dictionary management`
- `docs: record dialog display optimization summary`
