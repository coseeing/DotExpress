"""``wx.MessageBox`` with the application's own button labels (F-7, F-W9).

wx draws the OK button of a message box with a label from its own catalog, which
DotExpress does not load, so ``wx.MessageBox`` shows an English "OK". Yes and No
are Windows' common buttons, which Windows labels in the system language.
"""

from __future__ import annotations

import wx

from i18n import _


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
    """Ask before something that changes or loses the user's work; True only for the OK button.

    A warning box with the buttons ``ok_label`` and ``cancel_label``; Cancel is the
    default, and Esc, Alt+F4 and the close button answer it too (F-11 D1, D7). A Yes/No
    box would ignore Esc and Alt+F4. It is wx's generic dialog, not the native task
    dialog of ``message_box``: shown from a modal dialog, a task dialog with its own
    button labels answers Alt+F4 with its first button (measured with wx 4.2.5 on
    Windows 11 while planning F-11), here the one that changes the user's work.
    """
    with wx.GenericMessageDialog(parent, message, caption, wx.OK | wx.CANCEL | wx.CANCEL_DEFAULT | wx.ICON_WARNING) as dialog:
        dialog.SetOKCancelLabels(ok_label, cancel_label)
        return dialog.ShowModal() == wx.ID_OK
