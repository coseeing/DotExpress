# Text Processing — Implementation Review

Date: 2026-07-14

## Final assessment

**Approved.** The implementation conforms to the text-processing design specification
and implementation plan. No reproducible bug, regression, or unmet specification
requirement was found, so the conditional repair sub-agent loop was not started.

This review was performed by the main agent as a professional code review using the
Superpowers requesting-code-review and verification-before-completion workflows. The
runtime did not expose a control for selecting the requested named model variants, so
the review does not claim that model routing was applied.

## Review scope

The review used these documents as the source of truth:

- `docs/superpowers/finish_task.md`
- `docs/superpowers/specs/2026-07-14-text-processing-design.md`
- `docs/superpowers/plans/2026-07-14-text-processing.md`

Only the commits explicitly listed in `finish_task.md` were reviewed. Their commit
timestamps already place them in this oldest-to-newest order:

1. `8d76d76` — docs: add text processing design and plan
2. `bd2b10f` — feat: add user preprocessing script engine
3. `991dcaf` — feat: run user script before translation
4. `f762321` — refactor: remove nonstandard punctuation preprocessing
5. `518bb88` — refactor: keep one conversion output path
6. `7969f28` — feat: add text processing dialog
7. `bf9a27c` — feat: expose text processing settings
8. `525bd1d` — docs: record text processing verification
9. `495d96f` — fix: restore dictionary label translations

The later verification-note commit mentioned but not identified in the numbered list
was intentionally excluded from the commit-by-commit scope.

## Commit-by-commit findings

### `8d76d76` — design and plan

The English specification and implementation plan consistently capture the agreed
behavior: one unrestricted global `preprocessing.py`, execution on the conversion
worker thread, no timeout, processed text as the dual-view source, one positional
`main` parameter with any parameter name, helper functions/imports permitted, and no
configuration JSON field. The plan also preserves literal Unicode-braille dictionary
output while removing the nonstandard punctuation pipeline and redundant output API.

Finding: no issue.

### `bd2b10f` — script engine

The implementation provides the identity default without creating a missing file,
UTF-8 persistence, same-directory atomic replacement, AST/compile validation without
executing module code during save, exactly one top-level synchronous `main`, exactly
one positional parameter, a fresh unrestricted namespace per execution, helper/import
support, and a required string return value. Tests cover invalid external edits,
non-callable `main`, non-string returns, and failed-save preservation.

Finding: no issue.

### `991dcaf` — shared conversion integration

The script runs before Bopomofo mapping and translation. Empty input bypasses the
script. Script read, compile, contract, and execution failures are classified as
`text_processing`; `SystemExit`/`KeyboardInterrupt`-class failures are normalized so
the worker can report them. The processed source feeds both translation and dual-view
alignment, and all conversion requests continue through the existing background job
runner.

Finding: no issue.

### `f762321` — punctuation removal

The nonstandard punctuation module and test are removed, and punctuation now follows
normal translation. The literal-braille module retains the Unicode-braille dictionary
replacement helpers, with a regression test confirming that direct braille output
still bypasses normal text translation.

Finding: no issue.

### `518bb88` — one output path

`convert_text_for_output`, `translate_and_wrap_both`, and their supporting aliases are
removed. Production and demonstration callers use `convert_text_with_alignment()` and
consume `display_text`, leaving one source-preprocessing/output path.

Finding: no issue.

### `7969f28` — editor dialog

The modeless singleton dialog is titled “Text Processing”, uses the specified
720 × 440 initial size and 520 × 300 minimum size, provides a named monospaced
multiline editor, and implements OK, Cancel, and Apply behavior. Validation/save
failure keeps the dialog open and restores focus to the editor. Destroyed singleton
instances are recovered without hiding unrelated runtime failures.

Finding: no issue.

### `bf9a27c` — menu and localization

The Translation menu order is Convert, Dual View, Text Processing, Dictionary
Management, Settings. The handler opens the one global script next to the dictionary
files and reports read failures. New UI, validation, save, and conversion messages are
present in POT, PO, and compiled MO resources.

Finding: no issue in the final reviewed state. The catalog regression introduced by
POT regeneration is addressed by the later listed fix commit.

### `525bd1d` — verification record

The finish record identifies the implementation commits, reports focused and complete
test results, and explicitly avoids claiming Windows manual acceptance in a Linux
environment.

Finding: no issue.

### `495d96f` — translation regression fix

The gettext extraction input now includes dictionary entry labels, the Traditional
Chinese catalog and compiled MO restore `General`, `Bopomofo`, and `Unicode Braille`,
and tests protect those translations. The accompanying GUI/settings test adjustments
exercise the intended integration points.

Finding: no issue.

## Cross-cutting specification checks

- The single script is `preprocessing.py` beside the dictionary CSV files; no script
  source or timeout setting was added to `config.json`.
- Script execution remains unrestricted and synchronous inside the existing conversion
  worker thread; no foreground UI execution or timeout mechanism was introduced.
- Main-window conversion, single export requiring conversion, and batch export requiring
  conversion all enter the same conversion pipeline. Cached braille exports do not
  retranslate.
- Dual view uses processed source text, avoiding invalid alignment claims after arbitrary
  regex or structural edits.
- Text-processing failures remain distinct from translation and ASCII-output failures.
- Removed punctuation/output symbols have no remaining Python references, and the deleted
  punctuation files remain absent.

## Fresh verification evidence

Run from `client/`:

```text
.venv/bin/python -m unittest \
  tests.test_user_preprocessing_script \
  tests.test_conversion_text_pipeline \
  tests.test_conversion_text_dictionary_rules \
  tests.test_conversion_service \
  tests.test_conversion_jobs \
  tests.test_main_demo \
  tests.test_settings_dialogs \
  tests.test_translation_menu \
  tests.test_gui_document_flows \
  tests.test_input_shortcuts \
  tests.test_section_navigation -v

Ran 117 tests — OK
```

```text
.venv/bin/python -m unittest discover -s tests -v

Ran 382 tests — OK (skipped=7)
```

Additional checks run from the repository root:

```text
msgfmt --check --output-file=/tmp/dotexpress-review.mo \
  client/locales/zh_TW/LC_MESSAGES/dotexpress.po
python3 -m compileall -q \
  client/conversion client/settings client/ui client/gui.py client/main.py
rg -n "convert_text_for_output|translate_and_wrap_both|WrapBoth|ConvertWithAlignment|preprocess_punctuation|tokenize_punctuation" \
  client --glob '*.py'
test ! -e client/conversion/preprocessing/punctuation.py
test ! -e client/tests/test_punctuation.py
git diff --check
```

All checks passed; the removed-symbol search returned no matches.

The compiled Traditional Chinese catalog was also loaded with `gettext.GNUTranslations`
and directly checked for all seven text-processing messages plus `General`, `Bopomofo`,
and `Unicode Braille`; every lookup returned the expected translation.

## Remaining validation limitation

Windows manual UI acceptance was not performed because this review environment is
Linux. Therefore native wxPython focus/sizing behavior, packaged-client menu display,
and real liblouis conversion should still receive the Windows smoke test already
identified in the implementation plan. This is an unexecuted platform acceptance step,
not a discovered code defect.
