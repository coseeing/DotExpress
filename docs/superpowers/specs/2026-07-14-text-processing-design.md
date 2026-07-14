# Custom Python Text Processing Preprocessing Design

## Goal

Add a global **Text Processing** setting to the Translation menu. Users can write unrestricted Python code that defines a `main` function to rewrite source text before any text-to-braille conversion begins.

This feature replaces the non-standard punctuation processing in `conversion/preprocessing/punctuation.py`. Translation and dual view will always use the processed text returned by the user's `main()` as their source.

## Scope

Included:

- Add a **Text Processing** item to the Translation menu and a standalone dialog.
- Persist one global Python script.
- Run the script in the existing background conversion worker for every real conversion entry point.
- Feed the script output into the shared source-preprocessing pipeline.
- Remove punctuation tokenization and its punctuation rules.
- Remove the unused `convert_text_for_output()` API and the `translate_and_wrap_both()` output path used only by the demo and legacy tests, making `convert_text_with_alignment()` the sole conversion-output flow.
- Preserve dictionary replacements that directly output Unicode braille.

Excluded:

- A Python sandbox, capability restrictions, network or file restrictions, or a timeout.
- Multiple scripts, per-document scripts, script profile management, or a script test button.
- Character-level dual-view alignment between the original input and arbitrary processed text.

## User Interface and Persistence

Add a direct **Text Processing** item to the Translation menu after **Dual View** and before **Dictionary Management...**. It opens a standalone, resizable, modeless singleton dialog; choosing the item again raises the existing dialog instead of creating a second instance. The dialog has:

- The fixed title **Text Processing**.
- An initial size of `720 × 440`, matching the existing settings dialog.
- A multiline, monospaced Python editor with a clear accessible name.
- Existing `OK`, `Cancel`, and `Apply` behavior: `Apply` and `OK` save; `Cancel` discards unsaved edits.

The initial script is:

```python
def main(input: str) -> str:
    return input
```

The script is stored as `preprocessing.py` in the existing dictionary directory returned by `get_dictionary_directory()`, alongside dictionary files such as `default.csv`. When the file does not exist, the dialog displays the default identity script; the file is created in UTF-8 only on the first `Apply` or `OK`. Saving uses a same-directory temporary file followed by atomic `os.replace()`, so an interrupted write cannot leave a partial script. This is the only global script and applies to all documents, main-window conversions, and conversions triggered by single or batch exports when no cached braille exists. Exporting existing cached braille retains the current behavior and does not retranslate it.

## Script Contract and Validation

Users may define any helper functions, constants, and imports in the script. The only entry-point contract is a top-level `main`:

- The script must define exactly one top-level synchronous `def main(...)`; nested functions and `async def main(...)` do not satisfy the contract.
- It must define exactly one positional parameter and must not have additional positional parameters, keyword-only parameters, `*args`, or `**kwargs`; the parameter name is unrestricted.
- The `str -> str` annotation is the default template and documented contract, but identical annotation text is not required.
- The actual return value must be a `str`.

On save, the application only parses and compiles the script, then validates through the AST that exactly one top-level `def main(...)` with this exact parameter shape exists. Saving never calls `exec()`, so module-level code cannot run unexpectedly. If validation of a new script fails, the previously valid stored script remains unchanged.

Immediately before execution, the conversion worker reads `preprocessing.py`, so external file changes take effect on the next conversion and neither file I/O nor execution blocks the wxPython UI thread. For each conversion, the application creates a fresh namespace containing `__name__` and `__file__`, executes the script, obtains `main`, and calls `main(raw_text)`. Global state from a previous conversion is not retained. Python capabilities are unrestricted and code runs with the current user's permissions. There is no timeout: an infinite loop keeps that conversion worker running, but does not block the wxPython foreground UI.

## Translation and Dual-View Data Flow

```text
Original source text
  -> main(raw_text)
  -> Processed text
  -> Bopomofo character mapping
  -> Language detection, dictionary rules, and normal braille translation
  -> Braille output and dual view
```

