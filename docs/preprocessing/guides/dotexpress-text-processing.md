# DotExpress Text Processing Script Guide

Text Processing runs a Python script before translation. Use it for predictable source-text normalization, such as punctuation conversion, character replacement, or regular-expression cleanup.

## Required Contract

The script must define **exactly one** top-level, synchronous `main` function. It must have exactly one positional parameter and return a `str`:

```python
def main(text: str) -> str:
    return text
```

- You may choose the parameter name and type annotations, but do not add another positional parameter, keyword-only parameter, `*args`, or `**kwargs`.
- You may define helpers, constants, and imports. Each execution uses a fresh namespace, so do not depend on global state from an earlier translation.
- If `main` returns a non-string value or raises an exception, that translation ends with a Text Processing error.

## Data Flow and Scope

```text
Source text -> main(text) -> Bopomofo character mapping -> language detection, dictionaries, braille translation
```

The output of `main` is the text used for actual translation and Dual View alignment. Deleting, inserting, or reordering text changes the displayed and aligned source, so keep rewrite rules small and predictable.

Empty source text remains empty and does not run the script.

## Newlines and Whole-Document Text

`text` contains the complete document text; the script is not called once per line. If you only use `replace`, `re.sub`, or append characters one at a time, both `\n` and Windows `\r\n` remain unchanged.

```python
def main(text: str) -> str:
    return text.replace("\u00a0", " ")
```

Only calling `splitlines()` or `split()`, or reconstructing text with `"\n".join(...)`, can change newline format, remove a trailing newline, or prevent punctuation decisions from crossing lines.

## Recommended Patterns

### Simple replacement

```python
def main(text: str) -> str:
    return text.replace("……", "…")
```

### Regular-expression normalization

```python
import re


def main(text: str) -> str:
    return re.sub(r"[ \t]+", " ", text)
```

Do not replace `r"\s+"` with a space unless you deliberately intend to remove newlines too.

### Context-sensitive punctuation conversion

When scanning the entire string, decide explicitly whether a newline may be crossed. For example, `character.isspace()` treats spaces, tabs, and newlines as whitespace; if you skip them, opening and closing quotation marks can use the next or previous character on another line to determine their context.

## Braille, Dictionaries, and Languages

- Ordinary script output still passes through Bopomofo character mapping, language detection, dictionary rules, and translation tables. Do not assume arbitrary Unicode braille characters bypass later processing.
- A dictionary replacement that is itself Unicode braille has a dedicated DotExpress passthrough. This is distinct from text returned by a Text Processing script.
- If a script inserts Unicode braille or language-switch markers, test it with the actual translation tables, dictionary, and Dual View rather than only testing the Python string.

## Avoid These Practices

The script runs with the current user's permissions and is not sandboxed. It can technically read files, write files, access the network, or start processes, but these actions do not belong in translation preprocessing:

- Do not use wxPython, file pickers, or other GUI code; the script runs in a conversion worker.
- Do not modify source files, settings, or dictionary files. Translation can run repeatedly, making side effects unpredictable.
- Do not make network requests, perform long-running work, loop indefinitely, or wait for input. These prevent that conversion worker from completing.
- Do not perform side effects at module top level. Top-level code runs each time the script is loaded for a translation.

## Pre-Paste Checklist

1. Is `main` a top-level synchronous function with exactly one positional parameter?
2. Does every path return a `str`?
3. Are changes to `\n` and `\r\n` intentional?
4. Does the script avoid I/O, GUI code, network access, and uncontrolled long-running work?
5. Has it been tested with real Chinese, English, punctuation, newlines, dictionary replacements, and Dual View content?

From `client/`, you can first validate a script with the current executor:

```bash
python3 - <<'PY'
from pathlib import Path
from conversion.preprocessing.user_script import execute_preprocessing_script

print(execute_preprocessing_script(Path("/path/to/preprocessing.py"), "Test text\r\nSecond line"))
PY
```

This verifies the script's `main` contract, loading behavior, and return type. Confirm actual braille output in DotExpress as well.
