# Task 0 Review

## Review Scope

Reviewed the commits listed in `docs/superpowers/finish_task0.md`, in commit-time order:

1. `32985a9` `feat: add document import foundation`
2. `7f58970` `feat: import DOCX EPUB and PDF documents`
3. `7086fbe` `feat: expose multi-format document import`

Review references:

- `docs/superpowers/specs/2026-06-30-multi-format-document-import-design.md`
- `docs/superpowers/plans/2026-06-30-multi-format-document-import-implementation-plan.md`

The main agent performed the review. Confirmed defects were assigned to a GPT-5.4 sub-agent, then independently inspected and verified again by the main agent.

## Commit Review

### `32985a9` - Document import foundation

The AST, Markdown renderer, and shared lxml mapper match the intended architecture and keep inline semantics flattened to plain text.

Historical commit-level issue:

- `client/documents/importers/__init__.py` imported the DOCX, EPUB, and PDF importer modules before those files existed. Checking out this commit alone and running `tests.test_markdown_ast` fails with `ModuleNotFoundError`.
- This is no longer present in the final tree after `7f58970`, but the first commit was not independently buildable.

Defect found and fixed in the final tree:

- List items containing inline elements duplicated tail text, for example `One <em>bold</em> tail`.
- The mapper now buffers inline text and flushes it around actual nested block elements.
- Regression tests cover inline tails and tails following nested blocks.

### `7f58970` - DOCX, EPUB, and PDF importers

The format-specific pipelines, required dependencies, PDF `/MarkInfo` and `/StructTreeRoot` checks, and PyMuPDF fallback follow the design.

Defects found and fixed:

- `_build_page_indexes()` used real `pypdf.PageObject` instances as dictionary keys. `PageObject` is unhashable, so tagged PDFs silently abandoned semantic extraction and used plain-text fallback.
- Page lookup now uses stable object and indirect-reference identities. Tests use real pypdf page objects and `/Pg` indirect references.
- An unusable tagged tree with no extracted blocks returned an empty AST instead of triggering plain-text fallback. Empty semantic results now raise `ValueError`, and an integration test verifies fallback preserves available text.
- DOCX tests mocked already-semantic HTML, but Mammoth's default style map does not emit block quotes or horizontal rules for common Word styles. The importer now supplies a narrow style map for `Quote`, `Intense Quote`, and `Horizontal Rule`, while preserving Mammoth defaults and disabling embedded style maps and external file access.
- The plan's real-format smoke fixtures were missing. Copyright-free DOCX, EPUB, tagged PDF, and untagged PDF fixtures now exercise the actual libraries. DOCX covers heading, list, quotes, horizontal rule, and table. EPUB verifies two-item spine order and block semantics. The tagged PDF assertion proves the semantic path is used rather than fallback.

### `7086fbe` - Workspace and UI integration

The workspace loader registry, `Document.text` integration, batch issue behavior, duplicate handling, menu order, format keys, and file-dialog wildcard mapping match the spec. Existing DEP/TXT behavior remains intact.

Defect found and fixed:

- The Traditional Chinese PO and POT contained the new wildcard translations, but `dotexpress.mo` was not regenerated. Runtime gettext therefore returned English wildcard labels.
- The MO catalog was regenerated and is now covered by a runtime gettext test for PDF, DOCX, and EPUB wildcards.

## Final Assessment

No unresolved code or spec findings remain in the reviewed final tree.

Residual verification limits:

- Windows-only wxPython interaction and the packaged PyInstaller build were not run in this Linux environment.
- Existing liblouis tests requiring Windows remain skipped.
- The tagged PDF fixture covers a single-page H1 plus paragraph. List, quote, and table structure-tree mappings remain covered by unit-level logic rather than a complex PDF/UA fixture.

## Verification

Main-agent verification:

```bash
cd client
../client/.venv/bin/python -m unittest discover -s tests -v
```

Result: `167` tests run, `OK`, with `8` existing platform-specific skips.

```bash
cd client
../client/.venv/bin/python -m compileall -q .
```

Result: exit code `0`.

Runtime gettext verification loaded `client/locales/zh_TW/LC_MESSAGES/dotexpress.mo` and confirmed:

- `PDF files (*.pdf)|*.pdf` -> `PDF 檔案 (*.pdf)|*.pdf`
- `Word documents (*.docx)|*.docx` -> `Word 文件 (*.docx)|*.docx`
- `EPUB books (*.epub)|*.epub` -> `EPUB 電子書 (*.epub)|*.epub`

```bash
git diff --check
```

Result: no whitespace errors.
