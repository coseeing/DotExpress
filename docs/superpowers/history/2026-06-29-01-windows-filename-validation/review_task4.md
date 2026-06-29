# Review Task 4

## Review Scope

- Reviewed commits in chronological order:
  - `f975aa5` (`2026-06-29 08:50:37 UTC`) `fix: keep duplicate dictionary dialogs open`
  - `a270837` (`2026-06-29 09:01:53 UTC`) `fix: handle unchanged dictionary rename as no-op`
- References:
  - [Spec](/workspace/DotExpress/docs/superpowers/specs/2026-06-29-windows-filename-validation-design.md)
  - [Plan](/workspace/DotExpress/docs/superpowers/plans/2026-06-29-windows-filename-validation-implementation-plan.md)
  - [Finish Note](/workspace/DotExpress/docs/superpowers/finish_task4.md)
  - [Previous Review](/workspace/DotExpress/docs/superpowers/review_task3.md)

## Findings

### Important

1. The new no-op shortcut also swallows case-only renames, so users can no longer rename `alpha` to `Alpha`.
   - `rename_dictionary_after_name_prompt()` now treats any `casefold()`-equal source/target pair as a no-op ([name_prompt.py](/workspace/DotExpress/client/dictionaries/name_prompt.py:40)).
   - `rename_dictionary_from_dialog()` routes every rename through that helper ([gui.py](/workspace/DotExpress/client/gui.py:1283)).
   - That closes the task3 bug for unchanged names, but it also changes the semantics for case-only renames. Before this patch, `rename_dictionary(directory, "alpha", "Alpha")` actually renamed the file on the current codebase; after this patch, the helper returns the existing `alpha.csv` path without renaming.
   - Reproduction against the current code:

```bash
cd client
python3 - <<'PY'
from pathlib import Path
from tempfile import TemporaryDirectory
from dictionaries.manager import create_dictionary, ensure_default_dictionary
from dictionaries.name_prompt import rename_dictionary_after_name_prompt

with TemporaryDirectory() as td:
    directory = Path(td)
    ensure_default_dictionary(directory)
    create_dictionary(directory, "alpha")
    result = rename_dictionary_after_name_prompt(directory, "alpha", "Alpha")
    print("result", result.name)
    print("files", sorted(path.name for path in directory.glob("*.csv")))
PY
```

Observed result:

```text
result alpha.csv
files ['alpha.csv', 'default.csv']
```

   - Baseline before this helper:

```bash
cd client
python3 - <<'PY'
from pathlib import Path
from tempfile import TemporaryDirectory
from dictionaries.manager import create_dictionary, ensure_default_dictionary, rename_dictionary

with TemporaryDirectory() as td:
    directory = Path(td)
    ensure_default_dictionary(directory)
    create_dictionary(directory, "alpha")
    result = rename_dictionary(directory, "alpha", "Alpha")
    print("result", result.name)
    print("files", sorted(path.name for path in directory.glob("*.csv")))
PY
```

Baseline result:

```text
result Alpha.csv
files ['Alpha.csv', 'default.csv']
```

   - Missing coverage: the new tests cover exact same-name no-op, but there is still no test for case-only rename.

## Closed Finding

- Task3 Important finding is resolved: unchanged rename no longer falls into the duplicate retry loop. The new `test_same_name_rename_is_a_no_op` covers that path, and direct behavior now returns the existing path instead of raising `FileExistsError`.

## Verification

- `cd client && python3 -m unittest tests.test_dictionary_name_prompt tests.test_dictionary_manager tests.test_dialog_validation -v`
- `cd client && python3 -m unittest discover -s tests -v`

Results:

- Focused suite: `22` passed.
- Full client suite: `133` passed, `8` skipped.

## Assessment

- Review status: task3 finding is fixed, but the stack is still not ready to sign off because the new Important case-only rename regression remains.
