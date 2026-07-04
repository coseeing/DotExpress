# DotExpress 現況產品盤點 PRD

文件日期：2026-07-04  
文件性質：現況盤點，不代表未來 roadmap 承諾  
盤點基準：以目前 repository 中的 client、server、使用者文件與近期變更紀錄為準

## 1. Executive Summary

DotExpress 目前是一套以 Windows 桌面操作為核心的文字轉點字產品，主要服務需要製作紙本點字輸出的點譯人員、特教教師與相關助理人員。產品核心價值在於將多語文字內容轉為固定行寬的點字結果，並提供自訂字典、翻譯設定、多文件工作區、文件匯入匯出、雙欄對照檢視，以及最小化的 client initialization/version metadata 服務。就現況而言，DotExpress 已經不是單一轉換工具，而是一條可持續編修、管理與輸出點字文件的工作流程產品。

## 2. Problem Statement

### 誰有這個問題？

- 需要製作紙本點字教材或文件的點譯人員
- 需要快速處理教學內容的特殊教育教師與助教
- 需要在中文內容中混合英文、符號、數學片段的實務使用者

### 問題是什麼？

- 傳統點字轉譯工具對混合語言與專有名詞處理彈性不足。
- 紙本點字輸出需要固定行寬與可控斷行，單純文字轉換不足以支撐實務流程。
- 實際工作會涉及多份文件匯入、逐份修正、自訂字典套用、再匯出，而不是單次貼文即完成。
- 使用者需要看見原文與點字之間的對應關係，否則校稿與教學成本高。

### 為什麼痛？

- 點譯結果若不能細部控制，使用者會被迫依賴人工修正，效率與一致性都下降。
- 若沒有工作區與文件管理，批次教材製作流程會碎裂。
- 若沒有字典與翻譯表設定，專有名詞與語種切換容易失真。
- 若無法對照來源文字與點字，錯誤定位與校對會變慢。

### 現有證據

- 使用者文件已直接將產品定位為固定行寬、可印製的文字轉點字工具，並強調中英混合與自訂字典需求。
- `client/gui.py` 的主程式入口顯示目前 UI 已整合轉換、文件工作區、字典管理、翻譯設定、雙欄對照與背景初始化流程。
- `client/conversion/service.py` 顯示產品已處理語言切換、內嵌數學片段、字典套用與固定寬度換行。
- `client/documents/workspace.py` 顯示產品已採多文件工作區模型，而非單文件工具。

## 3. Target Users & Personas

### 主要 Persona：點譯作業者

- 角色：專職或兼職點譯人員
- 目標：將教材、講義或文件快速轉成可印製點字
- 需求：固定行寬、翻譯表控制、專有名詞校正、可重複編修
- 行為：會反覆轉換、校對、修字典、再輸出

### 次要 Persona：特教教師或教學支援人員

- 角色：需要自行準備點字教學內容的人員
- 目標：降低教材前製成本
- 需求：容易匯入既有文件、快速調整、可直接輸出 `.brl`
- 行為：常以現有文字檔、Word、PDF、EPUB 為來源

### 次要 Persona：校稿或教學對照使用者

- 角色：需要比較原文與點字對應關係的人
- 目標：降低校稿與教學解說成本
- 需求：能看到分段或逐字對齊結果
- 行為：會依賴 dual view 檢查轉譯合理性

### Jobs To Be Done

- 當我有一份教材時，我要能匯入或貼上內容，快速得到可印製的點字結果。
- 當轉譯不符合專業慣例時，我要能透過字典與翻譯設定修正，而不是整份重做。
- 當我要校稿時，我要能檢查原文和點字的對齊關係。
- 當我同時處理多份教材時，我要能在同一工作區保存與管理文件。

## 4. Strategic Context

### 產品目標

- 提供一套可在圖形化環境中完成的點字轉譯工作流
- 降低混合語言與專業詞彙帶來的人工修正成本
- 支援從來源文件到點字輸出的端到端流程

### 為何是現在的產品形態？

從近期 commit 與 specs 可看出產品正從「基礎轉換器」往「完整工作流工具」演進。近期已新增或強化的能力包含：

- 多格式文件匯入
- 匯入/匯出轉換流程
- dual view 原文/點字對照
- 字典過濾與管理改善
- NVDA 對齊的 liblouis runtime 維護流程

