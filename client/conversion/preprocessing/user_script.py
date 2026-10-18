"""The contract of a text-processing script: check, read, save and run it (F-18).

A script is a Python file with one top-level ``main`` that takes the source text and
returns the text to convert. Scripts run with the full rights of DotExpress; nothing
here limits what they do (F-18 D13).
"""

from __future__ import annotations

import ast
from pathlib import Path

from i18n import N_, _
from shared.atomic_write import write_text_atomically


# The script that changes nothing: its internal name (the stem of its file) and its text
# (F-18 D-D). It is also the template of a new script.
NO_PROCESSING_SCRIPT_NAME = "no-processing"
NO_PROCESSING_SCRIPT = "def main(input: str) -> str:\n    return input\n"
SCRIPT_SUFFIX = ".py"

# The single script of the Text Processing dialog, next to the dictionaries (before F-18).
PREPROCESSING_FILENAME = "preprocessing.py"
DEFAULT_PREPROCESSING_SCRIPT = NO_PROCESSING_SCRIPT


def preprocessing_script_path(dictionary_dir: Path | str) -> Path:
    return Path(dictionary_dir) / PREPROCESSING_FILENAME


def load_preprocessing_script(path: Path | str) -> str:
    source_path = Path(path)
    try:
        return source_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return DEFAULT_PREPROCESSING_SCRIPT


def _is_str_annotation(annotation: ast.expr) -> bool:
    """Whether ``annotation`` is ``str`` or the quoted ``"str"`` (F-18 D5, O2)."""
    if isinstance(annotation, ast.Name):
        return annotation.id == "str"
    return isinstance(annotation, ast.Constant) and isinstance(annotation.value, str) and annotation.value == "str"


def validate_script(source: str, *, filename: str = "<script>") -> None:
    """Check ``source`` without running it (F-18 D-B, D5).

    Raises ``SyntaxError`` if it does not compile, and ``ValueError`` with an untranslated
    msgid if it does not define exactly one top-level synchronous ``main`` with exactly one
    positional parameter, or if an annotation of ``main`` is not ``str``. Annotations are
    optional.
    """
    tree = ast.parse(source, filename=filename, mode="exec")
    compile(tree, filename, "exec")
    main_definitions = [
        node
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name == "main"
    ]
    if len(main_definitions) != 1 or not isinstance(main_definitions[0], ast.FunctionDef):
        raise ValueError(N_("The script must define exactly one top-level synchronous main function."))
    main = main_definitions[0]
    arguments = main.args
    positional = [*arguments.posonlyargs, *arguments.args]
    if (
        len(positional) != 1
        or arguments.kwonlyargs
        or arguments.vararg is not None
        or arguments.kwarg is not None
    ):
        raise ValueError(N_("main must define exactly one positional parameter and no other parameters."))
    if positional[0].annotation is not None and not _is_str_annotation(positional[0].annotation):
        raise ValueError(N_("The parameter of main must be annotated as str, or not annotated."))
    if main.returns is not None and not _is_str_annotation(main.returns):
        raise ValueError(N_("The return value of main must be annotated as str, or not annotated."))


def read_script_source(path: Path | str) -> str:
    """The text of the script at ``path``, UTF-8 with or without a BOM (F-18 D6).

    A missing file raises ``FileNotFoundError`` and a file that is not UTF-8
    ``UnicodeDecodeError``; other ``OSError``s pass through. Line ends are kept.
    """
    return Path(path).read_bytes().decode("utf-8-sig")


def save_script(path: Path | str, source: str) -> None:
    """Validate ``source`` and write it to ``path`` through a synced temporary file (F-8).

    The text is written as is (no newline translation). On an error the script keeps
    its bytes and no temporary file is left.
    """
    destination = Path(path)
    validate_script(source, filename=str(destination))
    destination.parent.mkdir(parents=True, exist_ok=True)
    write_text_atomically(destination, lambda stream: stream.write(source), encoding="utf-8", newline="")


save_preprocessing_script = save_script


def execute_script(path: Path | str, input_text: str) -> str:
    """Read the script at ``path``, check it and return ``main(input_text)`` (F-18 D10)."""
    source_path = Path(path)
    return _run_script(read_script_source(source_path), source_path, input_text)


def _run_script(source: str, source_path: Path, input_text: str) -> str:
    validate_script(source, filename=str(source_path))
    namespace = {
        "__name__": "__dotexpress_preprocessing__",
        "__file__": str(source_path),
    }
    exec(compile(source, str(source_path), "exec"), namespace)
    main = namespace.get("main")
    # Translated when raised, as the second one is formatted (F-12 D8).
    if not callable(main):
        raise TypeError(_("main is not callable."))
    output = main(input_text)
    if not isinstance(output, str):
        raise TypeError(_("main must return str, got {type}.").format(type=type(output).__name__))
    return output
