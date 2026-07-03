# Dual-View Braille Alignment Review

Review date: 2026-07-01

## Scope

Reviewed against:

- `docs/superpowers/finish_task0.md`
- `docs/superpowers/specs/2026-07-01-dual-view-braille-alignment-design.md`
- `docs/superpowers/plans/2026-07-01-dual-view-braille-alignment.md`

Commits were reviewed in chronological order, limited to those listed in the completion report:

1. `eb9f7f6` - `feat: preserve translation alignment segments`
2. `90bb02a` - `feat: build dual view alignment model`
3. `7cac2c5` - `feat: add dual view viewer integration`

The main agent performed each review pass. Confirmed defects were assigned to a GPT-5.4 repair subagent using regression-test-first fixes, then independently reviewed and verified by the main agent.

## Commit Review

### `eb9f7f6`

The conversion service correctly introduced a rich `ConversionOutput`, preserved translation segment boundaries, retained the existing string callback API, and kept wrapped output generation separate from the viewer model.

One important defect was found: `merge_translation_results()` returned the original object when only one segment existed. `_wrap_translation_results()` then mutated that object through `reclean_braille_endspace()`, `bind_word_tokens()`, and `reclean_token()`. The viewer therefore received token-bound data for the common single-segment case instead of the required pre-bind character alignment.

The GPT-5.4 repair subagent added a mutation-capable regression test. The test failed before the fix with `['word'] != ['w', 'o', 'r', 'd']`. The merge operation now starts from a fresh empty `TranslationResult`, so wrapping mutates only the merged copy. The main agent reviewed the offset behavior and reran the complete focused suite.

### `90bb02a`

The alignment model preserves document segment boundaries, produces source-character-centric items, supports zero/one/multiple braille cells, and handles spaces, newlines, and atomic multi-character tokens. The HTML renderer escapes visible content and metadata, uses document/segment/cell structure, and provides localized empty-state and segment labels.

No additional defect was found in this commit after the conversion mutation fix.

### `7cac2c5`

The integration adds `File > Dual View`, owns one modeless child frame, reuses and raises an existing viewer, avoids `wx.STAY_ON_TOP`, refreshes on open/manual-conversion/document-switch only, and raises a visible non-minimized viewer when the main frame becomes active. Export conversion does not replace manual-conversion alignment data. Rename, delete, close, gettext, and WebView lifecycle behavior are covered.

One cache-lifecycle defect was found in the partial-failure path of `Delete All`: after one document was deleted and a later unlink failed, stale alignment entries for deleted documents remained. Recreating a document with the same name could then show old alignment data.

The GPT-5.4 repair subagent added a regression test that failed with stale `alpha` and `ghost` cache entries. The fallback now retains cache entries only for documents reloaded from disk and refreshes an open viewer after restoring document state. The main agent reviewed the patch and reran the focused suite.

## Final Assessment

After two repair/re-review cycles, the main-agent review found no remaining Critical, Important, or Minor findings within the reviewed feature scope. The implementation matches the approved spec and plan based on code inspection and automated coverage.

The repair changes are currently uncommitted in:

- `client/conversion/service.py`
- `client/gui.py`
- `client/tests/test_conversion_service.py`
- `client/tests/test_gui_document_flows.py`

## Verification

Passed:

```bash
cd client
python3 -m unittest \
  tests.test_conversion_service \
  tests.test_dual_view_model \
  tests.test_dual_view_html \
  tests.test_action_menu \
  tests.test_dual_view_frame \
  tests.test_gui_document_flows -v
```

Result: `Ran 58 tests`, `OK`.

Also passed:

```bash
cd client
python3 -m compileall -q \
  conversion/service.py dual_view ui/dual_view.py gui.py \
  tests/test_conversion_service.py tests/test_dual_view_model.py \
  tests/test_dual_view_html.py tests/test_action_menu.py \
  tests/test_dual_view_frame.py tests/test_gui_document_flows.py

python3 -c 'import gettext; gettext.GNUTranslations(open("client/locales/zh_TW/LC_MESSAGES/dotexpress.mo", "rb"))'
git diff --check
```

The full client discovery command was also attempted. It ran 163 tests but ended with 12 errors and 8 skips because this environment does not have all packages from `client/requirements.txt`, including `mammoth` and `lxml`; later importer tests also encountered the GUI test's fallback dependency stubs. These failures are outside the reviewed dual-view changes. Windows-only liblouis tests were skipped as expected.

A real Windows wxPython smoke test was not available in this environment. Window ownership, foreground ordering, and the platform WebView backend still require the manual Windows checks listed in Task 8 of the implementation plan.
