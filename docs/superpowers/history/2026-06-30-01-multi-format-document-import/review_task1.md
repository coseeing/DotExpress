# Task 1 Review

## Review Scope

Main agent reviewed the commits listed in `docs/superpowers/finish_task0.md` in commit-time order:

1. `32985a9` `feat: add document import foundation`
2. `7f58970` `feat: import DOCX EPUB and PDF documents`
3. `7086fbe` `feat: expose multi-format document import`

The review compared each commit and the resulting working tree against:

- `docs/superpowers/specs/2026-06-30-multi-format-document-import-design.md`
- `docs/superpowers/plans/2026-06-30-multi-format-document-import-implementation-plan.md`

Existing uncommitted work was preserved. Confirmed defects were assigned to a sub-agent with test-first instructions, and every resulting change was independently reviewed and verified by the main agent.

## Commit Review

### `32985a9` - Document import foundation

The immutable block AST, centralized Markdown renderer, and shared lxml HTML/XHTML mapper match the planned architecture.

Findings:

- The commit was not independently testable because `documents.importers.__init__` imported the DOCX, EPUB, and PDF modules before those modules existed. The completed three-commit result resolves this historical sequencing issue.
- List-item inline content duplicated tail text in cases such as `One <em>bold</em> tail`. The working tree now buffers inline fragments and flushes them around nested block elements, with regression coverage.
- Ordered-list continuation indentation was fixed at two spaces. Item 10 and later therefore produced invalidly aligned multiline or nested content. The renderer now derives continuation width from the current marker, with a regression test for item 10.

### `7f58970` - DOCX, EPUB, and PDF importers

The format-specific importer boundaries, pinned dependencies, EPUB spine ordering, tagged-PDF inspection, and PyMuPDF fallback follow the design.

Findings:

- Real `pypdf.PageObject` values are unhashable, so the original page-index map caused tagged semantic extraction to fail and silently fall back. Page matching now uses stable indirect-reference and object identities.
- A tagged structure that produced no blocks returned an empty document instead of falling back. Empty semantic output is now treated as unreliable.
- DOCX conversion did not map common Word quote and horizontal-rule styles. A restricted Mammoth style map now handles `Quote`, `Intense Quote`, and `Horizontal Rule` while retaining the existing external-file and embedded-style-map protections.
- Tagged PDF `/LBody` descendants were flattened into one paragraph, losing nested list and block semantics. `/LBody` now recursively maps descendant blocks.
- Ordered PDF lists only read a direct `/ListNumbering` property. The importer now also reads `/ListNumbering` from a PDF `/A` attribute dictionary or attribute array while retaining direct-property compatibility.
- `PdfReadError` from tagged structure extraction escaped instead of invoking the required whole-file plain-text fallback. It is now handled narrowly as a semantic parsing failure.
- Real DOCX, EPUB, tagged PDF, and untagged PDF smoke fixtures were added. The tagged fixture asserts semantic Markdown so fallback cannot satisfy the test accidentally.

### `7086fbe` - Workspace and UI integration

The loader registry, `Document.text` integration, duplicate and batch issue behavior, menu ordering, format keys, and wildcard mapping match the spec without changing the DEP format or `Document` model.

Finding:

- PO and POT entries existed, but the Traditional Chinese MO catalog had not been regenerated. The compiled catalog is now updated and covered by runtime gettext assertions for PDF, DOCX, and EPUB wildcards.

## Main-Agent Re-review

The main agent inspected the sub-agent changes for spec compliance and code quality. The added exception handling remains limited to known tagged-PDF parse failures; it does not swallow arbitrary programming errors. Regression tests exercise AST and rendered behavior, including nested lists and two-digit ordered-list markers.

No unresolved code or spec findings remain in the reviewed working tree.

## Verification

From `client/`:

```bash
../client/.venv/bin/python -m unittest discover -s tests -v
```

Result: `171` tests ran successfully, with `8` existing platform-specific skips.

```bash
../client/.venv/bin/python -m compileall -q .
git diff --check
```

Result: both commands exited with status `0`.

Verification limits:

- Windows-only wxPython interaction and the packaged Windows build were not run in this Linux environment.
- Windows liblouis runtime tests remain skipped.
- Complex tagged-PDF list, quote, and table cases are primarily unit-level object-graph tests; the real tagged fixture currently covers heading and paragraph semantics.
