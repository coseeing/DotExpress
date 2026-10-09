# Windows Tooling Hygiene and Locale Regeneration (W-3) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `generate-pot.bat` writes client-relative forward-slash references in sorted order; Windows build/run leftovers are ignored; the readmes name the right script; the `.pot`, zh_TW `.po` and `.mo` are regenerated (checklist item 8) with no untranslated entry.

**Architecture:** Tests first (`scripts/tests/test_generate_pot.py`), then one commit per concern: bat, ignore rules, readme names, catalog regeneration, `Close` translation. Then verification, results, merge.

**Spec:** `docs/superpowers/specs/2026-10-09-w3-windows-tooling-locale-design.md`.

## Global Constraints

- Branch `fix/w3-windows-tooling-locale` from `main` (`4b4a2b6`). Merge with `git merge --no-ff`; never push, never delete the branch, never rewrite history.
- Never touch `client2/`, `preprocessing/`, `client/dictionary/`, `client/.venv`; do not delete `.sconsign.dblite`, `client/config.json` or `vendor/nvda/liblouis/dist/`.
- `core.autocrlf=true`: edit with the Edit tool (or `unix2dos` after a full rewrite of a `.bat`), not MSYS `sed -i`.
- Gettext tools: `C:\Program Files\gettext-iconv\bin` (0.23), on `PATH`.
- Every commit message ends with a blank line, then `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- Commands (Git Bash):
  ```bash
  REPO=/d/workspace/DotExpress
  PY=$REPO/client/.venv/Scripts/python.exe
  export PYTHONIOENCODING=utf-8
  ```

### Task 1: Tests (red)

- [ ] Add `scripts/tests/test_generate_pot.py` (spec D3).
- [ ] `$PY -m unittest scripts.tests.test_generate_pot` from `$REPO`: red. Expected: four orphan msgids; stale line numbers; `Close` empty; the bat test fails (old bat ignores the output argument and writes absolute references into `client/locales/dotexpress.pot`, which is restored with `git restore` afterwards).

### Task 2: `generate-pot.bat` (spec D1, D2)

- [ ] Rewrite the bat: relative paths, `\` to `/`, `findstr /v /i /b /l` exclusions, `sort.exe /l C`, `--from-code=UTF-8`, optional output, exit code. Keep the `xgettext --language=Python --keyword=_ --keyword=N_ --files-from=` prefix (`client/tests/test_i18n.py` asserts it). CRLF line ends.
- [ ] Run it into a scratch file: references relative, 353 msgids, no `tests/` or generated-helper references; twice gives the same output except the date.
- [ ] Commit `fix: generate POT with client-relative references (W-3)` (bat + new test file).

### Task 3: Ignore rules (spec D4)

- [ ] Root `.gitignore`: `/.sconsign.dblite`, `/vendor/nvda/liblouis/dist/`. `client/.gitignore`: `/config.json`. Extend `test_liblouis_build_contract.py`.
- [ ] `git status --short` no longer lists the three items; `git check-ignore -v` names the rules.
- [ ] Commit `chore: ignore scons outputs and runtime config (W-3)`.

### Task 4: Readme names

- [ ] `generate_pot.bat` to `generate-pot.bat` in `readme.md`, `docs/user/en/readme.md`, `docs/user/zh_TW/readme.md`.
- [ ] Commit `docs: fix generate-pot.bat name in readmes (W-3)`.

### Task 5: Regenerate catalogs (spec D5, checklist item 8)

- [ ] `cmd //c scripts\\generate-pot.bat`; `cd client && msgmerge --update --backup=none locales/zh_TW/LC_MESSAGES/dotexpress.po locales/dotexpress.pot`; `msgfmt --check --statistics -o locales/zh_TW/LC_MESSAGES/dotexpress.mo locales/zh_TW/LC_MESSAGES/dotexpress.po`.
- [ ] Check: the four orphans are `#~`; no new fuzzy or untranslated entries; translations unchanged per msgid; record diff summary.
- [ ] Commit `chore: regenerate POT, zh_TW catalog and MO (W-3)`.

### Task 6: `Close` translation (spec D6)

- [ ] `msgstr "關閉"` for `Close`; rebuild the `.mo`; `msgfmt --statistics` shows 353 translated.
- [ ] Commit `fix: restore zh_TW translation for Close (W-3)`.

### Task 7: Verification, results, merge

- [ ] `.mo` load check with `gettext.GNUTranslations` (count, `Close`, `Light`, `Unicode`, `General`).
- [ ] `$PY -m unittest discover -s scripts/tests` from `$REPO`: all OK.
- [ ] From `client/`: `$PY -m unittest discover -s tests`: `Ran 1143`, `FAILED (failures=1, errors=1, skipped=5)`.
- [ ] Fixture sha256; `git status --short`.
- [ ] Record results below, commit `docs: record W-3 verification results`, then:

```bash
git -C $REPO switch main
git -C $REPO merge --no-ff fix/w3-windows-tooling-locale \
  -m "merge: Windows tooling hygiene and locale regeneration (W-3)" \
  -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

## Results

(Filled in after Task 7.)
