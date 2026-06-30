# Multi-Format Document Import and Markdown Intermediate Design

## Summary

DotExpress currently supports document import only for plain-text `TXT` files and the existing packaged `DEP` format. This design expands import sources to `PDF`, `DOCX`, and `EPUB`, and converts imported content into a unified Markdown string before writing it into the existing `Document.text`.

The core of the design is not to generate output strings directly for each format. Instead, it introduces an intermediate AST that describes only block-level semantics. `DOCX` and `EPUB` follow a semantic-preserving path. `PDF` first checks whether tagged PDF structure is available; if usable semantics exist, they are converted into AST, and if not, the importer falls back directly to plain text without any layout heuristic inference.

## Background

- The current document import entry point is `on_import_document(format_key)` in [client/gui.py](/workspace/DotExpress/client/gui.py:1044).
- The current batch import implementation is `batch_import_documents()` in [client/documents/workspace.py](/workspace/DotExpress/client/documents/workspace.py:162).
- At present there are only two import formats:
  - `dep` -> `load_document_package()`
  - `txt` -> `load_text_document()`
- The current `Document` model contains only:
  - `name`
  - `text`
  - `braille`

This means new multi-format support should be designed primarily as a pre-import conversion step, rather than by changing the workspace storage model or the `DEP` package format.

## Goals

- Support importing documents from `PDF`, `DOCX`, and `EPUB`.
- Preserve block-level semantics for `DOCX` and `EPUB` where feasible and output Markdown.
- Extract block-level structure from `PDF` when tagged PDF semantics are available and output Markdown.
- Fall back to plain-text extraction for `PDF` when usable semantics are not available.
- Keep the existing `Document` model and `DEP` workspace format unchanged.
- Integrate the new formats into the existing `Import` menu and batch import flow.

## Non-Goals

- Do not change the `.dep` package format.
- Do not change the type of `Document.text`.
- Do not preserve inline semantics such as emphasis, links, or footnotes.
- Do not infer headings, lists, tables, block quotes, or horizontal rules from untagged PDFs.
- Do not promise Markdown table reconstruction for PDFs that lack structural markup.
- Do not support legacy `DOC` in the first version.

## Confirmed Requirements

This design follows these confirmed constraints:

- Version 1 of Word support includes `DOCX` only.
- Preserved semantics are limited to block-level elements:
  - headings
  - lists
  - block quotes
  - horizontal rules
  - tables
- Inline semantics are ignored for now.
- `PDF` must check `/MarkInfo` and `/StructTreeRoot` first.
- If a `PDF` has no semantics, it is converted directly to plain text without inference.
- If a `PDF` has semantics, those semantics must be extracted rather than always falling back to plain text.

## Core Decisions

### 1. Use a block-level AST as the only intermediate model

No new import format should output Markdown strings directly. Each importer first produces a shared AST, and a renderer then serializes that AST into Markdown.

Benefits:

- `DOCX`, `EPUB`, and `PDF` can share the same output rules for semantics.
- Tests can validate semantic structure directly instead of only comparing final strings.
- Future output formats such as plain text or HTML can reuse the same intermediate result.
- `PDF` plain-text fallback can still fit within the existing block vocabulary without requiring extra AST node types.

### 2. The AST supports block-level semantics only

The version 1 AST types are:

- `Document(blocks)`
- `Heading(level, text)`
- `Paragraph(text)`
- `ListBlock(ordered, items)`
- `ListItem(blocks)`
- `BlockQuote(blocks)`
- `HorizontalRule()`
- `Table(headers, rows)`

Where:

- `Heading.level` is limited to `1` through `6`
- `Paragraph.text` and `Heading.text` both store plain text only
- `ListItem.blocks` allows nested blocks so the model does not need to be rewritten for future extensions

No inline AST is introduced, such as `Strong`, `Emphasis`, `Link`, or `Footnote`.

### 3. The Markdown renderer is responsible only for serialization

