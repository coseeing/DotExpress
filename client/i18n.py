"""Shared gettext setup and bundled-resource lookup for the DotExpress client.

Consumers import the names they use: ``from i18n import _`` (plus ``N_`` and
``resource_path`` where needed). Each consumer then holds the same bound
``gettext`` method in its own module global ``_``, so tests that replace
translations patch the consumer's global (for example ``dialog._``).
Patching ``i18n._`` does not reach modules that have already imported it.
"""

import gettext
import sys
from collections.abc import Sequence
from pathlib import Path

LOCALE_DOMAIN = "dotexpress"
LOCALE_LANGUAGES = ("zh_TW",)
CLIENT_ROOT = Path(__file__).resolve().parent


def resource_path(relative_path: str) -> Path:
    """Return a bundled resource path: the PyInstaller bundle when frozen, else the client directory."""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        base_path = Path(sys._MEIPASS)
    else:
        base_path = CLIENT_ROOT
    return base_path / relative_path


def load_translation(
    localedir: Path | None = None,
    languages: Sequence[str] = LOCALE_LANGUAGES,
) -> gettext.NullTranslations:
    """Load the DotExpress catalog; a missing catalog gives a pass-through translation."""
    if localedir is None:
        localedir = resource_path("locales")
    return gettext.translation(
        LOCALE_DOMAIN,
        localedir=str(localedir),
        languages=list(languages),
        fallback=True,
    )


_translation = load_translation()
_ = _translation.gettext


def N_(message: str) -> str:
    """Mark a string for extraction without translating it."""
    return message
