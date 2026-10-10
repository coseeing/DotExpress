# F-8b Recovery and U+0000 (second part of F-8) review record

- Date: 2026-10-10. Written in English at the orchestrator's request (HANDOFF section 1 says Traditional Chinese; the fix record may follow either).
- Scope: main checkout `D:\workspace\DotExpress`, branch `fix/f8b-recovery-and-nul`, range `1b19290..HEAD` (4 commits: `aa2fd4f` plan and spec corrections, `348f320` D3-D5 recovery, `af0bac9` D12-D14 U+0000, `233f802` GUI record). Production diff: `client/documents/workspace.py` +82, `client/documents/workspace_service.py` +53/-4, `client/gui.py` +22; tests: `test_document_workspace.py` +244, `test_workspace_service.py` +207, `test_gui_document_flows.py` +164, `test_i18n.py` +40; catalogs `.pot`/`.po`/`.mo`; spec (EN and zh-TW, +17 each), plan (3394 lines), `auto-results.md` and three `auto/` scripts. 17 files, exactly the plan's "Global Constraints" list. `HEAD:client` tree ids of `348f320` (`b61ee7ab...`) and `af0bac9` (`667b2d2c...`) are the plan's; `233f802` keeps `667b2d2c...`.
- Read against: spec `docs/superpowers/specs/2026-10-10-f8-data-safety-cleanup-design.md` (D3-D5, D12-D15, "Corrected after planning (F-8b)" 1-9, Test Plan D-F, behavior table, Risks), the zh-TW spec, plan `docs/superpowers/plans/2026-10-10-f8b-recovery-and-nul.md` (Global Constraints, Spec Corrections 1-13, Review Focus, Expected Counts, Implementation Notes), `auto-results.md`, HANDOFF sections 1-2, `AGENTS.md`, the F-8a review record (format).
- Method: line-by-line reading of the three production diffs plus the surrounding code (`move_document_package`, `PackageFiles`, `_read_package`, `load_workspace_documents`, `batch_import_documents`, `shared/atomic_write.py` naming, `shared/name_validation.py`, `DocumentController`, `ui/message_box.py`, `documents/formats.py`, `BrailleFrame.__init__`/`OnInit` ordering, every caller of `_open_document_by_name`); the four test diffs; the catalog diffs; the full suite on Windows 11; 13 probes (P1-P13) and 10 self-written mutants on a scratch copy of `HEAD:client` (`git archive` plus the git-ignored liblouis runtime and `mathcat/`, under the session scratchpad `f8breview\`); the twelve `D:\dxtest\auto7*-f8b.log` / `auto7*-f8a2-f8b.log` files and the exe hash. No packaged build was launched for this review (the recorded logs cover every F-8b item and the questions left were answerable at the service level). No clipboard access anywhere. Nothing was staged or committed; `client/dictionary/`, `client/workspace/`, `client/config.json` and `client/log/` have the same sha256 before and after (table below). Statements that could not be measured are marked "reasoning".
- This record is written to disk only, not committed.

## Verification (Windows 11 26200, `$PY` = `D:\workspace\DotExpress\client\.venv\Scripts\python.exe`, `$SP` = session scratchpad `f8breview\`)

| Item | Command | Result |
| --- | --- | --- |
| app data | `(find client/dictionary client/workspace client/log -type f; ls client/config.json) \| sort \| xargs sha256sum` before and after | 4 files (`config.json` `508a65ea...`, `dictionary/default.csv` `8f0594e9...`, `log/init.log` `9c153f43...`, `workspace/new.dep` `a2f2a7f1...`) identical; their mtimes (20:02-20:47) predate every command of this review. `config.json`, `init.log` and `new.dep` differ from the F-8a review's hashes: the user's own app wrote them (plan Implementation Notes 1), not the tests |
| full suite (acceptance 1) | `cd client && $PY -B -X utf8 -m unittest discover -s tests` | `Ran 1434 tests`, `FAILED (errors=1, skipped=7)`; the only error is F-W6 `test_dictionary_name_prompt ... test_case_only_rename_still_renames`. 1434 = 1403 + 31 (D 15, E 14, F 2), as the plan's Expected Counts |
| focused modules (scratch copy) | `$PY -B -X utf8 -m unittest tests.test_document_workspace tests.test_workspace_service tests.test_gui_document_flows` | `Ran 341`, `OK (skipped=2)`; the Windows-only D9 ran |
| catalogs | `msgfmt --check --statistics -o $SP/fresh.mo ...dotexpress.po`; `sha256sum` of both `.mo`; `grep -c '^msgid '`; `grep -c '^#, fuzzy'`; `git diff 1b19290..HEAD -- client/locales` | `368 translated messages`, 0 fuzzy, 369 `msgid` lines (368 + header); the freshly compiled `.mo` is byte-identical to the committed one (`540d5a97...`); the `.pot` and `.po` diffs add exactly the four entries (two with `#, python-brace-format`) and refresh `#:` reference lines; `POT-Creation-Date` is `2026-10-10 12:00+0800` in both |
| line endings, indentation, ASCII | `git ls-files --eol`; `git diff --check`; grep of the diff for tabs and non-ASCII | the 7 changed `client/` files are `i/lf w/crlf`; `--check` clean; the 22 added `gui.py` lines are tab-indented; the three production files stay pure ASCII; the non-ASCII in tests is braille cells, CJK msgstr values and `「」`, which those files already held; U+0000 and U+FFFD appear only as `\x00` / `\ufffd` escapes (checked in the diff text) |
| commits | `git log --format='%h %ci %s%n%(trailers)' 1b19290..HEAD` | four commits, each ending `Co-Authored-By: Claude Opus 5.5`; no merge, no push; plan 20:43 -> t1 20:48 -> t2 20:49 -> N-f8b build (exe mtime 20:55) -> GUI logs 20:56-20:59 -> docs 21:01 |
| GUI record audit | the twelve `D:\dxtest\auto7{0,1,2,3,4,5}-f8b.log` and `...-f8a2-f8b.log`; `sha256sum D:\dxtest\N-f8b\DotExpress.exe` | every key line of `auto-results.md` matches its log verbatim (70: the recovery box naming `alpha`, `.tmp left unchanged: True`, the third start recovering `gamma`; 71/72: no box, `.tmp` unchanged; 73: the replacement box naming `alpha` and 2, the full editor text, the package rewritten with U+FFFD on the first switch; 74/75 as recorded); each `auto*-f8b` folder has one log, no re-run; exe `8a07ebd3...`, 48,763,113 bytes, as recorded; the scripts end only processes under their own folder (`dx.kill_under`) and `f8bgui.py:8` states that nothing touches the clipboard (grep confirms) |
| probes P1-P13 | `cd $SP\copy\client && $PY -B -X utf8 $SP\probes.py` (logger isolated with `isolate_file_logs`; writes only under `%TEMP%\f8breview-*`) | section 2.1 |
| self-written mutants (10) | `$PY -B -X utf8 $SP\mutants.py $SP\copy\client $PY` (one edit per mutant, old text exactly once, CRLF kept, restored and byte-compared afterwards) | 6 caught, 4 survived (m1, m3, m13, m15): section 2.2, findings M-1 to M-4 |
| not run | - | item 83 (NVDA, the user's); item 84 (F-8a's VHD item); POSIX-only tests (7 skips); F-W6; the plan's shuffle seeds (the new tests use their own temporary folders and isolate `dotexpress.gui`; reasoning) |

## Conclusion

**Ready after the fix phase.** No Critical. One Important (I-1), which is the user's decision of 2026-10-10 (delete the leftovers recovery does not use) and is designed in section 7; it needs code, tests, spec and plan updates, a new build and GUI re-checks of items 70-72 plus one new item. Eight Minor findings: M-1 to M-5 are cheap and should go in with the fix (four test gaps found by surviving mutants, one of them on a data-loss path, and one zh-TW term); M-6 to M-8 are documentation or optional.

D3 recovers exactly the measured leftovers: the interrupted Rename comes back under its old name, oldest first, the staged twin is left (today) and nothing is ever replaced (`os.rename`, Windows refuses a taken name; D9 pins it). The name rule looks at the disk in any case, the content rule at the loaded and already-recovered documents. D12 replaces U+0000 at every entry of a `Document` into the controller (startup load including recovered packages, Import through every loader, the Delete All reload); the saved record keeps the package as read, so the first save of an opened document writes the replaced text and an unopened one keeps its package byte-identical. D13 shows the warning once per document per session, after the editors hold the full text, and the count follows Rename and Delete. The four strings are translated, brace-format-flagged, and the `.mo` is in sync. The GUI record is consistent with its logs and the build hash.

## 1. Path analysis

### 1.1 D3-D5: recovery

| Path | Result | Basis |
| --- | --- | --- |
| Candidates | regular files matching `^\.(?P<stem>.+)\.(?i:dep)\.[A-Za-z0-9_]+\.tmp$` (`workspace.py:29`): both schemes match (`.alpha.dep.<16 hex>.tmp` from `shared/atomic_write.py:47`, `.alpha.dep.<8 chars>.tmp` from `PackageFiles.temporary_path`); `stem` must be its own normalization and the file must read as a package of `stem` (`_read_package`, `workspace.py:253`); anything else is skipped silently. A stem with a dot (`a.b`) works (P10). A folder named like a candidate is skipped (D test) | `workspace.py:341-369`; D4, D6, D7, "files that are not package leftovers" |
| Order | `(st_mtime_ns, stem.casefold(), stem)`; the moved-aside package keeps the old package's mtime (`os.replace`), the staged one is written after it, so the old name wins. Mutant m16 (directory order) is caught by two tests | `workspace.py:373`; D1, "oldest first", D13 |
| Name rule | `taken` = casefolded stems of every `*.dep` on disk, listed or not, any case (`Path.glob` on Windows is case-insensitive: `alpha.DEP` counts, P4); a recovered name is added | `workspace.py:370-376`; D5; mutant m21 caught |
| Content rule | `(text, braille)` of the listed documents plus the recovered ones; same text with different braille is recovered (P2). The staged twin of an interrupted Rename and the aside file of a completed Rename are skipped | `workspace.py:371-374`; D2, D8, D13; mutant m1 **survives** (M-2) |
| Rename | `os.rename(candidate, <stem>.dep)`; on Windows never replaces (D9: `[WinError 183]`, one `ERROR` line on `dotexpress.gui`, no traceback, the file stays). `os.unlink`, `os.remove`, `Path.unlink`, `os.replace`, `shutil.rmtree` are never called | `workspace.py:378-381`; D8, D9 |
| Service | `load_documents` runs recovery after `load_workspace_documents`, merges the recovered documents in list order, applies D12 to the merged list, records the merged raw documents (so an unchanged save of a recovered document writes nothing, D11), and keeps the names for `take_recovered_document_names` (once). The Delete All reload does not recover (D12 of the service tests) | `workspace_service.py:157-172`; mutant m17 caught |
| Frame | the box comes after the invalid-files dialog and before the first document opens; information icon; names one per line in recovery order | `gui.py:754-768`; D13 of the GUI tests; GUI 70 |
| Interaction with `new (2)` (D2) | a leftover never counts as taken for `free_document_name` (`lexists(<name>.dep)`), and a recovered document makes the default document unnecessary. An interrupted Add of `new` (only `.new.dep.<hex>.tmp`) comes back as `new`; nothing else is created (P5). A kept invalid `new.dep` plus a valid `.new.dep.<hex>.tmp`: the leftover is skipped (name taken) and `new (2)` is created as in F-8a | P5; `gui.py:737-752`; reasoning |
| Interaction with the invalid-files review | recovery runs inside `load_documents`, before `_review_invalid_workspace_files`. A valid leftover whose name is held by an invalid package is skipped; if the user then chooses "Delete Invalid Files", it is recovered at the **next** start, not this one (P7). Not wrong (nothing lost; the box names it then), but it is one of the "later start" cases, see I-1 (class L4) and M-7 | P7 |
| Races with Save and Rename (F-3, F-8a) | recovery runs once, in the constructor, before any save or rename of this process; the only writer in between would be another process. `os.rename` of a target that appeared meanwhile fails and is logged (D9). A leftover currently open for writing by another process cannot be renamed or deleted on Windows (`[Errno 13]`, P12), so an in-progress save or rename of a second instance is never hijacked (reasoning for the rename path; measured for the handle) | D9; P12 |
| Can recovery pick the wrong file or lose text? | No file is removed or replaced. A wrong name is possible only with a clock that moved backwards between the old package's save and the rename (the staged file would then be older and come back under the **new** name, as a completed Rename: P3, observation 8.1). Two documents with identical content: only one name survives (P1, spec Risks "very low"; it is not that rare for **empty** documents, see M-6). The newer text of an interrupted Save is not offered (D3, item 72) | P1, P3; spec D3 |
| Later-start recovery of skipped leftovers | measured in item 70's third start; the user decided on 2026-10-10 that such leftovers must be deleted (I-1, section 7) | `auto-results.md` item 70 |

### 1.2 D12-D14: U+0000

| Entry of a `Document` into the controller | Replaced? | Count | Record (F-5) | Basis |
| --- | --- | --- | --- | --- |
| `load_documents` (startup; packages and recovered packages) | yes, `_displayable_documents` on the merged list | set per name with a count > 0; `_nul_pending` replaced wholesale | the raw documents: the first save of an opened document writes U+FFFD; an unopened one keeps its package byte-identical and its count at the next load (E3-E5, GUI 73) | `workspace_service.py:157-167`; P6 (recovered package with NUL gets its count); mutant m3 (recovered left raw) **survives** (M-1) |
| `import_files` (`.txt`, `.dep`, `.pdf`, `.docx`, `.epub` all through `batch_import_documents`) | yes, before the write | set only after a successful write | the replaced document (what was written) | `workspace_service.py:215-231`; E6; mutant m15 (count recorded on a failed save) **survives** (M-4) |
| Delete All failure reload | yes | counts of names still on disk kept | raw remaining documents | `workspace_service.py:268-276`; E8; mutant m13 (no filtering) **survives** (M-3) |
| `create_document` (Add) | nothing to replace (empty text) | - | - | - |
| `rename_document` | controller text already replaced | moved to the new name | - | `workspace_service.py:249-250`; E7; mutant m20 caught; P9 (a new import under the old name gets its own count) |
| `delete_document`, completed Delete All | - | dropped / cleared | - | `workspace_service.py:258, 278`; E7 |
| `ConversionPresenter` `replace_document` (`ui/conversion_presenter.py:206`) and `ExportCoordinator` | editor text (`_editor_text`), which cannot hold U+0000 (spec Current State); exports read the controller, which holds U+FFFD | - | - | reasoning, spec D14 |
| `prepare_document_for_save` / `_encodable` | unchanged (O7): no path can bring U+0000 to a save | - | - | diff |

- **Count.** `_displayable` adds the text count and the braille count (`workspace.py:82-91`); the message says "{count} in all", which matches the number of U+FFFD the user sees across both editors. Mutant m18 (text only) is caught by five tests. For an imported document the braille is `None`, so only the text counts.
- **Once per document per session.** `take_replaced_character_count` pops (`workspace_service.py:176`; mutant m19 caught by four tests). After Rename the notice names the new name; after Delete the count is gone; a later Import under the same name sets a new one (P9). After a completed Delete All everything is cleared. No stale entry is possible: a count exists only for a listed name, and Add refuses listed names (reasoning).
- **Saved silently, not marked.** The app has no unsaved indicator. A document opened with U+FFFD is written at the next document switch or close without any edit by the user (spec D12, item 73). This is intended; the only visible consequence is that a read-only or locked package holding U+0000 now fails to save when the user switches away or closes, although the user typed nothing. Before F-8b the same package failed in the same way with the cut text, so it is not a regression (observation 8.2).
- **Notice placement.** `gui.py:614-625`, after editors, list, title and dual view (E10 records the editor values at the moment of the box). Callers: `on_open_document` and `_open_adjacent_document` focus the source editor after it; the startup path focuses it in `_load_startup_documents`; the single-file Import shows the notice before the Import Issues dialog (E12); Delete of the open document opens the neighbour and may show its notice.

### 1.3 D15: catalogs

Four msgids, all in `gui.py`, 364 -> 368; `msgmerge`'s fuzzy match of `Documents Recovered` to `Documents` was removed (0 fuzzy); `{name}`, `{count}`, `{mark}` (twice) and `{names}` appear in msgid and msgstr identically; U+FFFD enters through `{mark}` only, the msgids stay ASCII; the `.mo` is byte-identical to a fresh `msgfmt` of the `.po`. See section 4 for the wording.

## 2. Probes and mutants

### 2.1 Probes (`$SP\probes.py`, scratch copy, Python 3.13.15)

| # | Measured | Result |
| --- | --- | --- |
| P1 | listed `new` ("", `None`), aside `.new (2).dep._vw4x6f_.tmp` ("", `None`, 60 s old), staged `.draft.dep.mlw4jang.tmp` ("", `None`) | nothing recovered; both leftovers stay. The empty `new (2)` is skipped by the content rule (M-6) |
| P2 | listed `alpha` ("same", "1"), leftover `beta` ("same", "2") | `beta` recovered: the rule compares the tuple |
| P3 | aside `alpha` newer than staged `gamma` (clock moved back) | `gamma` recovered, `.alpha...tmp` stays: the Rename "completes" (observation 8.1) |
| P4 | `alpha.DEP` (invalid) plus `.alpha.dep.k2j1abcd.tmp` | skipped; `glob("*.dep")` returns `alpha.DEP` |
| P5 | only `.new.dep.0123456789abcdef.tmp` (interrupted Add of the default document), through the service | `new` recovered and reported; `free_document_name("new")` is then `new (2)` (not used, a document exists) |
| P6 | interrupted Rename of a package holding U+0000 (text `a\x00b`, braille `1\x00`), through the service | controller holds `a\ufffdb` / `1\ufffd`, recovered names `['alpha']`, count 2 |
| P7 | invalid `alpha.dep` plus a valid `.alpha.dep.<hex>.tmp`; then `delete_invalid_files`; then a new service | first load: nothing listed, nothing recovered; after the deletion the leftover is still a `.tmp`; the next start recovers `alpha` |
| P8 | Delete All failing on the **second** document (alpha deleted, beta refused) | `completed=False`, controller `['beta', 'zoo']`, counts alpha 0, beta 2, zoo 1: the code filters correctly; the shipped test (failure on the first document) does not distinguish (M-3) |
| P9 | `alpha` (count 1) renamed to `gamma`, then `alpha.txt` with two NUL imported | counts gamma 1, alpha 2, then 0, 0 |
| P10 | `.a.b.dep.k2j1abcd.tmp` holding `a.b` | recovered as `a.b.dep` |
| P11 | a Save `.tmp` with no package (`.alpha.dep.<hex>.tmp` only) | recovered as `alpha` |
| P12 | `os.unlink` and `os.rename` of a leftover another handle holds open for writing (Windows) | both `PermissionError(13)`: the file is left alone |
| P13 | listed `alpha` ("newer alpha"), aside `.alpha...tmp` ("old alpha", 120 s), staged `.gamma...tmp` ("old alpha", 100 s) | `gamma` recovered with the old text; the aside stays (its name is taken, its content differs from the listed `alpha`; after the loop it duplicates the recovered `gamma`): relevant to the classification in section 7 |

### 2.2 Self-written mutants (`$SP\mutants.py`; modules `test_document_workspace`, `test_workspace_service`, `test_gui_document_flows`; unmutated `Ran 341`, `OK (skipped=2)`)

```text
m1  content rule compares text only ........................... OK (skipped=2)   -- survives (M-2)
m3  U+0000 replaced in the loaded documents only, recovered raw  OK (skipped=2)   -- survives (M-1)
m13 Delete All failure keeps every pending count ............... OK (skipped=2)   -- survives (M-3)
m15 import records a count although the save failed ............ OK (skipped=2)   -- survives (M-4)
m16 candidates processed in directory order .................... FAILED (failures=2)  oldest_first, startup_reports_recovered_documents
m17 recovered documents appended, not merged in list order ...... FAILED (failures=1)  load_documents_recovers_and_reports_names_once
m18 _displayable count ignores braille ......................... FAILED (failures=5)
m19 count not popped (notice on every open) .................... FAILED (failures=4)
m20 rename drops the pending count ............................. FAILED (failures=1)
m21 taken built from listed names only ......................... FAILED (failures=1)  name_held_by_an_unlisted_package
```

The plan's 24 mutants (all caught, Implementation Notes) cover the spec's acceptance criterion 8; the four survivors are outside that list.

## 3. Tests, logging, isolation

- `test_document_workspace` and `test_workspace_service` isolate `dotexpress.gui` in `setUpModule` (`isolate_file_logs`); the recovery tests assert `assertNoLogs` except D9 (`assertLogs(..., "ERROR")`, one record, `exc_info` `None`). The logger is bound at call time (`workspace.py:381`), so importing `documents.workspace` adds no file handler; the scratch copy had no `log/` folder after the probes and tests.
- The leftovers in tests are written with `PackageFiles().write` and aged with `os.utime` (`age_s`), as the probe found them; `_raw_leftover` builds member-mismatch archives with `zipfile`.
- The `Mock` service harness sets `take_recovered_document_names.return_value = []` and `take_replaced_character_count.return_value = 0` (`test_gui_document_flows.py:276-279`), as the spec requires.
- E10 patches `gui.message_box` to record the editor values at the moment of the box: it proves the order (editors first), not only the event list.
- `test_recovery_never_deletes_or_replaces_a_file` (`test_document_workspace.py:999`) and `test_startup_ignores_leftover_temporary_files` (`test_gui_document_flows.py:2134`) pin that skipped leftovers stay; both must change under I-1 (section 7.6).
- Red-first: each plan step has a stated reason (missing function, `AttributeError` on the new service methods, missing msgstr), replayed in the dry run; the counts 1403 -> 1419 -> 1434 and the tree ids match.

## 4. Localization

| msgid | msgstr | Reading |
| --- | --- | --- |
| `Characters Replaced` | `已取代字元` | fine as a caption; NVDA reads it first |
| `Some characters in document "{name}" cannot be shown ({count} in all). Each one has been replaced with the replacement character {mark}, so the text after it is kept.\n\nDelete or change these {mark} characters before converting. Otherwise each one appears in the braille as an escape code.` | `文件「{name}」中有 {count} 個無法顯示的字元，已全部以替代字元 {mark} 標示，後面的文字都保留下來了。\n\n轉譯前請刪除或修改這些 {mark}，否則每一個都會在點字中變成一段跳脫碼。` | natural Taiwan usage; placeholders identical. One term is off: the app calls the action **轉換** (`Convert` -> `執行轉換`, `轉換中`, `此文件沒有可顯示的轉換資料`) and reserves **轉譯** for the liblouis tables (`轉譯表`, `預設轉譯表`); "轉譯前" should be "轉換前" (M-5). Optional: Unicode's zh-TW name of U+FFFD is 替換字元; 替代字元 is also understood |
| `Documents Recovered` | `已復原文件` | fine |
| `DotExpress was interrupted while saving or renaming a document. These documents were recovered:\n\n{names}\n\nCheck that their content is what you expect.` | `DotExpress 上次在儲存或重新命名文件時中斷，已復原以下文件：\n\n{names}\n\n請確認內容是否正確。` | natural; the task dialog shows the first sentence as the main instruction and the names plus the last sentence as content (GUI 70) |

- Both long entries carry `#, python-brace-format`; the formatted strings are checked through the compiled `.mo` (F1 and F2).
- The English wording that reaches the user elsewhere is unchanged (import issue text, OS errors), as before.

## 5. Spec, plan, record, process

- Spec D3-D5, D12-D15, "Corrected after planning (F-8b)" 1-9 (EN and zh-TW, 17 lines each), the behavior table rows and Test Plan D-F all have matching code and tests; the counts (D 15, E 14, F 2 as split; 1419, 1434; 368 msgids) are the committed ones. Design per File matches the diff (no other `client/` file changed).
- The plan has an "Implementation Notes" section (F-8a review M-6 asked for it) with the tree ids, the application-data observation and the open question.
- `auto-results.md` lists the GUI items, the build, the scripts, the open question as an observation and item 83 as the user's manual item, unticked.
- Statements that I-1 will invalidate and that must be updated together with it: spec "After this task" bullet 2 ("No temporary file is ever deleted"), Non-goals ("deleting or cleaning up temporary files"), D3 last paragraph and D5 ("Startup never deletes a `.tmp`"), "What Stays Identical" ("Temporary files are never deleted by the app"), Risks "A skipped leftover is recovered at a later start", O3, Open Questions last paragraph, Out of Scope ("cleaning up leftover `.tmp` files (would need the user's consent; not planned)"), "Corrected after planning (F-8b)" 9; the zh-TW twins; plan Spec Corrections 13 and Implementation Notes 3; `auto-results.md` item 70 and "待決問題"; the docstrings of `recover_interrupted_packages` ("never deletes") and of `workspace_service.py` ("it never deletes or replaces a file"); the F-3 comment in `test_startup_ignores_leftover_temporary_files`.
- HANDOFF section 2 constraints: no restricted file touched; fixtures unchanged by the diff (`client/tests/fixtures/` not in the range); `AGENTS.md` not in the diff (git-ignored, reasoning).

## 6. Findings

### Critical

None.

### Important

**I-1 Leftovers that recovery decides not to use stay on disk and come back as extra documents at a later start** (`client/documents/workspace.py:370-385`; `auto-results.md` item 70, third start; spec "Corrected after planning (F-8b)" 9)
- Scenario: Rename `alpha` -> `gamma` crashes between the move aside and the install. The first start recovers `alpha` and leaves `.gamma.dep.mlw4jang.tmp`. The user edits `alpha`. The next start finds `gamma` free and its content unique, recovers it, and shows "已復原文件: gamma" with the old text, possibly weeks after the crash. The same happens with the aside file of a completed Rename once the renamed document is edited (item 71 after an edit), and with a Save leftover once its document is renamed or deleted (item 72).
- User decision (2026-10-10): leftovers that recovery decides not to use must be deleted. Not implemented in this range; the design is in section 7.
- Cheap: moderately. About 25 production lines in one function, 8-10 test changes, spec and plan edits, one rebuild and four GUI runs.

### Minor

**M-1 No test pins that a recovered package holding U+0000 is replaced before it reaches the controller** (`client/documents/workspace_service.py:160-162`; mutant m3 survives: applying `_displayable_documents` to the loaded list and appending the recovered documents raw passes all 341 tests)
- Scenario under the mutant: an interrupted Rename of a document that holds U+0000 is recovered, opened at startup, cut at the first U+0000 by the editor, and written back cut at the first switch: the data loss of item 73 on the recovery path. The shipped code is correct (P6); the test gap is on a data-loss path.
- Suggested fix (cheap): extend `test_load_documents_recovers_and_reports_names_once` or add one service test: aside and staged files with `a\x00b` / `1\x00`; assert the controller holds `a\ufffdb` / `1\ufffd`, `take_replaced_character_count("alpha") == 2`, and the first save with the replaced values writes once.

**M-2 The content rule's tuple comparison is not pinned** (`client/documents/workspace.py:374`; mutant m1, comparing text only, survives)
- Scenario under the mutant: an interrupted Rename of a document whose text equals another listed document's text but whose braille differs (converted vs not converted) is not recovered; the document stays only in the `.tmp` (and, after I-1, must not be deleted: its tuple is unique).
- Suggested fix (cheap): one test like P2 (listed `("same", "1")`, leftover `("same", "2")` -> recovered), or a subTest in `test_documents_are_recovered_oldest_first`.

**M-3 `test_delete_all_failure_reload_keeps_only_pending_counts` fails on the first document, so the filter is never exercised** (`client/tests/test_workspace_service.py:1239-1265`; `workspace_service.py:274-275`; mutant m13 survives)
- Scenario under the mutant: Delete All deletes `alpha` (count 1), fails on `beta`; `alpha`'s stale count stays; a later single-file Import of a clean `alpha.txt` opens it, `_open_document_by_name` pops the stale 1 and shows "Characters Replaced ... 1 in all" for a document without any. Rare, but the test should pin the filter (P8 shows the shipped code is right).
- Suggested fix (cheap): make the injected failure hit `beta.dep` (the second name) and assert counts `[0, 2, 1]` for `alpha`, `beta`, `zoo` with `alpha` gone from the controller.

**M-4 A count recorded for an import whose save failed would not be caught** (`client/documents/workspace_service.py:221-231`; mutant m15 survives)
- Scenario under the mutant: `beta.txt` with U+0000 fails to save (disk full); the count for `beta` stays; the user then adds `beta` and gets "Characters Replaced" for an empty document. The shipped code records the count after the write only.
- Suggested fix (cheap): in `test_import_saves_the_replaced_text_and_counts_it` (or a new test) inject `full_disk` for one file with U+0000 and assert its count is 0 and the others' counts unchanged.

**M-5 "轉譯前" should be "轉換前"** (`client/locales/zh_TW/LC_MESSAGES/dotexpress.po:1351`; `client/tests/test_i18n.py:101, 109`; the spec's rendered box at line 410 of both spec files; plan blocks at 2076, 2084, 2566, 2614, 2760; the plan's and `auto-results.md`'s recorded box texts)
- Scenario: the user reads "轉譯前請刪除..." and looks for a 轉譯 command; the menu says 執行轉換. The rest of the catalog uses 轉譯 only for the tables.
- Suggested fix (cheap): change the msgstr, recompile the `.mo` (`msgfmt --check`, 368 translated, 0 fuzzy), update the two expected strings in `test_i18n.py`, and the rendered box in the spec files; the plan's historical blocks can stay as they were, with one line in the Implementation Notes. Optionally 替代字元 -> 替換字元 (Unicode's zh-TW name); both are understood, so this is a matter of taste. The GUI scripts print the whole box (`f5gui.describe`: title, main instruction, content) and the plan's Task 4 Step 4 blocks are compared line by line, so the expected `content` of items 73-75 changes with the msgstr; the fix's re-run of item 73 (and 74/75 if re-run) must use the new text.

**M-6 Two documents with identical content: the interrupted one loses its name, and after I-1 its file** (`client/documents/workspace.py:374`; P1; spec Risks "very low")
- Scenario: two empty documents (`new`, `new (2)`), or two imports of the same file under different names; a Rename of one is interrupted. The aside file duplicates the other document's `(text, braille)` and is skipped; today it stays on disk, after I-1 it is deleted (class L3). No text is lost; the document and its name are. The content rule cannot tell this case from the aside file of a completed Rename (item 71), which must be skipped.
- Suggested fix: no code. Change the spec's Risk from "very low" to "low (empty documents)", and say in D3 that after I-1 the file is removed. Optional, not cheap: compare content only against documents whose name differs from `stem` *and* whose package is newer than the leftover (the aside of a completed Rename is always older than the installed package; the duplicate document of P1 may be older or newer), which narrows but does not close the gap.

**M-7 Recovery runs before the invalid-files review** (`client/gui.py:755-757`; `workspace_service.py:157-160`; P7)
- Scenario: a valid leftover whose name is held by an invalid package is skipped at this start; the user deletes the invalid package in the dialog; the leftover comes back at the next start with the box. Nothing is lost, but the user sees the name reappear one start later. After I-1 this leftover is class L4 (kept), so the behaviour stays.
- Suggested fix: not cheap (a second service call after the dialog, or a controller merge after the review, plus a GUI order change); leave it and note it in the spec's D3 ("a name freed by deleting an invalid package is recovered at the next start"). If the orchestrator wants it: split `load_documents` into load and `recover_interrupted()` called by the frame after `_review_invalid_workspace_files`, with the same box.

**M-8 The startup boxes are owned by a frame that is not yet shown** (`client/gui.py:754-768`, `614-625`; `BrailleApp.OnInit`: `BrailleFrame(...)` then `Show()`)
- Scenario (accessibility): the recovery box and the first document's replacement box appear before the main window, with no taskbar button for DotExpress. A user who is in another program while the app starts has nothing to Alt+Tab to except the dialog itself (it is a separate top-level window, so it does appear in Alt+Tab; measured only indirectly: GUI 70/73 found it by title and its OK had focus). Same pattern as the existing `InvalidWorkspaceFilesDialog` since F-3, so not new; NVDA reads a modal dialog when it takes the foreground, which item 83 will confirm.
- Suggested fix: optional, not cheap to re-verify: show the startup boxes with `wx.CallAfter` after `Show()`, or show the frame first. Not for F-8b; worth a line in F-12 (UI polish) if item 83 shows a problem.

## 7. User decision: delete the leftovers recovery decides not to use

### 7.1 What exists after a crash, and what "decided not to use" means

Every file in the workspace that matches `_INTERRUPTED_PACKAGE` and is a regular file is one of:

| Class | Condition (evaluated **after** the recovery loop, against the final `taken` and `contents`) | Example | Only copy of user text? | Action |
| --- | --- | --- | --- | --- |
| L0 | not a candidate: name does not match, or not a regular file (folder, symlink), or `stem` is not its own normalization, or the file **is** a readable zip archive but not a package of `stem` (member names differ, non-UTF-8 members, two `.txt`) | `.delta.dep.x.tmp` folder; `. alpha.dep.x.tmp`; `.alpha.dep.x.tmp` holding `beta.txt` | cannot be DotExpress's own file (names are validated and members always match); may be the user's | **untouched** |
| L1 | candidate, `stem` valid, `zipfile.ZipFile` raises `BadZipFile` (empty file from `temporary_path`, or a write interrupted before the central directory) | `.beta.dep.k2j1abcd.tmp` of 0 bytes; a truncated Save file | never: the Save or Rename it belonged to still had the old package, Add writes an empty document, Import has its source file | **delete** |
| L2 | valid package, recovered (renamed to `<stem>.dep`) | item 70's `alpha` | - | used |
| L3 | valid package, not recovered, and its `(text, braille)` equals a listed document's or a recovered one's | the staged twin of an interrupted Rename (70), the aside of a completed Rename (71), a Save file identical to its package, the aside of P13 after `gamma` was recovered | no: the same text and braille are in a package on disk | **delete** |
| L4 | valid package, not recovered because its name is taken, and its content is unique | a Save file with newer text next to its package (72); a valid leftover behind a kept invalid `.dep` (P7); a leftover behind a folder named `<stem>.dep` | **yes** | **keep**, untouched (the user's second instruction: never delete the only copy) |
| L5 | valid package whose `os.rename` failed (D9) | a file created meanwhile | yes | keep, logged (as today); tried again at the next start |

"Decided not to use" therefore means L1 and L3. L4 is the one place where the user's two instructions pull apart: these files are also "not used", but deleting them loses text that exists nowhere else (the newer text of an interrupted Save). The recommendation is to keep L4 and to record it as the residual of the later-start behaviour: an L4 file comes back at a later start only when its own name becomes free (the user renames or deletes that document, or deletes the invalid package), and then the box names it. This residual needs a crash between `fsync` and `os.replace` of a Save followed by a rename or delete of that very document, and nothing is lost. If the user prefers the literal reading (delete L4 too), the only code change is to drop the content test in step 4 below; the spec's D3 sentence "the `.tmp` stays on disk for manual recovery" (Risks) then goes. A third option, recovering an L4 file at once under a free name such as `alpha (2)` and naming it in the box, offers the newer text but needs no new string; it reverses the spec's rejected alternative "offering the newer text of an interrupted Save" and is a user decision, not the orchestrator's default.

Empty documents (M-6) are L3 when another listed document is empty too: deleted. The spec should say so.

### 7.2 Algorithm (`recover_interrupted_packages`, one function, no new public API)

1. Collect candidates as today, but keep the `os.stat` result taken when the file was read, and sort the files that are not packages into `unreadable` (L1, only on `zipfile.BadZipFile`; every other exception, including `NameValidationError` from the stem check and `ValueError`/`UnicodeDecodeError` from `_read_package`, leaves the file in L0).
2. Run the recovery loop as today (`os.rename`, name rule, content rule, oldest first). Files the loop skips go into `unused` with their document; files whose rename failed are logged and go nowhere (L5).
3. After the loop, for each `unused` file: if `(document.text, document.braille) in contents` (the **final** set, which now includes every recovered document) it is L3; otherwise L4, kept. P13 shows why the classification must wait for the loop: the aside `alpha` is skipped first (name taken) and becomes a duplicate only once `gamma` is recovered.
4. Delete L1 and L3 with `_remove_leftover(path, status)`: re-`os.stat` the path; if it is no longer a regular file, or `st_size`/`st_mtime_ns` differ from the values taken when the file was read, do nothing (another process touched it); else `os.unlink(path)`. Any `OSError` (held open, read-only, already gone) is logged once at `WARNING` on `dotexpress.gui` (`Cannot remove unused temporary file %s: %s`, bound at call time as the error above) and the file stays; it is classified again at the next start. Never `os.replace`, never `shutil.rmtree`, never a `.dep` path, never a path that was not in the candidate list of this call, never a symlink (`path.is_symlink()` puts it in L0).
5. The return value stays `list[Document]`; `load_documents`, `take_recovered_document_names` and the box are unchanged. No message mentions the deletions (they are the app's own temporary files); a `DEBUG` line per removed file is optional (the tests' `assertNoLogs` uses `INFO`, so `DEBUG` would not break them).
6. Only startup deletes: the Delete All reload still does not call the function (existing test).

Ordering relative to recovery: deletion is the last step of the same call, after every `os.rename`; a duplicate is deleted only when the package it duplicates is on disk (listed, loaded from disk, or just renamed into place). Failures while deleting never fail startup and never prevent a recovery. Safety against another process: Windows refuses `unlink` of a file open for writing (P12), the re-stat guards against a file rewritten between the read and the delete, and a second DotExpress instance is outside the spec anyway.

Rough size: `workspace.py` +25/-5 (the candidate tuple grows by the stat and the two lists; `_remove_leftover` is ~12 lines); `workspace_service.py` docstring only; `gui.py` unchanged; no new string.

### 7.3 Tests the fix needs

`test_document_workspace.py` (`RecoverInterruptedPackagesTest`):

1. Rework `test_recovery_never_deletes_or_replaces_a_file` into `test_recovery_never_replaces_and_removes_only_unused_leftovers`: same setup; `os.replace`, `shutil.rmtree` still 0 calls; `os.unlink` called exactly for `.gamma.dep.mlw4jang.tmp` (L3) and `.delta.dep.k2j1abcd.tmp` (L1); listing afterwards `[".beta.dep.97dc8315c5cf865f.tmp", "alpha.dep", "beta.dep"]` (the Save leftover with newer text, L4, stays byte-identical).
2. `test_interrupted_rename_is_recovered_under_the_old_name`: the staged twin is gone; `alpha.dep` bytes unchanged.
3. `test_leftover_of_a_completed_rename_is_not_recovered`: the aside is removed, `gamma.dep` unchanged, nothing logged.
4. `test_leftover_save_next_to_its_package_is_not_recovered`: **unchanged** (L4 kept) and its comment says why.
5. `test_invalid_and_empty_temporary_files_are_ignored` -> `..._are_removed`: the truncated, `not a zip` and empty files are gone; nothing else changed.
6. `test_name_held_by_an_unlisted_package_is_not_recovered`: unchanged (L4), with the assertion that the file stays.
7. `test_names_that_are_not_valid_document_names_are_ignored`, `test_member_names_must_match_the_temporary_file_name`, `test_files_that_are_not_package_leftovers_are_ignored`: unchanged (L0): they now also pin that deletion does not reach these files.
8. `test_documents_are_recovered_oldest_first`: the two twins `.zeta...` and `.delta...` are removed; listing `["alpha.dep", "beta.dep"]`.
9. New: `test_a_duplicate_is_removed_only_after_its_twin_is_on_disk` (P13 shape): listed `alpha` newer text, aside `alpha` old text, staged `gamma` old text -> `gamma` recovered, the aside removed (it duplicates `gamma`), `alpha.dep` unchanged.
10. New: `test_removal_failure_is_logged_and_leaves_the_file` (Windows only, `hold_open` from `tests/windows_file_handles.py` with share read only, or a patched `os.unlink` raising `PermissionError` on all platforms): the recovered document is still returned, the file stays, exactly one `WARNING` record `Cannot remove unused temporary file <path>: ...`, no traceback.
11. New: `test_a_leftover_changed_after_it_was_read_is_kept`: patch `os.unlink` to assert it is not called while the file's mtime is bumped between read and delete (patch `os.stat` or rewrite the file from inside a patched `os.rename`).
12. New: `test_recovery_after_a_failed_rename_keeps_the_file` extends D9: the file whose rename failed is not deleted (L5).
13. Mutants to run (plan's `f8b_mutants.py` style): delete before the loop; delete L4; delete on any exception from `_read_package` (an L0 member-mismatch archive must survive); use `os.replace`; skip the re-stat; swallow the `OSError` without logging.

`test_workspace_service.py`:

14. `test_load_documents_recovers_and_reports_names_once`: listing `["alpha.dep", "beta.dep"]`.
15. `test_delete_all_failure_reload_does_not_recover`: unchanged, now also pins that the reload deletes nothing.

`test_gui_document_flows.py`:

16. `test_startup_ignores_leftover_temporary_files` -> `test_startup_removes_unreadable_leftover_temporary_files_without_a_message`: the two `not a zip` files are gone, no box, `good` listed.
17. `test_startup_reports_recovered_documents`: listing `["alpha.dep", "bad.dep", "beta.dep"]` (both staged twins removed; the invalid `bad.dep` untouched).

Also M-1 to M-4 above. Expected counts: +4 or +5 tests (`Ran 1438` or `1439`), `FAILED (errors=1, skipped=7)` plus one more skip if test 10 is Windows-only (it is not, with the patch variant).

### 7.4 Documents to update with the fix

Section 5's list: spec (EN and zh-TW) "After this task" 2, Non-goals, D3 (a new paragraph "Leftovers that are not used", with the class table), D5, the behavior table rows for items 70-72, "What Stays Identical", Risks (replace "A skipped leftover is recovered at a later start" by the L4 residual), O3, Open Questions, Out of Scope, "Corrected after planning (F-8b)" 9 (add "Decided by the user (2026-10-10): L1 and L3 are deleted; L4 kept"); plan Spec Corrections 13 and Implementation Notes; the two docstrings; `auto-results.md` item 70 and the "待決問題" section (resolved).

### 7.5 GUI re-checks (new build `N-f8b2`, new `D:\dxtest\auto*-f8b2` folders, the committed scripts with updated expectations)

| Item | Expected after the fix |
| --- | --- |
| 70 | first start: box naming `alpha`; files `['alpha.dep']` (the staged `gamma` twin is gone); restart: no box; third start after editing `alpha`: **no box**, docs `['alpha']`, files `['alpha.dep']` |
| 71 | no box; files `['gamma.dep']` (the aside removed); restart identical |
| 72 | **unchanged**: no box; `alpha` with the package's text; `.alpha.dep.97dc8315c5cf865f.tmp` byte-identical (L4) |
| 70b (new) | workspace `alpha.dep` plus an empty `.beta.dep.k2j1abcd.tmp`, a `not a zip` `.alpha.dep.0123456789abcdef.tmp` and a `.gamma.dep.x2y3z4w5.tmp` held open by `lock.py` (share read only): no box; the first two are gone; the held one stays and `log\gui.log` has one `WARNING ... Cannot remove unused temporary file`; after `lock.py` ends, the next start removes it |
| 73-75 | not affected by the deletion code; re-run 73 (at least) if M-5 changes the msgstr, since the scripts print the box's full content and the expected block compares it line by line |

Item 83 (NVDA) stays the user's.

## 8. Other observations (no action)

1. **Clock moved backwards** (P3): if the aside file is newer than the staged one, the staged file is recovered first and the Rename completes under the new name; the aside is then L3 and, after I-1, deleted. Only a clock change between the old package's save and the Rename can cause it; the text is intact either way.
2. **Read-only or locked package holding U+0000**: opened at startup, it cannot be switched away from or closed without the F-5 dialog, because the replaced text must be written. Before F-8b the cut text failed in the same way; not a regression. A note for F-12 if the user asks.
3. `path.is_file()` and the explicit `normalize_document_name(stem) != stem` check are both redundant with `_read_package` (a folder or a mismatching stem raises there); harmless, and the plan says so for the stem check.
4. The `.pot` and `.po` reference-line churn (267 and 276 lines) is the refresh of `#:` lines that F-8a's line moves left stale; the substantive change is the four entries.
5. The GUI scripts read the editors with `WM_GETTEXT`, so `\r\n` appears in the recorded values; the packages hold `\n`. Consistent with F-7's records.
6. The review tooling (`$SP\probes.py`, `$SP\mutants.py`, the scratch copy) stays in the scratchpad; no `D:\dxtest` folder was created or changed by this review; no process was started or ended.

## 9. Disposition (fix phase, 2026-10-10)

The fix phase ran on the same branch after this review (commits `41805bc`..`176a1ae`, then this record, committed as "docs: F-8b review record"). `HEAD:client` is `f6bd18c91dd1ccf78ff1c6d248f31df000d7337b`. Full suite `Ran 1444`, `FAILED (errors=1, skipped=7)`, F-W6 only; fixtures and application data unchanged. Details: the plan's "Implementation Notes (fix phase, 2026-10-10)" and `auto-results.md` "審查修正後的重新檢查（N-f8b2）".

| Finding | Disposition | Where |
| --- | --- | --- |
| I-1 leftovers recovery does not use stay and come back later | **fixed** (the user's decision of 2026-10-10), section 7's design: L0 untouched, L1 and L3 deleted after every rename (`os.unlink` of this call's candidates only, re-`lstat` guard, never a `.dep`, a symbolic link or `os.replace`), L2 recovered, L4 kept (Decided by orchestrator with the recommended default; user may override before merge), L5 kept. Deviations: a failed deletion is logged at `ERROR`, not `WARNING`, because `dotexpress.gui` and its `gui.log` handler drop anything below `ERROR` (a warning would never reach `gui.log`); an archive with damaged member data counts as L0 (kept), not L1. 7.3's tests 1-12 and 14-17 are in (test 13's mutants: 14 written, all caught); spec (EN and zh-TW), plan notes and both docstrings updated; GUI 70, 70b (new), 71, 72 re-run on `N-f8b2` as 7.5 expects | `41805bc`, `57466b3`, `176a1ae` |
| M-1 recovered package with U+0000 not pinned | **fixed** (test): `test_recovered_package_with_nul_is_replaced_and_counted`; fails on m3 | `5d4c989` |
| M-2 content rule's tuple comparison not pinned | **fixed** (test): `test_same_text_with_different_braille_is_recovered`; fails on m1 | `f249599` |
| M-3 Delete All failure filter not exercised | **fixed** (test): `test_delete_all_failure_after_a_deletion_drops_the_deleted_count` (the failure hits `beta`; the existing test is kept); fails on m13 | `5368bdb` |
| M-4 count recorded for a failed import save | **fixed** (test): `test_import_whose_save_fails_records_no_count`; fails on m15 | `7a485cf` |
| M-5 "轉譯前" should be "轉換前" | **fixed**: msgstr, `.mo` (368 translated, 0 fuzzy, byte-identical to a fresh `msgfmt`), `test_i18n`, the spec's string table and rendered box (both languages), the GUI scripts' expected box content (`f8bgui.REPLACED_CONTENT`); 73-75 re-run on `N-f8b2`. `替代字元` kept (the usual zh-TW name of U+FFFD); the plan's executed blocks keep the old text, with a note | `f853059`, `57466b3`, `176a1ae` |
| M-6 identical content: the interrupted one loses its name, and now its file | **documented**: spec Risks now "low, empty documents" (was "very low"), D3 says the leftover is deleted (L3) | `57466b3` |
| M-7 recovery runs before the invalid-files review | **documented**: spec D3 and a new Risk ("a name freed in the invalid-files dialog is recovered one start later"); no code change | `57466b3` |
| M-8 startup boxes owned by a frame not yet shown | **deferred** to F-12 (UI polish); no code. Added to manual item 83 (point 3: whether NVDA reads the boxes and Alt+Tab reaches them when the user is in another program at startup) and to the spec's Out of Scope | `176a1ae`, `57466b3` |

Manual item 83 stays unticked for the user (now on `D:\dxtest\N-f8b2\DotExpress.exe`).