The Markdown renderer is responsible for:

- `Heading` -> `#` through `######`
- `Paragraph` -> normal paragraphs
- `ListBlock` / `ListItem` -> ordered or unordered lists
- `BlockQuote` -> `>`
- `HorizontalRule` -> `---`
- `Table` -> Markdown tables

The renderer must not infer structure and must not reinterpret source content. All semantic decisions must be completed inside the format-specific importers.

### 4. `DOCX`, `EPUB`, and `PDF` use format-specific strategies rather than one universal converter

This design does not use a single pipeline such as “convert everything to HTML first, then convert HTML to Markdown.”

Reasons:

- `DOCX` and `EPUB` already contain clearer document semantics and should preserve them directly.
- If `PDF` lacks structural tags, converting it to HTML does not make it a reliable semantic source.
- A single universal path would let PDF degradation leak into `DOCX` and `EPUB`, reducing maintainability.

Therefore each format has its own importer, while all importers share the same AST and Markdown renderer.

### 5. `PDF` uses a two-path strategy: semantic first, plain text on fallback

The `PDF` processing order is fixed:

1. Open the file with `pypdf`.
2. Check `/MarkInfo` in the catalog and document structure.
3. Check whether `/StructTreeRoot` exists.
4. If usable tagged structure exists, follow `tagged PDF -> AST -> Markdown`.
5. If it does not exist, cannot be parsed, or cannot be mapped reliably to the supported block-level AST, fall back to plain-text extraction with `PyMuPDF`.

The key points of this decision are:

- `pypdf` is a required dependency of the `PDF` importer and is responsible for structure inspection and structure-tree reading.
- `PyMuPDF` is a required dependency for the plain-text fallback and is responsible for stable text extraction.
- No heuristics should guess semantics from font size, indentation, boldness, or line segments.

## Module Design

Suggested new modules for document import:

- `client/documents/importers/__init__.py`
- `client/documents/importers/base.py`
- `client/documents/importers/markdown_ast.py`
- `client/documents/importers/markdown_renderer.py`
- `client/documents/importers/docx_importer.py`
- `client/documents/importers/epub_importer.py`
- `client/documents/importers/pdf_importer.py`
- `client/documents/importers/html_to_ast.py`

### `base.py`

Define a shared importer interface, for example:

- `import_document(path: Path) -> ImportedDocument`
- `ImportedDocument(name: str, markdown_text: str)`

`ImportedDocument` should be the formal return type rather than a plain tuple. The important boundary is that AST generation and Markdown rendering stay encapsulated inside the importer layer and are not exposed to the UI layer.

### `markdown_ast.py`

Define the AST node data structures. `dataclass(frozen=True)` is recommended to make tests and comparisons more stable.

### `markdown_renderer.py`

Accept a `Document` AST and output a Markdown string. All newline rules must be centralized here so that importers do not each hand-roll Markdown and drift apart in formatting.

### `html_to_ast.py`

Centralize the block-level `HTML/XHTML -> AST` mapping logic shared by the `DOCX` and `EPUB` importers.

This layer is fixed to `lxml`:

- `DOCX` uses `lxml.html`
- `EPUB` uses `lxml.html`, switching to `lxml.etree` XML parsing mode when necessary for XHTML

This design does not use `BeautifulSoup` as the primary parser.

## Import Flow by Format

### `DOCX`

`DOCX` uses `mammoth` as the primary converter.

Flow:

1. Read the `DOCX`.
2. Convert it to clean HTML with `mammoth`.
3. Parse the HTML DOM with `lxml.html`.
4. Map the following elements into AST:
   - `h1`-`h6` -> `Heading`
   - `p` -> `Paragraph`
   - `ul` / `ol` / `li` -> `ListBlock` / `ListItem`
   - `blockquote` -> `BlockQuote`
   - `hr` -> `HorizontalRule`
   - `table` / `tr` / `th` / `td` -> `Table`
