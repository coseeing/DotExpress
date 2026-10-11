"""Why an imported file was skipped, in words the user can act on (F-12 D3).

Nothing here imports wx or ``dictionaries``. DotExpress's own loaders raise ``ImportProblem``
for a file they refuse; ``describe_import_problem`` gives the reason of each line of the
Import Issues dialog (``{file name}: {reason}``), translated when it is called.
"""

from __future__ import annotations

from i18n import _
from shared.name_validation import NameValidationError

DEP_FORMAT_KEY = "dep"


class ImportProblem(ValueError):
    """A file that DotExpress's own loaders refuse to import.

    ``str()`` is the English text of before F-12 (for logs and ``except ValueError``);
    ``reason`` is the msgid shown to the user, marked with ``N_`` where the error is raised.
    """

    def __init__(self, detail: str, reason: str) -> None:
        super().__init__(detail)
        self.reason = reason


def describe_import_problem(error: Exception, format_key: str) -> str:
    """The reason shown for a file that the loader of ``format_key`` could not import."""
    if isinstance(error, ImportProblem):
        return _(error.reason)
    if isinstance(error, PermissionError):
        # F-6's CANNOT_OPEN text (dictionaries.read_problems), written here too: documents
        # do not depend on dictionaries.
        return _(
            "The file cannot be opened. It may be in use by another program, or you may not have "
            "permission to read it. Close the other program and try again."
        )
    if isinstance(error, NameValidationError):
        # The texts of the document name dialog; an empty name is told by its length.
        if error.code in ("empty", "too_long"):
            return _("Document name must be 1 to 32 characters.")
        return _("Document name is not a valid Windows file name.")
    if format_key.casefold() == DEP_FORMAT_KEY and not isinstance(error, OSError):
        # A damaged archive, a missing member, metadata that is not JSON, text that is not UTF-8.
        return _("Imported file must be a valid DotExpress DEP package.")
    if isinstance(error, UnicodeDecodeError):
        return _("The file is not saved as UTF-8 text. Save it again as UTF-8, for example with Save As in Notepad.")
    return _("The file cannot be read: {error}").format(error=error)
