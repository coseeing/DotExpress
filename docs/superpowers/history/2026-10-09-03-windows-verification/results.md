# Windows 驗證記錄（HANDOFF §4.1–4.2）

- 日期：2026-10-09
- 環境：Windows 11 Pro 10.0.26200；`client\.venv`（Python 3.13.13、wxPython 4.2.5 msw）；VS 2022 Build Tools + clang-cl；`core.autocrlf=true`。
- 起點：`main` 的 `d0ae3b4`（剛 clone 的工作目錄，`client\braille\` 尚無產生檔）；終點：`115f57f`（W-1～W-3 merge 後）。
- 本記錄涵蓋可自動執行的項目；需要 packaged build、NVDA 或人工操作的項目列在最後「尚待人工執行」。

## 1. HANDOFF §4.1：`python gui.py` 啟動

| 步驟 | 結果 |
| --- | --- |
| `scripts\verify-liblouis-export-state.bat`（建置前） | `Missing current DLL`：全新 clone，`client\braille\liblouis.dll` 不存在（不是舊 DLL） |
| `scripts\clean-liblouis.bat` → `build-liblouis.bat` → `install.bat` | 三者皆 exit 0（vcvarsall 印出的 `'vswhere.exe' is not recognized` 為無害訊息） |
| `verify-liblouis-export-state.bat`（建置後） | 9 個符號全部 `OK`（含 `lou_freeTableInfo`）；NVDA reference DLL 不存在，僅檢查目前 DLL |
| `pip install -r client\requirements.txt` | 裝進原本空的 `client\.venv` |
| `python gui.py`（`client\`） | 啟動成功，視窗標題 `new - DotExpress`；`log\init.log` 只有 server 端 `/client/init` 回 404 的記錄（非致命） |
| 真 liblouis 冒煙測試 | 中文預設、UEB g1、UEB g2（`the`→`⠮`）、中英混排皆正確；liblouis `3.37.0` |

## 2. Windows 驗證總清單（P2 記錄 1–16）與 delta（F 記錄 17–29）中可自動執行的項目

| # | 結果 |
| --- | --- |
| 1 | `4.2.5 msw (phoenix) wxWidgets 3.2.9 False` ✔ |
| 2 | `fc /b client\braille\louis_helper.py vendor\nvda\liblouis\runtime\louis_helper.py`：`no differences encountered` ✔ |
| 3 | sha256：`client\braille\liblouis\__init__.py` `8e2f911f27725be9d18e792b4c011a64d195cc16b0f9c2cebfe37e842e93cde4`；`louis_helper.py` `e2107d59c5c0cd5767ff54df30bd78c7acad0686ae1159d928077f8e73c47739`；`liblouis.dll` `31178a5bb52e8fdc76da08a4cf601b343af23821fb85941159def744807a4e55`（工作目錄 CRLF 位元組） |
| 4 | W-1 前：module-level `SkipTest` 直接中斷，0 個測試執行（見 §4 F-W1）。W-1＋W-2 後：`Ran 7`，全部通過 |
| 5 | `Ran 43`，`OK` |
| 6 | W-2 後：`Ran 1143`，`failures=1, errors=1, skipped=5`。failure＝已知 P2-5 測試；error＝`test_dictionary_name_prompt ... test_case_only_rename_still_renames`（既有缺陷）；5 個 skip 皆為平台 skip（4 個 POSIX permission bits、1 個 case-insensitive FS）。原本 7 個 liblouis skip 已消失 |
| 7 | 見 §3（source run；packaged build 的部分尚待人工） |
| 8 | W-3 完成：`.pot` 353 msgid、參照改為 client 相對路徑並移到 `settings/options.py`；四個孤兒在 `.po` 變為 `#~`；`msgfmt --statistics` 353 translated、0 untranslated、0 fuzzy；`.mo` 以 `gettext.GNUTranslations` 載入驗證；readme 檔名已修 |
| 17 | `Ran 253`：預期中的 `test_case_only_rename_still_renames` error 出現；另 2 個 HTML 匯出 CRLF failure 由 W-2 修正（測試假設，非 regression）。`MoveDocumentPackageTest`、case-only rename 等 NTFS 測試全數通過 |
| 22 | `Ran 162`，`OK (skipped=3)`（A8–A10 POSIX only） |