5. Pass the AST to the Markdown renderer.
6. Use the file stem as the document name and output final Markdown.

Version 1 does not preserve:

- bold
- italics
- links
- images
- footnotes

### `EPUB`

`EPUB` uses `ebooklib` as the primary reader.

Flow:

1. Read the `EPUB`.
2. Extract XHTML/HTML content in spine order.
3. Parse each chapter DOM with `lxml`.
4. Map the same block-level elements used for `DOCX` into AST.
5. Preserve reasonable separation between chapter contents so adjacent spine items do not collapse into a single block.
6. Pass the merged AST to the Markdown renderer.

Key decisions:

- Spine order is the single source of truth for output order.
- Internal EPUB links and navigation structures are not preserved.
- No metadata block is emitted.

### `PDF`

The `PDF` importer has two paths.

#### Path A: tagged PDF semantic path

This path requires `pypdf` to confirm and read a usable `/StructTreeRoot`.

Version 1 formally supports only these block-level mappings:

- `H1`-`H6` -> `Heading`
- `P` -> `Paragraph`
- `L` / `LI` / `Lbl` / `LBody` -> `ListBlock` / `ListItem`
- `BlockQuote` or equivalent quote container -> `BlockQuote`
- `Table` / `TR` / `TH` / `TD` -> `Table`
- structure elements that clearly represent horizontal separation -> `HorizontalRule`

The following cases must not be repaired with heuristics:

- structure tags are missing but the content visually looks like a heading
- only font-size differences exist, without structure tags
- only alignment or indentation exists, without list structure
- a table exists only visually, without parseable structure

For unsupported or unreliably mappable tagged structures:

- If the descendant text can still be flattened safely in source order into a single text block, degrade it to `Paragraph`
- If even source order cannot be preserved reliably, abandon the semantic path for the entire file and fall back to plain text

Version 1 does not process inline tags, footnotes, cross-references, or links.

#### Path B: plain-text fallback

If a `PDF` lacks usable semantics, or `pypdf` cannot build a reliable AST:

1. Use `PyMuPDF` to extract text in page order.
2. Apply the minimum necessary normalization:
   - normalize line endings
   - remove obvious empty-page output
3. Concatenate the text in page order and split it into one or more `Paragraph` blocks using blank-line rules.
4. Pass the result to the Markdown renderer.

Principles of this path:

- guarantee readable plain text only
- do not guess headings
- do not guess lists
- do not guess block quotes
- do not guess horizontal rules
- do not guess tables

## Integration with Existing DotExpress

### Document Model

The `Document` data model remains unchanged:

- `name`
- `text`
- `braille`

Importer output still writes only to `Document.text`. This avoids:

- changing workspace load/save formats
- changing `.dep` internal contents
- changing the existing translation, braille conversion, or editor interfaces

### Workspace and Package Format

The `.dep` format remains unchanged:

- it still stores `<name>.txt`
- it still stores `<name>.brl`
- imported Markdown is stored directly as the `.txt` content

This means the workspace does not need to know whether the original source file was `PDF`, `DOCX`, or `EPUB`.

### Import Entry Point

The existing `batch_import_documents()` must be extended to dispatch loaders by `format_key` rather than choosing only between `dep` and `txt`.

Suggested logic:

- `dep` -> `load_document_package()`
- `txt` -> `load_text_document()`
- `docx` -> `load_imported_markdown_document(..., importer=docx_importer)`
- `epub` -> `load_imported_markdown_document(..., importer=epub_importer)`
- `pdf` -> `load_imported_markdown_document(..., importer=pdf_importer)`

### UI / Menu

The following must be expanded in sync:

- `Import` submenu formats
- `wx.FileDialog` wildcards
- import error message strings

New import formats:

- `PDF`
- `DOCX`
- `EPUB`

Existing `DEP` and `TXT` behavior remains unchanged.

## Error Handling

