# Task 1 修正程式碼審閱結果

## 審閱結論

**結果：修正方向正確，但尚未完成，不建議目前接受／合併為完成狀態。**

Task 1 已實質修正前次 review 的三項程式碼層 Critical：

- SConscript 不再保留 NVDA-only test table 區塊，並會回傳 build outputs。
- 最小 SCons environment 已補入 NVDA liblouis 繼承的關鍵 defines、CRT 與 link flags。
- runtime helper 已改為只從 pinned NVDA `louisHelper.py` 做 deterministic 轉換，不再讀取 DotExpress HEAD。

但前次兩項 runtime／驗證問題仍未關閉。目前 repository 中的 `liblouis.dll` 可辨識為 **3.35.0**，而 pinned `include/liblouis` source 是 **3.37.0**；tables 也沒有在本次 commit 重建。這仍是原始需求要排除的 DLL、wrapper、helper、tables 版本漂移。此外，新增的 runtime test 只檢查版本字串非空，即使在 Windows 執行，也無法偵測 3.35.0 DLL 搭配 3.37.0 source 的錯誤。

## 審閱範圍與 commit 順序

依 `docs/superpowers/finish_task1.md` 列出的 commit subject，解析出以下 commit，並按實際時間由舊到新審閱：

1. `e29a90c5aa7e083524938a64c781a6f1ae32e4bc` — `fix: align nvda liblouis sync and build contract`
2. `2647afc74181d6d0a6f4979f56b818b716f877a4` — `docs: record review task 1 results`

對照文件：

- `docs/superpowers/review_task0.md`
- `docs/superpowers/specs/2026-06-28-nvda-aligned-liblouis-build-design.md`
- `docs/superpowers/plans/2026-06-28-nvda-aligned-liblouis-build-implementation-plan.md`

工作目錄中未提交的 spec、中文版 spec、`readme.md`、`chat.txt` 與 `ref/` 不屬於這兩個 commit，未納入 findings，也未被修改。

## 前次 findings 狀態

| Task 0 finding | Task 1 狀態 | 判定 |
|---|---|---|
| SConscript 保留未定義的 `unitTestTablesDir`，且沒有回傳 outputs | 已移除完整 test block，加入 `Return("louisLibInstall", "louisPython", "louisTables")` | **程式碼層已修正；待 Windows SCons graph 驗證** |
| 最小 SCons environment 缺少 NVDA 前置設定 | 已加入 `UNICODE`、Windows target defines、`/MT`、release/link flags | **程式碼層已修正；待實際 compile/link command 驗證** |
| helper 從 `git show HEAD:client/...` 取得 | 已改為 deterministic source transformation，並新增 cwd isolation 測試 | **已修正** |
| 新 source 沒有相符 DLL／tables，且 tables 不會清理 stale files | 本次沒有重建 DLL／tables，也沒有加入清理機制 | **未修正** |
| 缺少 Windows runtime／ABI 測試與執行證據 | 已新增測試檔，但 Linux 全部 skip；尚無 Windows clean build／runtime 結果 | **部分修正** |

## Findings

### Critical — 目前 runtime artifacts 仍與 pinned source 不一致

位置／證據：

- `include/liblouis/configure.ac:4`：`AC_INIT([Liblouis], [3.37.0], ...)`
- `client/braille/liblouis.dll`：binary strings 顯示 `3.35.0`
- `e29a90c` 沒有修改 `client/braille/liblouis.dll`
- `e29a90c` 沒有修改 `client/braille/liblouis/tables/**`
- `e29a90c` 已修改 `client/braille/louis_helper.py`

本次修正讓 helper 更接近 pinned NVDA source，但產品仍會載入舊 DLL 與舊 tables。也就是：

```text
source / wrapper / helper：NVDA 選定的 liblouis 3.37.0 世代
DLL：3.35.0
tables：未證明由 3.37.0 source 產生
```

這不是單純缺少測試證據；目前 repository 實際內容就是不一致的 runtime bundle。雖然目前 wrapper 所引用的 DLL symbols 在舊 DLL 中可能仍存在，這不能保證 callback、table syntax、資料結構與行為相容。

這項問題在 Task 0 已被指出，Task 1 沒有修正；而 helper 更新後，runtime components 的世代差距更明確。

建議：

