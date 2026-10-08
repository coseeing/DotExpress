# 設定選項單一來源（P2-3）設計

## 目標

讓每一份設定選項清單只有一個定義。目前各設定的值、標籤、順序、範圍與轉譯表欄位，分別寫在 `settings/dialogs.py`、`settings/translation.py`、`settings/view.py` 與 `gui.py`；數學表選項也是寫死的，但 `conversion/math_braille_codes.py` 早已定義了它們。這是 `storage/refactor.md`（6.3 節）的路線圖任務 P2-3，涵蓋發現 O-3，以及 P-4 點名的 `if key == "math"` 分派。本任務也一併定案兩項審查後續：`settings/dialogs.py` 的 `_(table.displayName)` 要不要保留（P0 審查 M-5、P1 審查 P2 第 3 點），以及 P2-3 對 `__tables.py` localedir 問題要做什麼。

具體而言：

- 新增模組 `client/settings/options.py`。它只從 `i18n` 匯入 `N_`，另外匯入 `conversion.math_braille_codes`；內容是凍結的選項描述子（值加上標籤 msgid）、兩個整數範圍、五個轉譯表欄位，以及四個小型查詢函式。
- `settings/translation.py`、`settings/view.py`、`settings/dialogs.py` 與 `gui.py` 改從它讀取。各自的 tuple（`SUPPORTED_OUTPUT_MODES`、`VIEW_SCHEME_KEYS`、`BRAILLE_FONT_KEYS`、`_OUTPUT_MODES`、`_VIEW_SCHEME_OPTIONS`、`_BRAILLE_FONT_OPTIONS`、`CHOICE_SPECS`）、最小／最大值常數、寫死的 `UEB`/`Nemeth` 清單，以及 `{"default", "math"}` 集合都會移除。
- 選項標籤改為 `N_()` msgid，在建立控制項時才用 `_()` 翻譯。msgid 完全不變。
- 寫入設定檔的預設值仍留在 `config.py`。新增不變式測試，檢查這些預設值都在選項值之中。
- 保留 `_(table.displayName)`。從原始碼執行時，就是靠它才顯示翻譯後的表名；在打包版中它沒有作用（決策 D6）。

這次重構不改變行為。每個選項標籤、選項順序、選取索引、儲存值、正規化結果、spin 範圍與編輯區顏色，在 zh_TW 與未翻譯的執行環境下都維持相同。msgid 不變（353，集合相同）。黃金測試資料 `client/tests/fixtures/translation_golden.json`（sha256 `e67d95a1ae001d928b657f16468494d0e98beeea5a6425283090b34030211ccd`）與 `client/tests/fixtures/dictionary_entries_trace.json`（sha256 `f493da52376c8eac32a50c33b7f11870451360bed4bf26c1db339ccd2c66c2cf`）都不變。

規劃後修正：plan `docs/superpowers/plans/2026-10-08-p2-3-settings-options.md`（「Spec Corrections and Refinements」一節）更正了兩項事實（步驟 3 也必須搬移對話框的兩個 spin；`tests/test_settings_dialogs.py` 實際跑 47 個測試），並細化了測試計畫、步驟 3-5 的紅燈步驟、幾項程式碼選擇與測試數量；以下已併入這些修改。

## 現況（2026-10-08 於 `refactor/p2-3-settings-options` 驗證，HEAD `f16bfc8`，已合併 P0-*、P1-*、P2-1 與 P2-2）

縮排：`settings/*.py`、`config.py`、`tests/test_settings_dialogs.py`、`tests/test_view_settings.py` 與 `tests/test_translation_settings.py` 用 4 個空白；`gui.py` 用 tab。

基準：`cd client && $PY -m unittest discover -s tests` 得到 `Ran 973 tests`、`FAILED (failures=1, skipped=9)`。失敗的是 P2-5 的 `test_conversion_service ... test_translate_with_language_does_not_duplicate_existing_spaces_around_math`。聚焦集合 `tests.test_settings_dialogs tests.test_translation_settings tests.test_view_settings tests.test_settings_state tests.test_translation_tables tests.test_math_braille_codes` 跑 57 個測試，全部通過。msgid 掃描（`$SP/p12/tools/msgid_scan.py client`）回報原始碼有 353 個 msgid。（`$PY` = `$SP/venv/bin/python`，`$SP` = 本工作階段的 scratchpad。`.pot` 仍多出 4 個 P1-2 已移除的 wildcard msgid；重新產生 `.pot` 屬於 Windows 驗證債，不在本任務範圍。）

`storage/refactor.md` 的行號早於 P0 到 P2-2，以下為目前行號。

### 各選項清單目前所在位置

