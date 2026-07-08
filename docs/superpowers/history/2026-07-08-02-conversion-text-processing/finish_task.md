# Finish Task

## Result

完成 `conversion` 前處理與規則收斂：

- 新增 `client/conversion/text/` 作為 conversion-facing text processing 的唯一邊界。
- 將 char map、dictionary rules、math segmentation、pipeline orchestration 拆到新模組。
- `client/conversion/output.py` 與 `client/conversion/service.py` 改成走新 pipeline。
- `client/conversion/plain_text.py` 只保留 literal/error helpers。
- 刪除 `client/utils.py` 與 `client/conversion/segments.py`，不保留舊 helper 入口。
- 補上新的行為回歸測試，涵蓋 char maps、dictionary rules、math segments、pipeline 與既有 conversion / GUI 流程。

## Verification

已執行並通過：

- `python3 -m pytest tests/test_conversion_text_char_maps.py tests/test_conversion_text_dictionary_rules.py tests/test_conversion_segments.py -q`
- `python3 -m unittest tests.test_conversion_text_math_segments tests.test_conversion_text_pipeline tests.test_conversion_service -v`
- `python3 -m unittest tests.test_dual_view_model -v`
- `python3 -m unittest tests.test_gui_document_flows -v`

## Commits

- `aec3331` `refactor: converge conversion text processing`