1. 在 Windows x64 以修正後流程執行 clean build。
2. 確認產出的 `client/braille/liblouis.dll` 回報 `3.37.0`。
3. 重新產生完整 tables，並與 DLL、wrapper、helper 一起提交或由 packaging pipeline 強制重建。
4. 在完成上述事項前，不應把 Task 1 或整體 migration 標示為完成。

### Important — 新增的 runtime test 無法偵測 DLL/source 版本 mismatch

位置：

- `client/tests/test_liblouis_runtime.py:21-25`

目前版本測試只有：

```python
self.assertTrue(self.louis.version())
```

因此目前的 3.35.0 DLL 仍可通過此 assertion。即使補到 Windows 執行這五個測試，只要基本 API 和三張舊 tables 還能運作，測試就可能全部通過，但 build artifact 仍不是由 pinned 3.37.0 source 產生。

建議讓測試取得 expected version，例如解析 `include/liblouis/configure.ac`，再明確比對：

```python
self.assertEqual(expected_version, self.louis.version())
```

若 packaged test 不應依賴 source tree，則 build 時產生一份 runtime provenance 檔，記錄 NVDA commit、liblouis commit 與 liblouis version，再由測試核對 DLL version。

這個 assertion 應是 release-blocking，因為它直接驗證本任務最重要的 matched-runtime 契約。

### Important — tables 安裝仍不會移除 stale／被排除的舊檔

位置：

- `vendor/nvda/liblouis/build/sconscript:110-126`
- `sconstruct:50-52`
- `client/braille/liblouis/tables/`

修正後的 SConscript 會建立並回傳 table install nodes，但仍只執行 `env.Install`／`env.M4`，沒有在安裝前清空 runtime tables 目錄。

目前 tracked runtime 目錄仍含：

- `Makefile.am`
- `README`
- `maketablelist.sh`
- 多個 `.in` 檔

而同步後的 NVDA SConscript 明確不安裝這些檔案。這證明舊 runtime tree 不會自動收斂成目前 source 所定義的輸出集合。未來上游刪除或改名 table 時，舊檔也會殘留。

建議新增受控 cleanup target／pre-action：

1. clean build 時先移除 `client/braille/liblouis/tables/`。
2. 再由 SCons 安裝非 `.in` tables 並產生 `.in` 對應輸出。
3. 新增測試或 build 後驗證，禁止 `Makefile.am`、`README`、`maketablelist.sh` 與 `.in` 出現在 runtime tables。

注意：cleanup 必須納入 SCons dependency/order，不能只靠開發者手動刪除，否則一般 build 與 packaging build 仍可能使用 stale tables。

### Important — SConscript 的關鍵文字轉換沒有逐項確認成功

位置：

- `scripts/sync_nvda_liblouis.py:61-108`

`_adapt_sconscript()` 會將三段 NVDA code 改成：

- `louisLibInstall = env.Install(...)`
- `louisTables = env.Install(...)`
- 將 `env.M4(...)` outputs 加入 `louisTables`

但這三次 `source.replace(...)` 沒有像其他 adaptation marker 一樣檢查原始區塊存在，也沒有檢查 replacement count。若未來更新 NVDA commit 時只有排版、註解或區塊形狀改變，sync 仍可能成功寫出：

```python
Return("louisLibInstall", "louisPython", "louisTables")
```

而 `louisLibInstall` 或 `louisTables` 沒有被定義。現有 `compile()` 測試抓不到 runtime name resolution；現有測試也只確認 `Return(...)` 字串存在。

這是這次修正新增的升級風險。建議：

1. 對每個多行 replacement 先要求 `source.count(old) == 1`，否則丟出 `SyncError`。
2. 轉換完成後確認舊區塊不存在，且三個新 assignment／Return 均恰好出現一次。
3. 新增測試：任意改動其中一個 NVDA install block 後，sync 必須 fail fast，而不是產生延遲到 Windows build 才出錯的 SConscript。

### Important — 完成資訊正確揭露限制，但仍不足以宣告修正完成

位置：

- `docs/superpowers/finish_task1.md:34-41`

完成資訊有正確說明目前不是 Windows，尚未執行：

- `scripts/build-liblouis.bat`
- `scons --no-exec`
- DLL rebuild
- Windows runtime ABI verification

這項揭露是正確的，但也代表 spec 的成功條件尚未達成：