這代表現況產品重心不再只是翻譯演算法本身，也包含可用性、管理性、以及與 Windows/NVDA 生態相容的交付能力。

### 競爭與替代方案現況

本 PRD 未基於外部市場研究，只能依 repo 內描述推論：

- DotExpress 主要替代的是舊式、對混合語言支援不足或操作環境受限的點譯工具。
- 差異化能力在於多語轉換、自訂字典、固定寬度排版、dual view、以及 Windows GUI 工作流。

這一段屬推論，不是外部競品研究結論。

## 5. Solution Overview

### 高層產品描述

DotExpress 現況可分為六個產品層：

1. 文字轉點字引擎層
2. 翻譯控制層
3. 文件工作區層
4. 對照與校稿層
5. 匯入匯出層
6. 初始化服務層

### 主要使用流程

1. 使用者建立或開啟文件
2. 從文字框輸入內容，或匯入 `.txt` / `.dep` / `.pdf` / `.docx` / `.epub`
3. 選擇翻譯表、輸出模式、行寬與字典
4. 執行 Convert
5. 在主畫面或 Dual View 檢查結果
6. 視需要修改字典、重新轉換
7. 匯出 `.brl` 或 `.dep`，也可批次匯出全部文件

### 現有功能盤點

#### A. 多語與數學轉換

- 支援依語言切換翻譯表
- 支援中文、英文、日文等多語設定入口
- 支援內嵌 `$...$` 數學片段轉換
- 支援固定行寬換行
- 支援 Unicode 與 ASCII 兩種輸出模式

#### B. 自訂字典系統

- 字典以 CSV 管理
- 提供新增、刪除、重新命名、匯入、匯出
- 至少支援 `General`、`Bopomofo`、`Braille/Unicode` 類型
- 預設字典不可刪除
- 近期新增字典過濾相關能力，代表字典管理已進入可擴充階段

#### C. 文件工作區

- 內建 workspace 目錄概念
- 支援多文件列表
- 支援新增、開啟、重新命名、刪除、刪除全部
- 以 `.dep` 作為封裝格式，內含 `.txt`、`.brl` 與 pending metadata
- 可保存尚未完成轉換的文件狀態

#### D. 匯入與匯出

- 匯入：`.dep`、`.txt`、`.pdf`、`.docx`、`.epub`
- 匯出：單一 `.brl`、單一 `.dep`
- 批次匯出全部文件
- 匯入時會處理命名衝突與錯誤回報

#### E. Dual View 對照檢視

- 根據 translation result 建立原文到點字的對齊模型
- 支援 segment 與 character-level 對照資訊
- 用於校稿、教學與定位問題

#### F. 使用性與無障礙操作

- 有鍵盤快捷鍵與區塊巡覽
- 可調整檢視字體大小
- 支援明暗檢視方案
- Windows 上可註冊 SimBraille 私有字型
- UI 文案含繁中本地化資源

#### G. Client Init / Version Metadata

- 啟動時背景送出 client init request
- 上送版本、client id、作業系統、架構、語系等資訊
- server 端目前只做初始化事件紀錄與版本資訊回傳
- 尚未看到管理後台、分析報表或更多 API

## 6. Success Metrics

本 repo 尚未看到完整產品分析指標系統，因此以下分為「現況可觀察」與「建議未來補齊」。

### 現況可觀察指標

- client init 事件是否成功送達
- 版本 metadata 是否成功回傳
- 匯入與轉換流程是否能完成，不因格式或相依問題失敗
- 文件是否能保存為 `.dep` 並重新載入

### 建議未來補齊的產品指標

- 每次轉換成功率
- 匯入失敗率，依檔案格式拆分
- dual view 使用率
- 字典修改後再轉換的比例
- 每位使用者平均處理文件數
- 版本升級提示後的更新採納率

## 7. User Stories & Requirements

### Epic Hypothesis

如果提供一套支援多語轉換、文件管理、字典修正與原文點字對照的 Windows 工具，點譯與教材製作人員就能更穩定地完成紙本點字輸出，並降低人工修正與校稿成本。

### User Story 1

作為點譯作業者，我要能輸入或匯入文字內容並轉成固定行寬點字，讓我能直接進入印製前整理。

Acceptance Criteria:

- 可輸入來源文字並執行轉換
- 可設定寬度
- 轉換結果可顯示於點字結果區
- 可將結果匯出為 `.brl`

