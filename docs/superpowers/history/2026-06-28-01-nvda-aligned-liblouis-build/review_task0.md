# Task 0 程式碼審閱結果

## 審閱結論

**結果：不建議接受／合併。**

目前變更尚未達成「可由 NVDA 對齊流程成功建置 liblouis」的核心目標。SCons graph 在進入編譯前即會失敗；Python helper 的同步來源也是循環依賴於既有 DotExpress 檔案，而非由 NVDA source 產生。此外，新的 liblouis submodule 已釘選，但提交中沒有對應重建的 DLL、tables 或 Windows runtime 驗證。

## 審閱範圍與順序

依 `docs/superpowers/finish_task0.md` 列出的 commit，按 commit 時間由舊到新審閱：

1. `d6cb640543fb9cdedb7b7ea6382c3ce6cd208961` — `build: pin nvda liblouis sources`
2. `48d5646392a1bd29fec670e9911cae24ece937d5` — `build: add nvda liblouis sync tool`
3. `3f807ef4409f59ddfcffc52bf7f39aec61ea2e24` — `build: replace liblouis nmake flow with scons`
4. `b4532999960e48f118cde83594e6c60ee17d1abd` — `build: sync nvda liblouis integration`
5. `9fbb8bd5be6009126c9072e37a81ae26d57abe31` — `docs: describe nvda-aligned liblouis workflow`

對照文件：

- `docs/superpowers/specs/2026-06-28-nvda-aligned-liblouis-build-design.md`
- `docs/superpowers/plans/2026-06-28-nvda-aligned-liblouis-build-implementation-plan.md`

工作目錄中未提交的 spec、中文版 spec、`readme.md`、`chat.txt` 與 `ref/` 變更不列入這五個 commit 的審閱內容，也未被修改。

## Findings

### Critical — 同步後的 SConscript 必定在建置圖建立階段失敗

位置：

- `scripts/sync_nvda_liblouis.py:45-59`
- `vendor/nvda/liblouis/build/sconscript:127-137`
- `sconstruct:37-39`

`_adapt_sconscript()` 刪除了：

```python
unitTestTablesDir = env.Dir("#tests/unit/brailleTables")
```

但保留後段對 `unitTestTablesDir` 的使用，因此 SCons 執行到 custom test table 區塊時會產生 `NameError`。

此外，同步後的 `sconscript` 沒有 `Return(...)`，根層卻執行：

```python
outputs = SConscript(...)
Default(*outputs, helper)
```

即使先修掉 `unitTestTablesDir`，`outputs` 仍會是 `None`，接著在 iterable 展開時產生 `TypeError`。這兩個問題都發生在真正呼叫 `clang-cl` 之前。

現有 `test_synced_sources_compile` 只使用 Python `compile()` 檢查語法；`test_liblouis_build_contract` 只搜尋文字，所以無法發現 SCons evaluation 錯誤。

建議：

1. 同步時從 `# Custom tables unit test` 起移除完整的 NVDA-only test table 區塊。
2. 在同步後的 `sconscript` 明確加入 `Return("louisLib", "louisPython")`，或讓根 SConstruct 不展開未回傳值。
3. 在 Windows CI／測試環境執行至少一次 `scons --no-exec`，驗證整個 build graph，而非只編譯 Python 語法。

### Critical — 最小 SCons environment 沒有提供 NVDA SConscript 所依賴的編譯環境

位置：

- `sconstruct:21-34`
- `vendor/nvda/liblouis/build/sconscript:61-80`
- 參考來源：`include/nvda/nvdaHelper/archBuild_sconscript:92-103,169-178`

NVDA 先在 `archBuild_sconscript` 加入 `UNICODE`、Windows target defines、link flags 與 `/MT`，再 clone 成 `thirdPartyEnv`。liblouis 的 `sconscript` 因此直接執行：

```python
env["CPPDEFINES"].remove("UNICODE")
```

DotExpress 則直接從裸的 `Environment(...)` 建立 `thirdPartyEnv`，沒有加入 `UNICODE`。因此在修正前一項錯誤後，這裡仍會因缺少 `UNICODE` 而失敗。

