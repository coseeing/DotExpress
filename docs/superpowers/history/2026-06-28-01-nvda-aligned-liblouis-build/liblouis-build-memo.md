# liblouis build debug memo

Date: 2026-06-28

## Goal

釐清 DotExpress 在 Windows x64 build `liblouis` 時，為什麼會出現：

```text
error: call to undeclared function 'lou_freeTableFiles'
```

並對照 NVDA 的 build 行為找出差異。

## What was verified

### 1) NVDA reference build succeeds

我已讀取 `nvda-source.log`，確認 NVDA 的 liblouis build 可正常完成，且 `compileTranslationTable.c` 會成功編譯與 link。

### 2) DotExpress 的 generated `liblouis.h` 與 NVDA reference 一致

我比較過：

- `vendor/nvda/liblouis/build/liblouis.h`
- `ref/nvda/build/x86_64/liblouis/liblouis.h`

兩者內容一致，包含：

- `lou_findTables(const char *query);`
- `lou_listTables(void);`
- `lou_freeTableFiles(char **);`

所以問題不是 generated header 內容本身不同。

### 3) Preprocessor trace 顯示 DotExpress 實際預處理結果少了 `lou_freeTableFiles` prototype

我新增診斷 bat，對 `include/liblouis/liblouis/compileTranslationTable.c` 跑 `clang-cl /E` 與 `clang-cl /E /showIncludes`。

結果顯示：

- `include\liblouis\liblouis\liblouis.h` 有被 include
- `lou_findTables` 與 `lou_listTables` 在預處理輸出中存在
- 但 `lou_freeTableFiles(char **);` 在 DotExpress 的 `.i` 輸出中沒有出現

這點和 NVDA reference 的預處理輸出不同；NVDA 的 `.i` 中有完整保留 `lou_freeTableFiles(char **);`

## What this implies

這個錯誤不是來自：

- generated `vendor/nvda/liblouis/build/liblouis.h` 缺宣告
- include path 指到錯的檔案
- `compileTranslationTable.c` source 本身少呼叫前置宣告

而是 DotExpress 這邊的 preprocessing / include chain 在實際 build 時，對 `lou_freeTableFiles` 的宣告沒有保留下來。

## Temporary workaround applied

為了先讓 build 過，我在本地子模組 `include/liblouis` 的 `internal.h` 加了前置宣告：

```c
void EXPORT_CALL
lou_freeTableFiles(char **tables);
```

這個修補已 commit 到子模組：

- `b7cf2d69` — `fix: declare lou_freeTableFiles`

父 repo 也已更新 submodule pointer 並 commit：

- `fe34bd8` — `fix: stabilize liblouis build against missing prototype`

## Verification

已驗證：

- `python3 -m unittest scripts.tests.test_liblouis_build_contract -v`

通過。

## Important caveat

這個 workaround 放在 `include/liblouis/liblouis/internal.h`，屬於 upstream-like source tree 的修改。
後續 sync liblouis upstream 時，這個改動可能會：

- 被覆蓋
- 產生 merge conflict
- 需要再次確認是否仍然必要

因此這個修補應視為暫時性措施，不應當作最終狀態。

## Two different layers involved

這次除錯確認有兩個不同層次，不能混為同一件事：

### 1) Compile-time declaration layer

`include/liblouis/liblouis/internal.h` 裡補 `lou_freeTableFiles(char **tables);` 的前置宣告，是為了解決編譯期問題。

這一層處理的是：

- `clang-cl` 在 C99 模式下不能看到未宣告函式
- `compileTranslationTable.c` 在使用 `lou_freeTableFiles()` 前必須先知道它的原型

所以這個修補的作用是「讓 build 能過」。

### 2) Link/export layer

後來又發現 `client/braille/liblouis.dll` 少了 `lou_freeTableInfo` 的 export。

這和 compile-time 宣告不同，因為：

- source 裡已經有 `lou_freeTableInfo()` 的定義
- object 檔也有這個 symbol
- 但最後 DLL / import lib 的 export table 沒有它

因此我在 `sconstruct` 加上：

```text
/EXPORT:lou_freeTableInfo
```

這是為了強制 linker 匯出該符號，避免 export table 跟 NVDA 不一致。

這一層處理的是「編譯已成功，但最後 DLL 還是不是有完整 API」。

## Result

目前兩層都已處理：

- compile-time：`internal.h` 的前置宣告
- link/export：`sconstruct` 的顯式 `/EXPORT:lou_freeTableInfo`

這兩個修改是互補的，不是互相取代。

## Resolved root cause

已定位根因。

`compileTranslationTable.c` 透過：

```c
#include "internal.h"
```

而 `internal.h` 又用：

```c
#include "liblouis.h"
```

在這種 quoted include 的情況下，編譯器會先找目前來源檔所在目錄。因此只要工作樹裡殘留：

- `include/liblouis/liblouis/liblouis.h`

就會優先吃到這個 source-tree generated header，而不是 NVDA-aligned build 想使用的：

- `vendor/nvda/liblouis/build/liblouis.h`

這也解釋了先前的矛盾現象：

- 我比對的是 `vendor/nvda/liblouis/build/liblouis.h`
- 但實際 build include trace 顯示吃到的是 `include/liblouis/liblouis/liblouis.h`

換句話說，問題不在 `vendor/nvda/liblouis/build/liblouis.h` 內容，而在於它根本沒有被實際使用。

`include/liblouis/liblouis/liblouis.h` 是 upstream Windows `Makefile.nmake` 會生成的檔案，而且被 `include/liblouis/.gitignore` 忽略。這代表它很容易在先前走過 nmake / 本地實驗流程後殘留在工作樹裡，形成隱性污染。

一旦這個殘留檔存在，NVDA-aligned SCons build 雖然有生成自己的 header，也無法透過 include path 優先生效，因為 quoted include 會先命中 source file 同目錄的 `liblouis.h`。

## Fix applied

已將這個 root-cause fix 落到 build contract：

- `scripts/build-liblouis.bat`
  - 每次執行 `scons` 前先刪除 `include\liblouis\liblouis\liblouis.h`
- `scripts/clean-rebuild-dotexpress.bat`
  - clean rebuild 時也一併刪除同一個 shadowing header
- `scripts/tests/test_liblouis_build_contract.py`
  - 新增 regression test，要求 batch bootstrap 必須處理這個 source-tree generated header

## What this means

先前 `Open question` 不是「哪個條件編譯吃掉了 prototype」，而是：

- 實際編譯讀錯了 header
- 而且那個錯誤 header 來自 source tree 的殘留 generated artifact

所以這不是 `liblouis.h.in` 內容問題，也不是 NVDA `sconscript` 的 header generation 問題；是 include 搜尋順序加上髒工作樹 artifact 造成的 shadowing 問題。

## Relevant files

- `include/liblouis/liblouis/internal.h`
- `vendor/nvda/liblouis/build/sconscript`
- `sconstruct`
- `scripts/tests/test_liblouis_build_contract.py`
- `scripts/diagnose-liblouis-include-trace.bat`