### User Story 2

作為需要處理專有名詞的人，我要能使用自訂字典控制輸出，讓轉譯結果符合實務慣例。

Acceptance Criteria:

- 可建立與管理多份字典
- 可選取作用中的字典
- 字典可匯入與匯出
- 預設字典受到保護，不可刪除

### User Story 3

作為需要管理教材的人，我要能在同一工作區保存多份文件，讓我不必每次從零開始。

Acceptance Criteria:

- 可新增、開啟、重新命名與刪除文件
- 文件可保存為 `.dep`
- 開啟後能恢復文字與點字內容，或恢復 pending 狀態

### User Story 4

作為校稿或教學使用者，我要能看到原文與點字的對齊關係，讓我能定位轉譯問題。

Acceptance Criteria:

- 可從已有轉換結果開啟 dual view
- dual view 需顯示分段與對齊資訊
- 沒有轉換資料時需阻擋或提示

### User Story 5

作為產品維護者，我要能在啟動時知道客戶端版本與環境概況，讓我能執行最低限度的版本管控。

Acceptance Criteria:

- client 啟動時背景送出 init request
- server 可持久化紀錄
- server 可回傳目前版本與最低支援版本資訊

### 邊界條件與約束

- 主要桌面 client 為 wxPython 應用，明顯偏向 Windows 交付
- 部分測試與 liblouis 綁定在非 Windows 環境可能受限
- liblouis runtime 依賴 `include/liblouis`、`include/nvda`、`vendor/nvda/liblouis`
- `.dep` 是目前工作區與封裝流程的重要格式
- 數學轉換採 `$...$` 片段偵測，代表數學內容需符合此輸入約定

## 8. Out of Scope

以下能力目前不應被視為現況產品已具備：

- 雲端同步或多人協作
- Web 版主要編輯介面
- 完整產品分析後台
- 使用者帳號系統
- 線上字典共享平台
- server 端報表查詢、管理 API、統計 dashboard
- 以外部市場研究驗證的正式競品分析

## 9. Dependencies & Risks

### 技術依賴

- wxPython 桌面 UI
- liblouis runtime 與 NVDA 對齊流程
- Windows 建置鏈，包括 Visual Studio、Clang、SCons、miscDeps
- PDF/DOCX/EPUB 匯入相關套件
- FastAPI + SQLAlchemy + SQLite 的輕量 server

### 主要風險

- liblouis DLL 與 tables 不一致時，轉譯可能局部失效
- Windows 專屬相依提高跨平台測試成本
- 多格式匯入品質受第三方解析能力影響
- 現有 server 範圍很小，若未來把更多產品責任放到 server，需重新設計資料模型與安全性
- 現況缺乏完整產品遙測，難以量化哪些功能真正被使用

### 風險緩解方向

- 維持 NVDA/liblouis 同步流程與建置紀律
- 強化針對匯入與 dual view 的自動化測試
- 補齊轉換、匯入、匯出、版本檢查的事件級觀測性

## 10. Open Questions

- 目前主要使用者最常用的匯入來源格式是什麼？
- dual view 在實際點譯流程中是核心功能，還是進階輔助功能？
- 使用者是否需要字典層級的分類、標籤、共享或版本管理？
- 目前 client init 蒐集資料的產品用途與保留政策為何？
- 產品是否計畫長期維持 Windows-only，或需要更明確的跨平台策略？
- 數學轉譯的覆蓋範圍與品質標準目前如何定義？

## Appendix A. Source Basis

本文件主要依據以下 repo 內容整理：

- `docs/user/en/readme.md`
- `docs/user/zh_TW/readme.md`
- `docs/user/zh_TW/background.md`
- `docs/user/zh_TW/shortcuts.md`
- `client/gui.py`
- `client/conversion/service.py`
- `client/documents/workspace.py`
- `client/dictionaries/manager.py`
- `client/translation/settings.py`
- `client/dual_view/model.py`
- `client/client_init.py`
- `server/app/main.py`
- 2026-06-27 至 2026-07-03 間的近期 commit 與 `docs/superpowers/specs/`

## Appendix B. Interpretation Notes

- 這份文件刻意把「原始碼已明確存在的能力」和「依文件與程式結構推論的產品意圖」分開。
- 若後續要把此文件轉成 roadmap PRD，應另開新文件，不建議直接在本文件上混入未承諾功能。
