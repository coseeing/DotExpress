# Windows 工具整理與在地化檔重產（W-3）設計

## 目標

任務 W-3 讓 `scripts\generate-pot.bat` 在每個 Windows checkout 上產生相同的範本，忽略 Windows 建置／執行後留下的未追蹤檔案，修正 readme 中過時的 `generate_pot.bat` 檔名，接著執行 Windows 驗證清單第 8 項（`docs/superpowers/history/2026-10-08-03-refactor-p2/review_task.md`）：重產 `dotexpress.pot`、以 `msgmerge` 合併 zh_TW 目錄並重編 `dotexpress.mo`。

不改任何 Python 正式程式碼。應用程式使用的 msgid 集合不變。

## 現況（2026-10-09 於 Windows 11、`main` `4b4a2b6` 驗證）

- **A. `generate-pot.bat`** 以 `for /r %%f in (*.py)` 列出原始檔，得到的是絕對路徑。xgettext 會原樣寫進參照，所以執行後是 `#: D:\workspace\DotExpress\client\about.py:10`，而已提交的 `client/locales/dotexpress.pot` 是 `#: about.py:22`。檔案順序是目錄走訪順序，也沒有傳 `--from-code`。排除條件 `\tests\` 比對的是絕對路徑，若 checkout 位於任何名為 `tests` 的目錄底下，就什麼也抽不到。`install.bat` 之後磁碟上會有 `client\braille\louis_helper.py` 與 `client\braille\liblouis\__init__.py`（git-ignored 的產生檔），但兩者沒有 `_()`／`N_()`／`gettext` 呼叫，不會增加 msgid 或參照。
- **B. Windows 建置／執行後的未追蹤檔：** `vendor/nvda/liblouis/dist/`（scons 輸出，`scripts\clean-liblouis.bat` 會刪除）、`/.sconsign.dblite`（repo 根目錄的 scons 資料庫）、`client/config.json`（`client/app_paths.py` 寫在 app root 旁的使用者設定；`git log --all -- client/config.json` 為空，從未被追蹤）。
- **C. 過時檔名：** `readme.md:175`、`docs/user/en/readme.md:175`、`docs/user/zh_TW/readme.md:177` 寫 `scripts\generate_pot.bat`，實際檔名是 `scripts\generate-pot.bat`。`docs/superpowers/plans/` 中較舊的計畫保留原名作為歷史。根目錄的 `AGENTS.md`（清單中也有提到）被 git-ignore，本任務不修改。
- **D. 目錄檔：** 已提交的 `.pot`（2026-07-20）有 357 個 msgid，原始碼標記了 353 個。多出的四個是 P1-2 留下的孤兒：`EPUB books (*.epub)|*.epub`、`PDF files (*.pdf)|*.pdf`、`Text files (*.txt)|*.txt`、`Word documents (*.docx)|*.docx`。155 筆的參照已過期（P0-6、P1-2、P1-4、P2-3 搬動了程式碼；其中 81 筆移到其他檔案，例如選項標籤移到 `settings/options.py`）。`.po` 的 `msgfmt --statistics`：356 已翻譯、1 未翻譯（`Close`，`dialog.py`）。`Close` 在 `38ae85f` 譯為 `關閉`，在 `b584278` 遺失；因此 zh_TW 下對話框的 Close 按鈕顯示英文（列於審查待辦第 4 列）。

## 決策

- **D1. 相對路徑、排序、UTF-8 抽取。** bat 去掉每個路徑的 `client\` 前綴、把 `\` 換成 `/`、捨棄以 `.venv/`、`tests/`、`build/`、`dist/` 開頭的路徑（相對於 `client\`，因此與 checkout 位置無關），以 `%SystemRoot%\System32\sort.exe /l C` 排序（與地區設定無關；用完整路徑以避開 Git for Windows 的 `sort`），再執行 `xgettext --language=Python --keyword=_ --keyword=N_ --files-from=... --from-code=UTF-8`。產生的 helper 檔不排除：它們沒有任何訊息，輸出已與乾淨 checkout 相同。
- **D2. 可選的輸出路徑。** `generate-pot.bat [output.pot]` 預設為 `locales\dotexpress.pot`；參數讓測試可產生到暫存檔。腳本回傳 xgettext 的結束碼。
- **D3. 回歸測試 `scripts/tests/test_generate_pot.py`**（只用標準函式庫，附最小 PO 讀取器）：
  1. `.pot` 每個參照都是相對於 `client`、使用正斜線的 `path.py:N`，指向存在的檔案且行號在檔案範圍內；
  2. `.pot` 的 msgid 集合等於 `client/` 中 `_()`／`N_()` 的字串常值（與 `test_i18n` 的 marker 測試相同走訪），可抓出孤兒與遺漏的 msgid；
  3. zh_TW `.po` 的有效 msgid 與 `.pot` 相同且順序一致，沒有 fuzzy 或空翻譯；
  4. 僅限 Windows 且 `PATH` 上有 xgettext：執行 bat 產生到暫存檔，結果與已提交的 `.pot` 項目相同（msgid、參照、flag、順序）。
  測試 1 到 3 在所有平台執行。
- **D4. 忽略規則放在檔案所在處。** 根目錄 `.gitignore`：`/.sconsign.dblite` 與 `/vendor/nvda/liblouis/dist/`。`client/.gitignore`：`/config.json`（加錨點，避免隱藏 `client/` 下其他 `config.json`）。`test_liblouis_build_contract.py` 的 ignore 斷言加入新規則。
- **D5. 以預設換行重產。** 已提交的 `.pot`／`.po` 使用 gettext 預設的 79 欄換行，所以 `msgmerge` 不加 `--no-wrap`。指令：`msgmerge --update --backup=none locales\zh_TW\LC_MESSAGES\dotexpress.po locales\dotexpress.pot`，接著 `msgfmt --check -o ...dotexpress.mo ...dotexpress.po`。四個孤兒變成 `#~` 項目。項目順序跟隨新的 `.pot`（檔案已排序），因此 diff 也會重排項目；msgid 與譯文不變。
- **D6. 恢復 `Close` → `關閉`**（`38ae85f` 的譯文），獨立一個 commit，讓目錄沒有未翻譯項目（AGENTS.md 在地化規則）。不更動其他譯文。

