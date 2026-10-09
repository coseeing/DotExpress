# Windows Tooling Hygiene and Locale Regeneration (W-3) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** `generate-pot.bat` writes client-relative forward-slash references in sorted order; Windows build/run leftovers are ignored; the readmes name the right script; the `.pot`, zh_TW `.po` and `.mo` are regenerated (checklist item 8) with no untranslated entry.

**Architecture:** Red tests first (`scripts/tests/test_generate_pot.py`), then one commit per concern: bat, ignore rules, readme names, `Close` translation, catalog regeneration (with the new tests, which turn green there), stale catalog tests (spec D7). Then verification, results, merge.

**Spec:** `docs/superpowers/specs/2026-10-09-w3-windows-tooling-locale-design.md`.

## Global Constraints

- Branch `fix/w3-windows-tooling-locale` from `main` (`4b4a2b6`). Merge with `git merge --no-ff`; never push, never delete the branch, never rewrite history.
- Never touch `client2/`, `preprocessing/`, `client/dictionary/`, `client/.venv`; do not delete `.sconsign.dblite`, `client/config.json` or `vendor/nvda/liblouis/dist/`.
- `core.autocrlf=true`: edit with the Edit tool (or `unix2dos` after a full rewrite), not MSYS `sed -i`.
- Gettext tools: `C:\Program Files\gettext-iconv\bin` (0.23), on `PATH`.
- Every commit message ends with a blank line, then `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- Commands (Git Bash):
  ```bash
  REPO=/d/workspace/DotExpress
  PY=$REPO/client/.venv/Scripts/python.exe
  export PYTHONIOENCODING=utf-8
  ```

### Task 1: Tests (red, no commit)

- [x] Add `scripts/tests/test_generate_pot.py` (spec D3).
- [x] `$PY -m unittest scripts.tests.test_generate_pot` from `$REPO`: red (four orphan msgids; stale line numbers such as `gui.py:1328` in a 1101-line file; the bat ignores the output argument and writes `#: D:\workspace\DotExpress\client\about.py:10` into `client/locales/dotexpress.pot`, restored with `git restore`).

### Task 2: `generate-pot.bat` (spec D1, D2)

- [x] Rewrite the bat: relative paths, `\` to `/`, `findstr /v /i /b /l` exclusions, `sort.exe /l C`, `--from-code=UTF-8`, optional output, exit code. Keep the `xgettext --language=Python --keyword=_ --keyword=N_ --files-from=` prefix (`client/tests/test_i18n.py` asserts it). CRLF line ends.
- [x] Run it into a scratch file twice: identical apart from the date; 353 msgids; no `tests/`, generated-helper or backslash references; a bad output path returns 1; no temp files left.
- [x] Commit `fix: generate POT with client-relative references (W-3)`.

### Task 3: Ignore rules (spec D4)

- [x] Root `.gitignore`: `/.sconsign.dblite`, `/vendor/nvda/liblouis/dist/`. `client/.gitignore`: `/config.json`. Extend `test_liblouis_build_contract.py`.
- [x] Commit `chore: ignore scons outputs and runtime config (W-3)`.

### Task 4: Readme names

- [x] `generate_pot.bat` to `generate-pot.bat` in `readme.md`, `docs/user/en/readme.md`, `docs/user/zh_TW/readme.md`. Every other `scripts\*.bat|py` named in tracked non-history docs exists.
- [x] Commit `docs: fix generate-pot.bat name in readmes (W-3)`.

### Task 5: `Close` translation (spec D6)

- [x] `msgstr "關閉"` for `Close`; rebuild the `.mo` (`msgfmt` 0.23 rebuilds the committed `.po` into a byte-identical committed `.mo`, so the toolchain matches).
- [x] Commit `fix: restore zh_TW translation for Close (W-3)`.

### Task 6: Regenerate catalogs (spec D5, checklist item 8)

- [x] `cmd //c scripts\\generate-pot.bat`; in `client/`: `msgmerge --update --backup=none locales/zh_TW/LC_MESSAGES/dotexpress.po locales/dotexpress.pot`; `msgfmt --check --statistics -o locales/zh_TW/LC_MESSAGES/dotexpress.mo locales/zh_TW/LC_MESSAGES/dotexpress.po`; `unix2dos` the `.pot`/`.po` working copies.
- [x] The four orphans are `#~`; no fuzzy or untranslated entry; msgstr and flags unchanged per msgid; no rewrapping. New tests green.
- [x] Commit `chore: regenerate POT, zh_TW catalog and MO (W-3)` (with `scripts/tests/test_generate_pot.py`).