| 設定 | 值（順序 = 顯示順序） | 標籤（msgid -> zh_TW） | 定義處 | 重複推導處 |
| --- | --- | --- | --- | --- |
| 輸出模式（「Braille Type」） | `unicode`, `ascii` | "Unicode" -> Unicode、"ASCII" -> ASCII | `settings/dialogs.py:353-356` `_OUTPUT_MODES`（匯入時 `_()`） | `settings/translation.py:20` `SUPPORTED_OUTPUT_MODES`；預設值 `config.py:36` `DEFAULT_OUTPUT_MODE = "unicode"` |
| 寬度 | 10..200 | - | `settings/translation.py:18-19` `MIN/MAX_CONVERSION_WIDTH` | `translation.py:43-44` 夾限一次，`dialogs.py:394-397, 415-420` 又各一次；預設值 `config.py:37` = 40 |
| 檢視配色（「Scheme」） | `light`, `dark` | "Light" -> 淺色、"Dark" -> 深色 | `settings/dialogs.py:358-361` `_VIEW_SCHEME_OPTIONS` | `settings/view.py:15` `VIEW_SCHEME_KEYS`；`gui.py:94-103` `VIEW_SCHEMES`（以值為鍵的顏色）；預設值 `config.py:39` = `light` |
| 點字字型 | `default`, `simbraille` | "Default" -> 預設、"SimBraille" -> SimBraille | `settings/dialogs.py:363-366` `_BRAILLE_FONT_OPTIONS` | `settings/view.py:16` `BRAILLE_FONT_KEYS`；`gui.py:385` 的字面值 `"simbraille"`；預設值 `config.py:40` = `simbraille` |
| 字型大小 | 8..48 | - | `settings/view.py:13-14` `VIEW_FONT_SIZE_MIN/MAX` | `view.py:28` 夾限一次，`dialogs.py:605-608, 639-644` 又各一次；預設值 `config.py:38` = 12 |
| 轉譯表欄位 | `default`, `en`, `zh`, `ja`, `math` | "Default/English/Chinese/Japanese/Math Translation Table" -> 預設／英文／中文／日文／數學轉譯表 | `settings/dialogs.py:471-477` `CHOICE_SPECS`（key、標籤、檔名前綴） | `config.py:29-35` `DEFAULT_TRANSLATION_TABLES`（同樣的鍵、同樣的順序）；`dialogs.py:489`（不加「未選擇」）與 `:517`（必填）的 `{"default", "math"}`，以及 `is_valid` `:509-513` 的字面鍵 |
| 數學表 | `UEB`, `Nemeth`（原樣顯示，不翻譯） | - | `settings/dialogs.py:571-577` `_options_for_key("math")` | `conversion/math_braille_codes.py:1-2`（P1-1 leaf；`config.py:8` 再匯出）；`config.py:34` 的字面值 `"math": "UEB"` |

### 面板如何使用它們（`settings/dialogs.py`）

- `TranslationSettingsPanel`（369-462）：輸出模式用 `wx.Choice(choices=[label ...])`。選取 `< 0` 或超出範圍時，`_selected_output_mode` 回傳 `_OUTPUT_MODES[0][0]`。`_select_output_mode` 選取該值的索引，值不明時選 0。寬度 spin 的 `min/max/initial` 取自範圍，`initial` 與 `load_snapshot` 各自手寫夾限。
- `ViewSettingsPanel`（588-686）：同樣的模式出現兩次（配色、點字字型），另有字型大小 spin。`on_save` 透過 `normalize_view_settings` 正規化。
- `TranslationTablesPanel`（465-585）：`CHOICE_SPECS` 每項依序一列，每列有一個 `StaticText(label)` 與一個 `wx.Choice`。選項建立方式如下：`math` 用固定清單 `[UEB, Nemeth]`，且 `display_name == file_name`。其餘各列由 `_load_table_options()` 取 `listTables()` 中所有 `output` 為真的表，建成 `TableOption(fileName, _(displayName))`，依 `display_name.lower()` 排序；前綴為 `None` 時全部保留，前綴為 `p` 時只保留 `file_name.lower().startswith(p)` 的表。`default`/`math` 以外的列，最前面加上 `TableOption("", _("None selected"))`。沒有任何選項的列會停用，並設為 `NOT_FOUND`。`_select_choice_value` 選第一個 `file_name` 相等的選項，找不到就選索引 0。必填列中第一個空白的列，`validation_error` 回傳 `_("Please select a value for {field}.").format(field=label)`。`on_save` 寫入全部五個鍵。
- 標籤在匯入 `settings.dialogs` 時就翻譯一次（模組層級 tuple 與類別屬性中的 `_()`）。`_` 是 `i18n` 匯入時載入的 zh_TW 目錄所綁定的 `gettext`，同一個行程中目錄不會改變。

### 正規化與儲存

- `settings/translation.py:37-58`：不明的輸出模式改成 `DEFAULT_TRANSLATION_SETTINGS.output_mode`（= `config.DEFAULT_OUTPUT_MODE`），寬度則夾限。
- `settings/view.py:26-35`：字型大小夾限，不明的配色或點字字型改成 `config.DEFAULT_*` 的值。
- `config.py` 的 getter 只要儲存值是 `str`（或可轉換的 `int`）就回傳它，否則回傳預設值，不檢查是否屬於選項。轉譯表以 `DEFAULT_TRANSLATION_TABLES` 為底合併，從不比對選項（見特性 K3）。
- `settings/state.py`（snapshot）不含任何選項知識，不更動。

### `_(table.displayName)` 與 `__tables.py` 的 localedir（實測）

