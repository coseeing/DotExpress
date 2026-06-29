# Task 3 完成說明

本次根據實際 build 與 preprocessor trace，整理出 liblouis build mismatch 的 debug 結論，並先用最小修補讓 build 可繼續往下。

## 已確認的發現

- NVDA reference build 成功，`nvda-source.log` 顯示 `compileTranslationTable.c` 可正常編譯與 link。
- `vendor/nvda/liblouis/build/liblouis.h` 與 `ref/nvda/build/x86_64/liblouis/liblouis.h` 內容一致。
- 但對 `include/liblouis/liblouis/compileTranslationTable.c` 做預處理後，DotExpress 的結果中沒有保留 `lou_freeTableFiles(char **);` prototype。
- NVDA reference 的預處理結果則有保留 `lou_freeTableFiles(char **);`。
- 因此，問題不是 generated header 內容缺失，而是 DotExpress 的 preprocessing / include chain 在實際 build 時把那段宣告吃掉了。

## 採取的最小修補

為了先讓 build 過，我在 `include/liblouis/liblouis/internal.h` 補上前置宣告：

```c
void EXPORT_CALL
lou_freeTableFiles(char **tables);
```

這個修補是暫時性的 workaround，目的在於讓 `compileTranslationTable.c` 在編譯時能看到 prototype，避免 `lou_freeTableFiles` undeclared。

## 驗證

- `python3 -m unittest scripts.tests.test_liblouis_build_contract -v`
- `gcc -E -Ivendor/nvda/liblouis/build -Iinclude/liblouis/liblouis ... include/liblouis/liblouis/compileTranslationTable.c`
  - 驗證預處理輸出現在可見 `lou_freeTableFiles(char **);`

## 風險與後續

- 這個 workaround 放在 `include/liblouis` 的 upstream-like source tree，後續同步 liblouis upstream 時可能被覆蓋或產生 conflict。
- 目前 root cause 尚未完全定位，之後仍應繼續追查為什麼 DotExpress 的預處理結果會少掉這個 prototype。

## 新增 commit list

- `fe34bd8` — `fix: stabilize liblouis build against missing prototype`
- `b7cf2d69` — `fix: declare lou_freeTableFiles`

