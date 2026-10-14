"""Shared gettext setup and bundled-resource lookup for the DotExpress client.

Consumers import the names they use: ``from i18n import _`` (plus ``N_``,
``resource_path`` and ``html_language_tag`` where needed). ``_`` is a function
of this module that looks up the active catalog at each call, so a catalog made
active later by ``set_language`` reaches every consumer (F-14 D1). Tests that
replace translations patch the consumer's global (for example ``dialog._``);
patching ``i18n._`` does not reach modules that have already imported it.

The interface language is fixed: ``set_language(LOCALE_LANGUAGES[0])`` runs at
import, and only tests call it again (the seam for a future language switch).
It is not the braille conversion language of ``config.py`` (``get_lang``).
"""

import gettext
import sys
from collections.abc import Sequence
from pathlib import Path

LOCALE_DOMAIN = "dotexpress"
LOCALE_LANGUAGES = ("zh_TW",)
# The language of the msgids: what the user sees when no catalog is found.
SOURCE_LANGUAGE = "en"
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


_translation: gettext.NullTranslations = gettext.NullTranslations()
_language = SOURCE_LANGUAGE


def set_language(language: str, *, localedir: Path | None = None) -> None:
    """Make the catalog of ``language`` the active one (F-14 D1).

    The recorded interface language is ``language`` when its catalog was found, else
    ``SOURCE_LANGUAGE``, because the user then sees the msgids.
    """
    global _translation, _language
    translation = load_translation(localedir, (language,))
    _translation = translation
    _language = language if isinstance(translation, gettext.GNUTranslations) else SOURCE_LANGUAGE


def current_language() -> str:
    """The gettext code of the interface language (``zh_TW`` in the app)."""
    return _language


def html_language_tag(language: str | None = None) -> str:
    """The BCP 47 tag of ``language`` (default: the interface language): ``zh_TW`` gives ``zh-TW``."""
    return (current_language() if language is None else language).replace("_", "-")


def _(message: str) -> str:
    """Translate ``message`` with the active catalog; ``""`` stays ``""``, not the catalog header."""
    if not message:
        return message
    return _translation.gettext(message)


def N_(message: str) -> str:
    """Mark a string for extraction without translating it."""
    return message


set_language(LOCALE_LANGUAGES[0])