- `braille/tables/__tables.py`（NVDA 衍生，不可編輯）自建目錄，`localedir = resource_path("locales")`。它的 `resource_path` 用 `Path(__file__).parent.parent`，也就是 `client/braille`。從原始碼執行時 `client/braille/locales` 不存在，所以 `addTable` 拿到的是**英文**顯示名稱；打包後基準目錄是 `_MEIPASS`，拿到的是 **zh_TW** 名稱。
- 之後 `settings/dialogs.py:582` 再套一次 `_()`。用腳本以真實目錄檢查全部 198 個 `addTable` 呼叫（其中 196 個為 `output`），結果是：未翻譯的名稱 0 個；`_(_(name)) != _(name)` 的名稱 0 個，所以第二次翻譯是冪等的；而對話框的清單（先翻譯，再依 `.lower()` 排序）在兩種執行方式下**完全相同**。如果拿掉這個 `_()`，從原始碼執行時會顯示英文名稱，順序也不同（開頭是 "Afrikaans grade 1"……，而不是「世界文一級」……）。
- `listTables()` 依 `strxfrm(displayName)` 排序，所以它本身的順序在兩種執行方式下不同。但唯一的使用者就是這個面板，而面板會重新排序。因此 M-5 在任何地方都沒有可見影響。
- output 表中各檔名前綴的數量：`en` 10、`zh` 6、`ja` 2。

### 與此相關的測試

`tests/test_settings_dialogs.py`（39 個測試方法，實際跑 47 個測試：`_SingletonCharacterization` mixin 的 8 個方法在 `TextProcessingSingletonTest` 與 `DotExpressSettingsSingletonTest` 中各跑一次；`StubScope(settings_dialog_stubs(), isolate=("settings.dialogs",))`，stub 的 `listTables()` 回傳 `[]`）。其中兩個測試把 `panel.CHOICE_SPECS` 指定為 5 個 tuple 的清單，另有數個把 `settings.dialogs._` patch 成恆等函式。另外還有 `tests/test_view_settings.py`、`tests/test_translation_settings.py`、`tests/test_settings_state.py`、`tests/test_translation_tables.py`、`tests/test_math_braille_codes.py`、`tests/test_config.py`（釘住 `DEFAULT_*` 的值），以及 `tests/test_gui_document_flows.py`（`isolate=("gui", "settings.dialogs", "ui.dual_view")`；該處 `_apply_editor_view_settings` 一律被 mock，所以顏色從未被測試）。`tests/test_i18n.py` 斷言 `settings/dialogs.py` 從 `i18n` 只匯入 `{"_"}`，並確保 "Default"、"SimBraille"、"Braille Font" 仍會被擷取。

## 設計

### 決策摘要

- **D1 用描述子，不用 dict。** 每個選項是凍結 dataclass `SettingOption(value, label)`，`label` 就是 msgid。一份清單是依顯示順序排列的普通 `tuple`。不可變、可雜湊，除了查詢沒有其他行為。
- **D2 標籤是 msgid，在顯示時翻譯。** `options.py` 用 `N_()` 標記標籤，從不呼叫 `_()`；使用端在建立控制項或訊息時呼叫 `_(option.label)`。這沿用 P1-2 的模式（`ui/action_menu.py`、`documents/formats.py`）。正式環境的輸出相同，因為目錄在整個行程中固定不變；差異只出現在 patch `settings.dialogs._` 的測試中（見「風險」）。這樣 `options.py` 不帶任何目錄狀態，`settings/dialogs.py` 對 `i18n` 的匯入也維持 `{"_"}`。
- **D3 預設值留在 `config.py`。** `config` 不能匯入 `settings.options`：那會執行 `settings/__init__`，它匯入 `settings.translation`，而後者又從尚未初始化完成的 `config` 匯入（循環匯入）。`config` 也是寫入設定檔預設值的既定擁有者（`tests/test_config.py`）。重複改由不變式測試防止：每個 `config.DEFAULT_*` 都必須是選項值之一，或落在範圍內。正規化函式以參數接收預設值。
- **D4 數學選項取自 leaf。** `options.py` 從 `conversion.math_braille_codes` 匯入 `MATH_BRAILLE_TABLES`，不經過 `config`。math 欄位的 `fixed_choices` **就是**那個 tuple。`config.DEFAULT_TRANSLATION_TABLES["math"]` 改為 `DEFAULT_MATH_BRAILLE_TABLE`（值同樣是 `"UEB"`）。數學選項仍是不翻譯的專有名稱，不新增 msgid。
- **D5 以表格欄位取代 `CHOICE_SPECS` 與 `"math"` 分派。** 一列 `TranslationTableField(key, label, file_prefix, required, fixed_choices)` 就說明了面板目前依 key 決定的所有事。`required=True` 表示沒有「未選擇」項目，而且套用前必須選好，這與目前的兩個 `{"default", "math"}` 集合完全一致。`fixed_choices` 取代 `if key == "math"`。由 `listTables()` 建立 `TableOption` 清單的工作留在對話框，因為那是對 vendored 模組做的 UI 組裝。
- **D6 保留 `_(table.displayName)`。** 它並不多餘：它是第一方程式碼對 `__tables.py` localedir 問題的補償，而且在打包版中是冪等的（見上方實測）。呼叫處加上註解說明這點。另加一個守門測試，以真實目錄對 `__tables.py` 的每個名稱重新檢查冪等性，日後目錄若加入會衝突的項目就會明確失敗。除此之外，P2-3 不處理 M-5：它沒有可見影響，而修正需要編輯 `__tables.py`（禁止），或加一層沒有任何使用者的重新排序包裝。記錄為「不在此修」（P2-7 擁有 braille 膠水，可列為其後續候選）。
- **D7 超出範圍與不明值的選取規則完全保留。** 負數或超出範圍的選取索引對應到**第一個**選項的值，而不是 config 預設值；不明的值選取索引 0。這兩條規則移入兩個輔助函式，原本的六份複本合而為一。
- **D8 配色顏色放在配色描述子上。** `ViewSchemeOption(SettingOption)` 增加 `background` 與 `foreground`，型別為 RGB `tuple[int, int, int]`，所以 `options.py` 仍不依賴 wx。`gui.VIEW_SCHEMES` 名稱與結構不變，由描述子以 `wx.Colour(*rgb)` 建成。`_apply_editor_view_settings` 除了改用 `BRAILLE_FONT_SIMBRAILLE` 常數之外不變。
- **D9 舊名稱直接移除，不留別名。** grep 顯示 `SUPPORTED_OUTPUT_MODES`、`VIEW_SCHEME_KEYS`、`BRAILLE_FONT_KEYS`、`MIN/MAX_CONVERSION_WIDTH` 與 `VIEW_FONT_SIZE_MIN/MAX` 只被這次要改的模組使用，而對話框的 tuple 本來就是私有的。保留別名等於再造第二個來源。