## 驗收條件

1. `scripts\generate-pot.bat` 寫出 `#: about.py:10`、`#: settings/options.py:71` 這類參照，沒有絕對路徑或反斜線，共 353 個 msgid；連續執行兩次，除 `POT-Creation-Date` 外輸出相同。
2. `.po` 的 `msgfmt --statistics`：353 已翻譯、0 未翻譯、0 fuzzy；四個孤兒為 `#~`。`.mo` 可用 `gettext.GNUTranslations` 載入，含 353 則訊息加 header，且能翻譯搬移過的標籤（例如現在參照 `settings/options.py` 的 `Light`）。
3. Windows 上 `scripts/tests` 全數通過（含 bat 測試）；`client` 的 `discover -s tests` 維持 `Ran 1143`、`FAILED (failures=1, errors=1, skipped=5)`（已知的 P2-5 與只改大小寫重新命名兩項）。
4. 合併後 `git status --short` 只列出未追蹤的 `client2/` 與 `preprocessing/`。fixture 的 sha256 不變。
5. 變更檔案：`scripts/generate-pot.bat`、`scripts/tests/test_generate_pot.py`、`scripts/tests/test_liblouis_build_contract.py`、`.gitignore`、`client/.gitignore`、三份 readme、`client/locales/dotexpress.pot`、`client/locales/zh_TW/LC_MESSAGES/dotexpress.po`、`client/locales/zh_TW/LC_MESSAGES/dotexpress.mo`、W-3 文件。

## 範圍外

- 審查第 4 列的其他在地化待辦（Export All 摘要、錯誤 fallback、`HTML` 標籤、匯入原因訊息）。
- 根目錄 `AGENTS.md`（git-ignored）與提到 `generate_pot.bat` 的歷史計畫。
- checkout 路徑含 `!`（delayed expansion）或非 ASCII 字元的情況。