### Task 7: Stale catalog tests (spec D7)

- [x] `test_config` drops the four orphan assertions; `test_import_fixtures` checks `build_import_wildcard(translation.gettext)`.
- [x] Commit `test: stop pinning obsolete import-filter msgids in the catalog (W-3)`.

### Task 8: Verification, results, merge

- [x] `.mo` load check; `scripts/tests` and `client` `discover`; fixture sha256; `git status --short`.
- [x] Record results below, commit `docs: record W-3 verification results`, then:

```bash
git -C $REPO switch main
git -C $REPO merge --no-ff fix/w3-windows-tooling-locale \
  -m "merge: Windows tooling hygiene and locale regeneration (W-3)" \
  -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

## Results

2026-10-09, Windows 11, `client\.venv` Python 3.13, GNU gettext 0.23. Commits `497dd66` (bat), `8c79d3e` (ignores), `f7b67d0` (readmes), `411261a` (`Close`), `21b8cae` (regeneration + tests), `c5b716d` (stale catalog tests).

### generate-pot.bat

- References: `#: about.py:10`, `#: braille/tables/__tables.py:36`, `#: settings/options.py:71` (`Unicode`), `#: settings/options.py:75` (`Light`); no absolute, backslash, `tests/` or generated-helper reference. 353 msgids (354 `msgid` lines with the header). Two runs differ only in `POT-Creation-Date` (now local time, `+0800`; the old file had `+0000`).
- The generated `client\braille\louis_helper.py` and `client\braille\liblouis\__init__.py` are scanned but contain no marked strings, so the output equals a clean checkout.

### Catalog diff (`main`..branch, `client/locales`)

- `.pot`: 287 insertions, 301 deletions. 357 to 353 msgids (the four orphans removed). Of the 353: 155 reference changes (81 to other files, 74 line-only), 198 unchanged; no msgid or flag change. Entry order now follows the sorted file list.
- `.po`: 360 insertions, 362 deletions (including `Close`). Active 357 to 353; obsolete 27 to 31 (exactly the four orphans added, with their old translations; the 27 earlier `#~` unchanged). msgstr and flags unchanged for every active msgid except `Close` (`""` to `關閉`, Task 5). With references and the `#~` prefix stripped, every entry's text is identical (no rewrapping). `.po` order equals `.pot` order.
- `msgfmt --check --statistics`: before `356 translated messages, 1 untranslated message.`; after `353 translated messages.`; `msgattrib --only-fuzzy --no-obsolete`: none.
- `.mo` (26829 to 26579 bytes): `gettext.GNUTranslations` loads it, 354 catalog keys (353 + header); `Light` 淺色, `Dark` 深色, `Default Translation Table` 預設轉譯表, `Close` 關閉, `General` 一般, `Startup Error` 啟動錯誤; `Text files (*.txt)|*.txt` returns itself (obsolete).

### Tests

- `scripts/tests` (`$PY -m unittest discover -s scripts/tests` from `$REPO`): `Ran 33`, `FAILED (failures=1)`. The five `test_generate_pot` tests and the new gitignore test pass. The failure is pre-existing and Windows-only: `test_vendor_helper_snapshot` compares the CRLF working copy of `vendor/nvda/liblouis/runtime/louis_helper.py` (`core.autocrlf=true`) with the LF NVDA source (`eol=lf`); the two are equal after CRLF to LF. W-3 touches neither file.
- `client` (`$PY -m unittest discover -s tests`): `Ran 1143`, `FAILED (failures=1, errors=1, skipped=5)`: FAIL `test_conversion_service...test_translate_with_language_does_not_duplicate_existing_spaces_around_math` (P2-5), ERROR `test_dictionary_name_prompt...test_case_only_rename_still_renames` (case-insensitive file system). Before Task 7 the regeneration also failed `test_config...test_zh_tw_catalog_keeps_runtime_wildcard_translations_active` and `test_import_fixtures...test_zh_tw_catalog_loads_import_wildcard_translations` (spec D7).
- Fixture sha256: `translation_golden.json` `e67d95a1...211ccd`, `dictionary_entries_trace.json` `f493da52...c66c2cf` (unchanged).
- `git check-ignore -v`: `.gitignore:17:/.sconsign.dblite`, `.gitignore:18:/vendor/nvda/liblouis/dist/`, `client/.gitignore:7:/config.json`. `git status --short` lists only `client2/` and `preprocessing/`.