### `client/settings/options.py`（4 個空白）

允許的匯入：`__future__`、`collections.abc`、`dataclasses`、`i18n`（只限 `N_`）、`conversion.math_braille_codes`。新測試中的 AST 守門禁止匯入 `wx`、`gui`、`dialog`、`ui`、`config`、`braille`、`settings`（同層模組），也禁止匯入 `_` 或呼叫 `_()`。

```python
RGB = tuple[int, int, int]

@dataclass(frozen=True)
class SettingOption:
    value: str      # 寫入 config.json 的值
    label: str      # msgid（N_）；顯示時以 _() 翻譯

@dataclass(frozen=True)
class ViewSchemeOption(SettingOption):
    background: RGB
    foreground: RGB

@dataclass(frozen=True)
class IntRange:
    minimum: int
    maximum: int
    def clamp(self, value: int) -> int  # max(minimum, min(maximum, value))

@dataclass(frozen=True)
class TranslationTableField:
    key: str                                # translation_tables 的鍵
    label: str                              # msgid
    file_prefix: str | None                 # None：所有 output 表
    required: bool                          # 沒有「未選擇」；必須選取
    fixed_choices: tuple[str, ...] | None = None   # 原樣顯示，不翻譯

OUTPUT_MODE_UNICODE, OUTPUT_MODE_ASCII = "unicode", "ascii"
VIEW_SCHEME_LIGHT, VIEW_SCHEME_DARK = "light", "dark"
BRAILLE_FONT_DEFAULT, BRAILLE_FONT_SIMBRAILLE = "default", "simbraille"

OUTPUT_MODE_OPTIONS = (SettingOption(OUTPUT_MODE_UNICODE, N_("Unicode")),
                       SettingOption(OUTPUT_MODE_ASCII, N_("ASCII")))
VIEW_SCHEME_OPTIONS = (ViewSchemeOption(VIEW_SCHEME_LIGHT, N_("Light"), (255, 255, 255), (0, 0, 0)),
                       ViewSchemeOption(VIEW_SCHEME_DARK, N_("Dark"), (0, 0, 0), (255, 255, 255)))
BRAILLE_FONT_OPTIONS = (SettingOption(BRAILLE_FONT_DEFAULT, N_("Default")),
                        SettingOption(BRAILLE_FONT_SIMBRAILLE, N_("SimBraille")))
CONVERSION_WIDTH_RANGE = IntRange(10, 200)
VIEW_FONT_SIZE_RANGE = IntRange(8, 48)
TRANSLATION_TABLE_FIELDS = (
    TranslationTableField("default", N_("Default Translation Table"), None, True),
    TranslationTableField("en", N_("English Translation Table"), "en", False),
    TranslationTableField("zh", N_("Chinese Translation Table"), "zh", False),
    TranslationTableField("ja", N_("Japanese Translation Table"), "ja", False),
    TranslationTableField("math", N_("Math Translation Table"), None, True, MATH_BRAILLE_TABLES),
)

def option_values(options) -> tuple[str, ...]
def normalize_option_value(options, value, default: str) -> str   # 是成員就回傳 value，否則回傳 default
def option_index(options, value) -> int                           # 第一個相等值的索引，否則 0
def option_value_at(options, index: int) -> str                   # options[index].value；index < 0 或 >= len 時為 options[0].value
```

msgid 以字面值寫在 `N_()` 裡，所以 `xgettext --keyword=N_`（`scripts/generate-pot.bat` 已有）與 msgid 掃描都會擷取。匯入 `settings.options` 會執行 `settings/__init__`（因此也會載入 `config`），這和現在匯入任何 settings 模組時完全一樣；`options.py` 本身除了上列匯入之外不再增加任何匯入。現在匯入 `settings.translation` 或 `settings.view` 也會（經由 `options.py`）匯入 `i18n`；`i18n` 除了載入隨附的目錄之外沒有其他副作用，而每個 GUI 行程本來就會載入它。

小型程式碼選擇：每個欄位以屬性 docstring 說明，模組 docstring 記錄 D3 的循環匯入原因。`option_value_at` 保留舊的 `index < 0 or index >= len` 判斷；`normalize_option_value` 用 `in option_values(options)`（與以前一樣是 tuple 成員判斷）；`IntRange.clamp` 就是舊的 `max(minimum, min(maximum, value))`。

### 變更後的使用端

