# Speech Symbols Dialog Filter Review

## Review Scope

- Reviewer: main agent (GPT-5.5)
- Fix worker: sub-agent (GPT-5.4)
- Completion summary: `docs/superpowers/finish_task0.md`
- Design specification: `docs/superpowers/specs/2026-07-03-speech-symbols-dialog-filter-design.md`
- Implementation plan: `docs/superpowers/plans/2026-07-03-speech-symbols-dialog-filter-implementation-plan.md`
- Reviewed commit range: `963f348^..a022af0`

The commits were reviewed in author-date order, from oldest to newest. Only the commits listed in `finish_task0.md` were included.

## Commit-by-Commit Review

### 1. `963f348` — `feat: add virtual dictionary entry filtering`

Reviewed changes:

- Added `DictionaryEntryListCtrl` and `OnGetItemText`.
- Added `self.filtered_entries` while retaining `self.entries` as the complete source of truth.
- Added the immediate filter input and `wx.EVT_TEXT` binding.
- Changed the list style to include `wx.LC_VIRTUAL`.
- Added case-insensitive filtering of `Source Text` and `Braille`.
- Added visible-entry selection and button-state helpers.
- Added initial filtering tests.

Assessment:

- The implementation matches the virtual-list and filtering architecture in the specification.
- `Type` remains display-only and is not included in matching.
- No product-code defect was found in this commit.

### 2. `f5a2571` — `fix: preserve filtered dictionary selection`

Reviewed changes:

- Added tests for preserving a visible selection.
- Added tests for falling back to the first visible row.
- Added tests for empty-result button states.
- Added coverage for the immediate filter event.

Assessment:

- Selection preservation and empty-result behavior match the specification.
- `Edit` and `Delete` are disabled without an informational or warning dialog.
- No product-code defect was found in this commit.

### 3. `49ccb3c` — `feat: support filtered dictionary editing`

Reviewed changes:

- Removed the old physical list repopulation path.
- Updated add behavior to retain or clear the filter depending on whether the new entry matches.
- Updated edit and delete to resolve the selected visible entry back to `self.entries`.
- Changed duplicate exclusion from a visible index to the selected entry object.
- Added filtered add, edit, and delete tests.

Assessment:

- Add, edit, and delete behavior matches the specification.
- Save state remains based on `self.entries`.
- No product-code defect was found in this commit.

### 4. `55e8f1b` — `test: cover filtered dictionary persistence`

Reviewed changes:

- Added coverage proving `_save_entries()` writes all entries rather than only visible entries.
- Added duplicate-source validation coverage where the conflicting entry is outside the current filter.

Assessment:

- The persistence and validation tests cover the required regression behavior.
- One test-infrastructure defect was found when this file was evaluated as part of the full discovery sequence. The finding and repair rounds are recorded below.

### 5. `a022af0` — `feat: translate dictionary filter control`

Reviewed changes:

- Added the `Filter by:` translation as `篩選條件：`.
- Regenerated `dotexpress.mo`.

Assessment:

- The PO entry is valid.
- The compiled MO catalog resolves `Filter by:` to `篩選條件：`.
- No localization defect was found in this commit.

## Findings and Repair Rounds

### Round 1 — Important: new tests polluted global import state

Original location:

- `client/tests/test_speech_symbols_dialog.py`

Finding:

- The test module imported `dialog` through normal `sys.modules` resolution. If an earlier test had installed a `dialog` stub, the new tests imported that stub instead of `client/dialog.py`.
- The test module permanently installed fake `wx`, `mammoth`, `pymupdf`, `bs4`, `pypdf`, `markdown`, `markdownify`, `PIL`, `lxml`, and `ebooklib` modules. Later importer tests could therefore run against fake dependencies.
- The original 44-test success in this environment depended on this leakage: the fake `mammoth` allowed `test_dialog_validation` to import. After proper cleanup, that test correctly exposes the environment's missing dependency.

Impact:

- Test results depended on discovery order.
- The full-suite result was unreliable and could hide failures in unrelated importer tests.

Repair:

