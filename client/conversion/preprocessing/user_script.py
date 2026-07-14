from __future__ import annotations

import ast
import os
import tempfile
from pathlib import Path


PREPROCESSING_FILENAME = "preprocessing.py"
DEFAULT_PREPROCESSING_SCRIPT = "def main(input: str) -> str:\n    return input\n"


def preprocessing_script_path(dictionary_dir: Path | str) -> Path:
    return Path(dictionary_dir) / PREPROCESSING_FILENAME


def load_preprocessing_script(path: Path | str) -> str:
    source_path = Path(path)
    try:
        return source_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return DEFAULT_PREPROCESSING_SCRIPT


def validate_preprocessing_script(
    source: str,
    *,
    filename: str = PREPROCESSING_FILENAME,
) -> None:
    tree = ast.parse(source, filename=filename, mode="exec")
    compile(tree, filename, "exec")
    main_definitions = [
        node
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name == "main"
    ]
    if len(main_definitions) != 1 or not isinstance(main_definitions[0], ast.FunctionDef):
        raise ValueError("The script must define exactly one top-level synchronous main function.")
    arguments = main_definitions[0].args
    positional = [*arguments.posonlyargs, *arguments.args]
    if (
        len(positional) != 1
        or arguments.kwonlyargs
        or arguments.vararg is not None
        or arguments.kwarg is not None
    ):
        raise ValueError("main must define exactly one positional parameter and no other parameters.")


def save_preprocessing_script(path: Path | str, source: str) -> None:
    destination = Path(path)
    validate_preprocessing_script(source, filename=str(destination))
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            newline="",
            dir=destination.parent,
            prefix=f".{destination.name}.",
            suffix=".tmp",
            delete=False,
        ) as temporary:
            temporary.write(source)
            temporary_path = Path(temporary.name)
        os.replace(temporary_path, destination)
        temporary_path = None
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


def execute_preprocessing_script(path: Path | str, input_text: str) -> str:
    source_path = Path(path)
    source = load_preprocessing_script(source_path)
    validate_preprocessing_script(source, filename=str(source_path))
    namespace = {
        "__name__": "__dotexpress_preprocessing__",
        "__file__": str(source_path),
    }
    exec(compile(source, str(source_path), "exec"), namespace)
    main = namespace.get("main")
    if not callable(main):
        raise TypeError("main is not callable.")
    output = main(input_text)
    if not isinstance(output, str):
        raise TypeError(f"main must return str, got {type(output).__name__}.")
    return output
