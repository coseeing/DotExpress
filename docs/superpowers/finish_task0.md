# Task 0 完成說明

## 完成內容

- 新增 `client/documents/importers/` 基礎層，包含 immutable block-level AST、Markdown renderer，以及共用 HTML/XHTML -> AST mapper。
- 新增 `DOCX`、`EPUB`、`PDF` importer，並把它們接到既有 `Document.text` 流程。
- 擴充 `batch_import_documents()`，支援 `dep`、`txt`、`docx`、`epub`、`pdf`。
- 更新 `Import` 選單、`wx.FileDialog` wildcard 與繁中翻譯字串。
- 補齊新格式與整合層測試。

## 驗證

- `python3 -m compileall -q client`
- `../client/.venv/bin/python -m unittest tests.test_markdown_ast tests.test_markdown_renderer tests.test_html_to_ast tests.test_docx_importer tests.test_epub_importer tests.test_pdf_importer tests.test_document_workspace tests.test_action_menu -v`

## Commit List

- `32985a9` `feat: add document import foundation`
- `7f58970` `feat: import DOCX EPUB and PDF documents`
- `7086fbe` `feat: expose multi-format document import`
