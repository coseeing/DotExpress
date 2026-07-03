# Speech Symbols Dialog Filter — Completion Summary

## Overview

Implemented NVDA-style filtering in `SpeechSymbolsDialog` with virtual list support for handling hundreds to thousands of dictionary entries. Filtering is immediate, case-insensitive, and applies to `Source Text` and `Braille` fields only.

## Commit List

| Commit | Description |
|--------|-------------|
| `963f348` | feat: add virtual dictionary entry filtering |
| `f5a2571` | fix: preserve filtered dictionary selection |
| `49ccb3c` | feat: support filtered dictionary editing |
| `55e8f1b` | test: cover filtered dictionary persistence |
| `a022af0` | feat: translate dictionary filter control |

## Files Changed

```
client/dialog.py                               | 160 ++++---
client/locales/zh_TW/LC_MESSAGES/dotexpress.mo | binary (updated)
client/locales/zh_TW/LC_MESSAGES/dotexpress.po |   4 +
client/tests/test_speech_symbols_dialog.py     | 323 ++++++++++++++
4 files changed, 457 insertions(+), 30 deletions(-)
```

## Test Results

- **44/44 regression tests pass** (speech symbols dialog, dialog validation, dictionary actions, dictionary manager, dictionary import flow)
- **17 new focused tests** covering: filter matching, selection preservation, button states, CRUD flows under filtering, save persistence, duplicate validation

## Acceptance Criteria

All 10 acceptance criteria from the design spec are met:

- Filter input above entries list with "篩選條件：" label
- Immediate list updates as user types
- Filtering only checks Source Text and Braille (not Type)
- Case-insensitive matching via `casefold()`
- Virtual `wx.ListCtrl` with `wx.LC_VIRTUAL` for scalability
- Empty result disables Edit/Delete buttons without showing a message
- Adding matching entry keeps filter and selects new row
- Adding non-matching entry clears filter and selects new row
- Editing and deleting work correctly while filtered
- Save writes full dictionary (`self.entries`), not just filtered rows

## Architecture

- `DictionaryEntryListCtrl`: Virtual list subclass delegating cell text to dialog
- `self.entries`: Full dictionary (source of truth for save)
- `self.filtered_entries`: Currently visible entries after filter
- Entry-based selection tracking using object identity (`is`)
- All CRUD flows: capture from `filtered_entries` → mutate `entries` → reapply filter
