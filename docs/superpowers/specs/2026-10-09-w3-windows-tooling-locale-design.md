# Windows Tooling Hygiene and Locale Regeneration (W-3) Design

## Goal

Task W-3 makes `scripts\generate-pot.bat` produce the same template on every Windows checkout, ignores the build and runtime files a Windows build/run leaves untracked, fixes the stale `generate_pot.bat` name in the readmes, and then performs Windows verification checklist item 8 (`docs/superpowers/history/2026-10-08-03-refactor-p2/review_task.md`): regenerate `dotexpress.pot`, `msgmerge` the zh_TW catalog and rebuild `dotexpress.mo`.

No Python production code changes. The msgid set the application uses does not change.

## Current State (verified 2026-10-09 on Windows 11, `main` at `4b4a2b6`)

- **A. `generate-pot.bat`** lists sources with `for /r %%f in (*.py)`, which yields absolute paths. xgettext copies them into the references, so a run writes `#: D:\workspace\DotExpress\client\about.py:10`, while the committed `client/locales/dotexpress.pot` uses `#: about.py:22`. File order is the directory walk order. `--from-code` is not passed. The exclusion `\tests\` is matched against the absolute path, so a checkout below any directory named `tests` would extract nothing. `client\braille\louis_helper.py` and `client\braille\liblouis\__init__.py` exist on disk after `install.bat` (git-ignored, generated) but contain no `_()`/`N_()`/`gettext` calls, so they add no msgids or references.
- **B. Untracked after a Windows build/run:** `vendor/nvda/liblouis/dist/` (scons output, removed by `scripts\clean-liblouis.bat`), `/.sconsign.dblite` (scons database at the repo root) and `client/config.json` (user settings written next to the app root by `client/app_paths.py`; `git log --all -- client/config.json` is empty, so it was never tracked).
- **C. Stale name:** `readme.md:175`, `docs/user/en/readme.md:175` and `docs/user/zh_TW/readme.md:177` say `scripts\generate_pot.bat`; the file is `scripts\generate-pot.bat`. Older plans under `docs/superpowers/plans/` keep the name as history. Root `AGENTS.md` (also named in the checklist) is git-ignored and is not edited here.
- **D. Catalogs:** the committed `.pot` (2026-07-20) has 357 msgids; the sources mark 353. The four extra are orphans left by P1-2: `EPUB books (*.epub)|*.epub`, `PDF files (*.pdf)|*.pdf`, `Text files (*.txt)|*.txt`, `Word documents (*.docx)|*.docx`. 155 entries have stale references (P0-6, P1-2, P1-4 and P2-3 moved code; 81 of them to other files, for example option labels to `settings/options.py`). `msgfmt --statistics` on the `.po`: 356 translated, 1 untranslated (`Close`, `dialog.py`). `Close` was translated `關閉` in `38ae85f` and lost in `b584278`; the dialog Close button therefore shows English in zh_TW (listed in the review backlog, row 4).

## Decisions

- **D1. Relative, sorted, UTF-8 extraction.** The bat strips the `client\` prefix from each path, turns `\` into `/`, drops paths starting with `.venv/`, `tests/`, `build/` or `dist/` (relative to `client\`, so the checkout location no longer matters), sorts the list with `%SystemRoot%\System32\sort.exe /l C` (locale independent; the full path avoids Git for Windows' `sort`) and runs `xgettext --language=Python --keyword=_ --keyword=N_ --files-from=... --from-code=UTF-8`. The generated helper files are not excluded: they contribute nothing, so the output already matches a clean checkout.
- **D2. Optional output path.** `generate-pot.bat [output.pot]` defaults to `locales\dotexpress.pot`; the argument lets a test generate into a temporary file. The script returns xgettext's exit code.
- **D3. Regression tests in `scripts/tests/test_generate_pot.py`** (stdlib only, with a minimal PO reader):
  1. every `.pot` reference is `client`-relative, forward-slash `path.py:N`, names an existing file and a line inside it;
  2. the `.pot` msgid set equals the `_()`/`N_()` string literals in `client/` (the same walk as `test_i18n`'s marker test), which catches orphans and missing msgids;
  3. the zh_TW `.po` active msgids equal the `.pot` msgids in the same order, and none is fuzzy or empty;
  4. Windows with xgettext on `PATH` only: running the bat into a temporary file yields the committed `.pot` entries (msgid, references, flags, order).
  Tests 1 to 3 run on every platform.
- **D4. Ignore rules where the files live.** Root `.gitignore`: `/.sconsign.dblite` and `/vendor/nvda/liblouis/dist/`. `client/.gitignore`: `/config.json` (anchored, so no other `config.json` under `client/` is hidden). `test_liblouis_build_contract.py` gets the new rules in its ignore assertions.
- **D5. Regenerate with default wrapping.** The committed `.pot`/`.po` use gettext's default 79-column wrapping, so `msgmerge` runs without `--no-wrap`. Command: `msgmerge --update --backup=none locales\zh_TW\LC_MESSAGES\dotexpress.po locales\dotexpress.pot`, then `msgfmt --check -o ...dotexpress.mo ...dotexpress.po`. The four orphans become `#~` entries. Entry order follows the new `.pot` (sorted files), so the diff also reorders entries; msgids and translations do not change.
- **D6. Restore `Close` → `關閉`** (the translation from `38ae85f`), in its own commit, so the catalog has no untranslated entry (AGENTS.md localization rule). No other translation changes.

## Acceptance Criteria

1. `scripts\generate-pot.bat` writes references such as `#: about.py:10` and `#: settings/options.py:71`, no absolute or backslash path, 353 msgids; running it twice gives identical output apart from `POT-Creation-Date`.
2. `msgfmt --statistics` on the `.po`: 353 translated, 0 untranslated, 0 fuzzy; the four orphans are `#~`. The `.mo` loads with `gettext.GNUTranslations`, has 353 messages plus the header, and translates moved labels (for example `Light`, now referenced from `settings/options.py`).
3. `scripts/tests` all pass on Windows (including the bat test); `client` `discover -s tests` stays `Ran 1143`, `FAILED (failures=1, errors=1, skipped=5)` (the known P2-5 and case-only rename items).
4. After the merge `git status --short` lists only `client2/` and `preprocessing/` as untracked. Fixture sha256 unchanged.
5. Changed files: `scripts/generate-pot.bat`, `scripts/tests/test_generate_pot.py`, `scripts/tests/test_liblouis_build_contract.py`, `.gitignore`, `client/.gitignore`, the three readmes, `client/locales/dotexpress.pot`, `client/locales/zh_TW/LC_MESSAGES/dotexpress.po`, `client/locales/zh_TW/LC_MESSAGES/dotexpress.mo`, the W-3 docs.

## Out of Scope

- The other localization backlog items in review row 4 (Export All summary, error fallbacks, `HTML` labels, import reason messages).
- Root `AGENTS.md` (git-ignored) and historic plans that mention `generate_pot.bat`.
- Paths containing `!` (delayed expansion) or non-ASCII characters in the checkout location.