- `settings/translation.py`：`_normalize_output_mode` -> `normalize_option_value(OUTPUT_MODE_OPTIONS, value, DEFAULT_TRANSLATION_SETTINGS.output_mode)`；`_normalize_width` -> `CONVERSION_WIDTH_RANGE.clamp`。移除 `MIN/MAX_CONVERSION_WIDTH` 與 `SUPPORTED_OUTPUT_MODES`。由於 `settings/dialogs.py` 從 `.translation` 與 `.view` 匯入寬度與字型大小常數，同一步也要把對話框的兩個 spin（`min`/`max`/`initial` 與兩處 `load_snapshot` 夾限，共 4 處）及其匯入改為 `CONVERSION_WIDTH_RANGE`/`VIEW_FONT_SIZE_RANGE`；否則 `import settings.dialogs`（連帶 `gui`）會失敗。
- `settings/view.py`：同理，改用 `VIEW_FONT_SIZE_RANGE`、`VIEW_SCHEME_OPTIONS`、`BRAILLE_FONT_OPTIONS` 與 `config.DEFAULT_*`。移除那四個常數。
- `settings/dialogs.py`：移除三個選項 tuple 與 `CHOICE_SPECS`。選項以 `[_(o.label) for o in ...]` 建立。六個 `_selected_*`/`_select_*` 的內容改用 `option_value_at`/`option_index`，spin 改用 `range.minimum/maximum/clamp`（已在步驟 3 完成，見上）。`TranslationTablesPanel` 透過類別屬性 `TABLE_FIELDS = TRANSLATION_TABLE_FIELDS` 逐一處理 `TRANSLATION_TABLE_FIELDS`（測試可覆寫）。每列 `StaticText` 的標籤與驗證訊息都用 `_(field.label)`。`not field.required` 時在最前面加上「未選擇」。`is_valid`/`validation_error` 依欄位順序檢查必填欄位（`is_valid` 改為 `all(... for field in TABLE_FIELDS if field.required)`：呼叫相同，短路行為也與 `default and math` 相同）。`_options_for_key` 改為 `_options_for_field(field)`：有 `fixed_choices` 時建成 `TableOption(v, v)`，否則呼叫保留下來的 `_options_for_lang(field.file_prefix)`。`_load_table_options`、`TableOption` dataclass、`_("None selected")` 與 `_(table.displayName)`（在該清單上方加上新註解，D6）都留在對話框。
- `gui.py`：`VIEW_SCHEMES` 由 `VIEW_SCHEME_OPTIONS` 建成（鍵相同，值為 `{"background": wx.Colour(*bg), "foreground": wx.Colour(*fg)}`）。改用 `settings.braille_font == BRAILLE_FONT_SIMBRAILLE`。
- `config.py`：`DEFAULT_TRANSLATION_TABLES` 改為 `"math": DEFAULT_MATH_BRAILLE_TABLE`，其餘不變，`config` 也不新增匯入。
- 不更動：`settings/state.py`、`settings/translation_tables.py`、`conversion/*`（包括 `output.py:85` 的 `== "ascii"` 與 `text/pipeline.py:71` 的 `{"default", "math"}`，見「不在範圍內」）、`main.py`、`dual_view/*`、`braille/*`、`locales/*`、`scripts/*`。

## 維持不變的部分

所有選項的顯示順序與標籤（zh_TW：Braille Type `Unicode, ASCII`；Scheme `淺色, 深色`；Braille Font `預設, SimBraille`；表格列 `預設轉譯表, 英文轉譯表, 中文轉譯表, 日文轉譯表, 數學轉譯表`；math `UEB, Nemeth`；en/zh/ja 列最前面是「未選擇」）、每個儲存值對應的選取索引、每個索引對應的儲存值（包括 -1 與超出範圍）、spin 的 min/max/initial、正規化結果、驗證訊息與焦點目標、編輯區顏色、SimBraille 字型套用規則、儲存的 `config.json` 位元組、msgid 集合，以及原始碼執行與打包版中排序後的表格顯示名稱。

## 測試計畫

特徵化測試使用**真實的** zh_TW 目錄，絕不 patch `settings.dialogs._`（或 `gui._`）。在舊程式碼下，這種 patch 不會影響選項標籤，因為它們在匯入時就已翻譯；在新程式碼下，同樣的 patch 會顯示英文標籤。所以帶 patch 的測試記錄到的是實作細節，而不是使用者看到的結果。需要未翻譯的標籤時，就對 msgid 與 `i18n._(msgid)` 斷言。

### A. 對現有程式碼的特徵化（步驟 1）

A 部分直接寫出字面值（`"unicode"`、`"淺色"`、`(10, 200)`……），加上 `i18n._(msgid)` 與 `config.DEFAULT_*`，從不使用舊的 tuple，因此步驟 1 之後不再修改。位置：第 1-3 與第 6 項在 `tests/test_settings_dialogs.py`（`TranslationPanelOptionsTest`、`ViewPanelOptionsTest`、`TranslationTablesPanelOptionsTest`、`TableDisplayNameGuardTest`）；第 4 項在 `tests/test_translation_settings.py`（`TranslationSettingsNormalizeTest`）與 `tests/test_view_settings.py`（`ViewSettingsNormalizeTest`）；第 5 項在 `tests/test_gui_document_flows.py`（`EditorViewSettingsCharacterizationTest`），這是唯一有 gui stub scope 的模組。A 部分在現有程式碼上必然通過，所以另用一個拋棄式 mutant runner（不提交）對 `client/` 的複本套用 20 個單點破壞（輸出標籤未翻譯、配色順序對調、不明值選取最後一項、點字字型未選時存成 config 預設值、配色超出範圍時拋例外、寬度 spin 最大值少 1、重新載入寬度或字型大小初始值未夾限、math 也加上「未選擇」、表格列順序改變、math 選項倒序、表名未再翻譯、空白列仍啟用、不明表格選取最後一項、先驗證 math、儲存時漏掉 math、寬度下限未夾限、不明配色變成 dark、dark 前景色差 1、只在字型已註冊時才用 SimBraille），證明每一個都會讓 A 部分失敗。