- SCons Windows x64 build 成功；
- DLL 重新產生；
- tables 刷新；
- 中文、UEB grade 1、UEB grade 2 使用新 runtime 通過。

因此文件名稱可以保留為 Task 1 的修正紀錄，但整體狀態應標示為「程式碼修正完成，等待 Windows build/runtime verification」，不應視為 NVDA-aligned liblouis migration 已完成。

## 是否因 Task 1 引入新問題

Task 1 沒有發現會破壞既有非 Windows client 邏輯的明確回歸；helper 的主要行為變更均可追溯到 pinned NVDA source。

但有兩項新增風險：

1. `_adapt_sconscript()` 新增三段未驗證是否命中的多行 replacement，未來 NVDA 升級可能產生表面同步成功、實際 SCons evaluation 失敗的 vendor snapshot。
2. helper 已更新而 DLL/tables 未更新，使目前 repository 的 runtime bundle 世代差距更加明確；在 Windows 實際載入前不能假設 ABI／行為相容。

## Commit-by-commit 摘要

### `e29a90c` — 修正 sync 與 build contract

已確認的正向修正：

- `unitTestTablesDir` 與 NVDA custom test block 已從 vendor SConscript 移除。
- SConscript 已回傳 DLL、wrapper 與 table nodes。
- `UNICODE` 前置狀態可滿足 NVDA liblouis SConscript 的 `remove("UNICODE")`。
- `/MT`、release、Windows target 與主要 link flags已補入。
- `_adapt_helper()` 現在確實使用傳入的 NVDA source。
- cwd isolation 與 source propagation 測試有效覆蓋前次 helper 問題。
- runtime smoke test 覆蓋中文、UEB grade 1／2 和 resolver 基本路徑。

尚未完成／新風險：

- 沒有 Windows SCons graph、compile 或 link 證據。
- 沒有重建 DLL／tables。
- runtime test 不核對 DLL 與 pinned source version。
- table output 沒有 stale cleanup。
- SConscript 新增的多行 replacement 沒有 fail-fast marker 驗證。

### `2647afc` — Task 1 完成紀錄

commit 順序與內容正確，並如實揭露非 Windows 環境限制。問題在於「已處理 findings」容易被理解為全部關閉；實際上 runtime artifacts 與 Windows verification 仍是 open status。

## 已執行驗證

### 自動化測試

```text
python3 -m unittest \
  scripts.tests.test_sync_nvda_liblouis \
  scripts.tests.test_liblouis_build_contract -v
```

結果：**11 tests passed**。

```text
cd client
python3 -m unittest tests.test_liblouis_runtime -v
```

結果：**5 tests skipped**，原因為目前平台不是 Windows。這不是 runtime pass。

### 同步與 provenance

```text
cmp vendor/nvda/liblouis/runtime/louis_helper.py \
    client/braille/louis_helper.py
```

結果：一致。

```text
client/braille/liblouis/__init__.py
==
vendor/nvda/liblouis/python/__init__.py.in
    將 ###LIBLOUIS_SONAME### 替換為 liblouis.dll
```

結果：一致。

### 版本檢查

```text
rg '^AC_INIT' include/liblouis/configure.ac
```

結果：pinned source version 為 `3.37.0`。

```text
strings client/braille/liblouis.dll | rg '3\\.[0-9]+\\.[0-9]+'
```

結果：現有 DLL version 為 `3.35.0`。

### 其他檢查

```text
git diff --check 9fbb8bd..2647afc
```

結果：通過，沒有 whitespace error。

## 下一次 review 的接受條件

1. `_adapt_sconscript()` 對所有關鍵多行 replacements 做 exact-count／fail-fast 驗證。
2. 建置流程可 deterministic 清除 stale runtime tables。
3. 在 Windows x64 執行 `scons --no-exec` 並成功建立完整 graph。
4. 在 Windows x64 clean build 產生 `liblouis.dll`、wrapper、helper 與完整 tables。
5. DLL version 與 pinned source version 明確一致，目前應為 `3.37.0`。
6. Windows runtime tests 實際通過，不是 skip；並加入 DLL/source version equality assertion。
7. 執行既有 braille／translation regression tests，至少包含中文、UEB grade 1、UEB grade 2。
8. 更新完成紀錄，附上 Windows 命令、結果與產物 provenance。