Empty source text retains current behavior: it produces empty output without calling `main()`.

Processed text is what actually reaches the translator, so it is the only source text that dual view can align precisely. Arbitrary Python may use regular expressions, delete, insert, reorder, or generate external content; with only `main(input) -> str`, a character-level mapping back to the original input cannot be made reliably. This design deliberately does not use an unreliable diff-based approximation.

Current main-window conversion, plus single and batch exports when no cached braille exists, use `convert_text_with_alignment()` through `ConversionJobRunner`. `convert_text_for_output()` and its custom `wrap_both` branch have no production callers and exist only as a legacy API/test injection point, so they will be removed. `translate_and_wrap_both()` is still called directly by the `client/main.py` demo and legacy tests, creating a second output path; remove that wrapper and its dedicated lower-level helper as well, and update the demo to use `ConversionRequest` with `convert_text_with_alignment()`. Future callers that need only final text must use `.display_text`; they must not create a second conversion flow.

## Removing Legacy Punctuation Rules While Preserving Dictionary Braille Replacements

Remove `conversion/preprocessing/punctuation.py`, `preprocess_punctuation()`, and the punctuation-token branching in the service. Normal text segments will flow directly into the existing language-aware translation.

`literal_braille.py` also currently provides two punctuation-independent capabilities: `is_unicode_braille()` and `build_literal_translation_result()`. When a dictionary replacement itself contains Unicode braille, these are still needed to pass it directly through as braille output while preserving dual-view alignment. They must be retained, or moved to a more appropriate text-translation module if needed; removing punctuation must not remove this dictionary capability.

## Error Handling

If saving finds a syntax error, a `main` count other than one, or a `main` definition that violates the single-positional-input contract, the dialog stays open, shows the error, and does not save. I/O errors while reading the existing file or performing the atomic save are also shown; the application must not silently substitute the default and overwrite an existing file.

If reading, compiling, or executing the script fails during conversion, `main` is not callable at runtime, or it returns a non-string value, conversion raises `ConversionStageError("text_processing", error)` and fails with **Text processing failed: {error}**. Python-level `SystemExit` and `KeyboardInterrupt` are also normalized to ordinary runtime errors so the worker always delivers a completion callback; unrestricted Python means process-terminating capabilities such as `os._exit()` still cannot be intercepted. Do not expose a full traceback. A failure does not overwrite the existing braille output. Existing translation and ASCII-conversion failures remain separate error categories.

## Testing

- Default content when `preprocessing.py` is absent, reading, UTF-8 saving, and atomic replacement.
- Dialog title, initial size, accessible name, and `OK`/`Cancel`/`Apply` behavior.
- Save-time rejection of syntax errors, missing `main`, and definitions that violate the single-positional-input contract, without overwriting prior settings.
- Normal text rewriting and the use of helper functions and imports during conversion.
- Text-processing failures for runtime exceptions, a non-callable runtime `main`, and non-string returns.
- Main-window conversion, plus single and batch exports when conversion is required, apply the script through the single `convert_text_with_alignment()` pipeline; exports with cached braille do not retranslate.
- Dual view uses processed text.
- Unicode-braille dictionary replacements still work after the punctuation path is removed.
- `convert_text_for_output()`, `translate_and_wrap_both()`, their related wrappers/helpers, and legacy tests specific to them are removed, and the `client/main.py` demo uses the sole pipeline.

## Success Criteria

1. Users can save one global `main` script from the **Text Processing** dialog.
2. Every production conversion, including conversion triggered by export, processes text through `main()` without blocking the foreground UI; exports with cached braille do not retranslate.
3. Dual view consistently shows processed text.
4. Non-standard punctuation rules no longer affect translation.
5. Unicode-braille dictionary replacement behavior remains intact.
6. The codebase no longer contains `convert_text_for_output()` or `translate_and_wrap_both()` as a second conversion entry point.