更重要的是，DotExpress 未帶入 NVDA 的 `/MT` CRT 選擇及相關架構／link 設定，實際編譯參數並未達成「與 NVDA 對齊」。這不是單純補一個 key 即可；應明確整理 NVDA liblouis 所繼承的最小環境契約，並透過測試比對關鍵 flags。

建議：

1. 在 DotExpress SConstruct 重建 NVDA liblouis 真正依賴的最小 `thirdPartyEnv`，至少包含 `UNICODE` 的前置狀態與 NVDA 的 CRT／架構 flags。
2. 記錄並測試最終 `CCFLAGS`、`CPPDEFINES`、`LINKFLAGS`，避免只有 `sconscript` 檔案相似、實際編譯命令不同。
3. 用 Windows `scons -n` 輸出和同一 NVDA commit 的 liblouis compile/link command 做差異檢查。

### Critical — Python helper 並未從 NVDA source 同步

位置：

- `scripts/sync_nvda_liblouis.py:62-78`
- `scripts/sync_nvda_liblouis.py:119-125`
- `scripts/tests/test_sync_nvda_liblouis.py:127-141`

`_adapt_helper(source)` 只確認 NVDA source 含有幾個 marker，之後完全不使用 `source`，而是執行：

```python
git show HEAD:client/braille/louis_helper.py
```

這造成以下問題：

- `vendor/nvda/liblouis/runtime/louis_helper.py` 實際來自目前 DotExpress HEAD，不是固定 NVDA commit。
- NVDA helper 的 API、callback、resolver 或新增函式即使改變，同步結果仍會靜默保留舊 helper。
- `synchronize(root=...)` 不具 root 隔離性；結果取決於 process current working directory 所在 Git repository。
- 在尚未包含 `client/braille/louis_helper.py` 的新 repository、detached fixture 或從其他目錄呼叫時可能直接失敗。

目前測試也以真實 DotExpress checkout 的 `git show HEAD` 作為隱藏外部來源，因此測到的是「舊檔可被複製」，而不是「NVDA helper 可被 deterministic adaptation」。

這直接違反 spec 中「native build integration 與 Python wrapper/helper 必須一起同步」的核心要求。

建議：

1. `_adapt_helper()` 必須只由傳入的 NVDA `source` 產生結果。
2. 將 DotExpress 相容調整改為明確、具 marker 驗證的文字轉換，或維護一份可審查且可 deterministic 套用的 patch。
3. 測試 fixture 不得讀取目前 repository HEAD；應建立內容不同的 NVDA helper，斷言其函式／變更確實出現在 runtime helper。
4. 增加從非 repository current directory 呼叫 `synchronize(root=temp_root)` 的測試。

### Important — 已更新 liblouis source，但沒有提交相符的 DLL 與 tables

位置／證據：

- `d6cb640` 將 `include/liblouis` 從 `466c4c8...` 更新為 `2aa5f84...`。
- `b453299` 只更新 `client/braille/liblouis/__init__.py` 與 `vendor/nvda/liblouis/**`。
- `client/braille/liblouis.dll` 和 `client/braille/liblouis/tables/**` 未出現在任何完成文件列出的 commit。

因此目前版本庫中的 DLL／tables 並不能證明是由新的 `2aa5f84...` source 產生。這正是原始需求要避免的 DLL、Python wrapper 與 tables 版本漂移。

而且新 SCons 流程只有 `Install`，沒有在安裝前清空 `client/braille/liblouis/tables/`。現有目錄仍包含 `Makefile.am`、`README`、`maketablelist.sh` 與 `.in` 檔；這些都被 NVDA SConscript 明確排除。即使建置修好，舊檔與上游已刪除的 table 也可能繼續殘留。

建議：

1. 修好 build graph 後，在 Windows x64 clean environment 重建 DLL、wrapper 與完整 tables。
2. 安裝 tables 前先以受控方式清空目標目錄，避免上游刪除／改名的檔案殘留。
3. 驗證輸出中沒有 NVDA 已排除的 `.in`、`Makefile.am`、`README`、`maketablelist.sh`。
4. 若 repository 政策是追蹤 runtime artifacts，應將相符產物和 source pointer 一起提交；若不追蹤，則 packaging pipeline 必須在封裝前強制重建且不得使用舊檔。