面板的觀察方式：以 `SimpleNamespace` 作為 owner，在 `patch.multiple(module.wx, Choice=RecordingChoice, SpinCtrl=RecordingSpin)` 與 `patch.object(module, "listTables", ...)` 下，建構 `sys.modules["settings.dialogs"]` 中真正的面板類別。列由版面讀出：stub 的 `FlexGridSizer` 會記錄每次 `Add`，所以能依序取得（標籤、控制項）配對，驗證的焦點目標則與該列的控制項比對。只使用公開屬性 `output_choice`、`width_spin`、`dictionary_choice`、`scheme_choice`、`braille_font_choice`、`font_size_spin`（用來設定選取），從不讀取私有欄位或欄位清單。

1. 在 settings stub scope 下，以上述記錄用 `wx.Choice`/`wx.SpinCtrl` 實際建構 Translation 面板。斷言：輸出選項為 `["Unicode", "ASCII"]`（且 `== [i18n._("Unicode"), i18n._("ASCII")]`）；`unicode`/`ascii`/不明值的初始選取（0/1/0）；選取 0、1、-1、2 時 `on_save` 的值（`unicode`、`ascii`、`unicode`、`unicode`）；寬度 5、40、500 時寬度 spin 的 min/max/initial。
2. View 面板：配色選項 `["淺色", "深色"]`，點字字型選項 `["預設", "SimBraille"]`，各值與不明值的選取。`on_save` 把選取 -1 對應到 `light`/`default`（釘住 K1：不是 `simbraille`）。字型 spin 的 min/max/initial 會夾限。
3. Tables 面板，以 stub `listTables` 回傳假的類 `BrailleTable` 物件：有些是英文名稱（原始碼執行路徑），一個已是 zh_TW（打包路徑），一個 `output=False`，檔名涵蓋 `en`/`zh`/`ja` 前綴、一個大寫檔名（`en-GB-g2.ctb`）、一個 `zhcn` 前綴（K4）與一個不符合任何前綴的。斷言：列標籤與順序；每列的顯示清單（已排序，只有 en/zh/ja 最前面有「未選擇」，math 恰為 `UEB, Nemeth`）；英文名稱與 zh 名稱得到相同的 zh 標籤；沒有選項的列停用且為 `NOT_FOUND`；不明的儲存檔名選取索引 0（釘住 K2）；`on_save` 的鍵與順序；`default` 空白時的驗證訊息與焦點，再來是 `math` 空白時的。
4. 正規化函式：每份清單的每個值都原樣保留，不明值變成 `config.DEFAULT_*`，兩端都會夾限。
5. gui 配色顏色：在 gui scope 下，`gui.VIEW_SCHEMES` 等於 `{"light": {background (255,255,255), foreground (0,0,0)}, "dark": 相反}`（stub 的 `wx.Colour` 是 tuple）。由於步驟 5 會修改 `_apply_editor_view_settings`，而既有測試一律 mock 它，因此也一併特徵化：兩個編輯區的字型大小、顏色及其呼叫順序、字型已註冊／`win32`／兩者皆非時的 SimBraille 字型，以及不明值的正規化。
6. 表格顯示名稱守門（永久保留）：以 AST 解析 `braille/tables/__tables.py`，不匯入它。對每個 `addTable` 名稱斷言 `i18n._(i18n._(name)) == i18n._(name)`，並斷言 output 表翻譯後排序的清單，不論從英文名稱或從已翻譯名稱建立都相同。

### B. 選項模組（步驟 2；新的 `tests/test_settings_options.py`，4 個空白，無 wx，無 stub scope）

各 tuple 確切的值、msgid 與順序；描述子是凍結的，清單是 tuple；輔助函式的行為（成員、不明值、-1、超出範圍，以及空的選項 tuple：`option_values(()) == ()`、`option_index((), v) == 0`、`normalize_option_value((), v, d) == d`；`None` 檔名前綴由 A 部分的 default 列涵蓋）；`IntRange.clamp`。不變式：每個 `config.DEFAULT_OUTPUT_MODE/VIEW_SCHEME/BRAILLE_FONT` 都在對應的值之中；`DEFAULT_VIEW_FONT_SIZE`/`DEFAULT_CONVERSION_WIDTH` 都在各自範圍內；`tuple(f.key for f in TRANSLATION_TABLE_FIELDS) == tuple(config.DEFAULT_TRANSLATION_TABLES)`；math 欄位的 `fixed_choices is math_braille_codes.MATH_BRAILLE_TABLES`；`config.DEFAULT_TRANSLATION_TABLES["math"] == DEFAULT_MATH_BRAILLE_TABLE`，並以 AST 檢查 config 寫的是名稱 `DEFAULT_MATH_BRAILLE_TABLE`（讓步驟 2 的 config 修改先紅燈）；必填鍵恰為 `{"default", "math"}`。另有 AST 守門（匯入、不得有 `_`），並檢查每個標籤都是 `N_()` 的字面引數。共 19 個測試、四個類別：`OptionListsTest`（6）、`OptionHelpersTest`（5）、`ConfigDefaultsInvariantTest`（5）、`OptionsModuleGuardTest`（3）。此測試模組在最上層、任何 stub scope 之外匯入 `settings.options`，讓描述子類別的身分在各 scope 間一致。`tests/test_i18n.py` 新增 `test_settings_options_uses_shared_i18n`（`{"N_"}`），`settings/dialogs.py` 的期望仍為 `{"_"}`。