### Shared Principles

- When a single file import fails, report the corresponding `path` and `reason` through the existing `BatchIssue`
- Other successfully imported files are unaffected
- Importers must not open UI dialogs; they should only raise displayable exceptions

### `DOCX`

- Cannot open, corrupted format, or cannot convert to HTML -> import failure
- If conversion results in empty content, import may still succeed and produce empty Markdown

### `EPUB`

- Cannot read package, missing spine, or chapter content cannot be parsed -> import failure
- The strategy for chapter-level parse failures should stay conservative: if overall order or semantics would become unreliable, fail the entire import

### `PDF`

- Encrypted or cannot be opened -> import failure
- `/MarkInfo` / `/StructTreeRoot` missing -> go directly to plain-text fallback, not an error
- `/StructTreeRoot` exists but structure cannot be mapped reliably -> go directly to plain-text fallback, not an error
- `PyMuPDF` plain-text extraction fails -> import failure

The key point here is that lack of PDF semantics is not itself a failure condition; it is only the condition that triggers the fallback path.
PDF fallback produces normal `Paragraph` nodes and does not introduce a PDF-specific AST node type.

## Testing Strategy

### AST and Renderer Unit Tests

Verify:

- each AST node serializes correctly into Markdown
- `Table` outputs headers and data rows consistently
- spacing rules between `BlockQuote`, lists, and headings are stable
- `Paragraph` renders consistently both for normal paragraphs and for PDF fallback paragraphs

### Importer Unit Tests

`DOCX`:

- headings map to `Heading`
- lists map to `ListBlock`
- tables map to `Table`
- horizontal rules map to `HorizontalRule`

`EPUB`:

- output follows spine order
- content from adjacent chapters does not collapse together
- headings, lists, block quotes, and tables map correctly

`PDF`:

- tagged fixtures with `/MarkInfo` and `/StructTreeRoot` take the semantic path
- fixtures without semantic structure take the `Paragraph` fallback
- untagged PDFs do not trigger heuristic inference

### Integration Tests

Verify:

- `batch_import_documents()` accepts new `format_key` values
- imported files in the new formats produce `Document(name, text, braille=None)`
- duplicate-name checks continue to use the existing rules
- failed imports continue to report `BatchIssue` in the existing format

## Risks and Trade-offs

- The largest risk in the `PDF` semantic path is the lack of a mature high-level structure-tree API in the open-source Python ecosystem
  - Mitigation: explicitly limit `pypdf` to structure inspection and structure reading, and accept that version 1 supports only a limited set of block-level mappings
- Markdown tables have limited expressive power for complex tables
  - Accept this limitation; merged-cell layouts are not guaranteed to render perfectly
- The HTML structures produced from `DOCX` / `EPUB` may not exactly match the original source styling
  - Accept this limitation because the design goal is semantic readability, not style fidelity
- Writing Markdown back into `.txt` means workspace text is no longer pure prose
  - Accept this limitation because preserving Markdown semantics is itself a requirement

## Implementation Outline

1. Add the block-level AST and Markdown renderer.
2. Add the `DOCX` importer and complete `mammoth HTML -> AST -> Markdown`.
3. Add the `EPUB` importer and complete `ebooklib spine XHTML -> AST -> Markdown`.
4. Add the `PDF` importer and complete:
   - `pypdf` `/MarkInfo` / `/StructTreeRoot` checks
   - tagged structure -> AST
   - `PyMuPDF` plain-text fallback
5. Extend `batch_import_documents()` and related loader dispatch.
6. Extend the document import menu and wildcards.
7. Add importer, renderer, and integration tests.

## Open Questions

There are no unresolved design questions.

The following boundaries were explicitly confirmed before writing the spec:

- Version 1 `DOCX` support is `docx` only
- inline semantics are ignored for now
- `PDF` without semantics extracts plain text only
- `PDF` with semantics converts to block-level Markdown