`scripts/tests`（W-3 後）：`Ran 33`，`failures=1`，唯一失敗為 `test_vendor_helper_snapshot`（見 §4 F-W5）。

兩份 fixture（以 `git show HEAD:<path> | sha256sum` 計算）全程不變：`translation_golden.json` `e67d95a1…211ccd`、`dictionary_entries_trace.json` `f493da52…c66c2cf`。工作目錄的 sha 不同，是 `core.autocrlf=true` 造成的 CRLF，`git diff` 為空。

## 3. P2-5 基線（真 liblouis／MathCAT，source run）

重現方式（repo root）：

```bat
client\.venv\Scripts\python.exe docs\superpowers\history\2026-10-09-03-windows-verification\p25_baseline.py <out_dir>
client\.venv\Scripts\python.exe docs\superpowers\history\2026-10-09-03-windows-verification\p25_perf.py <out_dir> 100 400 1600
```

輸入文件 `p25_doc.txt`（sha256 `d287af56…5fa4a2`），輸出存在 `baseline/`（`.gitattributes` 設為 `-text`，位元組不轉換）。設定：預設翻譯表、`lang=zh_TW`、預設 charset maps、無使用者字典、寬度 40。

### A. 一次翻譯 vs 拆開翻譯（`zh-tw.ctb`，mode=4）

| 輸入 | 一次 | 拆開 | 相同 |
| --- | --- | --- | --- |
| `" 的值"`（`" "`＋`"的值"`） | `⠀⠙⠮⠁⠁⠱⠂` | `⠀⠙⠮⠁⠁⠱⠂` | ✔ |
| `"  中文"`（`"  "`＋`"中文"`） | `⠀⠀⠁⠯⠄⠿⠂` | `⠀⠀⠁⠯⠄⠿⠂` | ✔ |
| `"計算 "`（`"計算"`＋`" "`） | `⠅⠡⠐⠑⠻⠐⠀` | `⠅⠡⠐⠑⠻⠐⠀` | ✔ |

`" 的值"` 一次翻譯的 `raw_to_braille` 為 `[0, 1, 4]`：空白本來就是獨立 token。

### B. 失敗測試的輸入走真實 pipeline

`"計算 $1+2$ 的值"` → raw `['計', '算', ' ', '1+2', ' ', '的', '值']`，braille `⠅⠡⠐⠑⠻⠐⠀⠼⠁⠐⠖⠼⠃⠀⠙⠮⠁⠁⠱⠂`。空白沒有重複，且在真 adapter 下獨立成段。這證實 P2 review 的分析：失敗測試的差異只存在於 fake translator 的「一次呼叫＝一個 token」模型。建議 P2-5 依原建議放寬斷言（比對 join 後的 raw／braille），並加特性測試鎖住空白獨立成段。

### C. 混排長文件

| 模式 | BRL sha256（CRLF，與 BRL 匯出相同） | `reclean_braille_endspace` trim |
| --- | --- | --- |
| unicode | `365d28a9244a1ef79ab90c783a0a152fa4be26c12d3894862712fab63f9d683c` | 13 個 token／13 cells |
| ascii | `95b9a1a6bdb7956d2be0cd1c9eddd7670c606e9e4591116149813a0c2538bc64` | 13 個 token／13 cells |

被 trim 的全部是 zh-tw.ctb 輸出時尾端帶一個空白 cell 的 token：全形空白 `　`、`，`、`。`、`（`、`）`。在一般中文文字中，大約每 20 字就會有一次 trim。

### D. `reclean_braille_endspace` 效能（P1-5 defect 3）

純中文段落重複 N 次（`p25_perf.py`）：

| 字元數 | 翻譯 | wrap 合計 | 其中 reclean |
| --- | --- | --- | --- |
| 5,200 | 0.42 s | 0.13 s | 0.11 s |
| 20,800 | 1.03 s | 1.88 s | 1.81 s |
| 83,200 | 4.17 s | 28.92 s | 28.55 s |

