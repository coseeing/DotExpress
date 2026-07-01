# Dual-View Braille Alignment 完成摘要

這次實作已完成，重點如下：

- 新增 `Dual View` 的檢視流程，使用 `wx.html2.WebView` 顯示 modeless 視窗。
- `BrailleFrame` 已接上 session-only 的雙視快取，並在以下時機刷新：
  - 開啟 Dual View
  - 手動轉換成功
  - 切換文件
- 保留原本轉換輸出行為，export callback 仍維持 string API。
- 新增 character-level dual-view model 與 HTML renderer，保留 segment boundary。
- 已把可見字串加入 gettext catalog，並更新 `zh_TW` `.mo`。

驗證：

- `cd client && python3 -m unittest tests.test_conversion_service tests.test_dual_view_model tests.test_dual_view_html tests.test_action_menu tests.test_dual_view_frame tests.test_gui_document_flows -v`
- `python3 -c 'import gettext; gettext.GNUTranslations(open("client/locales/zh_TW/LC_MESSAGES/dotexpress.mo", "rb"))'`

說明：

- 這個環境沒有 `msgfmt`，因此 `.mo` 以 Python fallback 方式重新編譯。

新增 commits：

- `eb9f7f6` — `feat: preserve translation alignment segments`
- `90bb02a` — `feat: build dual view alignment model`
- `7cac2c5` — `feat: add dual view viewer integration`
