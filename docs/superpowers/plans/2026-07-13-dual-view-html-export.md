# Dual-View HTML Export Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add single-document and batch export of the existing dual-view HTML as an `HTML` option beside `DEP` and `BRL`.

**Architecture:** Register HTML as an export-only document format whose writer renders the existing dual-view model to UTF-8. Pass the current document's cached dual-view data through the existing GUI export workflow, preserving conversion and batch result handling. Drive both export submenus from one descriptor list with descriptive localized labels.

**Tech Stack:** Python 3, dataclasses, unittest, pathlib, gettext, existing dual-view HTML renderer.

## Global Constraints

- Menu order and labels: `封裝檔 DEP`, `點字檔 BRL`, `雙視檔 HTML`.
- Actual HTML filenames use the lowercase `.html` suffix.
- Single export and Export All expose the same formats and behavior.
- Follow TDD: each behavior gets a failing test before production code.
- Do not edit generated runtime files by hand.

---

### Task 1: Register and write HTML export format

**Files:**
- Modify: `client/documents/formats.py`
- Modify: `client/documents/workspace.py`
- Test: `client/tests/test_document_formats.py` (create if absent)

**Interfaces:**
- Produce `get_format("html")` with extension `.html`, exportable true, writer present, and `requires_braille` false.
- Produce an HTML writer that accepts `(path, document, dual_view_results=...)` and writes `render_dual_view_html(build_dual_view_model(dual_view_results))` as UTF-8 without changing the persisted `Document` dataclass.

- [ ] **Step 1: Write failing registry and writer tests.** Assert descriptor fields and patch the renderer/model lookup so a temporary path receives the expected complete HTML string.
- [ ] **Step 2: Run `cd client && python3 -m unittest tests.test_document_formats -v`; verify the new tests fail because `html` is unsupported.**
- [ ] **Step 3: Add `HTML_EXTENSION`, a writer that renders the GUI-provided dual-view results (with the existing empty model fallback), and the `html` descriptor.**
- [ ] **Step 4: Re-run the focused tests and verify they pass.**
- [ ] **Step 5: Commit with `feat: add dual-view html export format`.**

### Task 2: Add descriptive submenu labels and HTML dispatch

**Files:**
- Modify: `client/ui/action_menu.py`
- Modify: `client/gui.py`
- Modify: `client/locales/zh_TW/LC_MESSAGES/dotexpress.po`
- Test: `client/tests/test_action_menu.py`
- Test: `client/tests/test_gui_document_flows.py`

**Interfaces:**
- Export descriptors expose labels `Package DEP`, `Braille BRL`, and `Dual View HTML` to gettext while dispatch keys remain `dep`, `brl`, and `html`.
- Both submenu descriptors contain the same three formats in that order.

- [ ] **Step 1: Add failing action-menu tests for the two submenu format labels and export format keys.**
- [ ] **Step 2: Run `cd client && python3 -m unittest tests.test_action_menu -v`; verify the expected old `DEP`/`BRL` assertions fail.**
- [ ] **Step 3: Change the shared menu descriptors to hold format keys plus display labels, update GUI submenu construction/binding, and add translation markers/catalog entries.**
- [ ] **Step 4: Add a failing GUI test proving HTML export uses `.html` and the registry writer, then run the focused GUI test.**
- [ ] **Step 5: Implement descriptor-based wildcard selection and pass `self._dual_view_results_by_document.get(document.name, ())` only to the HTML writer in single and batch export paths.**
- [ ] **Step 6: Run `cd client && python3 -m unittest tests.test_action_menu tests.test_gui_document_flows -v`; verify all focused tests pass.**
- [ ] **Step 7: Commit with `feat: expose dual-view html export in menus`.**

### Task 3: Verify export behavior and documentation

**Files:**
- Modify: `docs/user/zh_TW/shortcuts.md`
- Modify: `docs/user/en/shortcuts.md`
- Test: existing focused tests and client test suite

- [ ] **Step 1: Update shortcut documentation to mention DEP, BRL, and HTML export submenu choices in both languages.**
- [ ] **Step 2: Run focused regression tests:** `cd client && python3 -m unittest tests.test_document_formats tests.test_action_menu tests.test_gui_document_flows tests.test_dual_view_html -v`.
- [ ] **Step 3: Run the full client suite with `cd client && python3 -m unittest discover -s tests -v`; record any platform-specific skips or dependency failures exactly.**
- [ ] **Step 4: Inspect `git diff --check` and `git status --short`, then commit documentation and verified test changes with `docs: document html export option`.**