### Important — 缺少 plan 要求的 Windows runtime／ABI 驗證，完成紀錄不足以證明功能完成

位置：

- `docs/superpowers/finish_task0.md`
- 缺少：`client/tests/test_liblouis_runtime.py`
- `scripts/tests/test_liblouis_build_contract.py:8-32`

implementation plan 要求新增 Windows-only runtime 測試，至少覆蓋：

- 新 wrapper 可載入新 DLL；
- table resolver 可找到 bundled tables；
- 中文預設表；
- UEB grade 1；
- UEB grade 2 contraction。

實作沒有新增該檔案。完成紀錄列出的驗證只有兩個 source-level unittest、sync 和 diff，沒有：

- `scripts/build-liblouis.bat`；
- `scons --no-exec`；
- 真正 Windows clean build；
- DLL load／symbol check；
- 中文與 UEB grade 1/2 translation。

現有 8 個測試均通過，但它們沒有執行 SCons graph，也沒有載入新建 DLL，因此不能作為本任務成功的證據。

建議：完成上述 runtime test，並在 Windows x64 執行 clean build 後留下完整命令與結果；在這些驗證完成前，不應把 Task 0 標示為完成。

## Commit-by-commit 摘要

### `d6cb640` — source pinning

兩個 submodule commit 的對齊方向正確：

- NVDA：`b493fe7e1f361a8d549f17a3353d826f6fe32334`
- liblouis：`2aa5f84b14de17bcfe8317862d11f6bd7d640e55`

`.gitmodules` 沒有 branch tracking，符合固定 commit 的要求。主要缺口是後續沒有產生並驗證與新 liblouis commit 相符的 runtime artifacts。

### `48d5646` — synchronization tool

allowlist、commit-only metadata、missing-source 檢查與 staging directory 的方向合理。但 helper adaptation 使用目前 HEAD 的既有檔案，破壞來源追溯與可重現性；SConscript adaptation 也只刪除變數宣告，留下引用。

### `3f807ef` — SCons migration

`vswhere`、VS 2022 bootstrap、`clang-cl`／SCons／`M4_EXE` fail-fast 檢查方向合理。但根 SConstruct 沒有完整提供 NVDA environment，且錯誤假設子 SConscript 會回傳 outputs。字串型 contract tests 無法驗證 build graph。

### `b453299` — vendor snapshot

`SOURCE.json` 符合 commit-only 格式，ctypes wrapper template 也有同步。但 frozen `sconscript` 本身不可執行，runtime helper 不是由 NVDA helper 轉換而來，且 DLL/tables 沒有更新。

### `9fbb8bd` — documentation

commit-only 升級流程與 prerequisites 的方向符合規格。然而文件提到 clean build 與 runtime tests，實作中沒有對應 runtime test，完成紀錄也沒有 Windows build 證據，因此文件描述超前於可驗證的實作狀態。

## 已執行驗證

```text
python3 -m unittest \
  scripts.tests.test_sync_nvda_liblouis \
  scripts.tests.test_liblouis_build_contract -v
```

結果：8 tests passed。

此結果同時證明現有測試存在覆蓋盲點，因為靜態檢查通過時，SConscript 中仍有未定義名稱及缺少回傳值。

其他檢查：

```text
git diff --check d6cb640^..9fbb8bd
```

結果：通過，未發現 whitespace error。

```text
rg -n "Return\\(|unitTestTablesDir" vendor/nvda/liblouis/build/sconscript
```

結果：沒有 `Return(...)`；仍有兩處使用未定義的 `unitTestTablesDir`。

## 接受條件

至少完成以下事項後再進行下一次 review：

1. 修正 SConscript adaptation，並讓 Windows `scons --no-exec` 成功。
2. 建立與 NVDA 相同語意的最小 `thirdPartyEnv`，確認 CRT、defines、architecture 和 link flags。
3. 讓 runtime helper 真正由 pinned NVDA helper deterministic 產生，移除 `git show HEAD:client/...`。
4. 清理並重建 matched DLL／tables／wrapper／helper。
5. 新增並執行 Windows runtime tests，驗證中文、UEB grade 1 與 grade 2。
6. 更新 `finish_task0.md`，列出實際 Windows build 與 runtime test 證據。
