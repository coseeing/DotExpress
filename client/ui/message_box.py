"""``wx.MessageBox`` with the application's own button labels (F-7, F-W9).

wx draws the OK button of a message box with a label from its own catalog, which
DotExpress does not load, so ``wx.MessageBox`` shows an English "OK". Yes and No
are Windows' common buttons, which Windows labels in the system language.
"""

from __future__ import annotations

import re

import wx

from i18n import _

# The access key a zh_TW label adds after its text, "(&S)".
_ACCESS_KEY_SUFFIX = re.compile(r"\(&[^)]\)")


def message_box(message: str, caption: str, style: int, parent: wx.Window | None = None) -> int:
    """Show a message box like ``wx.MessageBox``: same arguments and return values.

    Returns ``wx.OK``, ``wx.YES``, ``wx.NO`` or ``wx.CANCEL``. An OK button (and a
    Cancel button next to it) gets the translated label; a Yes/No box keeps the
    system's labels.

    ``style`` goes to ``wx.MessageDialog`` unchanged. Unlike ``wx.MessageBox``, which
    adds ``wx.ICON_INFORMATION`` (``wx.ICON_QUESTION`` with ``wx.YES``) when the style
    has no icon, this adds none: give the icon in ``style``, as every caller does.
    """
    with wx.MessageDialog(parent, message, caption, style) as dialog:
        if not style & wx.YES_NO:
            if style & wx.CANCEL:
                dialog.SetOKCancelLabels(_("OK"), _("Cancel"))
            else:
                dialog.SetOKLabel(_("OK"))
        answer = dialog.ShowModal()
    return {wx.ID_OK: wx.OK, wx.ID_YES: wx.YES, wx.ID_NO: wx.NO}.get(answer, wx.CANCEL)


def confirm_box(
    message: str,
    caption: str,
    ok_label: str,
    cancel_label: str,
    parent: wx.Window | None = None,
) -> bool:
    """Ask before something that changes or loses the user's work; True only for ``ok_label``.

    The system Yes/No warning box, like the other confirmations, with ``ok_label`` on Yes
    and ``cancel_label`` on No; No, the button that keeps the user's work, is the default,
    so Enter answers it. Esc, Alt+F4 and the close button do nothing in this box (F-15).

    The labels must not have an access key, so any "&" is dropped, with a "(&X)" suffix as
    the zh_TW catalog writes one. In the native task dialog Alt+<key> presses the button
    whose access-key character code equals the key's virtual-key code: Alt+F4 presses an
    "s" button, Alt+F10 a "y" one, Alt+Numpad4 a "d" one. Without access keys no Alt+key
    presses a button (F-15 probe, docs/superpowers/history/2026-10-15-01-f15-system-confirm-boxes/).
    F-11's wx generic dialog, which this replaces, answered Esc and Alt+F4 with Cancel.
    """
    with wx.MessageDialog(parent, message, caption, wx.YES_NO | wx.NO_DEFAULT | wx.ICON_WARNING) as dialog:
        dialog.SetYesNoLabels(_without_access_key(ok_label), _without_access_key(cancel_label))
        return dialog.ShowModal() == wx.ID_YES


def _without_access_key(label: str) -> str:
    """``label`` without "&": a "(&X)" access-key suffix goes whole (F-15)."""
    return _ACCESS_KEY_SUFFIX.sub("", label).replace("&", "")
