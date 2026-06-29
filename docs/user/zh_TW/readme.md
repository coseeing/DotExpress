# DotExpress

DotExpress 是一套文字轉點字工具，可將一般文字轉換為固定行寬的點字格式，並產生可直接用於紙本點字印製的輸出結果。

DotExpress 適合需要精準控制紙本點字輸出的點譯人員與教育工作者使用。

---

## 為什麼選擇 DotExpress？

DotExpress 的設計初衷，是為了解決傳統點字轉譯工具長期存在的限制，尤其是在處理中文、英文與技術符號等混合內容時常見的問題。它希望為教育與專業實務場域中的點譯工作，提供一套現代化、易於使用且兼顧無障礙需求的工作流程。

---

## 功能特色

### 多語文字轉譯

DotExpress 提供中文、英文與日文各自獨立的點字轉譯表設定。使用者可依不同語言與地區選擇合適的點字轉譯表，讓轉譯結果更貼近實際使用需求。

例如，中文可使用臺灣注音點字，英文則可使用 UEB 一級點字。

---

### 固定行寬設定

DotExpress 可將一般文字轉譯為每行固定點字格數的版面格式，以支援紙本點字製作。

使用者可以設定每行可容納的點字格數，輸出結果會依指定行寬自動排版，以配合不同紙張尺寸與印製需求。

---

### 自訂字典

為了處理標準轉譯表未涵蓋的專有名詞、罕見詞彙或專門術語，DotExpress 提供「自訂字典」功能。

這項功能可讓使用者即時調整轉譯結果，同時保留整體轉譯流程的彈性。

使用者可自行定義來源文字與對應點字之間的對照規則，以更細緻地控制轉譯輸出。

當目標點字編碼類型設為「一般」或「Unicode 點字」時，可在字元之間插入 `@` 作為分隔符號。如此一來，系統在換行時便能以字元為單位處理，避免整串點字被視為單一不可分割的內容。若類型設為「注音」，則不需要加入 `@`，系統會依注音規則自動斷行。

---

## 編輯字典

1. 點選 **Dictionary** 按鈕開啟字典編輯器。
2. 點選 **Add** 建立新的轉譯對應規則。
3. 選擇所需的字典模式，並輸入 **Source Text** 與對應的 **Braille** 欄位內容。

---

## 字典模式

自訂字典支援以下三種模式：

---

### 一般

在此模式下，**Braille** 欄位的內容會直接取代 **Source Text** 欄位內容，不會進行額外驗證。

適合單純的文字轉點字替換情境。

---

### 注音

在此模式下，**Braille** 欄位內容會取代 **Source Text**，並依注音符號規則解析輸入內容。

系統只允許合法的注音符號與聲調組合，並會進行基本驗證，以避免錯誤的注音序列。

此模式適合以臺灣注音點字作為轉譯來源的工作流程。

* 空白代表第一聲。
* 輸入內容必須符合正確的注音符號排列規則。

對於以下這些可單獨成立的聲母：

`ㄓ、ㄔ、ㄕ、ㄖ、ㄗ、ㄘ、ㄙ`

若未搭配韻母，系統會依注音點字規則自動補上對應的 `⠱` 點字碼。

---

### Unicode 點字

在此模式下，**Braille** 欄位會被視為純點字輸入。

只允許輸入 Unicode 點字區段（`0x2800` 到 `0x28FF`）內的字元。

適合熟悉點字，並且需要完整控制最終輸出內容的使用者。

---

透過多語轉譯、固定行寬設定與可自訂的字典系統，DotExpress 提供一套兼具精準度與彈性的文字轉點字流程，協助使用者更有效率地完成紙本點字轉譯與印製前準備工作。

---

## 建置與開發

本專案使用 Python 3.13（64 位元）開發。

若要在本機建置執行檔或產生翻譯檔案，請先確認 Python 版本符合需求，並安裝 `requirements.txt` 中列出的相依套件：

```bash
pip install -r requirements.txt
git submodule update --init include/liblouis
git submodule update --init include/nvda
```

上述指令只會初始化最上層的 `include/liblouis` 與 `include/nvda` submodule，不會遞迴抓取 NVDA 內部宣告的巢狀 submodule。只有在你明確需要巢狀 submodule 時，才需要使用 `git submodule update --init --recursive`。

---

### 建置執行檔

請在 Windows CMD 中執行下列指令，以 PyInstaller 建立執行檔：

```bat
scripts\build-dotexpress.bat
```

### 在 Windows 上建置 liblouis

DotExpress 會從兩份受版本控管的原始碼檢出內容建置 liblouis：

* `include/liblouis/`：上游 liblouis 原始碼 submodule
* `include/nvda/`：固定版本的 NVDA 原始碼 submodule，用於提供 liblouis 整合層
* `vendor/nvda/liblouis/`：由 NVDA 同步過來、凍結在 repo 內的 vendor 快照

最後產生的執行期輸出如下：

* `client/braille/liblouis.dll`
* `client/braille/liblouis/tables/`
* `client/braille/louis_helper.py`
* `client/braille/liblouis/__init__.py`

真正的來源依據是兩個 submodule 指標，而 `vendor/nvda/liblouis/` 則是 `include/nvda/` 與受追蹤執行期 Python 檔案之間的凍結同步快照。執行期所需的 DLL、helper、wrapper 與 tables 都是由這些來源產生，不應手動修改。

### 先備條件

* Visual Studio 2022 C++ 工具
* Clang tools for Windows
* 已安裝 SCons 的 Python 3（`py -m pip install scons`）
* 放在 `miscDeps/tools/` 的 GNU `m4.exe` 與 `regex2.dll`

### 初次檢出與建置

```bat
git submodule update --init include/liblouis
git submodule update --init include/nvda
py scripts\sync_nvda_liblouis.py
scripts\clean-liblouis.bat
scripts\build-liblouis.bat
scripts\install-liblouis.bat
```

### 手動升級 NVDA

1. 在 `include/nvda` 切換到核准使用的 commit。
2. 將 `include/liblouis` 設為 `git -C include/nvda rev-parse HEAD:include/liblouis` 所輸出的 gitlink。
3. 執行 `py scripts\sync_nvda_liblouis.py`。
4. 檢查 `vendor/nvda/liblouis/`、`SOURCE.json` 與重新產生的執行期 Python 檔案。
5. 重新 clean、build，並執行 liblouis 執行期測試。
6. 將兩個 submodule 指標、同步後的 vendor 檔案與重新產生的執行期檔案一併提交。

---

### 產生翻譯範本

若要更新翻譯範本檔（`.pot`），請執行：

```bat
scripts\generate_pot.bat
```

---

## 授權條款

本專案採用 GNU General Public License v2.0（GPL-2.0）授權。