- A GPT-5.4 sub-agent replaced the normal `dialog` import with a private file-based module loader.
- Dependency stubs are now scoped to the private load.
- All affected `sys.modules` bindings are restored afterward.
- Duplicate-message testing now patches the private dialog module's `wx.MessageBox`.
- An isolation regression test was added.

Main-agent re-review:

- The first repair still used `addCleanup(sys.modules.pop, "dialog")`, which deleted a pre-existing `dialog` binding instead of restoring it.
- The private loader also used `setdefault` for `wx`, making tests use real wxPython when it was already imported.
- The patch was returned to the same GPT-5.4 sub-agent.

### Round 2 — Important: cleanup and wx behavior were still environment-dependent

Repair:

- Cleanup now records whether `dialog` and `wx` existed and restores their exact previous objects.
- The private loader always uses a controlled wx stub while loading the module under test.
- A pre-existing real or stub wx module is restored after loading.
- The isolation test verifies both restoration and that the private dialog did not use the sentinel wx module.

Main-agent re-review:

- The actual patch was inspected, not accepted from the sub-agent report alone.
- No further correctness, isolation, or specification findings were found.

## Final Specification Assessment

The reviewed product implementation satisfies the design requirements:

- Immediate filtering is bound to text changes.
- Matching is case-insensitive.
- Matching checks only `Source Text` and `Braille`.
- The report list uses `wx.LC_VIRTUAL` and retrieves visible cell text on demand.
- Existing selection is retained when its entry remains visible.
- Selection falls back when an entry becomes hidden or is deleted.
- Empty results clear selection and disable `Edit` and `Delete` without a prompt.
- Adding a matching entry retains the filter and selects the new entry.
- Adding a non-matching entry clears the filter and selects the new entry.
- Editing and deleting operate on visible entries while updating the complete collection.
- Saving writes `self.entries`, including entries hidden by the active filter.
- The Taiwan Traditional Chinese translation is present in both PO and MO catalogs.

Final review result: no remaining blocking or important findings in the reviewed feature.

## Verification Evidence

### Passed

Command:

```bash
cd client && python3 -m unittest tests.test_speech_symbols_dialog -v
```

Result:

- 18 tests passed.
- This includes the original 17 behavior tests and the new import-isolation regression test.

Command:

```bash
cd client && python3 -m unittest \
  tests.test_speech_symbols_dialog \
  tests.test_dictionary_actions \
  tests.test_dictionary_manager \
  tests.test_dictionary_import_flow -v
```

Result:

- 37 tests passed.

Additional checks:

- A reproduction with pre-populated `sys.modules["dialog"]` and `sys.modules["wx"]` passed.
- The reproduction confirmed that both sentinel modules were preserved and no fake third-party modules leaked.
- `python3 -m py_compile dialog.py tests/test_speech_symbols_dialog.py` passed.
- `git diff --check 963f348^..a022af0` passed.
- The compiled gettext catalog returned `篩選條件：` for `Filter by:`.

### Environment-Limited

Command:

```bash
cd client && python3 -m unittest discover -s tests -v
```

Result:

- Full discovery is not green in the current Linux environment.
- Remaining failures are outside this feature and include missing `mammoth` and `lxml` dependencies plus pre-existing test-module stubs from other test files.
- After the repair, `test_speech_symbols_dialog` itself passes under discovery instead of importing another test's `dialog` stub.

Command:

```bash
cd client && python3 -m unittest \
  tests.test_speech_symbols_dialog \
  tests.test_dialog_validation \
  tests.test_dictionary_actions \
  tests.test_dictionary_manager \
  tests.test_dictionary_import_flow -v
```

Result:

- The feature tests pass.
- `test_dialog_validation` cannot import because `mammoth` is not installed in this environment.
- This failure was previously masked by the leaked fake module and is not caused by the product implementation.

Manual wxPython desktop verification was not available in this headless Linux environment.

## Files Changed During Review

- `client/tests/test_speech_symbols_dialog.py`
  - Isolated private loading of `client/dialog.py`.
  - Restored all scoped module bindings.
  - Added one import-isolation regression test.
- `docs/superpowers/review_task1.md`
  - Recorded review scope, commit results, repair rounds, and verification evidence.

No unrelated worktree changes were modified.
