---
name: dotexpress-text-processing
description: Use when creating, converting, reviewing, or debugging Python scripts intended for DotExpress Text Processing, including punctuation normalization, regex cleanup, newline preservation, and Unicode braille handling.
---

# DotExpress Text Processing

Create a self-contained Python script that predictably rewrites source text before DotExpress translation. Keep transformations small, deterministic, and free of external side effects.

## Required Contract

Define exactly one top-level synchronous `main` function with one positional parameter and no other parameters. Return `str` on every path.

```python
def main(text: str) -> str:
    return text
```

Parameter names and annotations may differ. Helpers, constants, and imports are allowed. Do not add keyword-only parameters, `*args`, or `**kwargs`. Do not depend on global state from an earlier translation: DotExpress loads the script into a fresh namespace for every execution.

## Translation Semantics

Account for the full pipeline:

```text
source -> main(text) -> Bopomofo mapping -> language detection -> dictionaries -> braille translation
```

The processed text becomes the source used for translation and Dual View alignment. Insertions, deletions, and reordering therefore change the displayed and aligned source. Empty source text bypasses the script.

Treat Unicode braille carefully. Ordinary script output still passes through later processing; it is not the same as the dedicated passthrough for a dictionary replacement that consists of Unicode braille. Test inserted braille with the actual translation tables, dictionary, and Dual View.

## Preserve Text Intentionally

Receive and process the complete document, not one line at a time. Preserve `\n`, Windows `\r\n`, tabs, and trailing newlines unless the user explicitly requests normalization.

- Prefer `replace`, targeted `re.sub`, or a character-preserving scan.
- Avoid `splitlines()` followed by `"\n".join(...)` when newline fidelity matters.
- Avoid replacing `r"\s+"` with a space unless removing newlines is intentional.
- Decide explicitly whether context-sensitive punctuation lookup may cross whitespace or line boundaries.

## Avoid Side Effects

DotExpress does not sandbox the script. Do not add wxPython or other GUI code, file selection, source-file mutation, settings or dictionary mutation, network access, subprocesses, user input, long-running work, or unbounded loops. Keep module-level code declarative because it runs whenever the script is loaded.

## Workflow

1. Read the requested behavior and any legacy implementation completely before editing.
2. Extract only pure text-to-text logic; remove GUI, encoding detection, backup, and file I/O layers.
3. Preserve rule ordering, multi-character token precedence, Unicode characters, and boundary behavior.
4. Write or update one self-contained `.py` file with `main(text: str) -> str` using Claude Code's file editing tools.
5. Use Bash to verify representative Chinese, English, punctuation, empty-string, Unicode, and `\n`/`\r\n` cases.

## Verification

At minimum run:

```bash
python3 -m py_compile /path/to/preprocessing.py
```

In a DotExpress checkout, also validate through the real executor from `client/`:

```bash
python3 - <<'PY'
from pathlib import Path
from conversion.preprocessing.user_script import execute_preprocessing_script

path = Path("/path/to/preprocessing.py")
assert isinstance(execute_preprocessing_script(path, "測試 text\r\n第二行"), str)
PY
```

Compare converted legacy logic against the original pure processing functions on representative samples whenever possible. Report exact commands and distinguish script failures from missing optional project dependencies.
