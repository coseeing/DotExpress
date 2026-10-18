"""A real ``no-processing.py`` for tests that convert (F-18b).

Conversion runs the selected script's file whatever it is, No Processing included, so a
request always carries a script path. Tests that do not care which script runs use this one:
it is written once per test run into a temporary folder (removed when the process ends) with
the exact text of No Processing, so the output is the input unchanged.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from text_scripts.manager import ensure_no_processing_script

_DIRECTORY: tempfile.TemporaryDirectory | None = None


def no_processing_script_path() -> Path:
    """The path of a ``no-processing.py`` that holds exactly ``NO_PROCESSING_SCRIPT``."""
    global _DIRECTORY
    if _DIRECTORY is None:
        _DIRECTORY = tempfile.TemporaryDirectory(prefix="dotexpress-no-processing-")
    return ensure_no_processing_script(Path(_DIRECTORY.name))