長度 ×4 時 reclean 約 ×16，確認是二次方，且在真實輸出上 trim 密度很高：8 萬字的文件光 reclean 就要約 29 秒，是翻譯本身的 7 倍。**建議把 P1-5 defect 3 從「優先 6（效能）」提升，並在 P2-5 一併改為線性（一次掃描並累計位移）**，golden fixture 與本基線的 BRL sha256 作為不變條件。

## 4. 本次發現

| ID | 內容 | 處理 |
| --- | --- | --- |
| F-W1 | Windows 11 內建 Microsoft 簽章的 `C:\Windows\System32\liblouis.dll`（舊 ABI，缺 `lou_freeTableFile`／`lou_freeTableInfo`）。產生的 binding 以裸名 `liblouis.dll` 載入。有 3 個測試先直接 `from braille import liblouis`，結果載到 System32 那份，而且同一個 process 之後經 `louis_helper` 的載入也被它污染。Production 只經 `louis_helper`（`os.add_dll_directory`），不受影響 | W-1（`9a4ae81`）：測試只經 `louis_helper`，並加上 AST 防護測試。後續建議：在產生器讓 binding 以絕對路徑載入 DLL |
| F-W2 | 6 個測試預期帶 Linux 假設（HTML 匯出 LF、瀏覽器路徑 `/`、`os.path.join`、`AC_INIT([Liblouis]` 大小寫）。production 行為與 `6e5819f` 相同 | W-2（`4b4a2b6`） |
| F-W3 | `generate-pot.bat` 在 Windows 寫出 `#: D:\workspace\...` 絕對參照；`.gitignore` 缺 `vendor/nvda/liblouis/dist/`、`/.sconsign.dblite`、`client/config.json`；三份 readme 寫成 `generate_pot.bat` | W-3（`115f57f`） |
| F-W4 | `Close` 在 `b584278` 遺失 zh_TW 翻譯（對話框 Close 按鈕顯示英文；缺陷清單第 4 項之一） | W-3 的 `411261a` 補回 |
| F-W5 | `scripts/tests` 的 `test_vendor_helper_snapshot` 在 Windows 失敗：`vendor/nvda/liblouis/runtime/louis_helper.py` 在 index 是 LF、工作目錄被 autocrlf 轉成 CRLF，正規化換行後內容相同 | 未處理；建議 `.gitattributes`（`eol=lf`）或測試正規化換行 |
| F-W6 | 字典改名只差大小寫（`alpha`→`Alpha`）在 Windows 上被 `FileExistsError` 擋下（`test_case_only_rename_still_renames`）。使用者可見：無法只改字典名稱的大小寫 | 既有缺陷，未處理 |
| F-W7 | 文字中的 `$` 一律視為 LaTeX 分隔：`NT$ 1,234 元…` 會從 `$` 起一路到下一個 `$`（可跨行）當成數學式，中文原樣輸出 | 既有行為，記錄；是否需要跳脫規則由使用者決定 |
| F-W8 | source run 時 `config.json`、`log\` 寫在 `client\` 底下（`app_paths` 以 app root 為準） | 符合設計；W-3 已 ignore `config.json` |

## 5. 尚待人工執行（需 packaged build、NVDA 或互動操作）

逐步操作與記錄欄見同資料夾的 `test.md`。

- **7**：packaged build 轉換 `p25_doc.txt`，比對 BRL sha256 是否等於 §3 C 的值（若不同，先確認寬度、翻譯表與字典設定一致）。
- **9–16**：packaged build 的路徑、對話框、字典編輯器、設定面板、字型同步、轉換與退出、選單與匯出、P0-5／P0-6 流程。
- **18–21**：F-1 在 NTFS 上的 case-only rename（含 7-Zip 鎖檔、唯讀屬性、即時防毒）。
- **23–29**：F-2 字典 OK 的位元組比對、Excel／記事本 BOM、鎖檔、唯讀、隱藏、防毒、ACL deny write。
