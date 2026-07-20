# External Dual View and Application Data Paths — Completion Record

## Outcome

Implemented the external-browser Dual View flow and unified DotExpress-managed writable data under the application root. Configuration, dictionaries, workspace, logs, and owned dual-view HTML now share the same path contract. Startup validates writability before constructing the translation runtime or main frame; startup/shutdown clean only DotExpress-owned dual-view HTML files. The embedded `DualViewFrame` implementation remains available and tested.

Each plan task was implemented by a dedicated subagent and independently reviewed. Review findings were returned to an implementer and re-reviewed until approved. The final whole-branch review found no functional defects; its sole test-hygiene finding was fixed and re-reviewed.

## Verification

- `cd client && /tmp/dotexpress-task7-venv/bin/python -m unittest discover -s tests -v`
  - 420 tests passed; 7 expected non-Windows skips.
- `msgfmt --check --output-file=client/locales/zh_TW/LC_MESSAGES/dotexpress.mo client/locales/zh_TW/LC_MESSAGES/dotexpress.po`
  - passed.
- `git diff --check 66f71ec..HEAD`
  - passed.

## Commit list

- `66f71ec` docs: plan external dual view paths
- `cbb98f9` refactor: centralize application data paths
- `c89ac03` refactor: unify managed file locations
- `87a1128` fix: use managed dictionary in demo
- `fd4ca47` fix: reject unwritable application data root
- `d50b28b` fix: localize application data startup error
- `6881c7b` feat: manage dual-view html files
- `0232516` feat: launch dual view in external browsers
- `9342291` feat: open dual view in external browser
- `290b5cd` fix: localize dual view browser error
- `b584278` fix: localize application data errors
- Completion-record commit (this commit): `docs: record external dual view implementation completion`