### C. 遷移（步驟 3-5）

每一步之後，A 部分都不需修改即可通過。既有測試只有一處修改：兩個指定 `panel.CHOICE_SPECS` 的測試在步驟 4 拿掉該指定（類別預設值就是同樣的五個欄位）。A 部分沒有需要切換的不變式測試（不變式都在 B 部分）。

步驟 3-5 的紅燈步驟：每一步先在 `tests/test_settings_options.py` 的 `OptionSourceConsumerTest` 加一個守門測試並確認紅燈。步驟 3（`test_normalizers_define_no_option_lists_or_ranges`）：`settings/translation.py` 的模組層級指定只有 `DEFAULT_TRANSLATION_SETTINGS`，`settings/view.py` 則沒有。步驟 4（`test_settings_panels_define_no_option_lists_or_option_values`）：`settings/dialogs.py` 只有 `_DEAD_WINDOW_ERROR_TYPES` 與 `CommitSettings`，`TranslationTablesPanel` 的類別本體只指定 `title`、`panel_description`、`TABLE_FIELDS`。步驟 5（`test_gui_spells_out_no_option_values`）只檢查 `gui.py` 的字面值。三個守門都檢查遷移後的模組中沒有任何選項值的字串字面值（`unicode ascii light dark simbraille UEB Nemeth`，對話框另加表格鍵）。守門是允許清單，從不寫出被移除的名稱，所以 AC6 的第一個 grep（也涵蓋 `client/tests`）仍為空。`translation.py` 不檢查 `"default"`，因為那裡它是預設字典的名稱。

## 遷移步驟（每一步一個全綠的 commit）

1. `test: characterize settings option lists`（A 部分，針對現有程式碼）。
2. `refactor: add settings option source`（B 部分。模組尚未被使用；唯一例外是 `config.DEFAULT_TRANSLATION_TABLES["math"]` 改為 `DEFAULT_MATH_BRAILLE_TABLE`，值完全相同）。
3. `refactor: normalize settings through option source`（`settings/translation.py`、`settings/view.py`；移除舊常數；也包括使用這些常數的對話框寬度與字型大小 spin 及其匯入；一個守門測試）。
4. `refactor: build settings panels from option source`（`settings/dialogs.py`；移除 `CHOICE_SPECS` 與 `_options_for_key` 分派；D6 註解；上述兩處測試修改；一個守門測試）。
5. `refactor: derive gui view schemes from option source`（`gui.py`；一個守門測試）。

## 驗收條件

1. Linux 上的路線圖驗證：`cd client && $PY -m unittest tests.test_settings_dialogs tests.test_translation_settings tests.test_view_settings tests.test_settings_options -v` 通過（99 個測試）。
2. 以下也全綠：`tests.test_settings_state tests.test_translation_tables tests.test_math_braille_codes tests.test_config tests.test_gui_document_flows tests.test_i18n tests.test_wx_stub tests.test_removed_dead_code tests.test_translation_golden tests.test_dictionary_entries_dialog`。
3. 完整套件：973 + 50 = 1023 個測試（步驟 1：27，步驟 2：20，步驟 3-5 各 1），`failures=1`（只有 P2-5），`errors=0`，`skipped=9`。shuffle harness（`$SP/shuffle_harness.py`）種子 0-19 每個都只有同一個失敗。`test_settings_options`、`test_settings_dialogs` 與 `test_gui_document_flows` 單獨執行可通過，並且與 `test_settings_options` 兩兩配對、兩種順序都通過。
4. 上述兩個測試資料的 sha256 不變，且 `git diff main -- client/tests/fixtures` 為空。
5. msgid 掃描：353，且以從 `main` 存下的清單執行 `--compare` 時回報 `SOURCE == SAVED`。`git diff main --stat -- client/locales scripts client/braille client/conversion client/dual_view client/main.py` 為空。
6. `grep -rnE "SUPPORTED_OUTPUT_MODES|VIEW_SCHEME_KEYS|BRAILLE_FONT_KEYS|_OUTPUT_MODES|_VIEW_SCHEME_OPTIONS|_BRAILLE_FONT_OPTIONS|CHOICE_SPECS|_options_for_key|MIN_CONVERSION_WIDTH|MAX_CONVERSION_WIDTH|VIEW_FONT_SIZE_MIN|VIEW_FONT_SIZE_MAX" client --include=*.py` 沒有任何輸出。`grep -rnE '"(unicode|ascii|light|dark|simbraille|UEB|Nemeth)"' client --include=*.py --exclude-dir=tests` 只列出 `settings/options.py`、`config.py`（`DEFAULT_OUTPUT_MODE`、`DEFAULT_VIEW_SCHEME`、`DEFAULT_BRAILLE_FONT`）、`conversion/math_braille_codes.py`、`conversion/output.py`（2 處）、`conversion/presenter.py`（1 處）與 `main.py`（1 處）。若工作目錄中有被 git 忽略的 `client/.venv`，兩個 grep 都需要加上 `--exclude-dir=.venv`，否則也會列出第三方套件。
7. `client/settings/options.py` 通過 AST 守門，`tests.test_i18n` 連同新的使用端測試一起通過。

## 風險

- **翻譯時機（D2）。** 正式環境的標籤相同，但 `patch("settings.dialogs._", identity)` 現在也會把選項與表格欄位標籤變成英文。現有使用這個 patch 的測試只斷言驗證訊息；而在 patch 下，那個訊息本來就使用英文欄位標籤，因為測試注入的是英文的 `CHOICE_SPECS`。A 部分完全不使用這個 patch。
- **循環匯入（D3）。** 日後若把預設值移進 `options.py`，再讓 `config` 匯入它，匯入時就會卡死。`options.py` 中加一段簡短註解，說明預設值為何不在那裡。
- **stub scope 下的類別身分。** 凍結 dataclass 的 `__eq__` 要求同一個類別。兩個載入 `settings.dialogs` 的 stub scope 都用 `evict_nothing`，新測試也在任何 scope 之前就匯入 `settings.options`。由配對順序測試與 shuffle 涵蓋。
- **藏在輔助函式裡的行為（D7）。** 「超出範圍 -> 第一個選項」與「不明值 -> 索引 0」很容易被「修正」成「-> 預設值」。A 部分透過面板釘住它們，B 部分釘住輔助函式。
- **xgettext 的原始碼參照。** 在 Windows 上重新產生 `.pot` 時，這些 msgid 的 `#:` 參照會移到 `settings/options.py`。msgid 本身不變，所以不需要編輯 `.po` 或重建 `.mo`。
- **PyInstaller。** `settings/options.py` 會經由 `settings/dialogs.py`、`settings/translation.py`、`settings/view.py` 與 `gui.py` 的靜態匯入被納入（只閱讀確認，未實際執行）。
- **真實 wx。** 這裡的一切都只用 stub 檢查過。

## 保留的既有特性（釘住，不修正）

1. **K1** 沒有選取（-1）或選取超出範圍時，Translation 與 View 面板儲存的是**第一個**選項（`unicode`、`light`、`default`），而不是 config 預設值（點字字型的預設值是 `simbraille`）。實務上不會發生，因為 `_select_*` 一定會選取某個索引。
2. **K2** 儲存的表格檔名若不在該列的選項中，會無聲地選取索引 0，按套用或確定時就會存下那個選項。`default` 列是依字母排序的第一個翻譯後表格，en/zh/ja 是「未選擇」，`math` 則是 `UEB`。
3. **K3** 轉譯表載入時從不正規化，任何字串都接受；`MATH_BRAILLE_TABLES` 以外的數學值會傳到轉換流程，由 `conversion/mathcat_adapter.py` 退回 `UEB`。
4. **K4** 前綴篩選只是對小寫檔名做 `startswith`（例如 `zh` 也會符合所有 `zh-*`/`zhcn*` 表）。

釘住這些特性的測試標記為 `# KNOWN QUIRK (P2-3 spec, Kn)`：K1 `ViewPanelOptionsTest.test_save_maps_out_of_range_selections_to_the_first_option` 與 `OptionHelpersTest.test_option_value_at_maps_out_of_range_indexes_to_the_first_option`；K2 `TranslationTablesPanelOptionsTest.test_unknown_or_missing_file_names_select_the_first_option`；K4 `TranslationTablesPanelOptionsTest.test_each_row_lists_its_tables_sorted_by_translated_name`。K3 除了 K2 之外沒有面板上可見的影響，交由既有的 `test_translation_tables` 涵蓋。

## Windows 驗證債

- 打包版、zh_TW、搭配 NVDA：在三個面板上分別開啟設定，將截圖與報讀出的選項清單和 `main` 比較（標籤、順序、初始選取）。切換配色與點字字型，檢查編輯區顏色與 SimBraille 字型。讓 en/zh/ja 維持「未選擇」後按套用。Default 列空白時顯示驗證訊息，並把焦點移到該列。
- 在 Windows 上從原始碼執行，顯示的表格名稱（已翻譯、已排序）與打包版相同（D6）。
- `scripts\generate-pot.bat`：msgid 集合不變，只有參照位置移動。
- PyInstaller 納入了 `settings/options.py`。

## 不在範圍內

- 把寫入設定檔的預設值移出 `config.py`（D3）；載入時正規化轉譯表（K3）；修正 K1、K2 或 K4。
- 編輯 `braille/tables/__tables.py`，或重新排序 `listTables()`（M-5 仍是 P2-7 的後續候選；沒有可見影響）。
- `conversion/output.py` 的 `"ascii"` 判斷，以及 `conversion/text/pipeline.py:71` 的 `{"default", "math"}`／由鍵推導出的語言清單。conversion 不能匯入 `settings`；在 conversion 端為輸出模式建立 leaf（類似 `math_braille_codes`）應另立任務。
- 字典選項（動態清單），以及 `get_settings_snapshot` 每次重新列出字典（P0 審查 M-8，P2-6）。
- `sync_open_font_size`（P2-4）。面板標題與說明仍在匯入時翻譯（類別屬性）。
- `main.py` 示範程式中的 `output_mode="unicode"`。
